import csv
import io
import json
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from app.services.investigations import create_report, update_report, update_report_metadata

REPORT_FIELDS = (
    "id",
    "report_type",
    "status",
    "scope",
    "generated_at",
    "evidence_sources",
    "limitations",
    "object_ref",
)


class ReportPdfUnsupportedError(RuntimeError):
    """Raised when the optional PDF rendering dependency is unavailable."""


def _report_metadata(report: Mapping[str, Any] | Any) -> dict[str, Any]:
    def value(field: str) -> Any:
        return report.get(field) if isinstance(report, Mapping) else getattr(report, field, None)

    return {field: _serialize_value(value(field)) for field in REPORT_FIELDS}


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    return str(value)


def render_report_json(report: Mapping[str, Any] | Any) -> str:
    """Render report metadata as human-readable JSON."""
    return json.dumps(_report_metadata(report), indent=2, ensure_ascii=False)


def render_report_csv(report: Mapping[str, Any] | Any) -> str:
    """Render report metadata as a two-column CSV document."""
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("field", "value"))
    for field, value in _report_metadata(report).items():
        rendered = (
            json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
        )
        writer.writerow((field, "" if rendered is None else rendered))
    return output.getvalue()


def render_report_pdf(report: Mapping[str, Any] | Any) -> bytes:
    """Render a minimal PDF when reportlab is installed.

    PDF support is intentionally optional so the backend does not gain a heavyweight
    dependency solely for exporting report metadata.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen.canvas import Canvas
    except ImportError as exc:
        raise ReportPdfUnsupportedError(
            "PDF report export is unsupported: install the optional 'reportlab' dependency."
        ) from exc

    output = io.BytesIO()
    canvas = Canvas(output, pagesize=letter)
    _, height = letter
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(72, height - 72, "Deepsight report")
    canvas.setFont("Helvetica", 10)
    y = height - 96
    for field, value in _report_metadata(report).items():
        canvas.drawString(72, y, f"{field}: {json.dumps(value, ensure_ascii=False)}")
        y -= 16
        if y < 72:
            canvas.showPage()
            y = height - 72
            canvas.setFont("Helvetica", 10)
    canvas.save()
    return output.getvalue()


__all__ = [
    "ReportPdfUnsupportedError",
    "create_report",
    "render_report_csv",
    "render_report_json",
    "render_report_pdf",
    "update_report",
    "update_report_metadata",
]
