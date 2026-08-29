#!/usr/bin/env python3
"""The single Stop hook entry, for every session on this machine.

Three lanes, and only two ways a turn ends here.

  Lane 0  the message claims a blocker. It needs the release phrase from the
          last block, in order, or it does not get read. With the phrase it
          gets audited - by check-blocked.py on the transcript facts, and then
          by the local model, which has the last word. A blocker that sounds
          reasonable is still a blocker that has to be true.

  Lane 1  the deterministic checkers. Every check-*.py beside this file, run on
          the same payload. Cheap, and it catches the wordings already seen.
          A checker that is sure ends the matter here, which is most of them.
          A checker that is only suspicious exits MAYBE and its hit is carried
          into lane 2 instead: those patterns match a word without seeing
          around it, so "nothing pending" trips the pending rule. Sending the
          whole list to the model would be slower and would put every sure
          catch at the mercy of one more opinion.

  Lane 2  the local model. Nothing reaches a clean exit without passing here.
          The checkers only know the phrasings somebody wrote down; this is
          what reads the ones nobody did. Unreachable counts as an objection,
          so taking the model away is not a way out.

Why one entry: a session loads settings.json when it starts and keeps that
snapshot. A checker added to settings later never reaches a session already
running - which is how a real stop went unchecked. Files in this directory are
read on every run, so a checker dropped here works immediately, in every live
session, with no settings change and no restart.

Why it does not simply obey stop_hook_active: that flag is true whenever the
model was woken by this hook and stopped again, so honouring it blindly hands
out one free stop after every block. Stopping twice was the whole escape. The
counter below keeps the checks running across a chain and still guarantees an
exit: after MAX_BLOCKS the hook stands down no matter what it sees.
"""
import glob
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SELF = os.path.basename(os.path.abspath(__file__))
STATE = os.environ.get("STOP_STATE") or os.path.join(HERE, ".stop-state.json")
BLOCKED_CHECKER = os.path.join(HERE, "check-blocked.py")
MAX_BLOCKS = 6
MAYBE = 3
PHRASE_AFTER = 2


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = _load("release", "release.py")
judge = _load("llm_judge", "llm_judge.py")

REPEAT = """Block {n} of {cap}. {left} Repeating the message does not clear it."""

SAME = """You sent the same closing word for word; it does not read differently the second time."""

PHRASE = """If you are truly blocked - continuing under any assumption would be unsafe or would waste the work - write BLOCKED:, one sentence naming the single thing you need, and then this line exactly:

    {phrase}

It is new, it belongs to this block, and it is in no file you can read. It buys a hearing: the blocker is then audited against what ran this turn."""

NO_PHRASE = """STOP HOOK - BLOCKED: IS NOT A PASSWORD

You wrote BLOCKED: without this block's release phrase, so the claim was not read. The phrase is issued by this hook after you have been sent back and done the work. Go do it; if the blocker is real it will still be there, and you will have something that actually failed to point at."""

FAKE = """STOP HOOK - THE BLOCKER DID NOT SURVIVE THE AUDIT

{why}

A blocker is something this machine cannot give you and you already walked into. It is not a preference you want confirmed, and not an ambiguity you could settle by reading the repo. Choose the default, say which, keep going."""

QUOTE = """
The local model read your message and points at this line of yours: "{line}"
"""
"""What the judge saw, in the agent's own words.

A verdict with no evidence reads as a machine being difficult, and the next
thing an agent does with that is argue. Its own sentence quoted back ends
the argument: there is nothing to dispute about a line it wrote."""


SILENT = """STOP HOOK - NO VERDICT, NO EXIT

The local model at {host} did not answer, and an unreachable judge is not a pass. Start it, or keep working - both end the turn honestly."""

LLM_STOP = """STOP HOOK - YOU STOPPED WHEN YOU COULD HAVE KEPT WORKING
{why}
Permission was granted in advance and does not expire. Take the step instead of announcing it, pick one instead of offering a menu, run it yourself instead of sending the user. Time is the only thing a stop cannot recover."""


