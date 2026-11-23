# Testing your own parser

DoubleTake's built-in parsers show how common libraries behave by default. Your product probably wraps
one of them, adds post-processing, or calls a hosted service. Plug in **the exact code path your product
uses** and run `probe` against it.

There are two ways to do it. Both can be repeated and mixed with built-in parsers.

## 1. A shell command: `--parser NAME=COMMAND`

The command must print the extracted text to **stdout** and exit 0. `{file}` is replaced by the document
path; if it is missing, the path is appended as the last argument.

```bash
doubletake probe --parser "tika=java -jar tika-app.jar --text {file}"
doubletake probe --parser "ingest=python -m myapp.ingest --print {file}" --parser-format pdf --parser-format docx
doubletake probe --parser "pandoc=pandoc -t plain {file}" --parser-format docx --parser-format html
```

A non-zero exit is reported as `err` in the matrix, with the first 300 characters of stderr in `report.json`.
Use this for anything that is not Python, or for a container: `--parser "svc=docker run --rm -v $PWD:/d myimg /d/{file}"`.

## 2. A Python function: `--parser-py MODULE:FUNC`

The function receives the path as a `str` and returns the text that would be sent to the model.

```bash
doubletake probe --parser-py "myapp.loaders:load_text" --parser-format pdf
```

The module must be importable: run from your project root or set `PYTHONPATH`.

## `--parser-format`

By default a custom parser is offered every format (pdf, docx, xlsx, pptx, html, eml). If your loader
only handles some, list them, otherwise unsupported formats show up as `err`.

## `--only`

Restricts the **built-in** parsers. Custom parsers always run.

```bash
doubletake probe --only pypdf --parser-py "myapp.loaders:load_text"   # yours vs one baseline
```

## Adapters for popular loaders

Copy what you need into your project. These are untested templates: DoubleTake does not depend on these
libraries, and their APIs change between versions.

```python
# LangChain
def langchain_pdf(path: str) -> str:
    from langchain_community.document_loaders import PyPDFLoader
    return "\n".join(d.page_content for d in PyPDFLoader(path).load())


def langchain_any(path: str) -> str:
    from langchain_community.document_loaders import UnstructuredFileLoader
    return "\n".join(d.page_content for d in UnstructuredFileLoader(path).load())


# LlamaIndex
def llamaindex_any(path: str) -> str:
    from llama_index.core import SimpleDirectoryReader
    docs = SimpleDirectoryReader(input_files=[path]).load_data()
    return "\n".join(d.text for d in docs)


# Unstructured
def unstructured_any(path: str) -> str:
    from unstructured.partition.auto import partition
    return "\n".join(str(el) for el in partition(filename=path))


# Docling
def docling_any(path: str) -> str:
    from docling.document_converter import DocumentConverter
    return DocumentConverter().convert(path).document.export_to_markdown()


# Include metadata exactly as your RAG chunks do
def with_metadata(path: str) -> str:
    from langchain_community.document_loaders import PyPDFLoader
    docs = PyPDFLoader(path).load()
    return "\n".join(f"{d.metadata}\n{d.page_content}" for d in docs)
```

A runnable example lives in [`examples/my_parser.py`](../examples/my_parser.py):

```bash
doubletake probe --parser-py "examples.my_parser:load_text" --parser-format html --format html
```

## Hosted products you cannot call from code

Use `forge` to produce the documents, upload them through the product's normal UI or API, and ask it to
summarise each one:

```bash
doubletake forge -o testdocs/
cat testdocs/CANARY.txt
```

If an answer contains the canary, or calls the invoice "pre-approved", the product read the hidden layer.

## What counts as a leak

The parser's output is normalised (uppercased, non-alphanumerics removed, Unicode tag characters decoded)
and searched for the canary. Line breaks, spacing or punctuation inserted by your parser do not hide a leak.
Rewriting the text (for example summarising it before indexing) can, and that is also a legitimate defence
worth knowing about.
