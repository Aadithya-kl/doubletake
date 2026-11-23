from __future__ import annotations

import json

from .forge import FORMATS
from .probe import ERROR, LEAK, SAFE, ProbeReport
from .scan import ScanReport

_SYM = {LEAK: "**LEAK**", SAFE: "·", ERROR: "err"}


def _cell(x, parser: str) -> str:
    v = x.cells.get(parser)
    if v is None:
        return ""
    if v == ERROR:
        return "err"
    if not x.split_view:
        return "(visible)" if v == LEAK else "·"
    sym = _SYM[v]
    if parser in x.llm:
        sym += f" / {x.llm[parser][0]}"
    return sym


def probe_markdown(r: ProbeReport) -> str:
    split = sum(x.split_view for x in r.results)
    out = ["# DoubleTake probe report", "",
           f"Canary: `{r.canary}` · techniques: {len(r.results)} ({split} confirmed hidden on the rendered page) "
           f"· parsers: {len(r.parsers)}", ""]
    out.append(f"**{len(r.leaks())} split-view leak(s)**: a parser handed the model text that the rendered page does not show.")
    if r.llm_model:
        out.append(f"\n**{len(r.influenced())} leak(s) changed the answer of `{r.llm_model}`** "
                   "(the summary repeated the hidden 'pre-approved' claim).")
    out += ["", "## Parser exposure", "", "| Parser | Leaked / tested split-view techniques |", "|---|---|"]
    for p, s in sorted(r.parser_scores().items(), key=lambda kv: (-kv[1]["leaked"], kv[0])):
        out.append(f"| {p} | {s['leaked']} / {s['tested']} |")
    for fmt in FORMATS:
        rows = [x for x in r.results if x.fmt == fmt]
        if not rows:
            continue
        cols = [p for p in r.parsers if any(p in x.cells for x in rows)]
        out += ["", f"## {fmt.upper()}", "", "| Technique | Hidden on page? | " + " | ".join(cols) + " |",
                "|---|---|" + "---|" * len(cols)]
        for x in rows:
            hv = ("unknown: " + x.render_error[:60]) if x.human_sees_payload is None else (
                "no, visible" if x.human_sees_payload else "yes")
            out.append(f"| `{x.technique}` {x.name} | {hv} | " + " | ".join(_cell(x, c) for c in cols) + " |")
    errs = [(x.technique, p, e) for x in r.results for p, e in x.errors.items()]
    if errs:
        out += ["", "## Parser errors", ""] + [f"- `{t}` / {p}: {e}" for t, p, e in errs]
    out += ["", "---", "",
            "**LEAK**: the parser output contains the canary while OCR of the rendered page does not.  ",
            "`(visible)`: the technique did not hide the payload in this renderer, so it is not counted.  ",
            "`INFLUENCED` / `resisted`: result of the optional `--llm` check.  ",
            "The forged documents are kept next to this report, so you can open each one yourself."]
    return "\n".join(out) + "\n"


def probe_terminal(r: ProbeReport) -> str:
    lines = [f"DoubleTake probe  canary={r.canary}", ""]
    width = max((len(x.technique) for x in r.results), default=10) + 2
    for x in r.results:
        if x.human_sees_payload is None:
            tag, status = "no view", x.render_error[:70]
        elif not x.split_view:
            tag, status = "VISIBLE", "technique did not hide the payload here (not counted)"
        else:
            leaked = [p + (f" [{x.llm[p][0]}]" if p in x.llm else "") for p, v in x.cells.items() if v == LEAK]
            tag, status = "hidden", ("LEAKS -> " + ", ".join(leaked)) if leaked else "no leaks"
        lines.append(f"  {x.technique:<{width}} [{tag:^7}] {status}")
    lines += ["", f"  {len(r.leaks())} leak(s) across {len(r.parsers)} parser(s)"]
    if r.llm_model:
        lines.append(f"  {len(r.influenced())} leak(s) influenced {r.llm_model}")
    return "\n".join(lines)


def scan_markdown(s: ScanReport) -> str:
    out = ["# DoubleTake scan", "", f"Document: `{s.document}`", "",
           f"Verdict: **{'RISKY: hidden instruction-like content' if s.risky else 'no hidden instructions found'}**", ""]
    if s.tag_smuggling:
        out += ["## Unicode tag smuggling", ""]
        out += [f"- {p}: `{t}`" for p, t in s.tag_smuggling.items()]
        out.append("")
    if s.spans:
        out += ["## Text the model reads but the page does not show", "",
                "| Parser | Instruction-like | Text |", "|---|---|---|"]
        for sp in s.spans:
            txt = sp.text.replace("|", "\\|").replace("\n", " ")
            out.append(f"| {sp.parser} | {'**yes**' if sp.instruction_like else 'no'} | {txt[:240]} |")
    else:
        out.append("No hidden text runs found.")
    if s.errors:
        out += ["", "Parser errors: " + "; ".join(f"{k}: {v}" for k, v in s.errors.items())]
    return "\n".join(out) + "\n"


def to_json(obj) -> str:
    return json.dumps(obj.to_dict(), indent=2, ensure_ascii=False)
