from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app import logging_config
from app.main import app
from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_vietnamese_passport() -> None:
    out = scrub_text("Passport number C1234567 issued in Hanoi")
    assert "C1234567" not in out
    assert "REDACTED_PASSPORT_VN" in out


def test_scrub_vietnamese_address_keywords() -> None:
    address = "số nhà 12, đường Nguyễn Trãi, phường Trung Hòa, quận Nam Từ Liêm"
    out = scrub_text(address)
    assert "REDACTED_ADDRESS_VN" in out
    assert "Nguyễn Trãi" not in out


def test_technical_text_is_not_mistaken_for_an_address() -> None:
    """Log preview là thứ đọc khi điều tra sự cố, redact nhầm là mất luôn manh mối."""
    for text in (
        "Đường dẫn dashboard nằm ở docs/dashboard-spec.md",
        "Cách tối ưu đường truyền khi p95 tăng cao là gì?",
        "Xã hội hóa chi phí quan sát",
    ):
        assert scrub_text(text) == text


def test_technical_id_is_not_mistaken_for_a_passport() -> None:
    text = "Model GPT4 xử lý request X1234567 trong 200ms"
    assert scrub_text(text) == text


def test_correlation_id_format(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    cid = response.headers.get("x-request-id")
    assert cid is not None
    assert re.fullmatch(r"req-[0-9a-f]{8}", cid)
