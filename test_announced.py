#!/usr/bin/env python3
"""The cases that decide whether the tail is an order or a report.

Every string here came off a real transcript. The false positives are the
expensive half: a gate that nags a turn which correctly handed a decision back
gets ignored, and then it catches nothing.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "announced", os.path.join(HERE, "check-announced.py"))
announced = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(announced)

BLOCK = 2
SOFT = 3
PASS = 0

CASES = (
    ("Sigo con `query`, `store` y el escritor de indice.", BLOCK),
    ("Sigo con la Ola 4.", BLOCK),
    ("Arranco con la Ola 1.", BLOCK),
    ("Empiezo por Ola 3.", BLOCK),
    ("Ahora voy a escribir el store.", BLOCK),
    ("Next I will wire the search package.", BLOCK),
    ("Next, I'll wire the search package.", BLOCK),
    ("I'll add the triage badge in the header.", BLOCK),
    ("I will now continue with the store.", BLOCK),
    ("Commits `4280560` y `42ac4b3`; sigo con P24.", BLOCK),

    ("Sigo esperando al agente de diseno.", PASS),
    ("Sigo cuando vuelvan con el mapa de consumidores.", PASS),
    ("Sigo con eso si queres.", PASS),
    ("Sigo con la Ola 2 cuando digas.", PASS),
    ("Sigue pendiente, sin tocar hasta que confirmes.", PASS),
    ("sigue cargando el companyfacts entero a un Value.", PASS),
    ("Necesito tu decision: mover la barra, o abrir una lane separada.", PASS),
    ("Baje el error a 40.9%. Necesito tu decision sobre los 49 archivos.", PASS),
    ("Cual preferis, Win32 crudo o walk?", PASS),
    ("Listo. Los tests pasan y el indice esta escrito.", PASS),
    ("I will not do that.", PASS),

    ("Falta el smoke manual de la GUI, que sigue pendiente.", SOFT),
    ("The watcher is not yet wired.", SOFT),
)


def main():
    var_failures = []
    for text, want in CASES:
        var_got, _ = announced.verdict(text)
        if var_got != want:
            var_failures.append("got %d want %d for %r" % (var_got, want, text))
    for line in var_failures:
        sys.stderr.write(line + "\n")
    print("%d cases, %d failures" % (len(CASES), len(var_failures)))
    return 1 if var_failures else 0


if __name__ == "__main__":
    sys.exit(main())
