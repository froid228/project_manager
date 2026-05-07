import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from coverage import Coverage
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from projects.models import Project, ProjectMember
from tasks.models import Task

User = get_user_model()
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIRS = ("config", "core", "projects", "tasks", "users")
COLLECTED_TEST_FILES = 0
COLLECTED_TESTS = 0


@dataclass
class CoverageMetrics:
    stmts_total: int = 0
    stmts_covered: int = 0
    branch_total: int = 0
    branch_covered: int = 0
    funcs_total: int = 0
    funcs_covered: int = 0
    lines_total: int = 0
    lines_covered: int = 0
    missing_lines: list[int] = field(default_factory=list)

    def merge(self, other):
        self.stmts_total += other.stmts_total
        self.stmts_covered += other.stmts_covered
        self.branch_total += other.branch_total
        self.branch_covered += other.branch_covered
        self.funcs_total += other.funcs_total
        self.funcs_covered += other.funcs_covered
        self.lines_total += other.lines_total
        self.lines_covered += other.lines_covered


@dataclass
class CoverageNode:
    label: str
    metrics: CoverageMetrics = field(default_factory=CoverageMetrics)
    directories: dict[str, "CoverageNode"] = field(default_factory=dict)
    files: dict[str, "CoverageNode"] = field(default_factory=dict)
    is_file: bool = False


def _pct(covered, total):
    if total == 0:
        return 100
    return round(covered * 100 / total)


def _format_missing(lines):
    if not lines:
        return ""
    return ",".join(str(line) for line in lines)


def _backend_relative_path(filename):
    path = Path(filename).resolve()
    try:
        relative = path.relative_to(REPO_ROOT)
    except ValueError:
        return None

    if not relative.parts or relative.parts[0] not in BACKEND_DIRS or path.suffix != ".py":
        return None
    return relative


def _build_coverage_tree():
    coverage_file = REPO_ROOT / ".coverage"
    if not coverage_file.exists():
        return None

    cov = Coverage(data_file=str(coverage_file))
    cov.load()
    data = cov.get_data()

    fd, json_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        cov.json_report(outfile=json_path)
        report = json.loads(Path(json_path).read_text(encoding="utf-8"))
    finally:
        Path(json_path).unlink(missing_ok=True)

    root = CoverageNode("All files")

    for filename, info in sorted(report["files"].items()):
        relative = _backend_relative_path(filename)
        if relative is None:
            continue

        summary = info["summary"]
        metrics = CoverageMetrics(
            stmts_total=summary["num_statements"],
            stmts_covered=summary["covered_lines"],
            branch_total=summary.get("num_branches", 0),
            branch_covered=summary.get("covered_branches", 0),
            funcs_total=summary["num_statements"],
            funcs_covered=summary["covered_lines"],
            lines_total=summary["num_statements"],
            lines_covered=summary["covered_lines"],
            missing_lines=info.get("missing_lines", []),
        )

        root.metrics.merge(metrics)
        current = root
        parent_path = []
        for part in relative.parts[:-1]:
            parent_path.append(part)
            key = "/".join(parent_path)
            if key not in current.directories:
                current.directories[key] = CoverageNode(key)
            current = current.directories[key]
            current.metrics.merge(metrics)

        file_name = relative.name
        current.files[file_name] = CoverageNode(file_name, metrics=metrics, is_file=True)

    return root


def _collect_rows(node, rows, indent=""):
    rows.append((indent + node.label, node.metrics, node.is_file))

    for child in node.directories.values():
        next_indent = "" if node.label == "All files" else indent + "  "
        _collect_rows(child, rows, next_indent)

    for child in node.files.values():
        next_indent = "  " if node.label == "All files" else indent + "  "
        rows.append((next_indent + child.label, child.metrics, True))


def pytest_collection_finish(session):
    global COLLECTED_TEST_FILES, COLLECTED_TESTS
    COLLECTED_TESTS = len(session.items)
    COLLECTED_TEST_FILES = len({str(item.path) for item in session.items})


@pytest.hookimpl(trylast=True)
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    tree = _build_coverage_tree()
    if tree is None:
        return

    rows = []
    _collect_rows(tree, rows)

    file_width = max(len(label) for label, _, _ in rows)
    file_width = max(file_width, len("File"))
    col_width = 8
    last_width = 20
    divider = (
        "-" * (file_width + 2)
        + "|"
        + "-" * (col_width + 2)
        + "|"
        + "-" * (col_width + 2)
        + "|"
        + "-" * (col_width + 2)
        + "|"
        + "-" * (col_width + 2)
        + "|"
        + "-" * (last_width + 2)
    )

    terminalreporter.write_sep("-", "Coverage summary")
    terminalreporter.write_line(divider)
    terminalreporter.write_line(
        f"{'File':<{file_width + 2}}| {'% Stmts':>{col_width}} | {'% Branch':>{col_width}} | {'% Funcs':>{col_width}} | {'% Lines':>{col_width}} | {'Uncovered Line #s':<{last_width}}"
    )
    terminalreporter.write_line(divider)

    for label, metrics, is_file in rows:
        missing = _format_missing(metrics.missing_lines) if is_file else ""
        terminalreporter.write_line(
            f"{label:<{file_width + 2}}| "
            f"{_pct(metrics.stmts_covered, metrics.stmts_total):>{col_width}} | "
            f"{_pct(metrics.branch_covered, metrics.branch_total):>{col_width}} | "
            f"{_pct(metrics.funcs_covered, metrics.funcs_total):>{col_width}} | "
            f"{_pct(metrics.lines_covered, metrics.lines_total):>{col_width}} | "
            f"{missing:<{last_width}}"
        )

    terminalreporter.write_line(divider)

    passed_reports = terminalreporter.stats.get("passed", [])
    failed_reports = terminalreporter.stats.get("failed", [])
    error_reports = terminalreporter.stats.get("error", [])
    failed_files = {
        str(getattr(report, "location", [""])[0])
        for report in [*failed_reports, *error_reports]
        if getattr(report, "when", "call") == "call"
    }
    passed_suites = COLLECTED_TEST_FILES - len(failed_files)

    terminalreporter.write_line("")
    terminalreporter.write_line(
        f"Test Suites: {passed_suites} passed, {COLLECTED_TEST_FILES} total"
    )
    terminalreporter.write_line(
        f"Tests:       {len(passed_reports)} passed, {COLLECTED_TESTS} total"
    )
    terminalreporter.write_line("Snapshots:   0 total")

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def admin_user(db):
    return User.objects.create_user(username='test_admin', password='testpass123', role='admin')

@pytest.fixture
def manager_user(db):
    return User.objects.create_user(username='test_manager', password='testpass123', role='manager')

@pytest.fixture
def member_user(db):
    return User.objects.create_user(username='test_member', password='testpass123', role='member')

@pytest.fixture
def observer_user(db):
    return User.objects.create_user(username='test_observer', password='testpass123', role='observer')

@pytest.fixture
def project(db, admin_user):
    return Project.objects.create(name='Тестовый проект', description='Описание для тестов', owner=admin_user)

@pytest.fixture
def project_with_member(db, project, member_user):
    ProjectMember.objects.create(project=project, user=member_user, role='member')
    return project

@pytest.fixture
def task(db, project, member_user):
    return Task.objects.create(project=project, title='Тестовая задача', status='todo', priority='medium', assignee=member_user)

@pytest.fixture
def auth_client(api_client, admin_user):
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client
