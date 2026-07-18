import json

from repo_doctor.models import Report


def render_json(report: Report) -> str:
    payload = report.model_dump(mode="json")
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
