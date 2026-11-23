"""Email (.eml) carriers.

Mail clients show the text/html alternative; many ingestion pipelines read
text/plain (or every part). The two alternatives need not agree.
"""

from __future__ import annotations

import html as _h
from email.message import EmailMessage
from email.policy import SMTP
from pathlib import Path

from ..canary import payload_for
from . import COVER_TEXT, Technique

SUBJECT = "Invoice 2026-0417"


def _html(extra: str = "") -> str:
    body = "".join(f"<p>{_h.escape(l)}</p>" for l in COVER_TEXT)
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>{body}{extra}</body></html>"


def _msg() -> EmailMessage:
    m = EmailMessage()
    m["From"] = "accounts@northwind.example"
    m["To"] = "ap@yourcompany.example"
    m["Subject"] = SUBJECT
    return m


def _make(draw):
    def build(out: Path, canary: str) -> Path:
        path = out.with_suffix(".eml")
        m = draw(payload_for(canary))
        path.write_bytes(m.as_bytes(policy=SMTP))
        return path

    return build


def _plain_html_mismatch(p):
    m = _msg()
    m.set_content("\n".join(COVER_TEXT) + "\n\n" + p)
    m.add_alternative(_html(), subtype="html")
    return m


def _html_display_none(p):
    m = _msg()
    m.set_content(_html(f"<div style='display:none'>{_h.escape(p)}</div>"), subtype="html")
    return m


def _custom_header(p):
    m = _msg()
    m["X-Processing-Note"] = p
    m.set_content(_html(), subtype="html")
    return m


TECHNIQUES = [
    Technique("eml.plain_html_mismatch", "eml", "text/plain vs text/html mismatch",
              "Client shows the HTML part; the plain-text alternative carries the payload.", _make(_plain_html_mismatch)),
    Technique("eml.html_display_none", "eml", "Hidden HTML in email", "display:none payload in the HTML body.",
              _make(_html_display_none)),
    Technique("eml.custom_header", "eml", "Custom X- header", "Payload in a non-displayed X- header.",
              _make(_custom_header)),
]
