"""SARIF 2.1.0 output, for GitHub code scanning and other SARIF viewers."""

from __future__ import annotations

import json
from pathlib import Path

from . import __version__
from .forge import by_id
from .probe import LEAK, ProbeReport
from .scan import ScanReport

_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
_INFO = "https://github.com/Aadithya-kl/doubletake"


def _run(rules: list[dict], results: list[dict]) -> dict:
    return {
        "$schema": _SCHEMA,
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "DoubleTake", "version": __version__, "informationUri": _INFO, "rules": rules}},
            "results": results,
        }],
    }


def _loc(path: str) -> list[dict]:
    return [{"physicalLocation": {"artifactLocation": {"uri": Path(path).as_posix()}}}]


def probe_sarif(r: ProbeReport) -> dict:
    techs = by_id()
    rules, seen, results = [], set(), []
    for x in r.results:
        if not x.split_view:
            continue
        for parser, verdict in x.cells.items():
            if verdict != LEAK:
                continue
            if x.technique not in seen:
                seen.add(x.technique)
                t = techs.get(x.technique)
                rules.append({
                    "id": x.technique,
                    "name": x.name,
                    "shortDescription": {"text": f"Split-view leak: {x.name}"},
                    "fullDescription": {"text": t.description if t else x.name},
                    "defaultConfiguration": {"level": "error"},
                })
            influenced = x.llm.get(parser, ("", ""))[0] if x.llm else ""
            msg = f"Parser '{parser}' passes hidden content to the model ({x.name}); the rendered page does not show it."
            if influenced:
                msg += f" LLM check: {influenced}."
            results.append({"ruleId": x.technique, "level": "error", "message": {"text": msg},
                            "locations": _loc(x.document), "properties": {"parser": parser}})
    return _run(rules, results)


SCAN_RULES = [
    {"id": "DT-SCAN-INSTRUCTION", "name": "HiddenInstruction",
     "shortDescription": {"text": "Hidden instruction-like text reaches the model"},
     "defaultConfiguration": {"level": "error"}},
    {"id": "DT-SCAN-HIDDEN-TEXT", "name": "HiddenText",
     "shortDescription": {"text": "Text reaches the model but is not visible on the rendered page"},
     "defaultConfiguration": {"level": "note"}},
    {"id": "DT-SCAN-TAG-SMUGGLING", "name": "UnicodeTagSmuggling",
     "shortDescription": {"text": "Invisible Unicode tag characters carry text"},
     "defaultConfiguration": {"level": "error"}},
]


def scan_sarif(reports: list[ScanReport]) -> dict:
    results = []
    for s in reports:
        for p, t in s.tag_smuggling.items():
            results.append({"ruleId": "DT-SCAN-TAG-SMUGGLING", "level": "error",
                            "message": {"text": f"[{p}] smuggled text: {t[:200]}"}, "locations": _loc(s.document)})
        for sp in s.spans:
            rid, lvl = ("DT-SCAN-INSTRUCTION", "error") if sp.instruction_like else ("DT-SCAN-HIDDEN-TEXT", "note")
            results.append({"ruleId": rid, "level": lvl, "message": {"text": f"[{sp.parser}] {sp.text[:300]}"},
                            "locations": _loc(s.document)})
    return _run(SCAN_RULES, results)


def dump(obj: dict) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)
