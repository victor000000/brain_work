from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Python 3.9+ with zoneinfo support is required") from exc

NY_TZ = ZoneInfo("America/New_York")
COMPLETION_PROMISE = "<promise>COMPLETE</promise>"


@dataclass
class StopDecision:
    should_stop: bool
    reason: str


def now_iso() -> str:
    return datetime.now(tz=NY_TZ).isoformat()


def ny_day_key() -> str:
    return datetime.now(tz=NY_TZ).strftime("%Y-%m-%d")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_history(state: dict[str, Any], action: str, detail: dict[str, Any]) -> None:
    state.setdefault("history", []).append({"ts": now_iso(), "action": action, "detail": detail})


def _resolve_progress_path(state: dict[str, Any], state_path: Path) -> Path:
    progress_log = str(state.get("progress_log") or "outputs/progress.txt").strip()
    progress_path = Path(progress_log)
    if not progress_path.is_absolute():
        progress_path = (state_path.parent / progress_path).resolve()
    return progress_path


def _append_progress(state: dict[str, Any], state_path: Path, line: str) -> None:
    path = _resolve_progress_path(state, state_path)
    _ensure_parent(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"[{now_iso()}] {line}\n")


def load_or_init_state(state_path: Path, template_path: Path, max_iterations: int, max_no_progress: int) -> dict[str, Any]:
    day_key = ny_day_key()

    if state_path.exists():
        state = _load_json(state_path)
        if state.get("day_key") == day_key:
            return state

    state = _load_json(template_path)
    state["day_key"] = day_key
    state["timezone"] = "America/New_York"
    state["progress_log"] = str(state.get("progress_log") or "outputs/progress.txt")
    state.setdefault("iteration", {})["max"] = max_iterations
    state["iteration"]["max_no_progress"] = max_no_progress
    state["iteration"]["current"] = 0
    state["iteration"]["no_progress_streak"] = 0
    state["iteration"]["last_branch"] = ""
    state["daily_diagnose"] = {
        "done": False,
        "objective": "",
        "constraints": "",
        "done_at": "",
    }
    state["submit_gate"] = {
        "submit_ready_count": 0,
        "verified_by_mcp": False,
        "alpha_ids_checked": [],
        "checked_at": "",
    }
    state["stop"] = {"should_stop": False, "reason": ""}
    state["loop_units"] = []
    state["history"] = []
    _append_history(state, "bootstrap", {"day_key": day_key})
    return state


def mark_nextmove(state: dict[str, Any], objective: str, constraints: str) -> dict[str, Any]:
    if state["daily_diagnose"].get("done"):
        _append_history(state, "mark_nextmove_skipped", {"reason": "already_done_today"})
        return state

    state["daily_diagnose"]["done"] = True
    state["daily_diagnose"]["objective"] = objective.strip()
    state["daily_diagnose"]["constraints"] = constraints.strip()
    state["daily_diagnose"]["done_at"] = now_iso()
    _append_history(
        state,
        "mark_nextmove_done",
        {
            "objective": state["daily_diagnose"]["objective"],
            "constraints": state["daily_diagnose"]["constraints"],
        },
    )
    return state


def seed_units(state: dict[str, Any], units_csv: str, reset_existing: bool) -> dict[str, Any]:
    if reset_existing:
        state["loop_units"] = []

    raw_units = [x.strip() for x in units_csv.split(",") if x.strip()]
    existing = len(state.get("loop_units", []))
    for index, branch in enumerate(raw_units, start=1):
        uid = f"U{existing + index:03d}"
        state["loop_units"].append(
            {
                "id": uid,
                "title": f"{branch} step",
                "branch": branch,
                "passes": False,
                "notes": "",
            }
        )
    _append_history(state, "seed_units", {"count": len(raw_units), "reset_existing": reset_existing})
    return state


def get_next_unit(state: dict[str, Any]) -> dict[str, Any] | None:
    for unit in state.get("loop_units", []):
        if not bool(unit.get("passes", False)):
            return unit
    return None


