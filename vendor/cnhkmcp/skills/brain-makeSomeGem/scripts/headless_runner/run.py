import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
import traceback
import uuid
from pathlib import Path

import pandas as pd
import requests


def _is_pid_running(pid: int | None) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        try:
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            output = (proc.stdout or "") + "\n" + (proc.stderr or "")
            return str(pid) in output and "No tasks are running" not in output
        except Exception:
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
        return 1

    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: failed to parse task meta: {meta_file}. {exc}")
        return 1

    pid = meta.get("pid")
    try:
        alive = _is_pid_running(pid if isinstance(pid, int) else None)
    except Exception as exc:
        print(f"WARN: failed to check pid state ({exc}); fallback to artifact status only")
        alive = False
    state = "running" if alive else "exited"
    stdout_log = Path(meta.get("stdout_log") or (task_dir / "stdout.log"))
    stderr_log = Path(meta.get("stderr_log") or (task_dir / "stderr.log"))

    print("=" * 70)
    print("Detached Task Status")
    print(f"task_id: {meta.get('task_id', task_id)}")
    print(f"pid: {pid}")
    print(f"state: {state}")
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


def _build_detached_child_cmd(script_path: Path, raw_argv: list[str]) -> list[str]:
    value_flags = {"--task-id", "--tasks-dir", "--status", "--tail-lines"}
    bool_flags = {"--detached"}
    filtered: list[str] = []
    i = 0
    while i < len(raw_argv):
        token = str(raw_argv[i])
        if token in bool_flags:
            i += 1
            continue
        if token in value_flags:
            i += 2
            continue
        filtered.append(token)
        i += 1
    return [sys.executable, str(script_path)] + filtered


def _launch_detached(cmd: list[str], cwd: Path, task_id: str, tasks_dir: Path, mode: str) -> tuple[int, Path]:
    task_dir = (tasks_dir / task_id).resolve()
    task_dir.mkdir(parents=True, exist_ok=True)

    stdout_log = task_dir / "stdout.log"
    stderr_log = task_dir / "stderr.log"
    meta_file = task_dir / "meta.json"

    popen_kwargs: dict = {}
    if os.name == "nt":
        popen_kwargs["creationflags"] = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
    else:
        popen_kwargs["start_new_session"] = True

    with stdout_log.open("a", encoding="utf-8") as out, stderr_log.open("a", encoding="utf-8") as err:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
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
        "pid": proc.pid,
        "status": "running",
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": mode,
        "command": cmd,
        "cwd": str(cwd),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
    }
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return proc.pid, task_dir


def _load_required_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise ValueError(f"Config file not found: {config_path}")

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Failed to parse config file: {config_path}. Error: {exc}")

    required_keys = [
        "brain_email",
        "brain_password",
        "moonshot_base_url",
        "moonshot_model",
        "moonshot_api_key",
    ]

    missing = []
    for key in required_keys:
        value = data.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(key)

    if missing:
        raise ValueError(
            "Missing required config fields: "
            + ", ".join(missing)
            + f". Please edit {config_path} and fill them."
        )

    return data

def _env_auth_ok() -> tuple[bool, str]:
    user = os.environ.get("BRAIN_USERNAME") or os.environ.get("BRAIN_EMAIL")
    pwd = os.environ.get("BRAIN_PASSWORD")
    if not user:
        return False, "Missing BRAIN_USERNAME or BRAIN_EMAIL"
    if not pwd:
        return False, "Missing BRAIN_PASSWORD"
    return True, "ok"


def _moonshot_ok(ideas_file: str | None) -> tuple[bool, str]:
    if ideas_file:
        return True, "ok"
    if not os.environ.get("MOONSHOT_API_KEY"):
        return False, "Missing MOONSHOT_API_KEY (required when ideas_file is null)"
    return True, "ok"


