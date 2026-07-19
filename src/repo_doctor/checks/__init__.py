from repo_doctor.checks.base import Check
from repo_doctor.checks.ci import GitHubActionsCheck
from repo_doctor.checks.docker import DockerCheck
from repo_doctor.checks.env_example import EnvExampleCheck
from repo_doctor.checks.license import LicenseCheck
from repo_doctor.checks.readme import ReadmeExistsCheck, ReadmeSectionsCheck
from repo_doctor.checks.tests import TestsCheck

DEFAULT_CHECKS: tuple[Check, ...] = (
    ReadmeExistsCheck(),
    ReadmeSectionsCheck(),
    LicenseCheck(),
    TestsCheck(),
    GitHubActionsCheck(),
    DockerCheck(),
    EnvExampleCheck(),
)

DEFAULT_CHECK_IDS = tuple(check.id for check in DEFAULT_CHECKS)
if len(set(DEFAULT_CHECK_IDS)) != len(DEFAULT_CHECK_IDS):
    raise RuntimeError("default check IDs must be unique")
