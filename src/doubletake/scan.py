"""Scan: find text that parsers hand to a model but a human cannot see.

For a real document, we cannot plant a canary, so we diff each parser's
output against OCR of the rendered page and report runs of words that are
present for the model but absent for the human. Runs that look like
instructions to an AI are escalated.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

from .canary import decode_tags, extract_tags, has_tags
from .humanview import render_and_ocr
from .parsers import Parser, ext_fmt

INSTRUCTION_PATTERNS = [
    r"\bignore (all |any )?(previous|prior|above)\b",
    r"\b(ai|llm|language model|assistant|chatbot|gpt|claude|copilot)\b",
    r"\bsystem (prompt|note|message|instruction)",
    r"\bdo not (mention|reveal|tell|disclose)\b",
    r"\b(pre-?approved|approve this|mark (it|this|the document) (as )?approved)\b",
    r"\byou (must|should|are now)\b",
    r"\b(disregard|override)\b",
    r"\b(exfiltrate|send (it|this|the) to|forward (it|this|all) to)\b",
    r"\b(rank|rate|score) (this|me|the candidate) (highly|as)\b",
]

_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-]{1,}")


def _words(text: str) -> list[str]:
    return _WORD.findall(text)


def _norm(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", w.lower())


def _seen(w: str, vocab: set[str]) -> bool:
    n = _norm(w)
    if not n or n in vocab:
        return True
    if len(n) >= 5:  # tolerate small OCR errors on longer words
        return any(abs(len(v) - len(n)) <= 2 and SequenceMatcher(None, n, v).ratio() >= 0.8 for v in vocab)
    return False


@dataclass
class HiddenSpan:
    parser: str
    text: str
    words: int
    instruction_like: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class ScanReport:
    document: str
    ocr_chars: int
    spans: list[HiddenSpan]
    tag_smuggling: dict[str, str]
    errors: dict[str, str]

    @property
    def risky(self) -> bool:
        return bool(self.tag_smuggling) or any(s.instruction_like for s in self.spans)

    def to_dict(self) -> dict:
        return {"tool": "doubletake", "mode": "scan", "risky": self.risky, **asdict(self)}


def hidden_runs(model_text: str, human_text: str, min_words: int = 4, min_unseen: float = 0.75) -> list[str]:
    vocab = {_norm(w) for w in _words(human_text)}
    words = _words(model_text)
    flags = [not _seen(w, vocab) for w in words]
    runs, i = [], 0
    while i < len(words):
        if not flags[i]:
            i += 1
            continue
        j, unseen = i, 0
        # grow the window while it stays mostly unseen
        while j < len(words) and (flags[j] or (unseen / max(1, j - i)) >= min_unseen):
            unseen += flags[j]
            j += 1
        while j > i and not flags[j - 1]:
            j -= 1
        if j - i >= min_words:
            runs.append(" ".join(words[i:j]))
        i = max(j, i + 1)
    return runs


def classify(text: str) -> list[str]:
    return [p for p in INSTRUCTION_PATTERNS if re.search(p, text, re.I)]


def run_scan(path: Path, parsers: list[Parser], min_words: int = 4) -> ScanReport:
    fmt = ext_fmt(path)
    human = render_and_ocr(path)
    spans: list[HiddenSpan] = []
    tags: dict[str, str] = {}
    errors: dict[str, str] = {}
    seen_texts: set[str] = set()
    for p in parsers:
        if fmt not in p.formats or not p.use_in_scan:
            continue
        try:
            raw = p.fn(path)
        except Exception as e:
            errors[p.name] = f"{type(e).__name__}: {e}"[:300]
            continue
        if has_tags(raw):
            tags[p.name] = extract_tags(raw)[:300]
        for run in hidden_runs(decode_tags(raw), human, min_words=min_words):
            reasons = classify(run)
            if run in seen_texts and not reasons:
                continue
            seen_texts.add(run)
            spans.append(HiddenSpan(p.name, run[:500], len(run.split()), bool(reasons), reasons))
    return ScanReport(str(path), len(human), spans, tags, errors)
