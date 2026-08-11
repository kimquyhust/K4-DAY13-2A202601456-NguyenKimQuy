# Báo cáo Day 13 Observability

> Trạng thái: bản nháp do leader dựng khung. Ô đánh dấu `⏳` đang chờ role tương ứng bàn giao, sẽ được thay bằng số liệu và evidence thật trước khi nộp. Không nộp bài khi còn ký hiệu `⏳`.

## 1. Thông tin nhóm

- Tên nhóm: K4 — 2A202601456
- Repository URL: https://github.com/kimquyhust/K4-DAY13-2A202601456-NguyenKimQuy
- Commit SHA cuối: ⏳ điền trước khi nộp
- Thành viên và vai trò:

| Thành viên | Vai trò | Branch |
|---|---|---|
| Nguyễn Vũ Việt Anh | R1 — Logging & PII | `feat/logging-pii` |
| Nguyễn Minh Đạt | R2 — Tracing & Prompt Version | `feat/tracing-prompt` |
| Nguyễn Văn Quân | R3 — Dashboard, SLO & Alert | `feat/dashboard-slo-alert` |
| Nguyễn Kim Quy | R4 — Incident, Report & Demo (leader) | `feat/incident-report` |

## 2. Kết quả kỹ thuật

| Chỉ số | Baseline (2026-08-11, trước khi làm) | Kết quả cuối |
|---|---|---|
| Điểm `validate_logs.py` | 30/100 | ⏳ R1, mục tiêu 100/100 |
| `python -m pytest -q` | 30 passed | ⏳ cập nhật sau khi merge |
| `validate_dashboard.py` | `HỢP LỆ: 6/6 panel` | giữ nguyên 6/6 |
| Tổng số traces | 0 (`tracing_enabled: false`) | ⏳ R2, tối thiểu 10 |
| Số PII leak còn lại | 0 | ⏳ giữ 0 |
| Link/đường dẫn dashboard | chưa có | ⏳ R3, `dashboard/app.py` |

## 3. Logging và tracing

- Evidence correlation ID: ⏳ R1 — `submission/evidence/r1-log-correlation-id.png`
- Evidence PII redaction: ⏳ R1 — `submission/evidence/r1-pii-redacted.png`
- Evidence trace waterfall: ⏳ R2 — `submission/evidence/r2-trace-waterfall.png`
- Giải thích một span đáng chú ý: span retrieval trong request chậm chiếm ~2,5 s trên tổng ~2,66 s (≈94% thời gian), trong khi span generation giữ nguyên ~0,15 s. Đây là cơ sở khoanh vùng root cause về tầng retrieval chứ không phải model.

Ghi chú kỹ thuật của leader: PII đã đạt PASS ngay từ baseline vì `/chat` chỉ log preview qua `summarize_text()` (hàm này gọi `scrub_text()` trước khi trả về). Processor `scrub_event` được bật thêm với vai trò defense-in-depth cho các field không đi qua `summarize_text`.

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: ⏳ R2 — v1, label `production`
- Version/label candidate: ⏳ R2 — v2, label `staging`
- Trace ID của mỗi version: ⏳ R2
- Bằng chứng đổi label hoặc rollback: ⏳ R2 — `submission/evidence/r2-rollback-before.png`, `r2-rollback-after.png`

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel có trong dashboard contract.`
- Evidence dashboard: ⏳ R3 — `submission/evidence/r3-dashboard-6panel.png`
- SLO đã chọn và lý do: ⏳ R3 — `config/slo.yaml`
- Alert rules và runbook: ⏳ R3 — `config/alert_rules.yaml` + `docs/alerts.md`

Yêu cầu leader đã chốt với R3: alert latency phải đặt ngưỡng **2000 ms** khớp `latency_threshold_ms` trong `config/challenge.json`, vì đo thực tế cho thấy sự cố đẩy p95 lên 2660 ms.

## 6. Điều tra challenge

- Challenge ID: `day13-k4-observability-v1` (cohort K4, incident `rag_slow`, seed 1304, feature `monitoring`, ngưỡng 2000 ms)
- Triệu chứng từ metrics: latency p95 tăng từ **155 ms** lên **2660 ms**, vượt ngưỡng 2000 ms. Error rate giữ **0%**; cost, token và quality **không đổi** → loại trừ `tool_fail` và `cost_spike`, triệu chứng thuần latency.
- Trace ID liên quan: ⏳ chạy lại sau khi R2 bật Langfuse
- Log line/correlation ID liên quan: ⏳ chạy lại sau khi R1 merge (log hiện còn `correlation_id: MISSING`)
- Root cause: bước retrieval bị chặn đồng bộ — `app/mock_rag.py` `time.sleep(2.5)` khi cờ `rag_slow` bật, khiến mọi request qua `retrieve()` cộng thêm ~2,5 s trước khi gọi LLM.
- Yếu tố khuếch đại: `LabAgent.run()` là hàm đồng bộ gọi trực tiếp trong endpoint `async def chat`, nên `time.sleep` chặn event loop; với `--concurrency 5` các request xếp hàng nối đuôi. Client đo **13 350 ms** trong khi app tự ghi `latency_ms` = **2660 ms** — độ trễ người dùng thật lớn gấp ~5 lần con số app ghi lại.
- Fix action: tắt incident; đặt timeout cho vector store và trả fallback khi quá hạn; đưa `retrieve()` sang bất đồng bộ hoặc chạy `agent.run()` trong threadpool; cache kết quả retrieval.
- Preventive measure: alert p95 > 2000 ms duy trì 5 phút; panel latency p50/p95/p99 có threshold line; timeout + circuit breaker cho phụ thuộc ngoài; load test hồi quy `--concurrency 5` trước mỗi release; đo thêm latency ở tầng client thay vì chỉ tin `latency_ms` của app.

Chi tiết số liệu hai pha đo và cách tái lập: [notes/r4-incident.md](notes/r4-incident.md).

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Nguyễn Vũ Việt Anh | Correlation ID, enrich log, PII redaction, test PII | ⏳ | ⏳ |
| Nguyễn Minh Đạt | Langfuse tracing, prompt v1/v2, label + rollback, log `prompt_resolved` nối trace ↔ log | ⏳ | ⏳ |
| Nguyễn Văn Quân | Dashboard 6 panel, SLO, 3 alert rules + runbook, test alert schema | ⏳ | ⏳ |
| Nguyễn Kim Quy | Kế hoạch nhóm và luật merge, dựng môi trường, điều tra challenge, `scripts/analyze_logs.py` + 8 test, báo cáo và demo | `cb5bacd`, ⏳ | Metric do app tự ghi có thể che giấu độ trễ người dùng thật khi tầng xử lý chặn event loop; phải đối chiếu nhiều tầng đo trước khi kết luận |
