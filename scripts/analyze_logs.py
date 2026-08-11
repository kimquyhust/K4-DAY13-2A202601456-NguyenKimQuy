"""Trích bằng chứng điều tra incident từ data/logs.jsonl.

Công cụ nội bộ của nhóm (vai R4 — Incident & Report). Không thay thế
`validate_logs.py` hay `validate_dashboard.py`; mục đích là dựng lại nhanh
luồng Metrics → Traces → Logs khi viết báo cáo và khi demo.

Ví dụ:
    python scripts/analyze_logs.py
    python scripts/analyze_logs.py --feature monitoring --top 5
    python scripts/analyze_logs.py --threshold-ms 2000 --out submission/evidence/r4-log-analysis.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from app.metrics import percentile


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"Không tìm thấy {path}. Chạy API và load test trước.")
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not records:
        raise SystemExit(f"{path} không có bản ghi JSON hợp lệ.")
    return records


def parse_ts(record: dict) -> datetime | None:
    raw = record.get("ts")
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def in_window(record: dict, since_minutes: int | None) -> bool:
    if since_minutes is None:
        return True
    ts = parse_ts(record)
    if ts is None:
        return False
    age_minutes = (datetime.now(timezone.utc) - ts).total_seconds() / 60
    return age_minutes <= since_minutes


def build_report(records: list[dict], *, feature: str | None, top: int, threshold_ms: int) -> list[str]:
    received = [r for r in records if r.get("event") == "request_received"]
    responded = [r for r in records if r.get("event") == "response_sent"]
    failed = [r for r in records if r.get("event") == "request_failed"]

    feature_warning: str | None = None
    if feature:
        matched = [r for r in responded if r.get("feature") == feature]
        if not matched and responded:
            feature_warning = (
                f"Không bản ghi nào có `feature={feature}` — log chưa được enrich. "
                "Cần merge phần Logging & PII (R1) rồi chạy lại; tạm thời phân tích toàn bộ log."
            )
        else:
            received = [r for r in received if r.get("feature") == feature]
            responded = matched
            failed = [r for r in failed if r.get("feature") == feature]

    latencies = [r["latency_ms"] for r in responded if isinstance(r.get("latency_ms"), int)]
    costs = [r["cost_usd"] for r in responded if isinstance(r.get("cost_usd"), (int, float))]
    tokens_in = [r["tokens_in"] for r in responded if isinstance(r.get("tokens_in"), int)]
    tokens_out = [r["tokens_out"] for r in responded if isinstance(r.get("tokens_out"), int)]
    quality = [r["quality_score"] for r in responded if isinstance(r.get("quality_score"), (int, float))]

    denominator = len(received) or len(responded) + len(failed)
    error_rate = (len(failed) / denominator * 100) if denominator else 0.0

    p95 = percentile(latencies, 95)
    verdict = "VƯỢT NGƯỠNG" if p95 > threshold_ms else "trong ngưỡng"

    lines = [
        "# Phân tích log — bằng chứng điều tra",
        "",
        f"- Nguồn: `data/logs.jsonl` · filter feature: `{feature or 'tất cả'}`",
        f"- Số bản ghi: request_received={len(received)}, response_sent={len(responded)}, request_failed={len(failed)}",
        "",
        "## Metrics rút từ log",
        "",
        "| Chỉ số | Giá trị |",
        "|---|---|",
        f"| Latency p50 | {percentile(latencies, 50):.0f} ms |",
        f"| Latency p95 | {p95:.0f} ms ({verdict} {threshold_ms} ms) |",
        f"| Latency p99 | {percentile(latencies, 99):.0f} ms |",
        f"| Latency max | {max(latencies) if latencies else 0} ms |",
        f"| Error rate | {error_rate:.2f}% |",
        f"| Tổng cost | {sum(costs):.6f} USD |",
        f"| Tokens in / out | {sum(tokens_in)} / {sum(tokens_out)} |",
        f"| Quality trung bình | {mean(quality):.3f} |" if quality else "| Quality trung bình | n/a |",
        "",
    ]

    if feature_warning:
        lines += [f"> Cảnh báo: {feature_warning}", ""]

    if failed:
        lines += ["## Breakdown lỗi", "", "| error_type | Số lần |", "|---|---|"]
        for error_type, count in Counter(r.get("error_type", "unknown") for r in failed).most_common():
            lines.append(f"| {error_type} | {count} |")
        lines.append("")

    slowest = sorted(
        (r for r in responded if isinstance(r.get("latency_ms"), int)),
        key=lambda r: r["latency_ms"],
        reverse=True,
    )[:top]

    lines += [
        f"## {len(slowest)} request chậm nhất — mở trace theo thứ tự này",
        "",
        "| latency_ms | correlation_id | feature | session_id | ts |",
        "|---:|---|---|---|---|",
    ]
    for record in slowest:
        lines.append(
            f"| {record['latency_ms']} | `{record.get('correlation_id', 'MISSING')}` | "
            f"{record.get('feature', '-')} | {record.get('session_id', '-')} | {record.get('ts', '-')} |"
        )
    lines.append("")

    missing_cid = [r for r in responded if not r.get("correlation_id") or r.get("correlation_id") == "MISSING"]
    if missing_cid:
        lines += [
            f"> Cảnh báo: {len(missing_cid)}/{len(responded)} bản ghi `response_sent` chưa có correlation ID "
            "→ chưa nối được log với trace. Cần merge phần Logging & PII (R1) rồi chạy lại.",
            "",
        ]

    prompt_events = [r for r in records if r.get("event") == "prompt_resolved"]
    if prompt_events:
        payload = prompt_events[-1].get("payload", {})
        lines += [
            "## Prompt version đang phục vụ",
            "",
            f"- name: `{payload.get('prompt_name')}` · label: `{payload.get('prompt_label')}` · "
            f"version: `{payload.get('prompt_version')}` · source: `{payload.get('prompt_source')}`",
            f"- trace_id mẫu: `{payload.get('trace_id')}`",
            "",
        ]
    else:
        lines += [
            "> Chưa thấy event `prompt_resolved` — cần merge phần Tracing & Prompt Version (R2) "
            "để nối log với trace ID.",
            "",
        ]

    return lines


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Trích bằng chứng điều tra từ log JSON")
    parser.add_argument("--log", type=Path, default=REPO_ROOT / "data" / "logs.jsonl")
    parser.add_argument("--feature", help="Chỉ phân tích một feature, ví dụ monitoring")
    parser.add_argument("--top", type=int, default=5, help="Số request chậm nhất cần liệt kê")
    parser.add_argument(
        "--threshold-ms",
        type=int,
        default=2000,
        help="Ngưỡng latency để đánh giá p95 (mặc định theo challenge.json)",
    )
    parser.add_argument("--since-minutes", type=int, help="Chỉ lấy log trong N phút gần nhất")
    parser.add_argument("--out", type=Path, help="Ghi kết quả ra file Markdown")
    args = parser.parse_args()

    records = [r for r in load_records(args.log) if in_window(r, args.since_minutes)]
    if not records:
        raise SystemExit("Không có bản ghi nào trong cửa sổ thời gian đã chọn.")

    report = "\n".join(build_report(
        records, feature=args.feature, top=args.top, threshold_ms=args.threshold_ms
    ))
    print(report)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report + "\n", encoding="utf-8")
        print(f"\nĐã ghi: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