def _build_datafields_df(
    session,
    instrument_type: str,
    region: str,
    delay: int,
    universe: str,
    dataset_id: str | None,
    data_type: str | None = None,
):
    def _get_json(url: str, retries: int = 8, sleep_seconds: float = 2.0):
        for attempt in range(retries):
            resp = session.get(url)
            if resp.status_code == 429:
                if attempt == retries - 1:
                    resp.raise_for_status()
                wait_s = sleep_seconds * (attempt + 1)
                print(f"[rate-limit] 429 for {url} ; sleep {wait_s:.1f}s and retry...", flush=True)
                time.sleep(wait_s)
                continue
            resp.raise_for_status()
            return resp.json() if resp.headers.get("content-type", "").lower().find("json") >= 0 else {}
        return {}

    base = (
        "https://api.worldquantbrain.com/data-fields"
        f"?instrumentType={instrument_type}&region={region}&delay={delay}&universe={universe}"
    )
    if dataset_id:
        base += f"&dataset.id={dataset_id}"

    payload = _get_json(base + "&limit=50&offset=0")
    total = int(payload.get("count", 0)) if isinstance(payload, dict) else 0
    results = list(payload.get("results", [])) if isinstance(payload, dict) else []

    for offset in range(50, total, 50):
        p = _get_json(base + f"&limit=50&offset={offset}")
        if isinstance(p, dict):
            results.extend(p.get("results", []))

    df = pd.DataFrame(results)

    before_count = len(df)
    before_types = {}
    if not df.empty and "type" in df.columns:
        before_types = df["type"].astype(str).str.upper().value_counts(dropna=False).to_dict()

    if data_type and not df.empty and "type" in df.columns:
        wanted = str(data_type).upper()
        df = df[df["type"].astype(str).str.upper() == wanted].reset_index(drop=True)
        after_types = df["type"].astype(str).str.upper().value_counts(dropna=False).to_dict() if not df.empty else {}
        print(
            f"[datafields] filter data_type={wanted} rows {before_count} -> {len(df)} "
            f"types_before={before_types} types_after={after_types}",
            flush=True,
        )
        if not df.empty and set(after_types.keys()) - {wanted}:
            raise RuntimeError(f"Data type filter mismatch: wanted={wanted}, got={after_types}")
    else:
        if data_type:
            print(
                f"[datafields] warning: data_type={data_type} requested but 'type' column unavailable or empty result",
                flush=True,
            )
        else:
            print(f"[datafields] no data_type filter, rows={before_count} types={before_types}", flush=True)

    return df


def build_command(python_exe: str, pipeline_script: Path, args: argparse.Namespace) -> list[str]:
    cmd = [
        python_exe,
        str(pipeline_script),
        "--data-category",
        str(args.data_category),
        "--region",
        str(args.region),
        "--delay",
        str(int(args.delay)),
        "--dataset-id",
        str(args.dataset_id),
        "--universe",
        str(args.universe),
        "--instrument-type",
        str(args.instrument_type),
        "--data-type",
        str(args.data_type),
        "--moonshot-model",
        str(args.moonshot_model),
    ]

    ideas_file = args.ideas_file
    if ideas_file:
        cmd.extend(["--ideas-file", str(ideas_file)])

    if bool(args.regen_ideas):
        cmd.append("--regen-ideas")

    max_fields = args.max_fields
    if max_fields is not None:
        cmd.extend(["--max-fields", str(int(max_fields))])

    if bool(args.no_operators_in_prompt):
        cmd.append("--no-operators-in-prompt")

    max_ops = args.max_operators
    if max_ops is not None:
        cmd.extend(["--max-operators", str(int(max_ops))])

    return cmd


