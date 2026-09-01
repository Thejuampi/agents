#!/usr/bin/env python3
"""After the hook fires, does the agent go back to work or stop again?

A reminder that fires and is ignored is worse than none: it teaches the model
the alarm is noise. This measures compliance, so the next fix targets what the
reminder failed to do rather than what it failed to detect.

Usage: audit-compliance.py <transcript.jsonl>
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


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
                tools = [b.get("name") for b in content
                         if isinstance(b, dict) and b.get("type") == "tool_use"]
            else:
                text, tools = (content or "").strip(), []
            out.append({"kind": entry.get("type"), "text": text, "tools": tools,
                        "at": entry.get("timestamp", "")[:19]})
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    data = rows(sys.argv[1])
    fired = obeyed = ignored = 0
    for i, row in enumerate(data):
        if "STOP HOOK" not in row["text"] or row["kind"] != "user":
            continue
        fired += 1
        worked = False
        for later in data[i + 1:]:
            if later["kind"] == "user" and "STOP HOOK" not in later["text"]:
                break
            if later["tools"]:
                worked = True
                break
        if worked:
            obeyed += 1
        else:
            ignored += 1
            print(f"  ignored at {row['at']}: {row['text'].splitlines()[0][:70]}")
    print(f"{os.path.basename(sys.argv[1])[:8]}: fired {fired}, worked after {obeyed}, "
          f"stopped anyway {ignored}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
