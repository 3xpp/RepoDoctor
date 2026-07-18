import os

import pytest

from repo_doctor.checks.ci import GitHubActionsCheck
from repo_doctor.checks.docker import DockerCheck
from repo_doctor.checks.tests import TestsCheck


def test_tests_directory_passes(tmp_path) -> None:
    (tmp_path / "tests").mkdir()
    assert TestsCheck().run(tmp_path).passed is True


def test_nested_typescript_spec_passes(tmp_path) -> None:
    source = tmp_path / "web" / "src"
    source.mkdir(parents=True)
    (source / "widget.spec.ts").write_text("export {};\n", encoding="utf-8")
    assert TestsCheck().run(tmp_path).passed is True


def test_dependency_test_file_is_ignored(tmp_path) -> None:
    source = tmp_path / "node_modules" / "package"
    source.mkdir(parents=True)
    (source / "widget.test.js").write_text("", encoding="utf-8")
    assert TestsCheck().run(tmp_path).passed is False


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFOs are unavailable")
def test_named_pipe_is_not_counted_as_a_test_file(tmp_path) -> None:
    os.mkfifo(tmp_path / "test_phantom.py")
    assert TestsCheck().run(tmp_path).passed is False


@pytest.mark.parametrize("broken", [False, True])
def test_symlinked_test_file_is_rejected(tmp_path, broken: bool) -> None:
    target = tmp_path / "missing.py" if broken else tmp_path / "source.py"
    if not broken:
        target.write_text("# Fixture.\n", encoding="utf-8")
    (tmp_path / "test_link.py").symlink_to(target)
    assert TestsCheck().run(tmp_path).passed is False


def test_github_workflow_requires_yaml_file(tmp_path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    assert GitHubActionsCheck().run(tmp_path).passed is False
    (workflows / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    assert GitHubActionsCheck().run(tmp_path).passed is True


def test_symlinked_github_directory_is_rejected(tmp_path) -> None:
    external = tmp_path / "external"
    workflows = external / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / ".github").symlink_to(external, target_is_directory=True)
    assert GitHubActionsCheck().run(tmp_path).passed is False


def test_symlinked_workflows_directory_is_rejected(tmp_path) -> None:
    external = tmp_path / "external"
    external.mkdir()
    (external / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    github = tmp_path / ".github"
    github.mkdir()
    (github / "workflows").symlink_to(external, target_is_directory=True)
    assert GitHubActionsCheck().run(tmp_path).passed is False


def test_symlinked_workflow_file_is_rejected(tmp_path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    target = tmp_path / "ci.yml"
    target.write_text("name: CI\n", encoding="utf-8")
    (workflows / "linked.yml").symlink_to(target)
    assert GitHubActionsCheck().run(tmp_path).passed is False


def test_docker_candidate_passes(tmp_path) -> None:
    (tmp_path / "compose.yaml").write_text("services: {}\n", encoding="utf-8")
    assert DockerCheck().run(tmp_path).passed is True


def test_symlinked_docker_candidate_is_rejected(tmp_path) -> None:
    target = tmp_path / "container.txt"
    target.write_text("FROM scratch\n", encoding="utf-8")
    (tmp_path / "Dockerfile").symlink_to(target)
    assert DockerCheck().run(tmp_path).passed is False
