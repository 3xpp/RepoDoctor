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
