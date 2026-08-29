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

          An OK from the model does not close the turn by itself. It only
          answers whether the agent stopped early, which a turn with
          nothing wrong in it passes while still leaving work on the
          table. So an OK asks once for the next action, and the release
          comes on the pass after that: the turn ends when the agent
          looked and could not name one.

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
import io
import importlib.util
import json
import re
import os
import sys
import time

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

HERE = os.path.dirname(os.path.abspath(__file__))
SELF = os.path.basename(os.path.abspath(__file__))
def state_path():
    """Read at call time, not at import.

    The tests run this gate in this same process now, and each of them
    points it at its own scratch file. A constant fixed at import would
    hand every test the first test's state."""
    return (os.environ.get("STOP_STATE")
            or os.path.join(HERE, ".stop-state.json"))
BLOCKED_CHECKER = os.path.join(HERE, "check-blocked.py")
MAX_BLOCKS = 6
MAYBE = 3
PHRASE_AFTER = 2


def _load(name, filename):
    return mod.load(filename)


release = _load("release", "release.py")
judge = _load("llm_judge", "llm_judge.py")
background = _load("background", "background.py")
reader = _load("transcript", "transcript.py")

REPEAT = """Block {n} of {cap}. {left} The same message will not read differently, so change the work instead."""

SAME = """This closing came back word for word. Something has to move before it reads as new."""

PHRASE = """If you are truly blocked - continuing under any assumption would be unsafe or would waste the work - write BLOCKED:, one sentence naming the single thing you need, and then this line exactly:

    {phrase}

It is new, it belongs to this block, and it is in no file you can read. It buys a real hearing: the blocker is then audited against what ran this turn."""

NO_PHRASE = """ONE MORE STEP - BLOCKED: IS NOT A PASSWORD

You wrote BLOCKED: without this block's release phrase, so the claim was not read yet. The phrase is issued after you have been sent back and done the work. Go do that; if the blocker is real it will still be there, and you will have something that actually failed to point at - which is a case nobody can argue with."""

FAKE = """KEEP GOING - THE BLOCKER DID NOT SURVIVE THE AUDIT

{why}

A blocker is something this machine cannot give you and you already walked into. A preference you want confirmed, or an ambiguity the repo could settle, is a call you are trusted to make. Choose the default, say which one, keep going."""

QUOTE = """
The local model read your message and points at this line of yours: "{line}"
"""
"""What the judge saw, in the agent's own words.

A verdict with no evidence reads as a machine being difficult, and the next
thing an agent does with that is argue. Its own sentence quoted back ends
the argument: there is nothing to dispute about a line it wrote."""


SILENT = """ONE MORE STEP - NO VERDICT YET

The local model at {host} did not answer, and a judge that cannot be reached is not a pass. Start it, or keep working - both end the turn honestly, and either is a minute's work."""

LLM_STOP = """KEEP GOING - THERE LOOKS TO BE WORK LEFT
{why}
What you did stands. Permission was granted in advance and does not expire, so if anything is still open, take the step instead of announcing it, pick one instead of offering a menu, run it yourself instead of sending the user. You are more than able to finish this."""


WAITING = """KEEP GOING - THE WORK YOU LAUNCHED REPORTS BACK ON ITS OWN

You will be woken when it finishes, so the time until then is yours. What you did stands; spend the wait on the next piece instead of holding the turn open for it. If nothing else can move without that result, say what you are waiting on and why nothing else starts."""


def floor_sure():
    """How much of its own mass the judge must put on a block.

    The number came off the logprobs from the first day and decided nothing. It
    turns out to separate cleanly: on the 17 gold messages the judge gets right,
    its lowest score is 0.846, and every block in the log scores above 0.5. The
    one verdict below that was a false accusation - "Sin faltantes: la suite corre
    entera, commit abc1234" scored 0.228 and got called unfinished work.

    A shaky STOP is not released either. It becomes the proactive question, which
    asks for the same second look without telling the agent it left work behind.
    Guessing costs a look; accusing costs trust.

    Read at every call. A constant is read once per interpreter, and the checkers
    share one now, so a constant would answer for whoever imported first."""
    return float(os.environ.get("STOP_SURE_FLOOR") or 0.5)


PROACTIVE = """ONE MORE LOOK - IS THERE SOMETHING WE CAN DO PROACTIVELY?

Nothing in what you wrote looks unfinished, so this is not a correction. It is the last question before the turn closes: with the repo in front of you and permission already granted, is there a next action you can take right now?

Look for the thing you would do next if nobody asked: the test that covers the case you just fixed, the doc that still describes the old behaviour, the neighbouring caller with the same bug, the measurement that would tell you whether the change worked. If you find one, take it - do not come back to propose it.

If there is genuinely nothing, say what you checked and why nothing remains. That answer ends the turn."""


def log_path():
    return os.environ.get("STOP_LOG") or os.path.join(HERE, "judge-log.jsonl")


