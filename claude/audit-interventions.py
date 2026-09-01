#!/usr/bin/env python3
"""Juan's own pushback is the ground truth. Every time he had to correct the
agent, the message just before it was a stop that should not have happened.

This finds those pairs and asks whether the detectors would have caught the
agent's message first. What survives here is a real miss, found by his signal
instead of by my definition of a stop.

Usage: audit-interventions.py <transcript.jsonl>
"""
import importlib.util
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name, alias):
    spec = importlib.util.spec_from_file_location(alias, os.path.join(HERE, name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


perm = load("check-permission.py", "perm")
claim = load("check-done-claim.py", "claim")

PUSHBACK = re.compile(
    r"me est[aá]s pidiendo permiso|no me pregunt|te dije|ya te dije|otra vez|"
    r"por qu[eé] (te )?(par|frena|detuv)|segu[ií]\b|no pares|dale\b|"
    r"de verdad te cre|no ten[ií]as que|no era|eso no|por que empezaste|"
    r"volv[ií] a repet|no entiendo por qu[eé]|esta listo para ir a prod|"
    r"asi directo|me estas diciendo que",
    re.IGNORECASE,
)


SYNTHETIC = re.compile(
    r"this session is being continued|caveat: the messages below|"
    r"<system-reminder>|<command-name>|<local-command-stdout>|"
    r"the summary below covers",
    re.IGNORECASE,
)


def rows(path):
    out = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not isinstance(entry, dict) or entry.get("type") not in ("assistant", "user"):
                continue
            content = entry.get("message", {}).get("content")
            if isinstance(content, list):
                text = " ".join(b.get("text", "") for b in content
                                if isinstance(b, dict) and b.get("type") == "text").strip()
                tools = any(isinstance(b, dict) and b.get("type") == "tool_use" for b in content)
                result = any(isinstance(b, dict) and b.get("type") == "tool_result"
                             for b in content)
            else:
                text, tools, result = (content or "").strip(), False, False
            out.append({"kind": entry.get("type"), "text": text, "tools": tools,
                        "result": result, "at": entry.get("timestamp", "")[:19]})
    return out


def caught(text, acted):
    if perm.offenders(text, None, acted):
        return True
    return bool(claim.CLAIM.search(claim.unquoted(text)))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    data = rows(sys.argv[1])
    misses = []
    total = 0
    acted = False
    last_assistant = None
    for row in data:
        if row["kind"] == "assistant":
            if row["tools"]:
                acted = True
            if row["text"]:
                last_assistant = (row, acted)
            continue
        if row["result"] or "STOP HOOK" in row["text"]:
            continue
        if SYNTHETIC.search(row["text"][:600]):
            acted = False
            last_assistant = None
            continue
        if PUSHBACK.search(row["text"]) and last_assistant:
            total += 1
            message, did = last_assistant
            if not caught(message["text"], did):
                misses.append((row, message))
        acted = False
    print(f"{os.path.basename(sys.argv[1])[:8]}: {total} pushbacks, {len(misses)} the "
          f"detectors would have missed")
    for push, message in misses:
        print(f"\n--- Juan at {push['at']}: {push['text'][:110]}")
        print(f"    agent said: {message['text'][-260:]}".replace("\n", " "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