def main() -> int:
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--status", default=None)
    pre_parser.add_argument("--tasks-dir", default="../outputs/tasks")
    pre_parser.add_argument("--tail-lines", type=int, default=40)
    pre_args, _ = pre_parser.parse_known_args()

    here = Path(__file__).resolve().parent
    pre_tasks_dir = Path(pre_args.tasks_dir)
    if not pre_tasks_dir.is_absolute():
        pre_tasks_dir = (here / pre_tasks_dir).resolve()
    else:
        pre_tasks_dir = pre_tasks_dir.resolve()

    if pre_args.status and str(pre_args.status).strip():
        return _print_task_status(
            tasks_dir=pre_tasks_dir,
            task_id=str(pre_args.status).strip(),
            tail_lines=pre_args.tail_lines,
        )

    parser = argparse.ArgumentParser(description="Headless launcher for direct alpha pipeline")
    parser.add_argument("--config", default="config.json", help="Path to config JSON (default: config.json)")
    parser.add_argument("--data-category", required=True, help="Dataset category, e.g. analyst")
    parser.add_argument("--region", required=True, help="Region, e.g. EUR")
    parser.add_argument("--delay", required=True, type=int, help="Delay, e.g. 1")
    parser.add_argument("--dataset-id", required=True, help="Dataset id, e.g. analyst4")
    parser.add_argument("--universe", default="TOP3000", help="Universe (default: TOP3000)")
    parser.add_argument("--instrument-type", default="EQUITY", help="Instrument type (default: EQUITY)")
    parser.add_argument("--data-type", default="MATRIX", choices=["MATRIX", "VECTOR"], help="Data type (default: MATRIX)")
    parser.add_argument("--moonshot-model", default=None, help="Moonshot model (default from config)")
    parser.add_argument("--ideas-file", default=None, help="Optional ideas markdown path")
    parser.add_argument("--regen-ideas", action="store_true", help="Force regenerate ideas markdown")
    parser.add_argument("--max-fields", type=int, default=None, help="Optional max fields passed to LLM")
    parser.add_argument("--max-operators", type=int, default=None, help="Optional max operators passed to LLM")
    parser.add_argument("--no-operators-in-prompt", action="store_true", help="Disable operators in prompt")
    parser.add_argument("--moonshot-base-url", default=None, help="Optional Moonshot base url")
    parser.add_argument("--moonshot-retries", type=int, default=None, help="Optional Moonshot retries")
    parser.add_argument("--moonshot-retry-backoff", type=float, default=None, help="Optional Moonshot retry backoff")
    parser.add_argument("--detached", action="store_true", help="Launch this run in background and return immediately")
    parser.add_argument("--task-id", default=None, help="Optional task id for detached mode")
    parser.add_argument("--tasks-dir", default="../outputs/tasks", help="Task directory root for detached mode")
    parser.add_argument("--status", default=None, help="Show detached task status by task id and exit")
    parser.add_argument("--tail-lines", type=int, default=40, help="Tail lines for --status output")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print command without executing")
    args = parser.parse_args()

    base_dir = here.parent
    tasks_dir = Path(args.tasks_dir)
    if not tasks_dir.is_absolute():
        tasks_dir = (here / tasks_dir).resolve()
    else:
        tasks_dir = tasks_dir.resolve()

    if args.detached:
        task_id = args.task_id.strip() if args.task_id and args.task_id.strip() else f"gem_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        child_cmd = _build_detached_child_cmd(Path(__file__).resolve(), sys.argv[1:])
        mode = f"{args.region}_{args.dataset_id}_delay{args.delay}"
        try:
            pid, task_dir = _launch_detached(cmd=child_cmd, cwd=here, task_id=task_id, tasks_dir=tasks_dir, mode=mode)
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

    pipeline_script = base_dir / "trailSomeAlphas" / "run_pipeline.py"
    pipeline_cwd = base_dir / "trailSomeAlphas"

    if not pipeline_script.exists():
        print(f"ERROR: Pipeline script not found: {pipeline_script}")
        return 2

    config_path = Path(args.config).resolve() if Path(args.config).is_absolute() else (here / args.config).resolve()
    try:
        cfg = _load_required_config(config_path)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    # Inject required runtime settings from config
    os.environ["BRAIN_EMAIL"] = str(cfg["brain_email"]).strip()
    os.environ["BRAIN_PASSWORD"] = str(cfg["brain_password"]).strip()
    os.environ["MOONSHOT_API_KEY"] = str(cfg["moonshot_api_key"]).strip()
    os.environ["MOONSHOT_BASE_URL"] = str(cfg["moonshot_base_url"]).strip()

    # CLI model takes priority; otherwise use config model
    if args.moonshot_model is None:
        args.moonshot_model = str(cfg["moonshot_model"]).strip()

    auth_ok, auth_msg = _env_auth_ok()
    if not auth_ok:
        print(f"ERROR: {auth_msg}")
        return 2

    moon_ok, moon_msg = _moonshot_ok(args.ideas_file)
    if not moon_ok:
        print(f"ERROR: {moon_msg}")
        return 2

    env = os.environ.copy()
    if args.moonshot_base_url:
        env["MOONSHOT_BASE_URL"] = str(args.moonshot_base_url)
    if args.moonshot_retries is not None:
        env["MOONSHOT_RETRIES"] = str(int(args.moonshot_retries))
    if args.moonshot_retry_backoff is not None:
        env["MOONSHOT_RETRY_BACKOFF"] = str(float(args.moonshot_retry_backoff))

    print("=" * 70)
    print("Headless Direct Alpha Runner")
    print(f"Config: {config_path}")
    print(f"Pipeline: {pipeline_script}")
    print(f"Workdir: {pipeline_cwd}")
    print("Command:")
    print(" ".join(build_command(sys.executable, pipeline_script, args)))
    print("=" * 70)

    if args.dry_run:
        print("Dry-run completed. No process executed.")
        return 0

    try:
        os.chdir(str(pipeline_cwd))
        sys.path.insert(0, str(pipeline_cwd))

        import run_pipeline as rp  # type: ignore

        original_expand = rp.ace_lib.expand_dict_columns

        def _safe_expand_dict_columns(data):
            try:
                if data is None or getattr(data, "empty", False):
                    return data
                if len(getattr(data, "columns", [])) == 0:
                    return data
                first_row = data.iloc[0]
                dict_columns = [col for col in data.columns if isinstance(first_row.get(col), dict)]
                if not dict_columns:
                    return data
            except Exception:
                return data
            return original_expand(data)

        rp.ace_lib.expand_dict_columns = _safe_expand_dict_columns

        session_holder = {"session": None}

        original_start_session = rp.start_brain_session

        def _patched_start_session(email: str, password: str):
            s = original_start_session(email, password)
            session_holder["session"] = s
            return s

        rp.start_brain_session = _patched_start_session

        original_get_datafields = rp.ace_lib.get_datafields

        def _patched_get_datafields(session, instrument_type="EQUITY", region="USA", delay=1, universe="TOP3000", search="", dataset_id=None, data_type=None, **kwargs):
            print(
                f"[patched_get_datafields] instrument_type={instrument_type} region={region} delay={delay} universe={universe} "
                f"dataset_id={dataset_id} data_type={data_type} search={'<set>' if search else '<empty>'}",
                flush=True,
            )
            if search and not dataset_id:
                return original_get_datafields(
                    session,
                    instrument_type=instrument_type,
                    region=region,
                    delay=delay,
                    universe=universe,
                    search=search,
                )
            return _build_datafields_df(
                session=session,
                instrument_type=instrument_type,
                region=region,
                delay=int(delay),
                universe=universe,
                dataset_id=dataset_id,
                data_type=data_type,
            )

        rp.ace_lib.get_datafields = _patched_get_datafields

        original_run_script = rp.run_script

        def _patched_run_script(args_list, cwd):
            if len(args_list) >= 2 and str(args_list[1]).endswith("fetch_dataset.py"):
                session = session_holder.get("session")
                if session is None:
                    raise RuntimeError("Internal error: BRAIN session not initialized before fetch_dataset step")

                parsed = {}
                i = 2
                while i < len(args_list):
                    token = str(args_list[i])
                    if token.startswith("--") and i + 1 < len(args_list):
                        parsed[token] = str(args_list[i + 1])
                        i += 2
                    else:
                        i += 1

                dataset_id = parsed.get("--datasetid")
                region = parsed.get("--region", "EUR")
                delay = int(parsed.get("--delay", "1"))
                universe = parsed.get("--universe", "TOP3000")
                instrument_type = parsed.get("--instrument-type", "EQUITY")
                data_type = parsed.get("--data-type")

                print(
                    f"[patched_run_script/fetch_dataset] dataset_id={dataset_id} region={region} delay={delay} "
                    f"universe={universe} instrument_type={instrument_type} data_type={data_type}",
                    flush=True,
                )

                if not dataset_id:
                    raise RuntimeError("Missing --datasetid while intercepting fetch_dataset.py")

                df = _build_datafields_df(
                    session=session,
                    instrument_type=instrument_type,
                    region=region,
                    delay=delay,
                    universe=universe,
                    dataset_id=dataset_id,
                    data_type=data_type,
                )

                if df is None or df.empty:
                    raise RuntimeError(
                        f"No datafields returned for dataset={dataset_id}, region={region}, delay={delay}, universe={universe}"
                    )

                safe_dataset_id = "".join([c for c in dataset_id if c.isalnum() or c in ("-", "_")])
                folder_name = f"{safe_dataset_id}_{region}_delay{delay}"
                dataset_folder = rp.FEATURE_IMPLEMENTATION_DIR / "data" / folder_name
                dataset_folder.mkdir(parents=True, exist_ok=True)
                output_path = dataset_folder / f"{folder_name}.csv"
                df.to_csv(output_path, index=False)
                return f"Intercepted fetch_dataset.py and wrote {len(df)} rows to {output_path}"

            return original_run_script(args_list, cwd)

        rp.run_script = _patched_run_script

        def _patched_call_moonshot(api_key: str, model: str, system_prompt: str, user_prompt: str, timeout_s: int = 180):
            base_url = os.environ.get("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")
            url = f"{base_url.rstrip('/')}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip, deflate",
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": True,
            }

            retries = int(os.environ.get("MOONSHOT_RETRIES", "3"))
            backoff_s = float(os.environ.get("MOONSHOT_RETRY_BACKOFF", "2"))

            last_exc = None
            for attempt in range(retries + 1):
                try:
                    resp = requests.post(
                        url,
                        headers=headers,
                        json=payload,
                        stream=True,
                        timeout=(30, timeout_s),
                    )
                    if resp.status_code >= 300:
                        raise RuntimeError(f"Moonshot API error {resp.status_code}: {resp.text[:500]}")

                    content_parts = []
                    thinking = False

                    for raw_line in resp.iter_lines(decode_unicode=False):
                        if not raw_line:
                            continue

                        try:
                            line = raw_line.decode("utf-8", errors="replace").strip()
                        except Exception:
                            continue

                        if not line.startswith("data:"):
                            continue

                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break

                        try:
                            event = __import__("json").loads(data_str)
                        except Exception:
                            continue

                        choices = event.get("choices") or []
                        if not choices:
                            continue
                        choice0 = choices[0] if isinstance(choices[0], dict) else None
                        if not choice0:
                            continue

                        delta = choice0.get("delta") or {}
                        if not isinstance(delta, dict):
                            delta = {}

                        reasoning_piece = delta.get("reasoning_content")
                        if reasoning_piece:
                            if not thinking:
                                thinking = True
                                print("=============开始思考=============", flush=True)
                            print(str(reasoning_piece), end="", flush=True)

                        content_piece = delta.get("content")
                        if content_piece:
                            if thinking:
                                thinking = False
                                print("\n=============思考结束=============", flush=True)
                            content_parts.append(str(content_piece))
                            print(str(content_piece), end="", flush=True)

                        finish_reason = choice0.get("finish_reason")
                        if finish_reason:
                            break

                    if thinking:
                        print("\n=============思考结束=============", flush=True)

                    final_content = "".join(content_parts)
                    if not final_content.strip():
                        raise RuntimeError("Moonshot stream ended without content")
                    return final_content
                except Exception as exc:
                    last_exc = exc
                    if attempt >= retries:
                        raise
                    sleep_s = backoff_s * (2 ** attempt)
                    print(f"[moonshot-retry] attempt={attempt + 1} failed: {exc}; sleep {sleep_s:.1f}s")
                    time.sleep(sleep_s)

            raise RuntimeError(f"Moonshot request failed: {last_exc}")

        rp.call_moonshot = _patched_call_moonshot

        def _is_timeout_like(exc: Exception) -> bool:
            err = str(exc).lower()
            return (
                "read timed out" in err
                or "timeout" in err
                or "moonshot" in err
                or "api.moonshot.cn" in err
            )

        old_argv = sys.argv[:]
        try:
            cli_args = build_command(sys.executable, pipeline_script, args)
            run_args = ["run_pipeline.py"] + cli_args[2:]

            base_fields = args.max_fields if args.max_fields is not None else 50
            retry_fields = [max(1, int(base_fields) // 2), max(1, int(base_fields) // 4)]

            sys.argv = run_args
            try:
                rp.main()
            except Exception as first_exc:
                if not _is_timeout_like(first_exc):
                    raise

                print(f"[moonshot-timeout] first attempt timed out; retry #2 with --max-fields {retry_fields[0]}...")
                second_args = run_args + ["--max-fields", str(retry_fields[0])]
                sys.argv = second_args
                try:
                    rp.main()
                except Exception as second_exc:
                    if not _is_timeout_like(second_exc):
                        raise

                    print(f"[moonshot-timeout] second attempt timed out; retry #3 with --max-fields {retry_fields[1]}...")
                    third_args = run_args + ["--max-fields", str(retry_fields[1])]
                    sys.argv = third_args
                    rp.main()
        finally:
            sys.argv = old_argv

        dataset_folder = f"{args.dataset_id}_{args.region}_delay{args.delay}"
        final_path = base_dir / "trailSomeAlphas" / "skills" / "brain-feature-implementation" / "data" / dataset_folder / "final_expressions.json"
        print("\nPipeline finished successfully.")
        print(f"Expected result file: {final_path}")
        return 0
    except Exception as exc:
        print("\nPipeline failed with exception:")
        print(str(exc))
        print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(2)
