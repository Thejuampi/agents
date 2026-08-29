import re, sys
B = chr(92)
src = open("PAPER.md", encoding="utf-8").read()
src = re.sub(r"(?m)(?<=[^\n])\n(?=[^\n|#])", " ", src)

def esc(t):
    t = t.replace("&", B + "&").replace("%", B + "%").replace("_", B + "_")
    t = t.replace("<", B + "textless{}").replace(">", B + "textgreater{}")
    return t

def inline(t):
    t = esc(t)
    def wrap(name):
        return lambda m: B + name + chr(123) + m.group(1) + chr(125)
    t = re.sub(r"`([^`]+)`", wrap("texttt"), t)
    t = re.sub(r"[*][*]([^*]+)[*][*]", wrap("textbf"), t)
    t = re.sub(r"(?<![*])[*]([^*]+)[*](?![*])", wrap("emph"), t)
    def pair(m):
        return "``" + m.group(1) + "''"
    t = re.sub(chr(34) + "([^" + chr(34) + "]*)" + chr(34), pair, t)
    return t

out = []
rows = []
for line in src.splitlines():
    s = line.rstrip()
    if s.startswith("|"):
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        rows.append(cells)
        continue
    if rows:
        out.append(B + "begin{table}[h]")
        out.append(B + "centering")
        out.append(B + "begin{tabular}{l" + "r" * (len(rows[0]) - 1) + "}")
        out.append(B + "toprule")
        out.append(" & ".join(inline(c) for c in rows[0]) + " " + B + B)
        out.append(B + "midrule")
        for row in rows[1:]:
            out.append(" & ".join(inline(c) for c in row) + " " + B + B)
        out.append(B + "bottomrule")
        out.append(B + "end{tabular}")
        out.append(B + "end{table}")
        rows = []
    if s.startswith("## "):
        out.append(B + "section{" + inline(re.sub(r"^[0-9]+[.] ", "", s[3:])) + "}")
    elif s.startswith("# "):
        continue
    elif s.startswith("**") and s.count("**") >= 2:
        lead, rest = s[2:].split("**", 1)
        out.append(B + "paragraph{" + inline(lead) + "}" + inline(rest))
    else:
        out.append(inline(s))

head = open("paper-head.tex", encoding="utf-8").read()
body = chr(10).join(out)
open("paper.tex", "w", encoding="utf-8").write(head + body + chr(10) + B + "end{document}" + chr(10))
print("wrote paper.tex")
