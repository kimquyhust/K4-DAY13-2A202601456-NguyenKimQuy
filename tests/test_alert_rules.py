from __future__ import annotations

import re
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_alert_rules_file_exists_and_no_todo() -> None:
    alert_rules_path = REPO_ROOT / "config" / "alert_rules.yaml"
    assert alert_rules_path.exists(), "Tệp config/alert_rules.yaml không tồn tại."
    content = alert_rules_path.read_text(encoding="utf-8")
    assert "TODO" not in content, "Tệp config/alert_rules.yaml vẫn còn chứa chuỗi 'TODO'."


def test_alert_rules_schema_and_valid_fields() -> None:
    alert_rules_path = REPO_ROOT / "config" / "alert_rules.yaml"
    data = yaml.safe_load(alert_rules_path.read_text(encoding="utf-8"))

    assert isinstance(data, dict), "Cấu hình alert_rules phải là một YAML dictionary."
    assert "alerts" in data, "Cấu hình alert_rules phải chứa key 'alerts'."

    alerts = data["alerts"]
    assert isinstance(alerts, list), "'alerts' phải là danh sách."
    assert len(alerts) >= 3, "Danh sách alerts phải có ít nhất 3 quy tắc cảnh báo."

    required_fields = {"name", "severity", "condition", "type", "owner", "runbook"}
    valid_severities = {"P1", "P2", "P3"}

    for idx, alert in enumerate(alerts):
        assert isinstance(alert, dict), f"Alert ở chỉ mục {idx} phải là dictionary."
        missing_fields = required_fields - set(alert.keys())
        assert not missing_fields, f"Alert '{alert.get('name')}' thiếu các trường: {missing_fields}"

        for field in required_fields:
            assert alert[field], f"Trường '{field}' trong alert '{alert['name']}' không được rỗng."

        severity = alert["severity"]
        assert severity in valid_severities, (
            f"Alert '{alert['name']}' có severity '{severity}' không hợp lệ (phải thuộc P1, P2, P3)."
        )


def test_alert_runbook_anchors_exist_in_alerts_md() -> None:
    alert_rules_path = REPO_ROOT / "config" / "alert_rules.yaml"
    alerts_doc_path = REPO_ROOT / "docs" / "alerts.md"

    assert alerts_doc_path.exists(), "Tệp docs/alerts.md không tồn tại."
    doc_content = alerts_doc_path.read_text(encoding="utf-8")

    data = yaml.safe_load(alert_rules_path.read_text(encoding="utf-8"))
    alerts = data.get("alerts", [])

    for alert in alerts:
        runbook = alert.get("runbook", "")
        assert runbook.startswith("docs/alerts.md#"), (
            f"Runbook path '{runbook}' trong alert '{alert.get('name')}' không đúng định dạng 'docs/alerts.md#anchor'."
        )

        anchor = runbook.split("#", 1)[1]
        if anchor.startswith("alert-"):
            alert_num = anchor.replace("alert-", "")
            expected_heading = f"## Alert {alert_num}"
            assert expected_heading in doc_content, (
                f"Anchor '{anchor}' từ alert '{alert.get('name')}' không khớp với tiêu đề '{expected_heading}' trong docs/alerts.md."
            )
        else:
            assert f"#{anchor}" in doc_content or f"id=\"{anchor}\"" in doc_content, (
                f"Anchor '{anchor}' không tìm thấy trong docs/alerts.md"
            )
