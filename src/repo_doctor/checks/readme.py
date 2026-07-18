import re
from pathlib import Path

from repo_doctor.models import Finding, Severity

README_PRIORITY = ("readme.md", "readme.rst", "readme")
RECOGNIZED_SECTIONS = {
    "installation": ("installation",),
    "usage": ("usage",),
    "quickstart": ("quickstart", "quick start"),
    "setup": ("setup",),
    "testing": ("testing",),
    "development": ("development",),
    "contributing": ("contributing",),
    "license": ("license", "licence"),
}
ATX_HEADING_RE = re.compile(r"^\s*#{1,6}\s+(.+?)\s*#*\s*$")
UNDERLINE_RE = re.compile(r"^\s*([=\-~^\"'`:+*#<>_])\1{2,}\s*$")


def find_readme(repo_path: Path) -> Path | None:
    entries = sorted(
        (
            entry
            for entry in repo_path.iterdir()
            if not entry.is_symlink() and entry.is_file()
        ),
        key=lambda entry: entry.name,
    )
    for candidate_name in README_PRIORITY:
        matches = [
            entry for entry in entries if entry.name.casefold() == candidate_name
        ]
        if matches:
            return matches[0]
    return None


def _extract_headings(text: str) -> list[str]:
    headings: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        atx_match = ATX_HEADING_RE.fullmatch(line)
        if atx_match:
            headings.append(atx_match.group(1))
        if (
            index + 1 < len(lines)
            and line.strip()
            and UNDERLINE_RE.fullmatch(lines[index + 1])
        ):
            headings.append(line.strip())
    return headings


def _recognized_section_count(headings: list[str]) -> int:
    recognized: set[str] = set()
    for heading in headings:
        normalized = re.sub(r"[^a-z0-9]+", " ", heading.casefold()).strip()
        for section, aliases in RECOGNIZED_SECTIONS.items():
            if any(
                re.search(
                    rf"(?:^|\s){re.escape(alias)}(?:$|\s)",
                    normalized,
                )
                for alias in aliases
            ):
                recognized.add(section)
    return len(recognized)


class ReadmeExistsCheck:
    def run(self, repo_path: Path) -> Finding:
        passed = find_readme(repo_path) is not None
        return Finding(
            id="readme-exists",
            title="README exists",
            description=(
                "A supported root README file is present."
                if passed
                else "No supported root README file was found."
            ),
            severity=Severity.HIGH,
            category="Documentation",
            recommendation=(
                "Keep the README aligned with the project."
                if passed
                else "Add README.md with the project's purpose and setup guidance."
            ),
            passed=passed,
        )


class ReadmeSectionsCheck:
    def run(self, repo_path: Path) -> Finding:
        readme = find_readme(repo_path)
        section_count = 0
        if readme is not None:
            try:
                text = readme.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                text = ""
            section_count = _recognized_section_count(_extract_headings(text))
        passed = section_count >= 2
        return Finding(
            id="readme-sections",
            title="README has useful sections",
            description=(
                f"The README contains {section_count} recognized sections."
                if readme is not None
                else "README usefulness cannot pass without a README."
            ),
            severity=Severity.MEDIUM,
            category="Documentation",
            recommendation=(
                "Keep installation and usage guidance current."
                if passed
                else "Add at least two sections such as Installation, Usage, or Testing."
            ),
            passed=passed,
        )
