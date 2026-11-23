"""Forge split-view ("two-faced") documents.

Each Technique writes a document whose visible page shows ordinary cover
text, while a hidden layer carries a canary payload.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

COVER_TEXT = [
    "INVOICE 2026-0417",
    "Supplier: Northwind Marine Supplies Pvt Ltd",
    "Description: Deck fittings and mooring line, qty 12",
    "Total due: INR 48,250.00  Payment terms: net 30",
    "Please contact accounts with any questions.",
]


FORMATS = ("pdf", "docx", "xlsx", "pptx", "html", "eml")


@dataclass(frozen=True)
class Technique:
    id: str
    fmt: str  # one of FORMATS
    name: str
    description: str
    build: Callable[[Path, str], Path]  # (out_path_without_ext, canary) -> path


def registry() -> list[Technique]:
    from . import docx_, eml, html, pdf, pptx_, xlsx

    return [*pdf.TECHNIQUES, *docx_.TECHNIQUES, *xlsx.TECHNIQUES, *pptx_.TECHNIQUES, *html.TECHNIQUES, *eml.TECHNIQUES]


def by_id() -> dict[str, Technique]:
    return {t.id: t for t in registry()}
