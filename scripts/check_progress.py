"""Bảng tiến độ nhóm — đọc thẳng nội dung branch trên remote, không hỏi ai cả.

Công cụ của leader (vai R4). Mỗi checkpoint được kiểm bằng một dấu hiệu cụ thể
trong code, nên trạng thái "xong" là kiểm chứng được chứ không phải tự khai.

    python scripts/check_progress.py                 # bảng tổng
    python scripts/check_progress.py --role R1       # chi tiết một người
    python scripts/check_progress.py --no-fetch      # không gọi mạng
    python scripts/check_progress.py --stale-minutes 30
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def read_at(ref: str, path: str) -> str | None:
    """Nội dung file tại một ref; None nếu file chưa tồn tại ở ref đó."""
    content = git("show", f"{ref}:{path}")
    return content if content else None


def uncommented(content: str | None, needle: str) -> bool:
    """needle xuất hiện ở một dòng code thật, không phải dòng đã comment."""
    if not content:
        return False
    return any(
        needle in line and not line.strip().startswith("#") for line in content.splitlines()
    )


@dataclass
class Check:
    label: str
    done: bool
    hint: str = ""


@dataclass
class RoleStatus:
    role: str
    owner: str
    branch: str
    checks: list[Check] = field(default_factory=list)
    last_commit: str = ""
    last_author: str = ""
    minutes_idle: float | None = None
    commits_ahead: int = 0
    exists: bool = True

    @property
    def done_count(self) -> int:
        return sum(1 for check in self.checks if check.done)

    @property
    def percent(self) -> int:
        return round(self.done_count / len(self.checks) * 100) if self.checks else 0


def branch_activity(status: RoleStatus, ref: str) -> None:
    if not git("rev-parse", "--verify", "--quiet", ref):
        status.exists = False
        return
    status.last_commit = git("log", "-1", "--format=%s", ref)
    status.last_author = git("log", "-1", "--format=%an", ref)
    raw_ts = git("log", "-1", "--format=%cI", ref)
    if raw_ts:
        committed = datetime.fromisoformat(raw_ts)
        status.minutes_idle = (datetime.now(timezone.utc) - committed).total_seconds() / 60
    ahead = git("rev-list", "--count", f"origin/main..{ref}")
    status.commits_ahead = int(ahead) if ahead.isdigit() else 0


def check_r1(ref: str) -> list[Check]:
    middleware = read_at(ref, "app/middleware.py")
    logging_config = read_at(ref, "app/logging_config.py")
    main = read_at(ref, "app/main.py")
    pii = read_at(ref, "app/pii.py")

    pattern_count = len(re.findall(r'^\s*"[a-z_]+":\s*r?"', pii or "", re.MULTILINE))

    return [
        Check(
            "Correlation ID không còn hard-code MISSING",
            bool(middleware) and 'correlation_id = "MISSING"' not in middleware,
            "app/middleware.py:18",
        ),
        Check(
            "clear_contextvars() được gọi",
            uncommented(middleware, "clear_contextvars()"),
            "app/middleware.py:13",
        ),
        Check(
            "bind_contextvars(correlation_id=...)",
            uncommented(middleware, "bind_contextvars(correlation_id"),
            "app/middleware.py:20",
        ),
        Check(
            "Response header x-request-id",
            uncommented(middleware, 'headers["x-request-id"]'),
            "app/middleware.py:28",
        ),
        Check(
            "scrub_event đã vào pipeline processor",
            uncommented(logging_config, "scrub_event,"),
            "app/logging_config.py:45",
        ),
        Check(
            "/chat enrich log bằng bind_contextvars",
            uncommented(main, "bind_contextvars("),
            "app/main.py:47",
        ),
        Check(
            f"PII patterns > 4 (đang có {pattern_count})",
            pattern_count > 4,
            "app/pii.py:11",
        ),
        Check("Notes cá nhân đã viết", read_at(ref, "submission/notes/r1-logging-pii.md") is not None),
    ]


def check_r2(ref: str) -> list[Check]:
    agent = read_at(ref, "app/agent.py")
    return [
        Check(
            "Log prompt_resolved nối trace ↔ log",
            bool(agent) and "prompt_resolved" in agent,
            "app/agent.py",
        ),
        Check(
            "Có lấy trace_id trong log",
            bool(agent) and "get_current_trace_id" in agent,
            "app/agent.py",
        ),
        Check("Notes cá nhân đã viết", read_at(ref, "submission/notes/r2-tracing-prompt.md") is not None),
    ]


def check_r3(ref: str) -> list[Check]:
    alerts_yaml = read_at(ref, "config/alert_rules.yaml")
    alerts_doc = read_at(ref, "docs/alerts.md")
    slo = read_at(ref, "config/slo.yaml")

    empty_runbook_fields = sum(
        1 for line in (alerts_doc or "").splitlines() if line.strip() in {"- Tên:", "- Severity:", "- Owner:"}
    )

    return [
        Check(
            "alert_rules.yaml không còn TODO",
            bool(alerts_yaml) and "TODO" not in alerts_yaml,
            "config/alert_rules.yaml",
        ),
        Check(
            "Alert có owner là người thật",
            bool(alerts_yaml) and "owner: TODO" not in alerts_yaml and "owner:" in alerts_yaml,
            "config/alert_rules.yaml",
        ),
        Check(
            f"Runbook đã điền (còn {empty_runbook_fields} trường rỗng)",
            bool(alerts_doc) and empty_runbook_fields == 0,
            "docs/alerts.md",
        ),
        Check(
            "SLO đã chốt (bỏ dòng note mẫu)",
            bool(slo) and "Replace with your group's target" not in slo,
            "config/slo.yaml",
        ),
        Check("Dashboard chạy được tồn tại", read_at(ref, "dashboard/app.py") is not None, "dashboard/app.py"),
        Check("Test alert schema", read_at(ref, "tests/test_alert_rules.py") is not None),
        Check("Notes cá nhân đã viết", read_at(ref, "submission/notes/r3-dashboard-slo.md") is not None),
    ]


def check_r4(ref: str) -> list[Check]:
    report = read_at(ref, "submission/REPORT.md")
    return [
        Check("Notes điều tra đã viết", read_at(ref, "submission/notes/r4-incident.md") is not None),
        Check("Công cụ trích bằng chứng", read_at(ref, "scripts/analyze_logs.py") is not None),
        Check(
            "REPORT không còn ô chờ (⏳)",
            bool(report) and "⏳" not in report,
            "submission/REPORT.md",
        ),
    ]


ROLES = [
    ("R1", "Nguyễn Vũ Việt Anh", "feat/logging-pii", check_r1),
    ("R2", "Nguyễn Minh Đạt", "feat/tracing-prompt", check_r2),
    ("R3", "Nguyễn Văn Quân", "feat/dashboard-slo-alert", check_r3),
    ("R4", "Nguyễn Kim Quý", "feat/incident-report", check_r4),
]


def collect(*, use_remote: bool) -> list[RoleStatus]:
    statuses = []
    for role, owner, branch, checker in ROLES:
        ref = f"origin/{branch}" if use_remote else branch
        status = RoleStatus(role=role, owner=owner, branch=branch)
        branch_activity(status, ref)
        status.checks = checker(ref) if status.exists else []
        statuses.append(status)
    return statuses


def format_idle(minutes: float | None) -> str:
    if minutes is None:
        return "—"
    if minutes < 60:
        return f"{minutes:.0f} phút"
    return f"{minutes / 60:.1f} giờ"


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Bảng tiến độ nhóm Day 13")
    parser.add_argument("--role", help="Chỉ xem một vai: R1, R2, R3 hoặc R4")
    parser.add_argument("--no-fetch", action="store_true", help="Không git fetch, dùng dữ liệu local")
    parser.add_argument("--local", action="store_true", help="Đọc branch local thay vì origin/")
    parser.add_argument(
        "--stale-minutes",
        type=int,
        default=45,
        help="Bao lâu không push thì coi là im lặng và cần giục (mặc định 45)",
    )
    args = parser.parse_args()

    if not args.no_fetch and not args.local:
        print("Đang fetch origin...")
        git("fetch", "--quiet", "origin")

    statuses = collect(use_remote=not args.local)
    if args.role:
        statuses = [s for s in statuses if s.role.upper() == args.role.upper()]
        if not statuses:
            raise SystemExit(f"Không có vai: {args.role}")

    print("\n=== TIẾN ĐỘ NHÓM DAY 13 ===\n")
    print(f"{'Vai':<4} {'Người':<22} {'Xong':<8} {'Commit':<7} {'Im lặng':<10} Việc cuối")
    print("-" * 96)
    for status in statuses:
        if not status.exists:
            print(f"{status.role:<4} {status.owner:<22} {'branch chưa có trên remote'}")
            continue
        flag = "  <-- CẦN GIỤC" if (status.minutes_idle or 0) > args.stale_minutes and status.percent < 100 else ""
        progress = f"{status.done_count}/{len(status.checks)}"
        print(
            f"{status.role:<4} {status.owner:<22} {progress:<8} {status.commits_ahead:<7} "
            f"{format_idle(status.minutes_idle):<10} {status.last_commit[:40]}{flag}"
        )

    print()
    for status in statuses:
        if not status.exists:
            continue
        print(f"--- {status.role} · {status.owner} · {status.branch} ({status.percent}%) ---")
        for check in status.checks:
            mark = "[x]" if check.done else "[ ]"
            hint = f"  → {check.hint}" if check.hint and not check.done else ""
            print(f"  {mark} {check.label}{hint}")
        print()

    blocked = [s for s in statuses if s.role != "R1" and s.percent < 100]
    r1 = next((s for s in statuses if s.role == "R1"), None)
    if r1 and r1.percent < 100:
        print("Nhắc: R1 chưa xong — chưa merge được thì R3 và R4 không có log đủ trường để chốt evidence.")
    elif blocked:
        print("R1 xong rồi: merge ngay và báo cả nhóm rebase origin/main.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
