import csv
import io
import json
from datetime import UTC, datetime

from app.services.reports import (
    ReportPdfUnsupportedError,
    render_report_csv,
    render_report_json,
    render_report_pdf,
)

REPORT = {
    "id": "report-1",
    "report_type": "investigation",
    "status": "published",
    "scope": {"asset_id": "asset-1"},
    "generated_at": datetime(2026, 1, 2, 3, 4, tzinfo=UTC),
    "evidence_sources": ["scanner", "manual"],
    "limitations": "Partial coverage",
    "object_ref": None,
}


def test_render_report_json_serializes_metadata():
    rendered = json.loads(render_report_json(REPORT))

    assert rendered["report_type"] == "investigation"
    assert rendered["scope"] == {"asset_id": "asset-1"}
    assert rendered["generated_at"] == "2026-01-02T03:04:00+00:00"


def test_render_report_csv_quotes_structured_values():
    rows = list(csv.reader(io.StringIO(render_report_csv(REPORT))))

    assert rows[0] == ["field", "value"]
    assert ["limitations", "Partial coverage"] in rows
    assert ["scope", '{"asset_id": "asset-1"}'] in rows
    assert ["evidence_sources", '["scanner", "manual"]'] in rows


def test_render_report_pdf_explicitly_reports_optional_dependency():
    try:
        rendered = render_report_pdf(REPORT)
    except ReportPdfUnsupportedError as exc:
        assert "reportlab" in str(exc)
    else:
        assert rendered.startswith(b"%PDF")
