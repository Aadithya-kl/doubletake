"""Positive controls: the payload is plainly VISIBLE.

Used by `doubletake selftest` and the test suite. If the human-view oracle
does not see the canary in these, it cannot be trusted to say a payload is
hidden in the real techniques (every result would be a false leak).
"""

from __future__ import annotations

import html as _h
from email.message import EmailMessage
from email.policy import SMTP
from pathlib import Path

from . import COVER_TEXT, Technique


def _visible_line(canary: str) -> str:
    return f"Reference {canary}"


def _pdf(out: Path, canary: str) -> Path:
    from . import pdf

    path = out.with_suffix(".pdf")
    c = pdf._base(path)
    c.drawString(60, 500, _visible_line(canary))
    c.save()
    return path


def _docx(out: Path, canary: str) -> Path:
    from . import docx_

    path = out.with_suffix(".docx")
    d = docx_._base()
    d.add_paragraph(_visible_line(canary))
    d.save(str(path))
    return path


def _xlsx(out: Path, canary: str) -> Path:
    from . import xlsx

    path = out.with_suffix(".xlsx")
    wb = xlsx._base()
    wb.active["A8"] = _visible_line(canary)
    wb.save(str(path))
    return path


def _pptx(out: Path, canary: str) -> Path:
    from . import pptx_

    path = out.with_suffix(".pptx")
    prs, slide = pptx_._base()
    pptx_._textbox(slide, _visible_line(canary))
    prs.save(str(path))
    return path


def _html(out: Path, canary: str) -> Path:
    from . import html

    path = out.with_suffix(".html")
    path.write_text(html._page(f"<p>{_h.escape(_visible_line(canary))}</p>"), encoding="utf-8")
    return path


def _eml(out: Path, canary: str) -> Path:
    path = out.with_suffix(".eml")
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = "accounts@northwind.example", "ap@yourcompany.example", "Invoice 2026-0417"
    body = "".join(f"<p>{_h.escape(l)}</p>" for l in COVER_TEXT) + f"<p>{_h.escape(_visible_line(canary))}</p>"
    m.set_content(f"<html><body>{body}</body></html>", subtype="html")
    path.write_bytes(m.as_bytes(policy=SMTP))
    return path


CONTROLS = [
    Technique(f"control.{fmt}", fmt, f"Visible control ({fmt})", "Payload drawn in plain sight.", fn)
    for fmt, fn in [("pdf", _pdf), ("docx", _docx), ("xlsx", _xlsx), ("pptx", _pptx), ("html", _html), ("eml", _eml)]
]
