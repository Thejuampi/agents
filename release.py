#!/usr/bin/env python3
"""The release phrase: the only way out of a block that is not doing the work.

Every checker used to let a message through the moment it contained BLOCKED:.
That string is in the source. An agent reads the hook, types the string, and
walks. The escape was cheaper than the work it was guarding.

A phrase fixes that by not existing until the hook decides to hand one out. It
is drawn fresh from the system CSPRNG, so there is nothing in this file to read
and nothing to guess. It is issued only from the second block on the same
chain, so no stop can be escaped on its first attempt - by then the agent has
been sent back once and has done a turn of real work. It is ordered, so half of
it is not enough. It is single use, and issuing a new one voids the last.

The phrase proves the agent read the block. It does not prove the blocker is
real; check-blocked.py still audits that.
"""
import importlib.util
import os
import re
import secrets

_mod = importlib.util.spec_from_file_location(
    "_hook_mod", os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mod.py"))
mod = importlib.util.module_from_spec(_mod)
_mod.loader.exec_module(mod)

_perm = mod.load("check-permission.py")

WORDS = (
    "anvil basalt cinder dovetail ember flint granite harbor ingot jetty "
    "kiln lattice mortise nickel obsidian pumice quarry rivet sandstone tungsten "
    "umber vellum wicket xenon yardarm zircon alloy bramble cistern drift"
).split()

PARTS = 4
BLOCKED = re.compile(r"BLOCKED:", re.IGNORECASE)


def mint():
    """Four word-hex pairs in a random order. Nothing here is derivable from
    the source, so reading this file buys an agent no shortcut."""
    rng = secrets.SystemRandom()
    return [f"{word}-{secrets.token_hex(2)}"
            for word in rng.sample(WORDS, PARTS)]


def render(parts):
    return " ".join(parts)


def normalise(text):
    return re.sub(r"\s+", " ", text or "").strip().lower()


def presented(message, parts):
    """True when the message claims a blocker and carries the whole phrase,
    in order, after the claim. Out of order is a miss; so is a partial."""
    if not parts:
        return False
    mark = BLOCKED.search(message or "")
    if not mark:
        return False
    flat = normalise(message)
    phrase = normalise(render(parts))
    where = flat.find(phrase)
    if where < 0:
        return False
    return where > len(normalise(message[:mark.start()]))


def claims_block(message):
    """Only the agent's own claim counts. Writing about the marker - quoting
    it, or naming it in code - is not writing it, and a message that explains
    how this gate works must not be read as trying to open it.

    Getting this wrong is safe in one direction only. A missed claim falls
    through to the checkers and the model, which is the stricter path; a
    phantom one sends an honest report down the blocker lane it never asked
    for."""
    return bool(BLOCKED.search(_perm.unquoted(message or "")))
