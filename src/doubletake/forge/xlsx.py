from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font

from ..canary import payload_for
from . import COVER_TEXT, Technique


def _base() -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Invoice"
    for i, line in enumerate(COVER_TEXT, start=1):
        ws.cell(row=i, column=1, value=line)
    ws.column_dimensions["A"].width = 60
    return wb


def _make(draw):
    def build(out: Path, canary: str) -> Path:
        path = out.with_suffix(".xlsx")
        wb = _base()
        draw(wb, payload_for(canary))
        wb.save(str(path))
        return path

    return build


def _hidden_sheet(wb, p, state="hidden"):
    ws = wb.create_sheet("Notes")
    ws["A1"] = p
    ws.sheet_state = state


def _hidden_row(wb, p):
    ws = wb.active
    ws.cell(row=8, column=1, value=p)
    ws.row_dimensions[8].hidden = True


def _hidden_col(wb, p):
    ws = wb.active
    ws["C2"] = p
    ws.column_dimensions["C"].hidden = True


def _white(wb, p):
    ws = wb.active
    ws["A8"] = p
    ws["A8"].font = Font(color="FFFFFF")


def _comment(wb, p):
    wb.active["A1"].comment = Comment(p, "accounts")


TECHNIQUES = [
    Technique("xlsx.hidden_sheet", "xlsx", "Hidden worksheet", "Payload on a sheet with state=hidden.", _make(_hidden_sheet)),
    Technique("xlsx.very_hidden_sheet", "xlsx", "Very hidden worksheet",
              "Payload on a sheet with state=veryHidden (cannot be unhidden from Excel's UI).",
              _make(lambda wb, p: _hidden_sheet(wb, p, "veryHidden"))),
    Technique("xlsx.hidden_row", "xlsx", "Hidden row", "Payload in a hidden row.", _make(_hidden_row)),
    Technique("xlsx.hidden_column", "xlsx", "Hidden column", "Payload in a hidden column.", _make(_hidden_col)),
    Technique("xlsx.white_text", "xlsx", "White text", "Payload in a white-font cell.", _make(_white)),
    Technique("xlsx.cell_comment", "xlsx", "Cell comment", "Payload in a cell comment (not printed).", _make(_comment)),
]
