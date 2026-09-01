#!/usr/bin/env python3
"""The paper counts things the repo can count for itself.

Every number here was written by hand once and went stale the first time a
pattern was added. A claim about the code belongs in a test, so the suite
fails instead of the reader finding it."""
import importlib.util
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ("paper-head.tex", "paper-body.tex", "paper-appendix.tex",
         "paper-results.tex")
COUNTED = (r"(\d{3}) (?:regular expressions|pattern labeling functions"
           r"|patterns are grouped)")


def load(alias, filename):
    spec = importlib.util.spec_from_file_location(
        alias, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


perm = load("perm", "check-permission.py")


def sources():
    lines = 0
    suites = 0
    for name in sorted(os.listdir(HERE)):
        if not name.endswith(".py"):
            continue
        if name.startswith("test_"):
            suites += 1
            continue
        with open(os.path.join(HERE, name), encoding="utf-8") as handle:
            lines += sum(1 for _ in handle)
    return lines, suites


def builds():
    """What the appendix says each stored corpus produces.

    A table is reproducible when the file it was computed on is still named
    and still answers the same. The three builds differ by 20 fires and the
    difference is the whole demotion result, so a benchmark pointed at the
    newest file quietly reports a number no table claims."""
    appendix = dict(tex()).get("paper-appendix.tex", "")
    found = re.findall(
        r"texttt\{(corpus[a-z0-9.-]*\.json)\} & (\d+) & (\d+) & (\d+), ([\d.]+)",
        appendix)
    return {row[0]: (int(row[1]), int(row[2]), int(row[3]), row[4])
            for row in found}


def lanes(name):
    if not os.path.exists(os.path.join(HERE, name)):
        return None
    out = subprocess.run([sys.executable, os.path.join(HERE, "bench-lanes.py"),
                          name], cwd=HERE, capture_output=True, text=True).stdout
    head = re.search(r"(\d+) closings, (\d+) pushes", out)
    shipped = re.search(r"either .shipped.\s+(\d+)\s+([\d.]+)", out)
    if not head or not shipped:
        return None
    return (int(head.group(1)), int(head.group(2)),
            int(shipped.group(1)), shipped.group(2))


def drift():
    """The weekly rates and the stratified test, read off the benchmark.

    These went into the paper the day the drift was found. The corpus moves
    when it is rebuilt and so do they, and a rate quoted in prose has nothing
    holding it to the script that produced it."""
    out = subprocess.run([sys.executable, os.path.join(HERE, "bench-drift.py")],
                         cwd=HERE, capture_output=True, text=True).stdout
    weeks = re.findall(r"(\d{4}-\d{2}-\d{2})\s+\d+\s+\d+\s+([\d.]+)", out)
    test = re.search(r"p ([\d.]+)", out)
    seen = f"{float(test.group(1)):.4f}" if test else ""
    return weeks[:4], seen


def tex():
    out = []
    for name in FILES:
        path = os.path.join(HERE, name)
        if os.path.exists(path):
            out.append((name, open(path, encoding="utf-8").read()))
    return out


def corpus(raw=False):
    path = os.path.join(HERE, "corpus.json")
    if not os.path.exists(path):
        return []
    data = json.load(open(path, encoding="utf-8"))
    if raw:
        return data
    return [r for r in data if not r.get("noise")]


def main():
    failures = []
    cases = 0
    patterns = perm.patterns_for(HERE)
    total = len(patterns)
    doubts = sum(1 for label, _ in patterns if perm.weak(label))

    cases += 1
    for name, body in tex():
        said = {int(n) for n in re.findall(COUNTED, body)}
        if said and said != {total}:
            failures.append(f"{name} counts {sorted(said)}, repo has {total}")

    cases += 1
    splits = []
    for name, body in tex():
        splits += [[int(n) for n in hit]
                   for hit in re.findall(r"(\d+) of the (\d+) are firm", body)]
        splits += [[int(n) for n in hit] for hit in re.findall(
            r"Of (\d+) patterns, (\d+) are firm and (\d+) are doubts", body)]
    for claim in splits:
        want = ([total - doubts, total] if len(claim) == 2
                else [total, total - doubts, doubts])
        if claim != want:
            failures.append(f"the firm split says {claim}, repo has {want}")

    cases += 1
    if not splits:
        failures.append("the paper stopped stating the firm split")

    cases += 1
    for name, body in tex():
        for line in body.splitlines():
            if line.startswith("ef{") or line.startswith("extt"):
                failures.append(f"{name} carries a broken macro: {line[:40]}")

    rows = corpus()
    pushes = sum(1 for r in rows if r.get("push"))
    results = dict(tex()).get("paper-results.tex", "")

    cases += 1
    if rows and str(len(rows)) not in results:
        failures.append(f"the results never state the corpus size {len(rows)}")

    cases += 1
    if rows and str(pushes) not in results:
        failures.append(f"the results never state the push count {pushes}")

    body = dict(tex()).get("paper-body.tex", "")
    lines, suites = sources()

    cases += 1
    if "in one sentence" not in body or "work ask" not in body:
        failures.append("the paper dropped the quick-chat skip")

    cases += 1
    near = f"{round(lines / 100) * 100:,} lines of Python"
    if near not in body:
        failures.append(f"the paper miscounts the code, which is {near}")

    cases += 1
    if f"{suites} test files" not in body:
        failures.append(f"the paper miscounts the suites, which are {suites}")

    whole = "".join(text for _, text in tex())
    named = set(re.findall(r"texttt\{([a-z-]+\.py)\}", whole))

    cases += 1
    missing = sorted(name for name in named if not os.path.exists(
        os.path.join(HERE, name)))
    if missing:
        failures.append("the paper names scripts that do not exist: "
                        + ", ".join(missing))

    cases += 1
    if "stop.json" not in whole:
        failures.append("the paper never names stop.json")
    elif not os.path.exists(os.path.join(HERE, "stop.json")):
        failures.append("the paper names stop.json, which is not in the repo")

    cases += 1
    silent = sorted(name for name in os.listdir(HERE)
                    if name.startswith("bench-") and name not in named)
    if silent:
        failures.append("benchmarks the paper never names: " + ", ".join(silent))

    for name, want in builds().items():
        cases += 1
        got = lanes(name)
        if got != want:
            failures.append(f"{name} prints {got} where the appendix claims {want}")

    results = dict(tex()).get("paper-results.tex", "")
    weeks, chi = drift()

    for week, rate in weeks:
        cases += 1
        if rate not in results:
            failures.append(f"the drift table misses the {week} rate {rate}")

    cases += 1
    if chi and chi not in results:
        failures.append(f"the stratified test now reads p = {chi}")

    raw = corpus(True)
    appendix = dict(tex()).get("paper-appendix.tex", "")

    cases += 1
    if raw and f"{len(raw)} closings" not in appendix:
        failures.append(f"the appendix miscounts the build, which reads {len(raw)}")

    cases += 1
    if "union is 620" in results or "agree on only 253" in results:
        failures.append("results still quotes a union from the wrong build")

    cases += 1
    if "92 closings" not in results or "170 closings" not in results:
        failures.append("results dropped the unique-lane cuts")

    cases += 1
    if "0.213" not in results or "463 closings" not in results:
        failures.append("results dropped the human-subset headline")

    cases += 1
    tree_out = subprocess.run(
        [sys.executable, os.path.join(HERE, "bench-tree.py"),
         "corpus-v4-27b.json"],
        cwd=HERE, capture_output=True, text=True).stdout
    fix = re.search(r"fixtures (\d+), wrong (\d+)", tree_out)
    all_row = re.search(
        r"all closings (\d+) leftover (\d+).*extra_fp (\d+)", tree_out)
    if not fix or not all_row:
        failures.append("bench-tree.py did not print the fixture and leftover rows")
    else:
        nfix, nwrong = fix.group(1), fix.group(2)
        nclose, nleft, nfp = all_row.group(1), all_row.group(2), all_row.group(3)
        whole = "".join(text for _, text in tex())
        if nwrong != "0":
            failures.append(f"the pick-rule fixtures now have {nwrong} wrong")
        if f"{nfix} fixtures" not in whole and "seven fixtures" not in whole:
            failures.append(f"the paper never states the {nfix} fixtures")
        if nleft not in results or "extra false positives" not in results.lower():
            failures.append("results dropped the leftover word row")
        if nclose not in results:
            failures.append(f"results dropped the leftover denominator {nclose}")
        if nfp != "0":
            failures.append(f"leftover extra FP is now {nfp}")

    cases += 1
    readme = open(os.path.join(HERE, "README.md"), encoding="utf-8").read()
    if "## The decision tree" not in readme:
        failures.append("README dropped the English decision-tree section")
    elif "## El árbol de decisiones" in readme or "arbol de decisiones" in readme:
        failures.append("README still describes the tree in Spanish")
    elif "seven fixtures" not in readme:
        failures.append("README dropped the seven-fixture pick rule")
    elif "in one sentence" not in readme:
        failures.append("README dropped the quick-chat skip")

    cases += 1
    blind = subprocess.run(
        [sys.executable, os.path.join(HERE, "label-blind.py"), "score"],
        cwd=HERE, capture_output=True, text=True).stdout
    kappa = re.search(r"Cohen kappa ([\d.]+)", blind)
    seen = kappa.group(1) if kappa else ""
    if not seen or seen not in results:
        failures.append(f"the blind kappa now reads {seen or 'nothing'}")

    print(f"{cases} cases, {len(failures)} failures")
    for line in failures:
        print("  FAIL", line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
