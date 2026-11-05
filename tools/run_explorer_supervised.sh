#!/bin/bash
# Keep the explorer running across hard kills.
#
# `simulate_alphas.py` already restarts itself on exceptions (MAX_RESTARTS, with
# a healthy-run reset). It cannot survive a signal it never sees: on 2026-10-05
# the process died twice with no trace at all — no `Crash #N` line, no
# traceback, the last log line an ordinary batch submission — and stayed dead
# for as long as it took someone to notice. This wrapper respawns it and records
# the exit code, so a SIGKILL (137) or SIGTERM (143) is visible if it happens
# again.
#
# `make stop` kills this supervisor as well as the explorer; otherwise the
# supervisor would dutifully bring back what the operator just stopped.
set -u

cd "$(dirname "$(dirname "$(readlink -f "$0")")")" || exit 1

PYTHON="${PYTHON:-$PWD/.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
    echo "Project Python not found: $PYTHON; run make setup" >&2
    exit 1
fi
# Keep a second host supervisor from launching a competing database writer.
mkdir -p "${BRAIN_LOG_DIR:-brain_logs}"
exec 9>"${BRAIN_LOG_DIR:-brain_logs}/explorer.lock"
if ! flock -n 9; then
    echo "An explorer supervisor already owns this workspace" >&2
    exit 1
fi
STDOUT_LOG="${BRAIN_LOG_DIR:-brain_logs}/simulate_stdout.log"
SUP_LOG="${BRAIN_LOG_DIR:-brain_logs}/supervisor.log"
RESPAWN_DELAY=15
MAX_RESPAWN_DELAY=900

# A run this long is a real run, not a failed start: the backoff resets.
# Below it the failure is upstream, and retrying at a fixed 15s makes it worse.
HEALTHY_RUN_SEC=300

mkdir -p "$(dirname "$STDOUT_LOG")"

echo "[supervisor] started pid=$$ at $(date -u +%FT%TZ)" >>"$SUP_LOG"
delay=$RESPAWN_DELAY
while true; do
    started=$(date +%s)
    "$PYTHON" simulate_alphas.py >>"$STDOUT_LOG" 2>&1
    code=$?
    ran=$(( $(date +%s) - started ))
    # Back off on a *fast* exit, because the cause is upstream rather than in
    # the explorer: observed live 2026-10-08, the auth POST returned 429 "API
    # rate limit exceeded" and the explorer exited in ~5s, so the fixed 15s
    # respawn re-POSTed to the endpoint that had just refused it, every 15s,
    # indefinitely — a rate-limited endpoint held down by the retry loop
    # itself. Doubling gives that window time to lapse; a run that lasted
    # HEALTHY_RUN_SEC resets it, so this cannot stretch an ordinary crash
    # recovery into a 15-minute outage.
    if [ "$ran" -ge "$HEALTHY_RUN_SEC" ]; then
        delay=$RESPAWN_DELAY
    else
        delay=$(( delay * 2 ))
        [ "$delay" -gt "$MAX_RESPAWN_DELAY" ] && delay=$MAX_RESPAWN_DELAY
    fi
    echo "[supervisor] $(date -u +%FT%TZ) explorer exited code=$code after ${ran}s — respawning in ${delay}s" >>"$SUP_LOG"
    sleep "$delay"
done
