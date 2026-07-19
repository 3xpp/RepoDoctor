from pathlib import Path

import pytest

from repo_doctor.checks import DEFAULT_CHECK_IDS, DEFAULT_CHECKS
from repo_doctor.checks.base import Check

EXPECTED_CHECK_IDS = (
    "readme-exists",
    "readme-sections",
    "license-exists",
    "tests-exist",
    "ci-exists",
    "docker-exists",
    "env-example",
)


def test_default_check_ids_are_exact_ordered_and_unique() -> None:
    assert DEFAULT_CHECK_IDS == EXPECTED_CHECK_IDS
    assert len(set(DEFAULT_CHECK_IDS)) == len(DEFAULT_CHECK_IDS)


def test_default_checks_satisfy_protocol_and_reuse_ids(tmp_path: Path) -> None:
    for check in DEFAULT_CHECKS:
        assert isinstance(check, Check)
        finding = check.run(tmp_path, excluded_paths=frozenset())
        assert finding.id == check.id


def test_default_check_ids_are_read_only() -> None:
    for check in DEFAULT_CHECKS:
        with pytest.raises(AttributeError):
            setattr(check, "id", "changed")
