#!/usr/bin/env python3
"""Read-only Gmail connector bridge for the BRAIN email archive.

DSH has no native Gmail tool.  The local Codex app-server does expose the
ChatGPT Gmail connector as the MCP server ``codex_apps``.  This module starts a
*local* Codex app-server over stdio, opens an ephemeral thread, and calls only
the Gmail read/search tools directly (no model turn, no write actions).

Security boundaries:
  * Tool allowlist below is read-only.  Send/delete/label/draft calls are not
    reachable through this module.
  * Email content is untrusted data.  This module never executes message code
    or follows links.
  * No DuckDB, no service/container control, no project Python required.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

CODEX_EXE = os.environ.get(
    "DSH_CODEX_EXE",
    r"C:\Users\victo\AppData\Local\Programs\OpenAI\Codex\bin\codex.exe",
)
DEFAULT_CWD = os.environ.get("DSH_GMAIL_CWD", os.environ.get("TEMP", r"C:\Windows\Temp"))
READ_ONLY_TOOLS = frozenset(
    {
        "gmail.search_emails",
        "gmail.search_email_ids",
        "gmail.read_email",
        "gmail.batch_read_email",
        "gmail.read_email_thread",
        "gmail.batch_read_email_threads",
        "gmail.get_profile",
        "gmail.list_labels",
    }
)


class ConnectorError(RuntimeError):
    pass


class CodexGmail:
    """Direct JSON-RPC client for the read-only Gmail connector."""

    def __init__(self, codex_exe: str = CODEX_EXE, cwd: str = DEFAULT_CWD) -> None:
        self.codex_exe = codex_exe
        self.cwd = cwd
        self.proc: subprocess.Popen[str] | None = None
        self.thread_id: str | None = None
        self._replies: queue.Queue[dict[str, Any]] = queue.Queue()
        self._next_id = 0
        self._reader: threading.Thread | None = None

    # -- lifecycle ---------------------------------------------------------
    def __enter__(self) -> "CodexGmail":
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def start(self) -> None:
        if self.proc is not None:
            return
        if not Path(self.codex_exe).is_file():
            raise ConnectorError(f"Codex executable not found: {self.codex_exe}")
        self.proc = subprocess.Popen(
            [self.codex_exe, "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=self.cwd,
        )
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        init = self._request(
            "initialize",
            {
                "clientInfo": {"name": "brain-email-archive", "title": None, "version": "1.0"},
                "capabilities": None,
            },
        )
        if "result" not in init:
            raise ConnectorError(f"app-server initialize failed: {init}")
        started = self._request("thread/start", {"cwd": self.cwd, "ephemeral": True})
        try:
            self.thread_id = started["result"]["thread"]["id"]
        except (KeyError, TypeError) as exc:
            raise ConnectorError(f"app-server thread/start failed: {started}") from exc
        status = self._request(
            "mcpServerStatus/list",
            {"threadId": self.thread_id, "detail": "toolsAndAuthOnly", "serverName": "codex_apps"},
        )
        servers = (status.get("result") or {}).get("data") or []
        if not servers or servers[0].get("name") != "codex_apps":
            raise ConnectorError("codex_apps MCP server is not available; is Codex logged in?")
        if not self._server_has_gmail(servers[0]):
            status = self._request(
                "mcpServerStatus/list",
                {"threadId": self.thread_id, "detail": "full", "serverName": "codex_apps"},
            )
            servers = (status.get("result") or {}).get("data") or []
            if not servers or not self._server_has_gmail(servers[0]):
                raise ConnectorError("Gmail connector tools are not exposed by codex_apps")

    @staticmethod
    def _server_has_gmail(server: dict[str, Any]) -> bool:
        tools = server.get("tools") or {}
        return "gmail.search_emails" in tools or "gmail.read_email" in tools

    def close(self) -> None:
        proc, self.proc = self.proc, None
        if proc is None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    # -- json-rpc ----------------------------------------------------------
    def _read_loop(self) -> None:
        assert self.proc is not None and self.proc.stdout is not None
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._replies.put(json.loads(line))
            except json.JSONDecodeError:
                continue

    def _request(self, method: str, params: dict[str, Any] | None = None, timeout: float = 120.0) -> dict[str, Any]:
        if self.proc is None or self.proc.stdin is None:
            raise ConnectorError("app-server is not running")
        self._next_id += 1
        request_id = self._next_id
        message: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        self.proc.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                reply = self._replies.get(timeout=max(0.05, deadline - time.time()))
            except queue.Empty:
                break
            if reply.get("id") == request_id:
                return reply
        raise ConnectorError(f"timed out waiting for app-server method {method}")

    # -- read-only Gmail calls --------------------------------------------
    def call(self, tool: str, arguments: dict[str, Any], timeout: float = 180.0) -> dict[str, Any]:
        if tool not in READ_ONLY_TOOLS:
            raise ConnectorError(f"refusing non-read-only Gmail tool: {tool}")
        if self.thread_id is None:
            raise ConnectorError("connector is not started")
        reply = self._request(
            "mcpServer/tool/call",
            {
                "threadId": self.thread_id,
                "server": "codex_apps",
                "tool": tool,
                "arguments": arguments,
            },
            timeout=timeout,
        )
        if "result" not in reply:
            raise ConnectorError(f"{tool} failed: {reply}")
        result = reply["result"]
        if result.get("isError"):
            text = " ".join(str(part.get("text", "")) for part in result.get("content") or [])
            raise ConnectorError(f"{tool} returned isError: {text[:2000]}")
        return result

    def search(self, query: str, max_results: int = 100, next_page_token: str = "") -> dict[str, Any]:
        args: dict[str, Any] = {"query": query, "max_results": max_results}
        if next_page_token:
            args["next_page_token"] = next_page_token
        result = self.call("gmail.search_emails", args)
        return result.get("structuredContent") or {}

    def search_ids(self, query: str, max_results: int = 500, next_page_token: str = "") -> dict[str, Any]:
        args: dict[str, Any] = {"query": query, "max_results": max_results}
        if next_page_token:
            args["next_page_token"] = next_page_token
        result = self.call("gmail.search_email_ids", args)
        return result.get("structuredContent") or {}

    def read(self, message_id: str, fmt: str = "full") -> dict[str, Any]:
        result = self.call("gmail.read_email", {"message_id": message_id, "format": fmt})
        return result.get("structuredContent") or {}

    def batch_read(self, message_ids: list[str]) -> dict[str, Any]:
        result = self.call("gmail.batch_read_email", {"message_ids": message_ids}, timeout=300.0)
        return result.get("structuredContent") or {}

    def list_labels(self) -> dict[str, Any]:
        result = self.call("gmail.list_labels", {})
        return result.get("structuredContent") or {}


def _parse_ids(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="search messages")
    p_search.add_argument("--query", required=True)
    p_search.add_argument("--max", type=int, default=100)
    p_search.add_argument("--page-token", default="")

    p_ids = sub.add_parser("search-ids", help="search message ids")
    p_ids.add_argument("--query", required=True)
    p_ids.add_argument("--max", type=int, default=500)
    p_ids.add_argument("--page-token", default="")

    p_read = sub.add_parser("read", help="read one full message")
    p_read.add_argument("--id", required=True, dest="message_id")
    p_read.add_argument("--format", default="full", choices=["full", "metadata", "minimal", "raw"])

    p_batch = sub.add_parser("batch-read", help="read up to 100 full messages")
    p_batch.add_argument("--ids", required=True, help="comma-separated immutable Gmail message IDs")

    sub.add_parser("labels", help="list labels")

    args = parser.parse_args(argv)
    with CodexGmail() as gmail:
        if args.command == "search":
            payload = gmail.search(args.query, args.max, args.page_token)
        elif args.command == "search-ids":
            payload = gmail.search_ids(args.query, args.max, args.page_token)
        elif args.command == "read":
            payload = gmail.read(args.message_id, args.format)
        elif args.command == "batch-read":
            payload = gmail.batch_read(_parse_ids(args.ids))
        else:
            payload = gmail.list_labels()
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
