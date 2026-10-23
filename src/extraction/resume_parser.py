from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from pypdf import PdfReader


def read_resume(path: str | Path) -> str:
    """Extract text from a PDF, DOCX, or plain-text resume."""
    resume_path = Path(path)
    if not resume_path.is_file():
        raise FileNotFoundError(f"Resume file not found: {resume_path}")

    suffix = resume_path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(resume_path))
        if reader.is_encrypted:
            raise ValueError("Encrypted PDF resumes are not supported.")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".docx":
        text = _read_docx(resume_path)
    elif suffix in {".txt", ".md"}:
        text = resume_path.read_text(encoding="utf-8")
    else:
        raise ValueError(
            "Unsupported resume format. Use PDF, DOCX, TXT, or Markdown."
        )

    if not text.strip():
        raise ValueError(
            f"No readable text was found in the resume: {resume_path}"
        )
    return text.strip()


def _read_docx(path: Path) -> str:
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(path) as archive:
        try:
            document_xml = archive.read("word/document.xml")
        except KeyError as error:
            raise ValueError(f"Invalid DOCX resume: {path}") from error

    root = ET.fromstring(document_xml)
    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        text = "".join(
            node.text or ""
            for node in paragraph.findall(".//w:t", namespace)
        )
        if text.strip():
            paragraphs.append(text)
    return "\n".join(paragraphs)
