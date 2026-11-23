"""Example custom parser for DoubleTake.

DoubleTake calls your function with the document path (str) and expects the
text your pipeline would hand to the model. Wrap whatever you really use:
a LangChain/LlamaIndex loader, Unstructured, Docling, an OCR service, ...

    doubletake probe --parser-py examples.my_parser:load_text --parser-format html

(run from the repository root so `examples` is importable, or put the module on PYTHONPATH)
"""

from __future__ import annotations

import re
from pathlib import Path


def load_text(path: str) -> str:
    """A deliberately naive HTML loader: strips tags with a regex.

    It drops comments' delimiters but keeps their text, and keeps hidden
    elements - DoubleTake will show you exactly which tricks get through.
    """
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    raw = raw.replace("<!--", " ").replace("-->", " ")
    return re.sub(r"<[^>]+>", " ", raw)


# --- More realistic adapters (uncomment the one you use) ---------------------
#
# def langchain_pdf(path: str) -> str:
#     from langchain_community.document_loaders import PyPDFLoader
#     return "\n".join(d.page_content for d in PyPDFLoader(path).load())
#
# def unstructured_any(path: str) -> str:
#     from unstructured.partition.auto import partition
#     return "\n".join(str(el) for el in partition(filename=path))
#
# def docling_any(path: str) -> str:
#     from docling.document_converter import DocumentConverter
#     return DocumentConverter().convert(path).document.export_to_markdown()