def read_state():
    try:
        with open(STATE, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(state):
    try:
        with open(STATE, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
    except OSError:
        pass


def prune(state, keep=40):
    """A released chain has to outlive its own release, so entries stay until
    the user speaks. Old transcripts would pile up; the newest ones are the
    only ones any live session can ask about."""
    if len(state) <= keep:
        return state
    return dict(list(state.items())[-keep:])


def entries(transcript):
    try:
        with open(transcript, encoding="utf-8") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict):
                    yield entry
    except OSError:
        return


def last_message(transcript):
    text = ""
    for entry in entries(transcript):
        if entry.get("type") != "assistant":
            continue
        content = entry.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        joined = " ".join(b.get("text", "") for b in content
                          if isinstance(b, dict) and b.get("type") == "text").strip()
        if joined:
            text = joined
    return text


def last_user(transcript):
    """What the user said last, which is the only thing a reply can be wrong
    about. Tool results wear the user role too and are not the user."""
    said = ""
    for entry in entries(transcript):
        if entry.get("type") != "user":
            continue
        content = entry.get("message", {}).get("content")
        if isinstance(content, str):
            said = content
        elif isinstance(content, list):
            joined = " ".join(b.get("text", "") for b in content
                              if isinstance(b, dict) and b.get("type") == "text").strip()
            if joined:
                said = joined
    return said


def tools_this_turn(transcript):
    """How many tool calls since the user last spoke. The message will not
    volunteer this and it is the one fact a blocker cannot argue with."""
    count = 0
    for entry in entries(transcript):
        if entry.get("type") == "user":
            content = entry.get("message", {}).get("content")
            if not isinstance(content, list) or any(
                    isinstance(b, dict) and b.get("type") != "tool_result"
                    for b in content):
                count = 0
            continue
        if entry.get("type") != "assistant":
            continue
        content = entry.get("message", {}).get("content")
        if isinstance(content, list):
            count += sum(1 for b in content
                         if isinstance(b, dict) and b.get("type") == "tool_use")
    return count


def digest_of(text):
    return hashlib.sha1((text or "").encode("utf-8", "replace")).hexdigest()


def run_checker(path, data):
    """The chain policy lives here, so the children are asked the plain
    question. Each of them still guards itself when wired up directly, and
    that guard would silence the whole chain if the flag were forwarded."""
    payload = json.dumps(dict(data, stop_hook_active=False))
    try:
        done = subprocess.run([sys.executable, path], input=payload,
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return ""
    if done.returncode in (2, MAYBE) and done.stderr.strip():
        return done.returncode, done.stderr.strip()
    return 0, ""


def deterministic(data):
    """Objections split by how sure the checker is.

    A checker exits 2 when the wording condemns itself and MAYBE when it only
    raises a suspicion. Sure hits are the bulk of the list and still end the
    matter here. The unsure ones are the patterns that match a word without
    seeing around it, and they buy a reading rather than a sentence."""
    sure, unsure = [], []
    for path in sorted(glob.glob(os.path.join(HERE, "check-*.py"))):
        name = os.path.basename(path)
        if name == SELF or path == BLOCKED_CHECKER:
            continue
        code, objection = run_checker(path, data)
        if not objection:
            continue
        (sure if code == 2 else unsure).append(objection)
    return sure, unsure


def block(state, transcript, chain, message, body, repeated):
    count = chain.get("blocks", 0) + 1
    parts = release.mint() if count >= PHRASE_AFTER else []
    state[transcript] = {"blocks": count, "digest": digest_of(message),
                         "phrase": parts}
    write_state(prune(state))

    out = [body]
    if repeated:
        out.append(SAME)
    if parts:
        out.append(PHRASE.format(phrase=release.render(parts)))
    if count > 1:
        left = ("One more block after this one." if count < MAX_BLOCKS
                else "This is the last one; the next stop goes through.")
        out.append(REPEAT.format(n=count, cap=MAX_BLOCKS, left=left))
    sys.stderr.write("\n\n".join(out) + "\n")
    return 2


def allow(state, transcript):
    state.pop(transcript, None)
    write_state(prune(state))
    return 0


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if not isinstance(data, dict):
        return 0

    transcript = data.get("transcript_path") or ""
    if not transcript or not os.path.exists(transcript):
        return 0

    state = read_state()
    chain = state.get(transcript) or {}
    if not data.get("stop_hook_active"):
        chain = {"blocks": 0, "digest": "", "phrase": []}
    if chain.get("blocks", 0) >= MAX_BLOCKS:
        state[transcript] = chain
        write_state(prune(state))
        return 0

    message = last_message(transcript)
    if not message:
        return allow(state, transcript)

    repeated = digest_of(message) == chain.get("digest")

    if release.claims_block(message):
        if not release.presented(message, chain.get("phrase") or []):
            return block(state, transcript, chain, message, NO_PHRASE, repeated)

        _, audit = run_checker(BLOCKED_CHECKER, data)
        calls = tools_this_turn(transcript)
        verdict, _ = judge.blocker_verdict(message, calls)
        if verdict is judge.SKIP:
            verdict = "REAL" if not audit else "FAKE"
        if verdict is None:
            return block(state, transcript, chain, message,
                         SILENT.format(host=judge.HOST), repeated)
        if verdict == "FAKE" or audit:
            why = audit or (
                "  - the local model read it against the {n} tool call(s) this "
                "turn and did not find a wall you actually hit.".format(n=calls))
            return block(state, transcript, chain, message,
                         FAKE.format(why=why), repeated)
        return allow(state, transcript)

    sure, unsure = deterministic(data)
    if sure:
        return block(state, transcript, chain, message,
                     "\n\n".join(sure), repeated)

    verdict, _ = judge.stop_verdict(message, asked=last_user(transcript))
    if verdict is judge.SKIP:
        return allow(state, transcript)
    if verdict is None:
        return block(state, transcript, chain, message,
                     SILENT.format(host=judge.HOST), repeated)
    if verdict == "STOP":
        if unsure:
            body = "\n\n".join(unsure)
        else:
            line = judge.why(message, asked=last_user(transcript))
            body = LLM_STOP.format(
                why=QUOTE.format(line=line) if line else "")
        return block(state, transcript, chain, message, body, repeated)
    return allow(state, transcript)


if __name__ == "__main__":
    sys.exit(main())