def complete_unit(state: dict[str, Any], unit_id: str, passes: bool, notes: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    for unit in state.get("loop_units", []):
        if str(unit.get("id")) == unit_id:
            unit["passes"] = bool(passes)
            unit["notes"] = notes.strip()
            _append_history(
                state,
                "complete_unit",
                {
                    "unit_id": unit_id,
                    "passes": bool(passes),
                    "notes": notes.strip(),
                },
            )
            return state, unit
    return state, None


def new_iteration(state: dict[str, Any], branch: str, change_note: str) -> dict[str, Any]:
    state["iteration"]["current"] += 1
    state["iteration"]["last_branch"] = branch
    _append_history(
        state,
        "new_iteration",
        {
            "iteration": state["iteration"]["current"],
            "branch": branch,
            "change_note": change_note,
        },
    )
    return state


def decide_enhance_mode(metadata_consistent: bool, complementary: bool, instability: bool) -> str:
    if metadata_consistent and complementary:
        return "cross"
    if instability:
        return "single"
    return "single"


def update_sim_summary(
    state: dict[str, Any],
    sim_csv: str,
    complete: int,
    failed: int,
    running: int,
    progressed: bool,
) -> dict[str, Any]:
    state.setdefault("artifacts", {})["sim_status_csv"] = sim_csv
    state.setdefault("sim_summary", {})["complete"] = max(0, int(complete))
    state["sim_summary"]["failed"] = max(0, int(failed))
    state["sim_summary"]["running"] = max(0, int(running))
    state["sim_summary"]["updated_at"] = now_iso()

    if progressed:
        state["iteration"]["no_progress_streak"] = 0
    else:
        state["iteration"]["no_progress_streak"] += 1

    _append_history(
        state,
        "update_sim",
        {
            "sim_csv": sim_csv,
            "complete": complete,
            "failed": failed,
            "running": running,
            "no_progress_streak": state["iteration"]["no_progress_streak"],
        },
    )
    return state


def _resolve_data_path(state_path: Path, raw_path: str) -> Path:
    p = Path(str(raw_path).strip())
    if p.is_absolute():
        return p
    skill_root = Path(__file__).resolve().parents[1]
    return (skill_root / p).resolve()


def set_artifacts(
    state: dict[str, Any],
    gem_idea_file: str | None,
    gem_expression_file: str | None,
    inspect_input_idea_file: str | None,
    alpha_list_file: str | None,
    sim_status_csv: str | None,
) -> dict[str, Any]:
    artifacts = state.setdefault("artifacts", {})
    artifacts.setdefault("gem_idea_file", "")
    artifacts.setdefault("gem_expression_file", "")
    artifacts.setdefault("inspect_input_idea_file", "")
    artifacts.setdefault("alpha_list_file", "")
    artifacts.setdefault("sim_status_csv", "")
    artifacts.setdefault("enhance_outputs", [])

    if gem_idea_file is not None:
        artifacts["gem_idea_file"] = gem_idea_file.strip()
    if gem_expression_file is not None:
        artifacts["gem_expression_file"] = gem_expression_file.strip()
    if inspect_input_idea_file is not None:
        artifacts["inspect_input_idea_file"] = inspect_input_idea_file.strip()
    if alpha_list_file is not None:
        artifacts["alpha_list_file"] = alpha_list_file.strip()
    if sim_status_csv is not None:
        artifacts["sim_status_csv"] = sim_status_csv.strip()

    _append_history(
        state,
        "set_artifacts",
        {
            "gem_idea_file": artifacts.get("gem_idea_file", ""),
            "gem_expression_file": artifacts.get("gem_expression_file", ""),
            "inspect_input_idea_file": artifacts.get("inspect_input_idea_file", ""),
            "alpha_list_file": artifacts.get("alpha_list_file", ""),
            "sim_status_csv": artifacts.get("sim_status_csv", ""),
        },
    )
    return state


def validate_handoff(state: dict[str, Any], state_path: Path, require_exists: bool) -> list[str]:
    errors: list[str] = []
    artifacts = state.setdefault("artifacts", {})
    gem_idea = str(artifacts.get("gem_idea_file") or "").strip()
    gem_expr = str(artifacts.get("gem_expression_file") or "").strip()
    inspect_idea = str(artifacts.get("inspect_input_idea_file") or "").strip()
    alpha_list = str(artifacts.get("alpha_list_file") or "").strip()
    sim_csv = str(artifacts.get("sim_status_csv") or "").strip()

    if inspect_idea and "final_expressions.json" in inspect_idea.replace("\\", "/"):
        errors.append("inspect_input_idea_file cannot be final_expressions.json")

    if inspect_idea and "_idea_" not in Path(inspect_idea).name:
        errors.append("inspect_input_idea_file must be *_idea_*.json")

    if gem_expr and not Path(gem_expr).name.endswith("final_expressions.json"):
        errors.append("gem_expression_file should point to final_expressions.json")

    if alpha_list and Path(alpha_list).name != "alpha_list.json":
        errors.append("alpha_list_file should be alpha_list.json")

    if require_exists:
        pairs = [
            ("gem_idea_file", gem_idea),
            ("gem_expression_file", gem_expr),
            ("inspect_input_idea_file", inspect_idea),
            ("alpha_list_file", alpha_list),
            ("sim_status_csv", sim_csv),
        ]
        for key, value in pairs:
            if not value:
                continue
            resolved = _resolve_data_path(state_path, value)
            if not resolved.exists():
                errors.append(f"{key} not found: {resolved}")

    if inspect_idea and gem_idea and Path(inspect_idea).name != Path(gem_idea).name:
        errors.append("inspect_input_idea_file should usually match gem_idea_file for makeSomeGem->inspect flow")

    return errors


def auto_pick_artifacts(
    state: dict[str, Any],
    state_path: Path,
    dataset_folder: str | None,
    set_default_downstream: bool,
) -> tuple[dict[str, Any], dict[str, str]]:
    skill_root = Path(__file__).resolve().parents[1]
    data_root = (
        skill_root.parent
        / "brain-makeSomeGem"
        / "scripts"
        / "trailSomeAlphas"
        / "skills"
        / "brain-feature-implementation"
        / "data"
    ).resolve()

    if not data_root.exists():
        raise FileNotFoundError(f"makeSomeGem data root not found: {data_root}")

    folders: list[Path]
    if dataset_folder and str(dataset_folder).strip():
        target = (data_root / str(dataset_folder).strip()).resolve()
        if not target.exists():
            raise FileNotFoundError(f"dataset folder not found: {target}")
        folders = [target]
    else:
        folders = [x for x in data_root.iterdir() if x.is_dir()]

    idea_candidates: list[Path] = []
    for folder in folders:
        idea_candidates.extend(folder.glob("*_idea_*.json"))

    if not idea_candidates:
        raise FileNotFoundError("No *_idea_*.json found under makeSomeGem data folders")

    latest_idea = max(idea_candidates, key=lambda p: p.stat().st_mtime)
    folder = latest_idea.parent
    final_expr = folder / "final_expressions.json"

    artifacts = state.setdefault("artifacts", {})
    artifacts["gem_idea_file"] = str(latest_idea)
    artifacts["inspect_input_idea_file"] = str(latest_idea)
    artifacts["gem_expression_file"] = str(final_expr) if final_expr.exists() else ""

    if set_default_downstream:
        default_alpha_list = (
            skill_root.parent
            / "brain-inspectRawTemplate-create-Setting"
            / "processed_templates"
            / latest_idea.stem
            / "alpha_list.json"
        ).resolve()
        default_sim_csv = (
            skill_root.parent
            / "brain-simAlphasinBatch-and-track"
            / "outputs"
            / "simulation_status.csv"
        ).resolve()
        if not str(artifacts.get("alpha_list_file") or "").strip():
            artifacts["alpha_list_file"] = str(default_alpha_list)
        if not str(artifacts.get("sim_status_csv") or "").strip():
            artifacts["sim_status_csv"] = str(default_sim_csv)

    picked = {
        "dataset_folder": folder.name,
        "gem_idea_file": str(latest_idea),
        "gem_expression_file": str(final_expr) if final_expr.exists() else "",
        "inspect_input_idea_file": str(latest_idea),
        "alpha_list_file": str(artifacts.get("alpha_list_file") or ""),
        "sim_status_csv": str(artifacts.get("sim_status_csv") or ""),
    }
    _append_history(state, "auto_pick_artifacts", picked)
    _append_progress(state, state_path, f"auto-pick-artifacts dataset_folder={folder.name}")
    return state, picked


def _is_submission_pass(record: dict[str, Any]) -> bool:
    if isinstance(record.get("all_passed"), bool):
        return bool(record["all_passed"])
    if isinstance(record.get("passes_check"), bool):
        return bool(record["passes_check"])
    checks = record.get("checks")
    if isinstance(checks, dict) and isinstance(checks.get("all_passed"), bool):
        return bool(checks["all_passed"])
    correlation = record.get("correlation_checks")
    if isinstance(correlation, dict) and isinstance(correlation.get("all_passed"), bool):
        return bool(correlation["all_passed"])
    return False


def update_submit_gate(
    state: dict[str, Any],
    ready_count: int,
    verified_by_mcp: bool,
    alpha_ids: list[str],
) -> dict[str, Any]:
    state["submit_gate"]["submit_ready_count"] = max(0, int(ready_count))
    state["submit_gate"]["verified_by_mcp"] = bool(verified_by_mcp)
    state["submit_gate"]["alpha_ids_checked"] = [x for x in alpha_ids if x]
    state["submit_gate"]["checked_at"] = now_iso()
    _append_history(
        state,
        "update_submit_gate",
        {
            "submit_ready_count": state["submit_gate"]["submit_ready_count"],
            "verified_by_mcp": state["submit_gate"]["verified_by_mcp"],
            "alpha_ids_checked": state["submit_gate"]["alpha_ids_checked"],
        },
    )
    return state


def update_submit_gate_from_checks(state: dict[str, Any], checks_json: Path) -> tuple[dict[str, Any], int]:
    payload = _load_json(checks_json)
    records: list[dict[str, Any]] = []

    if isinstance(payload, dict):
        if isinstance(payload.get("results"), list):
            records = [x for x in payload["results"] if isinstance(x, dict)]
        else:
            records = [payload]
    elif isinstance(payload, list):
        records = [x for x in payload if isinstance(x, dict)]

    passed_ids: list[str] = []
    checked_ids: list[str] = []

    for index, record in enumerate(records, start=1):
        alpha_id = str(record.get("alpha_id") or record.get("alphaId") or record.get("id") or f"unknown_{index}")
        checked_ids.append(alpha_id)
        if _is_submission_pass(record):
            passed_ids.append(alpha_id)

    state = update_submit_gate(
        state,
        ready_count=len(passed_ids),
        verified_by_mcp=True,
        alpha_ids=checked_ids,
    )
    _append_history(
        state,
        "update_submit_gate_from_checks",
        {"checks_file": str(checks_json), "passed_alpha_ids": passed_ids},
    )
    return state, len(passed_ids)


def check_stop(
    state: dict[str, Any],
    ready_target: int,
    enforce_max_iterations: bool,
    enforce_no_progress: bool,
) -> StopDecision:
    if not state["daily_diagnose"].get("done"):
        return StopDecision(False, "daily_diagnose_not_done")

    ready = int(state["submit_gate"].get("submit_ready_count", 0))
    verified = bool(state["submit_gate"].get("verified_by_mcp", False))
    target = max(1, int(ready_target))
    if ready >= target and verified:
        return StopDecision(True, f"goal_reached_{target}_submit_ready_alphas")

    if enforce_max_iterations and int(state["iteration"].get("current", 0)) >= int(state["iteration"].get("max", 12)):
        return StopDecision(True, "max_iterations_reached")

    if enforce_no_progress and int(state["iteration"].get("no_progress_streak", 0)) >= int(state["iteration"].get("max_no_progress", 3)):
        return StopDecision(True, "no_progress_streak_reached")

    return StopDecision(False, "continue_loop")


def apply_stop(state: dict[str, Any], decision: StopDecision) -> dict[str, Any]:
    state["stop"]["should_stop"] = decision.should_stop
    state["stop"]["reason"] = decision.reason
    _append_history(state, "check_stop", {"should_stop": decision.should_stop, "reason": decision.reason})
    return state


def print_summary(state: dict[str, Any]) -> None:
    passed_units = sum(1 for x in state.get("loop_units", []) if x.get("passes"))
    total_units = len(state.get("loop_units", []))

    print("=" * 70)
    print("brain-deepExplore daily loop summary")
    print(f"day_key: {state.get('day_key')}")
    print(f"daily_diagnose.done: {state.get('daily_diagnose', {}).get('done')}")
    print(f"iteration.current/max: {state.get('iteration', {}).get('current')}/{state.get('iteration', {}).get('max')}")
    print(f"last_branch: {state.get('iteration', {}).get('last_branch')}")
    print(f"loop_units passed/total: {passed_units}/{total_units}")
    sim = state.get("sim_summary", {})
    print(f"sim complete/failed/running: {sim.get('complete')}/{sim.get('failed')}/{sim.get('running')}")
    gate = state.get("submit_gate", {})
    print(f"submit_ready_count (MCP verified): {gate.get('submit_ready_count')} ({gate.get('verified_by_mcp')})")
    stop = state.get("stop", {})
    print(f"stop: {stop.get('should_stop')} | reason: {stop.get('reason')}")
    print("=" * 70)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ralph-style daily loop state manager for brain-deepExplore")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common_state_args(sp: argparse.ArgumentParser, include_template: bool = False) -> None:
        sp.add_argument("--state", required=True, help="Path to state json")
        if include_template:
            sp.add_argument("--template", default="templates/daily_state.template.json", help="State template json path")

    p_boot = sub.add_parser("bootstrap")
    add_common_state_args(p_boot, include_template=True)
    p_boot.add_argument("--max-iterations", type=int, default=12)
    p_boot.add_argument("--max-no-progress", type=int, default=3)

    p_nm = sub.add_parser("mark-nextmove")
    add_common_state_args(p_nm)
    p_nm.add_argument("--objective", required=True)
    p_nm.add_argument("--constraints", required=True)

    p_seed = sub.add_parser("seed-units")
    add_common_state_args(p_seed)
    p_seed.add_argument("--units", required=True, help="Comma separated branches, e.g. generate,setting,sim,review")
    p_seed.add_argument("--reset-existing", action="store_true")

    p_next = sub.add_parser("next-unit")
    add_common_state_args(p_next)

    p_complete = sub.add_parser("complete-unit")
    add_common_state_args(p_complete)
    p_complete.add_argument("--unit-id", required=True)
    p_complete.add_argument("--passes", required=True, choices=["true", "false"])
    p_complete.add_argument("--notes", default="")
    p_complete.add_argument("--emit-promise", action="store_true")

    p_iter = sub.add_parser("new-iteration")
    add_common_state_args(p_iter)
    p_iter.add_argument("--branch", required=True, choices=["generate", "setting", "sim", "single_enhance", "cross_enhance", "review"])
    p_iter.add_argument("--change-note", default="")

    p_decide = sub.add_parser("decide-enhance")
    add_common_state_args(p_decide)
    p_decide.add_argument("--metadata-consistent", required=True, choices=["true", "false"])
    p_decide.add_argument("--complementary", required=True, choices=["true", "false"])
    p_decide.add_argument("--instability", required=True, choices=["true", "false"])

    p_sim = sub.add_parser("update-sim")
    add_common_state_args(p_sim)
    p_sim.add_argument("--sim-csv", required=True)
    p_sim.add_argument("--complete", type=int, default=0)
    p_sim.add_argument("--failed", type=int, default=0)
    p_sim.add_argument("--running", type=int, default=0)
    p_sim.add_argument("--progressed", required=True, choices=["true", "false"])

    p_set_art = sub.add_parser("set-artifacts")
    add_common_state_args(p_set_art)
    p_set_art.add_argument("--gem-idea-file")
    p_set_art.add_argument("--gem-expression-file")
    p_set_art.add_argument("--inspect-input-idea-file")
    p_set_art.add_argument("--alpha-list-file")
    p_set_art.add_argument("--sim-status-csv")

    p_auto_art = sub.add_parser("auto-pick-artifacts")
    add_common_state_args(p_auto_art)
    p_auto_art.add_argument("--dataset-folder", default="", help="Optional exact dataset folder under makeSomeGem data, e.g. analyst45_EUR_delay1")
    p_auto_art.add_argument("--set-default-downstream", default="true", choices=["true", "false"])

    p_val_handoff = sub.add_parser("validate-handoff")
    add_common_state_args(p_val_handoff)
    p_val_handoff.add_argument("--require-exists", default="true", choices=["true", "false"])

    p_gate = sub.add_parser("update-submit-gate")
    add_common_state_args(p_gate)
    p_gate.add_argument("--ready-count", type=int, required=True)
    p_gate.add_argument("--verified-by-mcp", required=True, choices=["true", "false"])
    p_gate.add_argument("--alpha-ids", default="", help="Comma-separated alpha ids")

    p_gate_file = sub.add_parser("update-submit-from-checks")
    add_common_state_args(p_gate_file)
    p_gate_file.add_argument("--checks-json", required=True, help="JSON file that stores MCP submission-check outputs")

    p_check_stop = sub.add_parser("check-stop")
    add_common_state_args(p_check_stop)
    p_check_stop.add_argument("--ready-target", type=int, default=4)
    p_check_stop.add_argument("--enforce-max-iterations", action="store_true")
    p_check_stop.add_argument("--enforce-no-progress", action="store_true")

    p_summary = sub.add_parser("summary")
    add_common_state_args(p_summary)

    return parser.parse_args()


def to_bool(raw: str) -> bool:
    return str(raw).strip().lower() == "true"


def main() -> int:
    args = parse_args()
    state_path = Path(args.state).expanduser().resolve()
    template_raw = getattr(args, "template", "templates/daily_state.template.json")
    template_path = Path(template_raw).expanduser()
    if not template_path.is_absolute():
        template_path = (Path(__file__).resolve().parents[1] / template_path).resolve()

    if args.command == "bootstrap":
        state = load_or_init_state(
            state_path=state_path,
            template_path=template_path,
            max_iterations=max(1, int(args.max_iterations)),
            max_no_progress=max(1, int(args.max_no_progress)),
        )
        _save_json(state_path, state)
        _append_progress(state, state_path, "bootstrap completed")
        print(f"Bootstrap complete: {state_path}")
        print_summary(state)
        return 0

    if not state_path.exists():
        raise FileNotFoundError(f"state file not found: {state_path}. Run bootstrap first.")

    state = _load_json(state_path)

    if state.get("day_key") != ny_day_key():
        print("Warning: state day_key is not today (NY). Please run bootstrap to rotate day state.")

    if args.command == "mark-nextmove":
        state = mark_nextmove(state, args.objective, args.constraints)
        _append_progress(state, state_path, "daily diagnose marked done")
    elif args.command == "seed-units":
        state = seed_units(state, units_csv=args.units, reset_existing=bool(args.reset_existing))
        _append_progress(state, state_path, f"seeded units: {args.units}")
    elif args.command == "next-unit":
        unit = get_next_unit(state)
        if not unit:
            print("No incomplete unit.")
        else:
            print(json.dumps(unit, ensure_ascii=False, indent=2))
        return 0
    elif args.command == "complete-unit":
        state, updated = complete_unit(
            state,
            unit_id=args.unit_id,
            passes=to_bool(args.passes),
            notes=args.notes,
        )
        if not updated:
            raise ValueError(f"unit not found: {args.unit_id}")
        _append_progress(state, state_path, f"complete-unit {args.unit_id} passes={updated['passes']} notes={updated['notes']}")
        if updated["passes"] and args.emit_promise:
            print(COMPLETION_PROMISE)
    elif args.command == "new-iteration":
        state = new_iteration(state, branch=args.branch, change_note=args.change_note)
        _append_progress(state, state_path, f"new iteration {state['iteration']['current']} branch={args.branch}")
    elif args.command == "decide-enhance":
        mode = decide_enhance_mode(
            metadata_consistent=to_bool(args.metadata_consistent),
            complementary=to_bool(args.complementary),
            instability=to_bool(args.instability),
        )
        _append_history(
            state,
            "decide_enhance",
            {
                "metadata_consistent": to_bool(args.metadata_consistent),
                "complementary": to_bool(args.complementary),
                "instability": to_bool(args.instability),
                "mode": mode,
            },
        )
        _append_progress(state, state_path, f"decide-enhance mode={mode}")
        print(f"enhance_mode={mode}")
    elif args.command == "update-sim":
        state = update_sim_summary(
            state,
            sim_csv=args.sim_csv,
            complete=args.complete,
            failed=args.failed,
            running=args.running,
            progressed=to_bool(args.progressed),
        )
        _append_progress(state, state_path, f"update-sim complete={args.complete} failed={args.failed} running={args.running} progressed={args.progressed}")
    elif args.command == "set-artifacts":
        state = set_artifacts(
            state,
            gem_idea_file=args.gem_idea_file,
            gem_expression_file=args.gem_expression_file,
            inspect_input_idea_file=args.inspect_input_idea_file,
            alpha_list_file=args.alpha_list_file,
            sim_status_csv=args.sim_status_csv,
        )
        _append_progress(state, state_path, "set-artifacts updated")
    elif args.command == "auto-pick-artifacts":
        state, picked = auto_pick_artifacts(
            state,
            state_path=state_path,
            dataset_folder=args.dataset_folder,
            set_default_downstream=to_bool(args.set_default_downstream),
        )
        print(json.dumps(picked, ensure_ascii=False, indent=2))
    elif args.command == "validate-handoff":
        errors = validate_handoff(state, state_path=state_path, require_exists=to_bool(args.require_exists))
        if errors:
            for message in errors:
                print(f"HANDOFF_ERROR: {message}")
            return 2
        print("handoff validation passed")
        return 0
    elif args.command == "update-submit-gate":
        alpha_ids = [x.strip() for x in args.alpha_ids.split(",") if x.strip()]
        state = update_submit_gate(
            state,
            ready_count=args.ready_count,
            verified_by_mcp=to_bool(args.verified_by_mcp),
            alpha_ids=alpha_ids,
        )
        _append_progress(state, state_path, f"update-submit-gate ready_count={args.ready_count} verified_by_mcp={args.verified_by_mcp}")
    elif args.command == "update-submit-from-checks":
        checks_path = Path(args.checks_json).expanduser().resolve()
        if not checks_path.exists():
            raise FileNotFoundError(f"checks json not found: {checks_path}")
        state, passed_count = update_submit_gate_from_checks(state, checks_path)
        _append_progress(state, state_path, f"update-submit-from-checks passed_count={passed_count} file={checks_path}")
        print(f"ready_count_from_checks={passed_count}")
    elif args.command == "check-stop":
        decision = check_stop(
            state,
            ready_target=int(args.ready_target),
            enforce_max_iterations=bool(args.enforce_max_iterations),
            enforce_no_progress=bool(args.enforce_no_progress),
        )
        state = apply_stop(state, decision)
        _append_progress(state, state_path, f"check-stop should_stop={decision.should_stop} reason={decision.reason}")
        print(f"should_stop={decision.should_stop}")
        print(f"reason={decision.reason}")
    elif args.command == "summary":
        print_summary(state)
        return 0

    _save_json(state_path, state)
    print_summary(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
