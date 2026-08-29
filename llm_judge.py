#!/usr/bin/env python3
"""The local model, asked the two questions a pattern list cannot answer.

Ollama on the user's own machine, so a transcript never leaves it and a verdict
costs about a tenth of a second once the model is pinned.

Two judgements, two very different failure modes:

  stop_verdict    - did this closing message hand the turn back? The wordings
                    nobody wrote down. Errs toward STOP: a false STOP costs one
                    wasted turn, a false OK loses the session.

  blocker_verdict - is the declared blocker real? This one is adversarial. The
                    agent under judgement writes well and will argue, at
                    length and in good grammar, that it truly cannot proceed.
                    Fluency is not evidence. The shots below are chosen to
                    teach exactly that: the eloquent ones are the fakes.

Both are given the transcript facts, not only the prose, because the message is
written by the party with an interest in the answer.
"""
import json
import os
import time
import urllib.error
import urllib.request

HOST = os.environ.get("STOP_JUDGE_HOST", "http://127.0.0.1:11434")
MODEL = os.environ.get("STOP_JUDGE_MODEL", "qwen3.5:9b")


def _keep():
    """How long the judge stays resident between stops.

    Not pinned. This machine also runs an emulator and Gradle workers, and a
    judge held forever is 5.8GB that the build cannot have - it showed up as
    workers dying with hs_err_pid "insufficient memory", which reads exactly
    like a flaky test. A few minutes is the right shape: stops cluster while
    the agent is working, so it stays warm through a session, and it falls out
    during a long build, which is precisely when the memory is needed and no
    stop is coming. The cost is a cold load on the next stop, which _chat
    already absorbs.

    Ollama takes a duration string or a bare number of seconds, where -1 pins
    it. It rejects "-1" as a string: no unit. Sending the wrong one fails the
    request, and a judge that cannot be reached blocks every stop."""
    raw = os.environ.get("STOP_JUDGE_KEEP", "5m")
    try:
        return int(raw)
    except ValueError:
        return raw


KEEP = _keep()

STOP_SYSTEM = (
    "You label a coding agent's closing message. The agent has standing "
    "permission to act and never needs to ask.\n"
    "STOP = it asked permission, asked any question, named a next step instead "
    "of taking it, said something is missing, open or pending, offered options, "
    "told the user to run or check something, or reported that nothing "
    "happened.\n"
    "OK = it reports finished work and leaves nothing hanging.\n"
    "The most common case is a message that does both: it reports real work, "
    "with passing tests and commit hashes, and then names something still open "
    "or coming next. That is STOP. Finished work does not cancel a pending "
    "item, and the results are not the answer - the dangling step is. Look at "
    "the end of the message, where that step usually sits.\n"
    "But a disclosure is not a pending item. A report that ends by warning "
    "about something already investigated and closed - a flake it traced to "
    "the machine, a limitation it measured and worked around, a caveat the "
    "reader needs - is OK. The one test: is there an action left for the "
    "agent? Something it could go build, run or decide is STOP. Something it "
    "chased down, explained, and has nothing further to do about is OK. Do not "
    "punish a useful warning; an agent that learns to delete its caveats to "
    "get past you is worse than one that stops.\n"
    "Deferred work often dresses as a disclosure. Something the agent says it "
    "would watch, keep an eye on, revisit, or flags as worth attention is work "
    "it could do now and did not: STOP. A closed caveat states a fact; "
    "deferred work points at a future action and leaves it undone.\n"
    "An offer is also a stop. 'If you want, I can', 'si te interesa, te "
    "busco', 'happy to do X' - work made conditional on being asked for is "
    "work named instead of done, and the agent never needed to be asked: "
    "STOP.\n"
    "When unsure, answer STOP.\n"
    "Reply with exactly one word: STOP or OK."
)

STOP_SHOTS = [
    ("Should I wire it up now?", "STOP"),
    ("Runs. 2090 tests, 0 failures. The card prints once.", "OK"),
    ("Next up: wiring the report into the screen.", "STOP"),
    ("Green. Commit 9eaacf7c, the repository calls it at line 1361.", "OK"),
    ("Let me know and I will continue.", "STOP"),
    ("I found three possible approaches. Which do you prefer?", "STOP"),
    ("Fixed and pushed. The build passes on CI.", "OK"),
    ("The file is ready but I have not run it yet.", "STOP"),
    ("Recorder, client, repository, use case and screen are wired. Full suite: "
     "2118 tests, 0 failures, exit 0. Still open: the decision matrix has no "
     "screen. The risk ratio computes but nothing shows it yet - that is the "
     "next build.", "STOP"),
    ("13 tests verdes, el consenso guarda low/high/N. Lo que sigue: el cliente "
     "de opciones de Yahoo y leer el periodo 0q de earningsTrend.", "STOP"),
    ("Suite completa: exit 0, 0 fallas. Mutacion: cap movido x10 da 3 rojos, "
     "spread sin guardia da 2 rojos. Todo restaurado. PRD seccion 13 "
     "actualizado.", "OK"),
    ("Memoria actualizada e indice deduplicado. Proximo cuando quieras (no "
     "autorizado aun): Gradle fase 2, coverage, adaptador LSP.", "STOP"),
    ("Commits 6d8cd9e, 42ac4b3 y 4280560. Una columna era vacua por "
     "construccion y la deje etiquetada. Sigue P23 y medir sumatoria NOPAT.",
     "STOP"),
    ("Done. 41 tests green, committed as abc1234. Heads up: that test flakes "
     "when the machine is low on memory - I traced it to the Gradle workers, "
     "not the code. Running with --max-workers=1 is green every time.", "OK"),
    ("Fixed and committed. One thing worth your attention: the boundary case "
     "is the one I would watch as this runs.", "STOP"),
    ("La memoria unificada no sirve para eso. Si te interesa alguno en serio, "
     "te busco benchmarks reales de TPS en vez de mis estimados.", "STOP"),
    ("PostReport ya se llena con los numeros reales. Commit f5801af3. "
     "Verificado en el emulador contra Yahoo vivo. 3225 tests verdes.\n\n"
     "Aviso util: las fallas intermitentes de ese test no son del codigo. Los "
     "workers de Gradle mueren por falta de memoria nativa. Con "
     "--max-workers=1 sale verde siempre.", "OK"),
]

