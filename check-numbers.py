#!/usr/bin/env python3
"""Stop hook. The closing message reports a number. Did anything in this
session ever print it?

The other session reported "2236 pruebas, 0 fallas" after a grep that answered
`Binary file matches`. The count came from a regex over source files, not from
a test report. Nobody could tell from the prose, which is what makes an
invented number worse than a missing one.

This finds every number the message attaches to a result word and looks for it
in the session's own tool output. What is not there was not measured.
"""
import importlib.util
import json
import os
import re
import sys

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

HERE = os.path.dirname(os.path.abspath(__file__))

perm = mod.load("check-permission.py")

RESULT = re.compile(
    r"([\d][\d.,]*)\s*(?:"
    r"pruebas|tests?|casos|fallas|fallos|failures|failed|passed|passing|"
    r"skipped|verdes|green|errores|errors|mutantes|mutants"
    r")\b",
    re.IGNORECASE,
)

INVERTED = re.compile(
    r"(?:pruebas|tests?|casos|fallas|fallos|failures|passed|skipped|mutantes)"
    r"[:\s]+([\d][\d.,]*)",
    re.IGNORECASE,
)

DIGITS = re.compile(r"\d[\d.,]*")

REMINDER = """ONE MORE STEP - THESE FIGURES ARE NOT MEASURED YET

{items}

Nothing in this session printed them. A number nobody measured is the one a reader trusts most and checks least, so it is worth the extra minute: run the thing and quote what it says, or drop the figure. Everything else in the report holds up."""


def blocks(path):
    """Splits the session in two: what the agent said, and everything it did
    not write itself.

    The second half is the evidence. It holds every tool result and also every
    user turn - what Juan typed, what a peer session sent across. Those are
    sources the agent cannot forge, so a number that appears there is a number
    it read rather than invented. Leaving them out was a false positive on any
    session where the figure arrives in the conversation instead of from a
    command: quoting a count someone else measured is honest reporting, and
    the checker used to call it fabrication."""
    said, printed = [], []
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict):
                    continue
                kind = entry.get("type")
                content = entry.get("message", {}).get("content")
                if isinstance(content, str):
                    if kind == "user":
                        printed.append(content)
                    continue
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype == "text" and kind == "assistant":
                        said.append(block.get("text", ""))
                    elif btype == "text" and kind == "user":
                        printed.append(block.get("text", ""))
                    elif btype == "tool_result":
                        body = block.get("content")
                        if isinstance(body, list):
                            body = " ".join(b.get("text", "") for b in body
                                            if isinstance(b, dict))
                        printed.append(str(body or ""))
    except OSError:
        return [], []
    return said, printed


def claimed(message):
    out = []
    for match in list(RESULT.finditer(message)) + list(INVERTED.finditer(message)):
        raw = match.group(1).strip(".,")
        if raw and raw not in out:
            out.append(raw)
    return out


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}

    if payload.get("stop_hook_active"):
        return 0

    transcript = payload.get("transcript_path") or ""
    if not transcript or not os.path.exists(transcript):
        return 0

    said, printed = blocks(transcript)
    raw = next((t for t in reversed(said) if t.strip()), "")
    if not raw:
        return 0

    numbers = claimed(perm.unquoted(raw, code=False))
    if not numbers:
        return 0

    seen = set()
    for text in printed:
        seen.update(DIGITS.findall(text))
    plain = {n.replace(",", "").replace(".", "") for n in seen}

    missing = [n for n in numbers
               if n not in seen and n.replace(",", "").replace(".", "") not in plain]
    if not missing:
        return 0

    items = "\n".join(f"  - {n}, not found in this session's output" for n in missing[:8])
    sys.stderr.write(REMINDER.format(items=items) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