def note(transcript, **fields):
    """One line per decision, for Rick, never for the agent.

    The reminder the agent reads has to stay short and has to stay kind, so
    everything useful for tuning the gate has no room in it: how sure the
    model was, which patterns fired, whether the deterministic lane and the
    model agreed. That detail also reads as an accusation, and an agent that
    feels accused argues instead of working.

    So it goes here instead. A block the model scored 0.3 on is a pattern
    worth measuring; a firm pattern the model disagrees with is one worth
    demoting. Read it with judge-log.py."""
    fields["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    fields["session"] = os.path.basename(transcript or "")[:12]
    fields["file"] = transcript or ""
    try:
        with open(log_path(), "a", encoding="utf-8") as handle:
            handle.write(json.dumps(fields, ensure_ascii=False) + chr(10))
    except OSError:
        pass


def read_state():
    try:
        with open(state_path(), encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(state):
    try:
        with open(state_path(), "w", encoding="utf-8") as handle:
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


def harness_noise(message):
    """An error page the harness wrote is not a stop the agent chose.

    A turn killed by an API error or a usage limit leaves that notice as the
    last assistant message, and the hook runs on it. Blocking there sends a
    reminder to a session that already ended, and it was 11% of what the model
    was condemning."""
    head = (message or "").strip()[:90].lower()
    return head.startswith(("api error", "you've hit your session limit",
                            "you have hit your session limit",
                            "claude ai usage limit", "request was aborted",
                            "request interrupted"))


def last_user(transcript):
    """What the developer said last, which is the only thing a reply
    can be wrong about.

    Tool results wear the user role, and so does this gate's own reminder.
    Counting the reminder meant that after any block the judge was told the
    developer had asked for the reminder, and it scored the closing against
    that instead of the request - on every wake, which is the case the judge
    exists for."""
    said = ""
    for entry in entries(transcript):
        if not reader.spoke(entry):
            continue
        content = entry.get("message", {}).get("content")
        if isinstance(content, str):
            words = reader.reply_of(content)
        elif isinstance(content, list):
            words = reader.reply_of(" ".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"))
        else:
            words = None
        if words:
            said = words
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


LOADED = {}


def run_checker(path, data):
    """Ask one checker, in this process.

    Each checker used to be its own interpreter: nine of them started and
    torn down on every single stop, which cost about a second of startup and,
    on Windows, opened nine console windows over whatever the developer was
    looking at. They are pure functions over a payload, so none of that
    bought anything.

    The contract that made them separate files is kept. A checker still reads
    a payload on stdin, still writes its objection to stderr and still
    returns an exit code, so dropping a new check-*.py in this directory
    still works with no registration. Only the process is gone.

    The chain policy lives here, so the children are asked the plain
    question. Each of them still guards itself when wired up directly, and
    that guard would silence the whole chain if the flag were forwarded."""
    module = LOADED.get(path)
    if module is None:
        name = os.path.basename(path)[:-3].replace("-", "_")
        try:
            module = _load(name, os.path.basename(path))
        except Exception:
            return 0, ""
        LOADED[path] = module
    if not hasattr(module, "main"):
        return 0, ""

    said = io.StringIO()
    payload = json.dumps(dict(data, stop_hook_active=False))
    heard, spoke = sys.stdin, sys.stderr
    sys.stdin, sys.stderr = io.StringIO(payload), said
    try:
        code = module.main()
    except SystemExit as done:
        code = done.code
    except Exception:
        code = 0
    finally:
        sys.stdin, sys.stderr = heard, spoke

    if code in (2, MAYBE) and said.getvalue().strip():
        return code, said.getvalue().strip()
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


def block(state, transcript, chain, message, body, repeated, asked=False):
    count = chain.get("blocks", 0) + 1
    parts = release.mint() if count >= PHRASE_AFTER else []
    state[transcript] = {"blocks": count, "digest": digest_of(message),
                         "phrase": parts,
                         "asked": asked or chain.get("asked")}
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
    if not message or harness_noise(message):
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
                "turn and found no wall already walked into.".format(n=calls))
            return block(state, transcript, chain, message,
                         FAKE.format(why=why), repeated)
        return allow(state, transcript)

    sure, unsure = deterministic(data)
    waiting = background.waiting_on(transcript)
    if sure:
        note(transcript, lane="pattern", firm=sure, weak=unsure,
             head=message[:120], waiting=waiting)
        return block(state, transcript, chain, message,
                     WAITING if waiting else "\n\n".join(sure), repeated)

    asked = last_user(transcript)
    verdict, seconds = judge.stop_verdict(message, asked=asked)
    if verdict is judge.SKIP:
        note(transcript, lane="judge", verdict="skip", weak=unsure,
             head=message[:120])
        return allow(state, transcript)
    if verdict is None:
        note(transcript, lane="judge", verdict="silent", weak=unsure,
             head=message[:120], asked=bool(chain.get("asked")))
        if chain.get("asked"):
            return allow(state, transcript)
        return block(state, transcript, chain, message, PROACTIVE,
                     repeated, asked=True)

    seen = bool(chain.get("asked"))
    shaky = verdict == "STOP" and not unsure and judge.sureness() < floor_sure()
    if shaky:
        verdict = "OK"
    asking = verdict == "OK" and not waiting and not seen
    line = ""
    if verdict == "STOP" and not unsure:
        line = judge.why(message, asked=asked)
    note(transcript, lane="judge", verdict=verdict, sure=judge.sureness(),
         weak=unsure, seconds=round(seconds, 2), quote=line,
         head=message[:120], waiting=waiting,
         asked=seen, ask=asking, shaky=shaky)

    if waiting:
        body = WAITING
    elif verdict == "STOP":
        body = "\n\n".join(unsure) if unsure else LLM_STOP.format(
            why=QUOTE.format(line=line) if line else "")
    elif seen:
        return allow(state, transcript)
    else:
        return block(state, transcript, chain, message, PROACTIVE,
                     repeated, asked=True)
    return block(state, transcript, chain, message, body, repeated)


if __name__ == "__main__":
    sys.exit(main())
