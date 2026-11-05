import argparse
import datetime as dt
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

VALID_DATA_TYPES = {"MATRIX", "VECTOR"}
VALID_CROSS_STYLES = {"conservative", "balanced", "aggressive", "ultra-aggressive"}


def _normalize_manual_token(value: str, upper: bool = False) -> str:
    token = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").strip())
    token = re.sub(r"_+", "_", token).strip("_")
    if upper:
        return token.upper()
    return token.lower()


def _build_manual_idea_file_name(dataset_id: str, region: str, delay: int, suffix_seed: int) -> str:
    return f"{dataset_id}_{region}_{delay}_idea_{suffix_seed}.json"


def _parse_manual_templates_json(raw: str) -> list[dict[str, str]]:
    try:
        parsed = json.loads(raw)
    except Exception as exc:
        raise ValueError(f"invalid --manual-templates-json: {exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError("--manual-templates-json must be a JSON array")

    items: list[dict[str, str]] = []
    for row in parsed:
        if not isinstance(row, dict):
            continue
        template = str(row.get("template") or "").strip()
        idea = str(row.get("idea") or "").strip()
        if template:
            items.append({"template": template, "idea": idea})
    return items


def _create_manual_idea_files(
    base_dir: Path,
    dataset_id_raw: str | None,
    region_raw: str | None,
    delay_raw: int | None,
    templates: list[dict[str, str]],
) -> list[str]:
    dataset_id = _normalize_manual_token(dataset_id_raw or "", upper=False)
    region = _normalize_manual_token(region_raw or "", upper=True)

    if not dataset_id or not region or delay_raw is None:
        raise ValueError("请填写 --dataset-id / --region / --delay / --template-text（template 为必填）")
    if not re.search(r"[a-zA-Z]", dataset_id) or not re.search(r"\d", dataset_id):
        raise ValueError("--dataset-id must contain both letters and digits (e.g. fundamental3)")

    delay = int(delay_raw)
    if delay < 0 or delay > 10:
        raise ValueError("--delay 超出范围，需在 0-10 之间")

    if not templates:
        raise ValueError("No manual template content provided")

    out_dir = Path(tempfile.mkdtemp(prefix="enhance_manual_", dir=str((base_dir / "outputs").resolve())))
    paths: list[str] = []
    seed = time.time_ns()
    for idx, item in enumerate(templates, start=1):
        template = str(item.get("template") or "").strip()
        idea = str(item.get("idea") or "").strip()
        if not template:
            continue
        if not re.search(r"\{[^{}]+\}", template):
            raise ValueError(
                f"第 {idx} 组 template 缺少 '{{}}' 字段占位符。"
                "请按前端规则填写，例如 rank(ts_mean({ret}, 20) / ts_stddev({ret}, 20))."
            )
        if not idea:
            print("Warning: idea 为空。前端文案通常建议填写 idea 描述。")
        filename = _build_manual_idea_file_name(dataset_id, region, delay, seed + idx)
        idea_path = out_dir / filename
        idea_path.write_text(
            json.dumps({"template": template, "idea": idea}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        paths.append(str(idea_path.resolve()))

    if not paths:
        raise ValueError("Manual text input produced no valid template payload")
    return paths


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Failed to parse config file: {path}. Error: {exc}") from exc


def _pick(cfg: dict, keys: list[str], default: str | None = None) -> str | None:
    for key in keys:
        value = cfg.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def _load_required_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise ValueError(f"Config file not found: {config_path}")

    cfg = _read_json(config_path)

    brain_email = _pick(cfg, ["brain_email", "email", "brainEmail"])
    brain_password = _pick(cfg, ["brain_password", "password", "brainPassword"])
    moonshot_api_key = _pick(cfg, ["moonshot_api_key", "api_key", "moonshotApiKey"])
    moonshot_base_url = _pick(cfg, ["moonshot_base_url", "base_url", "moonshotBaseUrl"], "https://api.moonshot.cn/v1")
    moonshot_model = _pick(cfg, ["moonshot_model", "model", "moonshotModel"], "kimi-k2.6")

    missing = []
    if not brain_email:
        missing.append("brain_email")
    if not brain_password:
        missing.append("brain_password")
    if not moonshot_api_key:
        missing.append("moonshot_api_key")

    if missing:
        raise ValueError(
            "Missing required config fields: "
            + ", ".join(missing)
            + f". Please edit {config_path} and fill them."
        )

    return {
        "brain_email": brain_email,
        "brain_password": brain_password,
        "moonshot_api_key": moonshot_api_key,
        "moonshot_base_url": moonshot_base_url,
        "moonshot_model": moonshot_model,
    }


def _stream_process(cmd: list[str], cwd: Path, env: dict[str, str], idle_timeout_seconds: int) -> int:
    process = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    assert process.stdout is not None

    line_queue: queue.Queue[str | None] = queue.Queue()

    def _reader() -> None:
        try:
            for line in process.stdout:
                line_queue.put(line)
        finally:
            line_queue.put(None)

    reader_thread = threading.Thread(target=_reader, daemon=True)
    reader_thread.start()

    last_output_at = time.time()

    while True:
        try:
            item = line_queue.get(timeout=1.0)
        except queue.Empty:
            if process.poll() is not None:
                break
            if time.time() - last_output_at > idle_timeout_seconds:
                process.kill()
                raise TimeoutError(
                    f"No output for {idle_timeout_seconds} seconds. Process terminated."
                )
            continue

        if item is None:
            break

        last_output_at = time.time()
        print(item, end="")

    return process.wait()


def _launch_detached_process(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    task_id: str,
    tasks_dir: Path,
    mode: str,
    config_path: Path,
    idea_json: str | None,
    idea_json_list: list[str],
) -> tuple[int, Path]:
    task_dir = (tasks_dir / task_id).resolve()
    task_dir.mkdir(parents=True, exist_ok=True)

    stdout_log = task_dir / "stdout.log"
    stderr_log = task_dir / "stderr.log"
    meta_file = task_dir / "meta.json"

    creationflags = 0
    popen_kwargs: dict = {}
    if os.name == "nt":
        creationflags = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        popen_kwargs["creationflags"] = creationflags
    else:
        popen_kwargs["start_new_session"] = True

    with stdout_log.open("a", encoding="utf-8") as out, stderr_log.open("a", encoding="utf-8") as err:
        process = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=out,
            stderr=err,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            **popen_kwargs,
        )

    meta = {
        "task_id": task_id,
        "pid": process.pid,
        "status": "running",
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": mode,
        "command": cmd,
        "cwd": str(cwd),
        "config": str(config_path),
        "idea_json": idea_json,
        "idea_json_list": idea_json_list,
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
    }
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return process.pid, task_dir


def _is_pid_running(pid: int | None) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _tail_lines(path: Path, max_lines: int) -> list[str]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []
    keep = max(1, int(max_lines))
    return lines[-keep:]


def _print_task_status(tasks_dir: Path, task_id: str, tail_lines: int) -> int:
    task_dir = (tasks_dir / task_id).resolve()
    meta_file = task_dir / "meta.json"
    if not meta_file.exists():
        print(f"ERROR: task not found: {task_id}")
        print(f"Checked: {task_dir}")
        return 2

    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: failed to parse task meta: {meta_file}. {exc}")
        return 2

    pid = meta.get("pid")
    alive = _is_pid_running(pid if isinstance(pid, int) else None)
    state = "running" if alive else "exited"
    stdout_log = Path(meta.get("stdout_log") or (task_dir / "stdout.log"))
    stderr_log = Path(meta.get("stderr_log") or (task_dir / "stderr.log"))

    print("=" * 70)
    print("Detached Task Status")
    print(f"task_id: {meta.get('task_id', task_id)}")
    print(f"pid: {pid}")
    print(f"state: {state}")
    print(f"mode: {meta.get('mode')}")
    print(f"started_at: {meta.get('started_at')}")
    print(f"task_dir: {task_dir}")
    print(f"stdout_log: {stdout_log}")
    print(f"stderr_log: {stderr_log}")
    print("=" * 70)

    stdout_tail = _tail_lines(stdout_log, tail_lines)
    stderr_tail = _tail_lines(stderr_log, tail_lines)

    print(f"--- stdout (last {max(1, int(tail_lines))} lines) ---")
    if stdout_tail:
        for line in stdout_tail:
            print(line)
    else:
        print("<empty>")

    print(f"--- stderr (last {max(1, int(tail_lines))} lines) ---")
    if stderr_tail:
        for line in stderr_tail:
            print(line)
    else:
        print("<empty>")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Headless runner for brain-enhance-template")
    parser.add_argument("--config", default="configs/config.json", help="Config JSON path")
    parser.add_argument("--idea-json", default=None, help="Single idea json path")
    parser.add_argument("--idea-json-list", nargs="*", default=None, help="Cross mode idea json paths")
    parser.add_argument("--template-text", default=None, help="Manual single template text (no file required)")
    parser.add_argument("--idea-text", default=None, help="Manual single idea description (frontend usually treats as required)")
    parser.add_argument("--template-text-2", default=None, help="Second template text for manual cross mode (cross requires >=2 templates)")
    parser.add_argument("--idea-text-2", default=None, help="Second idea description for manual cross mode")
    parser.add_argument("--manual-templates-json", default=None, help="Manual cross templates JSON array: [{\"template\":\"...\",\"idea\":\"...\"}, ...]")
    parser.add_argument("--dataset-id", default=None, help="Required for manual text input; should include letters+digits, e.g. fundamental28")
    parser.add_argument("--region", default=None, help="Required for manual text input, e.g. GLB/USA/CHN")
    parser.add_argument("--delay", type=int, default=None, help="Required for manual text input; integer in [0,10]")
    parser.add_argument("--data-type", default="MATRIX", choices=["MATRIX", "VECTOR"], help="Dataset data type")
    parser.add_argument("--cross-prompt-style", default="balanced", choices=["conservative", "balanced", "aggressive", "ultra-aggressive"], help="Cross enhance style")
    parser.add_argument("--universe", default="TOP3000", help="Universe for fetch_dataset when needed")
    parser.add_argument("--instrument-type", default="EQUITY", help="Instrument type for fetch_dataset when needed")
    parser.add_argument("--feature-implementation-dir", default=None, help="Path to brain-feature-implementation directory")
    parser.add_argument("--template-enhance-dir", default=None, help="Path to template_final_enhance docs directory")
    parser.add_argument("--moonshot-model", default=None, help="Override Moonshot model")
    parser.add_argument("--idle-timeout-seconds", type=int, default=180, help="Kill child process if no output for N seconds")
    parser.add_argument("--detached", action="store_true", help="Launch enhance process in background and return immediately")
    parser.add_argument("--task-id", default=None, help="Optional task id for detached run")
    parser.add_argument("--tasks-dir", default="outputs/tasks", help="Task directory root for detached mode")
    parser.add_argument("--status", default=None, help="Show detached task status by task id and exit")
    parser.add_argument("--tail-lines", type=int, default=40, help="Tail lines for --status output")
    parser.add_argument("--dry-run", action="store_true", help="Print resolved settings without execution")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir.parent

    tasks_dir = Path(args.tasks_dir)
    if not tasks_dir.is_absolute():
        tasks_dir = (base_dir / tasks_dir).resolve()
    else:
        tasks_dir = tasks_dir.resolve()

    if args.status and str(args.status).strip():
        return _print_task_status(tasks_dir=tasks_dir, task_id=str(args.status).strip(), tail_lines=args.tail_lines)

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = (base_dir / config_path).resolve()
    else:
        config_path = config_path.resolve()

    try:
        cfg = _load_required_config(config_path)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    default_local_feature_impl = (base_dir / "brain-feature-implementation").resolve()
    default_fallback_feature_impl = (base_dir.parent / "brain-feature-implementation").resolve()
    feature_impl_dir = (
        Path(args.feature_implementation_dir).expanduser().resolve()
        if args.feature_implementation_dir
        else (default_local_feature_impl if default_local_feature_impl.exists() else default_fallback_feature_impl)
    )
    template_enhance_dir = (
        Path(args.template_enhance_dir).expanduser().resolve()
        if args.template_enhance_dir
        else (base_dir / "knowledge" / "template_final_enhance").resolve()
    )

    if not feature_impl_dir.exists():
        print(f"ERROR: feature implementation dir not found: {feature_impl_dir}")
        return 2
    if not (feature_impl_dir / "scripts").exists():
        print(f"ERROR: scripts dir not found under feature implementation dir: {feature_impl_dir / 'scripts'}")
        return 2
    if not template_enhance_dir.exists():
        print(f"ERROR: template enhance docs dir not found: {template_enhance_dir}")
        return 2

    data_type = (args.data_type or "MATRIX").strip().upper()
    if data_type not in VALID_DATA_TYPES:
        print(f"ERROR: invalid data type: {data_type}")
        return 2

    cross_style = (args.cross_prompt_style or "balanced").strip().lower()
    if cross_style not in VALID_CROSS_STYLES:
        print(f"ERROR: invalid cross prompt style: {cross_style}")
        return 2

    text_mode_requested = any(
        [
            bool((args.template_text or "").strip()),
            bool((args.template_text_2 or "").strip()),
            bool((args.manual_templates_json or "").strip()),
        ]
    )
    file_mode_requested = bool(args.idea_json) or bool(args.idea_json_list)
    if text_mode_requested and file_mode_requested:
        print("ERROR: Do not mix file input (--idea-json/--idea-json-list) with text input flags.")
        return 2

    idea_json_list: list[str] = []
    idea_json: str | None = None

    if text_mode_requested:
        templates: list[dict[str, str]] = []
        manual_templates_json_raw = (args.manual_templates_json or "").strip()
        if manual_templates_json_raw:
            try:
                templates.extend(_parse_manual_templates_json(manual_templates_json_raw))
            except ValueError as exc:
                print(f"ERROR: {exc}")
                return 2

        t1 = str(args.template_text or "").strip()
        i1 = str(args.idea_text or "").strip()
        t2 = str(args.template_text_2 or "").strip()
        i2 = str(args.idea_text_2 or "").strip()

        if t1 and not manual_templates_json_raw:
            templates.append({"template": t1, "idea": i1})
        if t2:
            templates.append({"template": t2, "idea": i2})

        try:
            manual_paths = _create_manual_idea_files(
                base_dir=base_dir,
                dataset_id_raw=args.dataset_id,
                region_raw=args.region,
                delay_raw=args.delay,
                templates=templates,
            )
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 2

        if len(manual_paths) >= 2:
            idea_json_list = manual_paths
            idea_json = None
        else:
            idea_json = manual_paths[0]
            idea_json_list = []

        print(f"Manual text input prepared {len(manual_paths)} idea file(s):")
        for path_str in manual_paths:
            print(f"  - {path_str}")
    else:
        idea_json_list = [str(Path(p).expanduser().resolve()) for p in (args.idea_json_list or []) if str(p).strip()]
        idea_json = str(Path(args.idea_json).expanduser().resolve()) if args.idea_json else None

    for path_str in idea_json_list:
        if not Path(path_str).exists():
            print(f"ERROR: idea json not found: {path_str}")
            return 2
    if idea_json and not Path(idea_json).exists():
        print(f"ERROR: idea json not found: {idea_json}")
        return 2

    if not idea_json and not idea_json_list:
        print("ERROR: No input provided. Use file input (--idea-json/--idea-json-list) or text input (--template-text/--manual-templates-json).")
        return 2

    env = os.environ.copy()
    env["BRAIN_EMAIL"] = cfg["brain_email"]
    env["BRAIN_USERNAME"] = cfg["brain_email"]
    env["BRAIN_PASSWORD"] = cfg["brain_password"]
    env["MOONSHOT_API_KEY"] = cfg["moonshot_api_key"]
    env["MOONSHOT_BASE_URL"] = cfg["moonshot_base_url"]
    env["MOONSHOT_MODEL"] = args.moonshot_model.strip() if args.moonshot_model else cfg["moonshot_model"]

    env["DATA_TYPE"] = data_type
    env["CROSS_PROMPT_STYLE"] = cross_style
    env["UNIVERSE"] = str(args.universe).strip()
    env["INSTRUMENT_TYPE"] = str(args.instrument_type).strip()
    env["FEATURE_IMPLEMENTATION_DIR"] = str(feature_impl_dir)
    env["TEMPLATE_ENHANCE_DIR"] = str(template_enhance_dir)

    if idea_json_list:
        env["IDEA_JSON_LIST"] = json.dumps(idea_json_list, ensure_ascii=False)
        env.pop("IDEA_JSON", None)
    elif idea_json:
        env["IDEA_JSON"] = idea_json
        env.pop("IDEA_JSON_LIST", None)

    enhance_script = script_dir / "enhance_template.py"
    if not enhance_script.exists():
        print(f"ERROR: enhance script not found: {enhance_script}")
        return 2

    cmd = [sys.executable, str(enhance_script)]
    run_mode = "cross" if idea_json_list else "single"
    task_id = args.task_id.strip() if args.task_id and args.task_id.strip() else f"enhance_{int(time.time())}_{uuid.uuid4().hex[:6]}"

    print("=" * 70)
    print("Headless Enhance Runner")
    print(f"Config: {config_path}")
    print(f"Enhance script: {enhance_script}")
    print(f"Feature implementation dir: {feature_impl_dir}")
    print(f"Template docs dir: {template_enhance_dir}")
    print(f"Data type: {data_type}")
    print(f"Cross style: {cross_style}")
    print(f"Mode: {run_mode}")
    print(f"Command: {' '.join(cmd)}")
    if args.detached:
        print(f"Detached task id: {task_id}")
        print(f"Tasks dir: {tasks_dir}")
    print("=" * 70)

    if args.dry_run:
        print("Dry-run completed. No process executed.")
        return 0

    if args.detached:
        try:
            pid, task_dir = _launch_detached_process(
                cmd=cmd,
                cwd=script_dir,
                env=env,
                task_id=task_id,
                tasks_dir=tasks_dir,
                mode=run_mode,
                config_path=config_path,
                idea_json=idea_json,
                idea_json_list=idea_json_list,
            )
        except Exception as exc:
            print(f"ERROR: failed to launch detached process: {exc}")
            return 2

        print("Detached task launched.")
        print(f"task_id={task_id}")
        print(f"pid={pid}")
        print(f"task_dir={task_dir}")
        print(f"stdout_log={task_dir / 'stdout.log'}")
        print(f"stderr_log={task_dir / 'stderr.log'}")
        return 0

    try:
        return_code = _stream_process(
            cmd=cmd,
            cwd=script_dir,
            env=env,
            idle_timeout_seconds=max(30, int(args.idle_timeout_seconds)),
        )
    except TimeoutError as exc:
        print(f"ERROR: {exc}")
        print("Hint: check output artifacts before declaring failure.")
        return 124
    except KeyboardInterrupt:
        print("Interrupted by user.")
        return 130

    if return_code != 0:
        print(f"ERROR: child process exited with code {return_code}")
        return return_code

    print("Enhance flow finished successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
