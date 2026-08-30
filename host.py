#!/usr/bin/env python3
import json
import os
from pathlib import Path
from urllib.parse import quote


TOOLS = {
    "write": "Write",
    "search_replace": "Edit",
    "run_terminal_command": "Bash",
    "spawn_subagent": "Task",
    "monitor": "monitor",
    "scheduler_create": "croncreate",
}


def detect(payload, env=None):
    env = os.environ if env is None else env
    if isinstance(payload, dict):
        if "stopHookActive" in payload or payload.get("hookEventName"):
            return "grok"
        if payload.get("transcript_path"):
            return "claude"
    if env.get("GROK_HOOK_EVENT") or env.get("GROK_SESSION_ID"):
        return "grok"
    return "claude"


class View:
    def __init__(self, kind, payload, path, ignore, closing, waiting=None):
        self.kind = kind
        self.payload = payload
        self.path = path
        self.ignore = ignore
        self._closing = closing
        self.waiting = waiting or []

    def last_message(self):
        if self._closing:
            return self._closing
        text = ""
        for entry in entries(self.path):
            if entry.get("type") != "assistant":
                continue
            content = entry.get("message", {}).get("content")
            if not isinstance(content, list):
                continue
            joined = " ".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text").strip()
            if joined:
                text = joined
        return text


def view(payload, env=None):
    env = os.environ if env is None else env
    payload = payload if isinstance(payload, dict) else {}
    if detect(payload, env) == "grok":
        return _grok(payload, env)
    return _claude(payload)


def _claude(payload):
    path = payload.get("transcript_path") or ""
    data = dict(payload)
    data["transcript_path"] = path
    data["stop_hook_active"] = bool(payload.get("stop_hook_active"))
    data.setdefault("cwd", payload.get("cwd") or os.getcwd())
    closing = payload.get("last_assistant_message") or ""
    waiting = payload.get("background_tasks") or []
    return View("claude", data, path, False, closing, waiting)


def _grok(payload, env):
    reason = payload.get("reason")
    ignore = reason not in (None, "", "end_turn")
    session = payload.get("sessionId") or env.get("GROK_SESSION_ID") or ""
    cwd = (payload.get("cwd") or payload.get("workspaceRoot")
           or env.get("GROK_WORKSPACE_ROOT") or os.getcwd())
    closing = payload.get("lastAssistantMessage") or ""
    path = grok_history(cwd, session, env)
    waiting = payload.get("backgroundTasks") or []
    data = dict(payload)
    data["transcript_path"] = path
    data["cwd"] = cwd
    data["stop_hook_active"] = bool(
        payload["stopHookActive"] if "stopHookActive" in payload
        else payload.get("stop_hook_active"))
    data["last_assistant_message"] = closing
    return View("grok", data, path, ignore, closing, waiting)


def grok_history(cwd, session_id, env=None):
    if not session_id:
        return ""
    env = os.environ if env is None else env
    home = env.get("GROK_HOME") or str(Path.home() / ".grok")
    root = Path(home) / "sessions"
    direct = root / quote(str(cwd), safe="") / session_id / "chat_history.jsonl"
    if direct.is_file():
        return str(direct)
    for hit in root.glob("*/" + session_id + "/chat_history.jsonl"):
        return str(hit)
    return ""


def entries(path):
    rows = list(_rows(path))
    if not rows:
        return
    first = rows[0]
    project = not isinstance(first.get("message"), dict)
    for row in rows:
        if project:
            out = project_grok(row)
            if out is not None:
                yield out
        else:
            yield row


def _rows(path):
    if not path or not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    yield row
    except OSError:
        return


def project_grok(row):
    kind = row.get("type")
    if kind in ("reasoning", "system"):
        return None
    if kind == "tool_result":
        return {"type": "user", "message": {"content": [{
            "type": "tool_result",
            "tool_use_id": row.get("tool_call_id") or "",
            "content": row.get("content") or "",
        }]}}
    if kind == "user":
        if row.get("synthetic_reason"):
            return None
        content = row.get("content")
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        if not isinstance(content, list):
            content = []
        out = {"type": "user", "message": {"content": content}}
        stamp = row.get("timestamp") or row.get("ts")
        if stamp:
            out["timestamp"] = stamp
        return out
    if kind != "assistant":
        return None
    blocks = []
    text = row.get("content")
    if isinstance(text, str) and text.strip():
        blocks.append({"type": "text", "text": text})
    elif isinstance(text, list):
        blocks.extend(b for b in text if isinstance(b, dict))
    for call in row.get("tool_calls") or []:
        if not isinstance(call, dict):
            continue
        raw = call.get("arguments")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except ValueError:
                raw = {}
        if not isinstance(raw, dict):
            raw = {}
        name = str(call.get("name") or "")
        mapped = TOOLS.get(name.lower(), name)
        blocks.append({
            "type": "tool_use",
            "id": call.get("id") or "",
            "name": mapped,
            "input": raw,
        })
    out = {"type": "assistant", "message": {"content": blocks}}
    stamp = row.get("timestamp") or row.get("ts")
    if stamp:
        out["timestamp"] = stamp
    return out
