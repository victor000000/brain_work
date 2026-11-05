from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

COMPLETION_PROMISE = "<promise>COMPLETE</promise>"


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_state_path(raw_state_path: str) -> Path:
    candidate = Path(raw_state_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()

    root_based = (_skill_root() / candidate).resolve()
    if root_based.exists():
        return root_based

    cwd_based = (Path.cwd() / candidate).resolve()
    if cwd_based.exists():
        return cwd_based

    return root_based


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _next_unit(state: dict[str, Any]) -> dict[str, Any] | None:
    for unit in state.get("loop_units", []):
        if not bool(unit.get("passes", False)):
            return unit
    return None


def _seed_units_in_state(state: dict[str, Any], branches: list[str]) -> None:
    state.setdefault("loop_units", [])
    existing = len(state.get("loop_units", []))
    for index, branch in enumerate(branches, start=1):
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


def _stop_reached(state: dict[str, Any]) -> bool:
    stop = state.get("stop", {})
    return bool(stop.get("should_stop", False))


def _ready_target_reached(state: dict[str, Any], ready_target: int) -> bool:
    submit_gate = state.get("submit_gate", {})
    ready_count = int(submit_gate.get("submit_ready_count", 0))
    verified = bool(submit_gate.get("verified_by_mcp", False))
    return verified and ready_count >= max(1, int(ready_target))


def _append_progress(state: dict[str, Any], state_path: Path, line: str) -> None:
    progress_log = str(state.get("progress_log") or "outputs/progress.txt")
    p = Path(progress_log)
    if not p.is_absolute():
        p = (state_path.parent / p).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_agent_command(command: str, timeout_seconds: int) -> tuple[int, str]:
    process = subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
    )
    output = (process.stdout or "") + "\n" + (process.stderr or "")
    return process.returncode, output


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal Ralph outer-loop runner for brain-deepExplore")
    parser.add_argument("--state", required=True, help="State file path")
    parser.add_argument("--agent-command", required=True, help="Command template to execute each unit; placeholders: {unit_id} {branch} {title}")
    parser.add_argument("--max-iterations", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--sleep-seconds", type=int, default=2)
    parser.add_argument("--ready-target", type=int, default=4)
    parser.add_argument("--auto-refill-units", default="true", choices=["true", "false"])
    parser.add_argument("--unit-sequence", default="generate,setting,sim,review", help="Comma-separated branches for auto-refill")
    args = parser.parse_args()

    state_path = _resolve_state_path(args.state)
    if not state_path.exists():
        raise FileNotFoundError(
            "state not found. "
            f"resolved={state_path}; "
            f"skill_root={_skill_root()}; cwd={Path.cwd()}"
        )

    for i in range(1, max(1, args.max_iterations) + 1):
        state = _load_json(state_path)
        if _stop_reached(state):
            _append_progress(state, state_path, f"[runner] stop detected at iteration={i}; reason={state.get('stop', {}).get('reason')}")
            print("Stop flag detected. Exit runner.")
            return 0

        if _ready_target_reached(state, ready_target=args.ready_target):
            _append_progress(state, state_path, f"[runner] ready target reached ({args.ready_target}). exit")
            print("Submit-ready target reached. Exit runner.")
            return 0

        unit = _next_unit(state)
        if not unit:
            if str(args.auto_refill_units).lower() == "true":
                branches = [x.strip() for x in str(args.unit_sequence).split(",") if x.strip()]
                if not branches:
                    branches = ["generate", "setting", "sim", "review"]
                _seed_units_in_state(state, branches)
                _save_json(state_path, state)
                _append_progress(state, state_path, f"[runner] auto-refill units: {','.join(branches)}")
                unit = _next_unit(state)
            else:
                _append_progress(state, state_path, f"[runner] no incomplete unit at iteration={i}")
                print("No incomplete unit. Exit runner.")
                return 0

        unit_id = str(unit.get("id"))
        branch = str(unit.get("branch"))
        title = str(unit.get("title"))

        cmd = (
            args.agent_command
            .replace("{unit_id}", unit_id)
            .replace("{branch}", branch)
            .replace("{title}", title)
        )

        _append_progress(state, state_path, f"[runner] iteration={i} start unit={unit_id} branch={branch}")
        code, out = run_agent_command(cmd, timeout_seconds=max(30, int(args.timeout_seconds)))

        state = _load_json(state_path)
        updated = False
        for item in state.get("loop_units", []):
            if str(item.get("id")) == unit_id:
                if code == 0 and COMPLETION_PROMISE in out:
                    item["passes"] = True
                    item["notes"] = "runner detected completion promise"
                    _append_progress(state, state_path, f"[runner] unit={unit_id} PASS")
                else:
                    item["passes"] = False
                    snippet = out[-300:].replace("\n", " ")
                    item["notes"] = f"runner fail code={code} snippet={snippet}"
                    _append_progress(state, state_path, f"[runner] unit={unit_id} FAIL code={code}")
                updated = True
                break

        if updated:
            _save_json(state_path, state)

        time.sleep(max(0, int(args.sleep_seconds)))

    print("Max iterations reached in runner.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
