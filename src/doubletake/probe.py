"""Probe: forge every technique, read it with every parser, compare to the human view."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from .canary import contains_canary, new_canary, ocr_sees_canary, squash
from .forge import Technique, registry
from .humanview import render_and_ocr
from .parsers import Parser

LEAK, SAFE, ERROR = "LEAK", "safe", "error"
COVER_MARKER = "NORTHWIND"  # word from forge.COVER_TEXT that must be visible on every render


@dataclass
class TechniqueResult:
    technique: str
    fmt: str
    name: str
    document: str
    human_sees_payload: bool | None  # None = human view unavailable
    render_error: str = ""
    cells: dict[str, str] = field(default_factory=dict)  # parser -> LEAK / safe / error
    errors: dict[str, str] = field(default_factory=dict)
    llm: dict[str, tuple[str, str]] = field(default_factory=dict)  # parser -> (verdict, reply)

    @property
    def split_view(self) -> bool:
        """True when the payload is genuinely invisible on the rendered page."""
        return self.human_sees_payload is False


@dataclass
class ProbeReport:
    canary: str
    parsers: list[str]
    results: list[TechniqueResult]
    llm_model: str | None = None

    def leaks(self) -> list[tuple[str, str]]:
        return [(r.technique, p) for r in self.results if r.split_view for p, v in r.cells.items() if v == LEAK]

    def influenced(self) -> list[tuple[str, str]]:
        from .llm import INFLUENCED

        return [(r.technique, p) for r in self.results for p, (v, _) in r.llm.items() if v == INFLUENCED]

    def parser_scores(self) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for r in self.results:
            if not r.split_view:
                continue
            for p, v in r.cells.items():
                s = out.setdefault(p, {"tested": 0, "leaked": 0})
                if v in (LEAK, SAFE):
                    s["tested"] += 1
                    s["leaked"] += v == LEAK
        return out

    def to_dict(self) -> dict:
        return {
            "tool": "doubletake",
            "canary": self.canary,
            "parsers": self.parsers,
            "llm_model": self.llm_model,
            "summary": {
                "techniques": len(self.results),
                "split_view_techniques": sum(r.split_view for r in self.results),
                "leaks": len(self.leaks()),
                "llm_influenced": len(self.influenced()),
                "parser_scores": self.parser_scores(),
            },
            "results": [asdict(r) | {"split_view": r.split_view} for r in self.results],
        }


def human_view(doc: Path, canary: str) -> tuple[bool | None, str]:
    """(human_sees_payload, error). None when the render cannot be trusted."""
    try:
        ocr = render_and_ocr(doc)
    except Exception as e:  # renderer missing / crashed
        return None, str(e)[:300]
    if COVER_MARKER not in squash(ocr):
        # A blank or broken render would make every payload look "hidden".
        return None, "rendered page does not show the cover text; human view unreliable"
    return ocr_sees_canary(ocr, canary), ""


def run_probe(
    parsers: list[Parser],
    outdir: Path,
    techniques: list[Technique] | None = None,
    formats: set[str] | None = None,
    canary: str | None = None,
    progress: Callable[[str], None] = lambda msg: None,
    llm=None,  # llm.LLMConfig | None
) -> ProbeReport:
    canary = canary or new_canary()
    outdir.mkdir(parents=True, exist_ok=True)
    techs = [t for t in (techniques or registry()) if not formats or t.fmt in formats]
    results: list[TechniqueResult] = []
    used: list[str] = []

    for t in techs:
        progress(f"forging {t.id}")
        doc = t.build(outdir / t.id.replace(".", "_"), canary)
        res = TechniqueResult(t.id, t.fmt, t.name, str(doc), None)
        res.human_sees_payload, res.render_error = human_view(doc, canary)
        for p in parsers:
            if t.fmt not in p.formats:
                continue
            if p.name not in used:
                used.append(p.name)
            try:
                text = p.fn(doc)
            except Exception as e:
                res.cells[p.name] = ERROR
                res.errors[p.name] = f"{type(e).__name__}: {e}"[:300]
                continue
            leaked = contains_canary(text, canary)
            res.cells[p.name] = LEAK if leaked else SAFE
            if llm is not None and leaked and res.split_view:
                from .llm import check

                progress(f"  asking {llm.model} about {t.id} via {p.name}")
                res.llm[p.name] = check(llm, text, canary)
        results.append(res)
    return ProbeReport(canary, used, results, llm.model if llm else None)
