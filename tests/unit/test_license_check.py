import pytest

from repo_doctor.checks.license import LicenseCheck


def test_license_check_detects_missing_license(tmp_path) -> None:
    assert LicenseCheck().run(tmp_path).passed is False


@pytest.mark.parametrize(
    "name",
    ["LICENSE", "license.md", "LICENCE.txt", "COPYING.md", "UNLICENSE"],
)
def test_license_check_accepts_supported_names(tmp_path, name: str) -> None:
    (tmp_path / name).write_text("Fixture license text.\n", encoding="utf-8")
    assert LicenseCheck().run(tmp_path).passed is True
