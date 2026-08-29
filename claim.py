#!/usr/bin/env python3
"""The words an agent uses when it says the work is delivered.

Two checkers ask git something, and git is the expensive question in this
directory: on Windows its helper processes flash a console that no flag of
ours reaches. So neither one asks it while the work is still being written.
They ask when the agent claims the thing is finished, which is the only moment
the answer changes anything."""
import re

CLAIM = re.compile(
    r"\blisto\b|\bqueda (listo|cerrado|cableado)|cerrado y|cableado hasta|"
    r"\bterminad[oa]\b|\bcompleto\b|suite completa|0 fallas|0 failures|"
    r"todo verde|all green|\bship(ped|s)?\b|de punta a punta|"
    r"\bdone\b|\bit works\b|ya funciona|funciona\b.{0,20}\bahora\b|"
    r"\bexit 0\b|build successful",
    re.IGNORECASE,
)
