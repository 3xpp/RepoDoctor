from __future__ import annotations

import re
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
ACTION_USE_RE = re.compile(r"^\s*uses:\s+(\S+)", re.MULTILINE)
PINNED_ACTION_RE = re.compile(
    r"^\s*uses:\s+([^@\s]+)@([0-9a-f]{40})\s+#\s+(v[0-9.]+)\s*$",
    re.MULTILINE,
)
COMMUNITY_FILES = (
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    ".github/ISSUE_TEMPLATE/bug-report.yml",
    ".github/ISSUE_TEMPLATE/feature-request.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/pull_request_template.md",
)


def test_ci_workflow_is_pinned_and_runs_the_release_contract() -> None:
    workflow = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
    text = workflow.read_text(encoding="utf-8")

    required = (
        "name: CI",
        "contents: read",
        'python-version: ["3.12", "3.13", "3.14"]',
        'version: "0.11.7"',
        "uv sync --locked",
        "make test",
        "make test-e2e",
        "uv run ruff check .",
        "uv run ruff format --check .",
        "uv run mypy src",
        "uv build",
        "uv run repo-doctor scan . --fail-under 90",
    )
    assert all(fragment in text for fragment in required)

    action_uses = ACTION_USE_RE.findall(text)
    pinned_actions = PINNED_ACTION_RE.findall(text)
    assert action_uses == [f"{action}@{commit}" for action, commit, _version in pinned_actions]
    assert pinned_actions == [
        (
            "actions/checkout",
            "3d3c42e5aac5ba805825da76410c181273ba90b1",
            "v7.0.1",
        ),
        (
            "astral-sh/setup-uv",
            "c771a70e6277c0a99b617c7a806ffedaca235ff9",
            "v9.0.0",
        ),
        (
            "actions/checkout",
            "3d3c42e5aac5ba805825da76410c181273ba90b1",
            "v7.0.1",
        ),
        (
            "astral-sh/setup-uv",
            "c771a70e6277c0a99b617c7a806ffedaca235ff9",
            "v9.0.0",
        ),
    ]


def test_project_urls_and_readme_badges_use_the_canonical_repository() -> None:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]

    assert project["urls"] == {
        "Homepage": "https://github.com/3xpp/RepoDoctor",
        "Repository": "https://github.com/3xpp/RepoDoctor",
        "Issues": "https://github.com/3xpp/RepoDoctor/issues",
        "Security": "https://github.com/3xpp/RepoDoctor/security/policy",
    }

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    required = (
        "actions/workflows/ci.yml/badge.svg",
        "python-%3E%3D3.12",
        "License-MIT",
        "github/v/release/3xpp/RepoDoctor?include_prereleases",
    )
    assert all(fragment in readme for fragment in required)


def test_community_files_exist_and_readme_links_to_them() -> None:
    missing = [path for path in COMMUNITY_FILES if not (PROJECT_ROOT / path).is_file()]
    assert missing == []

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    required = (
        "[contributing guide](CONTRIBUTING.md)",
        "[security policy](SECURITY.md)",
        "[Code of Conduct](CODE_OF_CONDUCT.md)",
        "[Pull request checklist](.github/pull_request_template.md)",
        "issues/new?template=bug-report.yml",
        "issues/new?template=feature-request.yml",
    )
    assert all(fragment in readme for fragment in required)


def test_security_and_conduct_use_private_non_secret_routes() -> None:
    security = (PROJECT_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    conduct = (PROJECT_ROOT / "CODE_OF_CONDUCT.md").read_text(encoding="utf-8")

    advisory_url = "https://github.com/3xpp/RepoDoctor/security/advisories/new"
    assert advisory_url in security
    assert "Do not open a public issue or pull request" in security
    assert "Never include live credentials" in security
    assert advisory_url not in conduct
    assert "https://github.com/3xpp" in conduct
    assert "Do not publish sensitive details in an issue" in conduct


def test_issue_forms_are_structured_and_route_security_privately() -> None:
    template_root = PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE"
    bug = (template_root / "bug-report.yml").read_text(encoding="utf-8")
    feature = (template_root / "feature-request.yml").read_text(encoding="utf-8")
    config = (template_root / "config.yml").read_text(encoding="utf-8")

    assert "blank_issues_enabled: false" in config
    assert "https://github.com/3xpp/RepoDoctor/security/advisories/new" in config
    form_names = []
    for form in (bug, feature):
        name = re.search(r"^name:[ \t]+([^\n]*\S)[ \t]*$", form, re.MULTILINE)
        description = re.search(
            r"^description:[ \t]+([^\n]*\S)[ \t]*$",
            form,
            re.MULTILINE,
        )
        body = re.search(r"^body:[ \t]*$", form, re.MULTILINE)

        assert name is not None
        assert description is not None
        assert body is not None
        form_names.append(name.group(1))

        form_body = form[body.end() :]
        elements = list(
            re.finditer(
                r"^  - type:[ \t]+(?P<type>\S+)[ \t]*$"
                r"(?P<body>.*?)(?=^  - type:[ \t]+|\Z)",
                form_body,
                re.MULTILINE | re.DOTALL,
            )
        )
        supported_types = {
            "checkboxes",
            "dropdown",
            "input",
            "markdown",
            "textarea",
            "upload",
        }
        assert elements
        assert all(element.group("type") in supported_types for element in elements)
        assert any(element.group("type") != "markdown" for element in elements)

        form_ids = []
        for element in elements:
            element_ids = re.findall(
                r"^    id:[ \t]+([^\n]*\S)[ \t]*$",
                element.group("body"),
                re.MULTILINE,
            )
            expected_id_count = 0 if element.group("type") == "markdown" else 1
            assert len(element_ids) == expected_id_count
            form_ids.extend(element_ids)

        assert all(re.fullmatch(r"[A-Za-z0-9_-]+", form_id) for form_id in form_ids)
        assert len(form_ids) == len(set(form_ids))
        assert re.search(
            r"^    validations:[ \t]*$\n"
            r"^      required:[ \t]+true[ \t]*$",
            form_body,
            re.MULTILINE,
        )
        assert "mailto:" not in form

    assert len(form_names) == len(set(form_names))
    assert "render: shell" in bug
    assert "id: local-scope" in feature
