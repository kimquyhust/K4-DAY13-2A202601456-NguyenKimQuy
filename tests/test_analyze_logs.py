from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("analyze_logs", REPO_ROOT / "scripts" / "analyze_logs.py")
analyze_logs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analyze_logs)


def _record(event: str, **fields) -> dict:
    base = {"ts": "2026-08-11T08:00:00Z", "level": "info", "service": "api", "event": event}
    base.update(fields)
    return base


ENRICHED_LOG = [
    _record("request_received", correlation_id="req-aaaaaaaa", feature="monitoring"),
    _record(
        "response_sent",
        correlation_id="req-aaaaaaaa",
        feature="monitoring",
        latency_ms=2650,
        cost_usd=0.002,
        tokens_in=35,
        tokens_out=130,
        quality_score=0.84,
    ),
    _record("request_received", correlation_id="req-bbbbbbbb", feature="qa"),
    _record("request_failed", correlation_id="req-bbbbbbbb", feature="qa", error_type="RuntimeError"),
]


def build(records, **kwargs):
    options = {"feature": None, "top": 5, "threshold_ms": 2000}
    options.update(kwargs)
    return "\n".join(analyze_logs.build_report(records, **options))


def test_flags_p95_above_challenge_threshold():
    report = build(ENRICHED_LOG)
    assert "VƯỢT NGƯỠNG 2000 ms" in report


def test_reports_error_rate_and_breakdown():
    report = build(ENRICHED_LOG)
    assert "| Error rate | 50.00% |" in report
    assert "| RuntimeError | 1 |" in report


def test_feature_filter_narrows_to_selected_feature():
    report = build(ENRICHED_LOG, feature="monitoring")
    assert "request_failed=0" in report
    assert "log chưa được enrich" not in report


def test_warns_when_enrichment_missing_instead_of_returning_empty():
    raw = [
        _record("request_received"),
        _record("response_sent", latency_ms=150, cost_usd=0.001, tokens_in=30, tokens_out=90, quality_score=0.8),
    ]
    report = build(raw, feature="monitoring")
    assert "log chưa được enrich" in report
    assert "| Latency p95 | 150 ms" in report


def test_warns_when_correlation_id_missing():
    raw = [_record("response_sent", correlation_id="MISSING", latency_ms=100)]
    report = build(raw)
    assert "chưa có correlation ID" in report


def test_surfaces_prompt_version_when_r2_logging_present():
    records = ENRICHED_LOG + [
        _record(
            "prompt_resolved",
            service="agent",
            payload={
                "prompt_name": "day13-chat",
                "prompt_label": "production",
                "prompt_version": "2",
                "prompt_source": "langfuse",
                "trace_id": "trace-123",
            },
        )
    ]
    report = build(records)
    assert "day13-chat" in report
    assert "trace-123" in report


def test_load_records_rejects_missing_file(tmp_path):
    with pytest.raises(SystemExit):
        analyze_logs.load_records(tmp_path / "khong-ton-tai.jsonl")


def test_load_records_skips_broken_lines(tmp_path):
    log = tmp_path / "logs.jsonl"
    log.write_text(json.dumps(_record("response_sent", latency_ms=10)) + "\nkhong-phai-json\n", encoding="utf-8")
    assert len(analyze_logs.load_records(log)) == 1