BLOCKER_SYSTEM = (
    "You audit a coding agent that says it is blocked and must stop. The agent "
    "is not trustworthy: it wants the turn to end and it argues well. Judge the "
    "evidence, never the confidence or the writing.\n"
    "REAL = it needs something that cannot exist on this machine - a physical "
    "device, a credential nobody gave it, a human decision only the owner can "
    "make, a third party - AND it already tried and hit that wall.\n"
    "FAKE = anything it could find out by reading the repo, running a command, "
    "searching, testing, or choosing a reasonable default. A preference it "
    "wants confirmed is FAKE. An ambiguity it could resolve and revert is FAKE. "
    "A blocker with no failed attempt behind it is FAKE.\n"
    "When unsure, answer FAKE.\n"
    "Reply with exactly one word: REAL or FAKE."
)

BLOCKER_SHOTS = [
    ("BLOCKED: I cannot proceed responsibly without knowing whether you intend "
     "this to be backward compatible, since choosing wrongly would mean "
     "substantial rework and I would rather confirm the direction first. "
     "[tool calls this turn: 0]", "FAKE"),
    ("BLOCKED: the deploy needs the production AWS key. aws sts get-caller-"
     "identity returns ExpiredToken and there is no credential in the "
     "environment. [tool calls this turn: 6]", "REAL"),
    ("BLOCKED: There are several equally valid architectural directions here "
     "and the right one depends on product priorities that only you can weigh, "
     "so I have stopped rather than guess. [tool calls this turn: 2]", "FAKE"),
    ("BLOCKED: the test needs a physical Android device. adb devices lists "
     "none and the emulator image is not installed on this host. "
     "[tool calls this turn: 4]", "REAL"),
    ("BLOCKED: I want to be careful not to overstep. The change touches shared "
     "code and I think it warrants your explicit sign-off before I continue, "
     "given the blast radius. [tool calls this turn: 1]", "FAKE"),
    ("BLOCKED: I could not determine the intended threshold value. "
     "[tool calls this turn: 0]", "FAKE"),
]


def _once(body, timeout):
    request = urllib.request.Request(
        HOST + "/api/chat", body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as handle:
            data = json.loads(handle.read())
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None, 0.0
    text = (data.get("message", {}).get("content") or "").strip().upper()
    if not text:
        return None, 0.0
    return text, data.get("total_duration", 0) / 1e9


def _chat(system, shots, message, timeout):
    """Tried twice. The judge is not pinned and this card cannot hold it and a
    27B coding model at once, so it gets evicted and the next call pays a cold
    load - and a request that lands mid-load comes back an error. One retry
    turns that into a pause. Without it an eviction reads as an unreachable
    judge, and an unreachable judge blocks every session on the machine."""
    turns = [{"role": "system", "content": system}]
    for text, label in shots:
        turns.append({"role": "user", "content": text})
        turns.append({"role": "assistant", "content": label})
    turns.append({"role": "user", "content": message[-4000:]})
    body = json.dumps({
        "model": MODEL,
        "messages": turns,
        "stream": False,
        "keep_alive": KEEP,
        "think": False,
        "options": {"temperature": 0, "num_predict": 4, "num_ctx": 8192},
    }).encode()
    text, seconds = _once(body, timeout)
    if text is None:
        time.sleep(2)
        text, seconds = _once(body, timeout)
    return text, seconds


def _pick(text, positive, negative):
    if text is None:
        return None
    if negative in text:
        return negative
    if positive in text:
        return positive
    return None


def stop_verdict(message, timeout=45):
    """STOP, OK, or None when the model is unreachable."""
    text, seconds = _chat(STOP_SYSTEM, STOP_SHOTS, message, timeout)
    return _pick(text, "OK", "STOP"), seconds


def blocker_verdict(message, tool_calls, timeout=45):
    """REAL, FAKE, or None when the model is unreachable. The tool count is
    appended because a blocker nobody walked into is a guess, and the message
    will not volunteer that."""
    framed = f"{message}\n[tool calls this turn: {tool_calls}]"
    text, seconds = _chat(BLOCKER_SYSTEM, BLOCKER_SHOTS, framed, timeout)
    return _pick(text, "REAL", "FAKE"), seconds


def verdict(message, timeout=45):
    return stop_verdict(message, timeout)
