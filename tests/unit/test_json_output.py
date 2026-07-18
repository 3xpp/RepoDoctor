import json

from repo_doctor.models import Report
from repo_doctor.reporting.json_report import render_json


def test_json_output_is_valid_stable_and_newline_terminated(
    fixed_report: Report,
) -> None:
    rendered = render_json(fixed_report)
    payload = json.loads(rendered)
    assert rendered.endswith("\n")
    assert list(payload) == [
        "repo_path",
        "score",
        "max_score",
        "summary",
        "findings",
        "generated_at",
        "version",
    ]
    assert payload["generated_at"] == "2026-07-18T12:00:00Z"
    assert payload["findings"][0]["severity"] in {"info", "low", "medium", "high"}
    assert list(payload["findings"][0]) == [
        "id",
        "title",
        "description",
        "severity",
        "category",
        "recommendation",
        "passed",
    ]
