from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_progress", REPO_ROOT / "scripts" / "check_progress.py")
check_progress = importlib.util.module_from_spec(SPEC)
# @dataclass tra cứu module qua sys.modules khi class được tạo, nên phải đăng ký trước exec.
sys.modules["check_progress"] = check_progress
SPEC.loader.exec_module(check_progress)


def test_commented_out_code_does_not_count_as_done():
    source = "        # bind_contextvars(correlation_id=correlation_id)\n"
    assert check_progress.uncommented(source, "bind_contextvars(correlation_id") is False


def test_real_code_counts_as_done():
    source = "        bind_contextvars(correlation_id=correlation_id)\n"
    assert check_progress.uncommented(source, "bind_contextvars(correlation_id") is True


def test_missing_file_counts_as_not_done():
    assert check_progress.uncommented(None, "bất kỳ") is False


def test_percent_reflects_completed_checks():
    status = check_progress.RoleStatus(role="R9", owner="Ai Đó", branch="feat/x")
    status.checks = [
        check_progress.Check("a", True),
        check_progress.Check("b", True),
        check_progress.Check("c", False),
        check_progress.Check("d", False),
    ]
    assert status.done_count == 2
    assert status.percent == 50


def test_percent_is_zero_when_branch_has_no_checks():
    assert check_progress.RoleStatus(role="R9", owner="Ai Đó", branch="feat/x").percent == 0


def test_idle_formatting_switches_to_hours():
    assert check_progress.format_idle(None) == "—"
    assert check_progress.format_idle(20) == "20 phút"
    assert check_progress.format_idle(90) == "1.5 giờ"
