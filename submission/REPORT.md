# Báo cáo Day 13 Observability

> Trạng thái: đã merge cả 4 nhánh vào `main`. Số liệu dưới đây được đo lại trên bản merge
> ngày 2026-08-11, không phải số cũ của từng nhánh. Evidence đã đủ; chỉ còn điền commit SHA
> cuối ở mục 1 khi push.

## 1. Thông tin nhóm

- Tên nhóm: K4 — 2A202601456
- Repository URL: https://github.com/kimquyhust/K4-DAY13-2A202601456-NguyenKimQuy
- Commit SHA cuối: ⏳ điền SHA của commit cuối trên `main` khi nộp
- Thành viên và vai trò:

| Thành viên | Vai trò | Branch |
|---|---|---|
| Nguyễn Vũ Việt Anh | R1 — Logging & PII | `feat/logging-pii` |
| Nguyễn Minh Đạt | R2 — Tracing & Prompt Version | `feat/tracing-prompt` |
| Nguyễn Văn Quân | R3 — Dashboard, SLO & Alert | `feat/dashboard-slo-alert` |
| Nguyễn Kim Quy | R4 — Incident, Report & Demo (leader) | `feat/incident-report` |

## 2. Kết quả kỹ thuật

| Chỉ số | Baseline (2026-08-11, trước khi làm) | Kết quả cuối (sau merge) |
|---|---|---|
| Điểm `validate_logs.py` | 30/100 | **100/100** — 0 missing field, 0 PII leak, 17 correlation ID |
| `python -m pytest -q` | 30 passed | **45 passed** |
| `validate_dashboard.py` | `HỢP LỆ: 6/6 panel` | `HỢP LỆ: 6/6 panel` |
| Tổng số traces | 0 (`tracing_enabled: false`) | 12 (10 trace hai label + 2 trace rollback) |
| Số PII leak còn lại | 0 | 0 |
| Link/đường dẫn dashboard | chưa có | `streamlit run dashboard/app.py` |

Lệnh tái lập toàn bộ số trên:

```bash
rm -f data/logs.jsonl data/audit.jsonl
uvicorn app.main:app --env-file .env &
python scripts/load_test.py            # 10 request baseline
python scripts/validate_logs.py        # 100/100
python scripts/validate_dashboard.py   # 6/6 panel
python -m pytest -q                    # 45 passed
```

## 3. Logging và tracing

- Evidence correlation ID: `submission/evidence/r1-log-correlation-id.png` (và bản text `.txt`) — trọn vòng đời request `req-fd24948a`: `request_received` → `prompt_resolved` → `response_sent`, cả ba record cùng một `correlation_id`.
- Evidence PII redaction: `submission/evidence/r1-pii-redacted.png` (và `.txt`) — email, số điện thoại VN và số thẻ đều thành `[REDACTED_*]`; `grep` chuỗi PII gốc trong `data/logs.jsonl` trả về rỗng.
- Evidence `validate_logs.py`: `submission/evidence/r1-validate-logs.png` (và `.txt`).
- Evidence trace và metadata: `submission/evidence/r2-trace-list.png` (danh sách trace có metadata, tag `lab`/`claude-sonnet-4-5`, session ID) và `r2-trace-prompt-metadata.png` (panel metadata của một trace: `prompt_name: day13-chat`, `prompt_label: production`, `prompt_version: 1`, `prompt_source: langfuse`, `query_preview` đã scrub, `doc_count`).
- Giải thích một span đáng chú ý: span retrieval trong request chậm chiếm ~2,5 s trên tổng ~2,66 s (≈94% thời gian), trong khi span generation giữ nguyên ~0,15 s. Đây là cơ sở khoanh vùng root cause về tầng retrieval chứ không phải model.

Ghi chú kỹ thuật của leader: PII đã đạt PASS ngay từ baseline vì `/chat` chỉ log preview qua
`summarize_text()` (hàm này gọi `scrub_text()` trước khi trả về). Processor `scrub_event` được bật
thêm với vai trò defense-in-depth cho các field không đi qua `summarize_text`. Sau khi merge R2,
`scrub_event` được đặt **sau** `format_exc_info` nên che được cả text exception, vẫn **trước**
`JsonlFileProcessor()` nên file log không bao giờ thấy PII nguyên văn.

## 4. Prompt versioning

- Prompt name: `day13-chat` — text prompt, đúng ba biến `{{feature}}`, `{{docs}}`, `{{message}}`.
- Version/label baseline: v1, label `production`.
- Version/label candidate: v2, label `staging`.
- Trace ID của mỗi version:
  - `production`/v1: [`bc9879625e05c9689bffaddd8ced2518`](https://cloud.langfuse.com/project/cmsob02dn0100ad0hubskvz4q/traces/bc9879625e05c9689bffaddd8ced2518)
  - `staging`/v2: [`33fce3f382906a3ad4554ede9e1f3175`](https://cloud.langfuse.com/project/cmsob02dn0100ad0hubskvz4q/traces/33fce3f382906a3ad4554ede9e1f3175)
- Bằng chứng đổi label / rollback:
  - trước rollback (`production` → v2): [`21cfce66c33bfe447919b18a21f516a1`](https://cloud.langfuse.com/project/cmsob02dn0100ad0hubskvz4q/traces/21cfce66c33bfe447919b18a21f516a1)
  - sau rollback (`production` về v1): [`79009643d7361472c8a95cdf2f60bb29`](https://cloud.langfuse.com/project/cmsob02dn0100ad0hubskvz4q/traces/79009643d7361472c8a95cdf2f60bb29)
- Ảnh bằng chứng rollback: `submission/evidence/r2-rollback-before.png` — label `production` đang gắn trên **v2** ("Day 13 candidate prompt v2 with grounding and PII constraints"); `submission/evidence/r2-rollback-after.png` — sau rollback, `production` trở về **v1** ("Day 13 baseline prompt v1"), v2 chỉ còn `latest` + `staging`.
- Chi tiết: [evidence/r2-prompt-traces.md](evidence/r2-prompt-traces.md).
- Nối trace ↔ log: `app/agent.py` ghi event `prompt_resolved` mang `prompt_name`, `prompt_label`, `prompt_version`, `prompt_source` và `trace_id`, nên từ một dòng log tra ngược ra đúng trace trên Langfuse. Test bảo vệ: `tests/test_agent_prompt_trace.py`.

Kiểm chứng lại qua Langfuse API ngày 2026-08-11: project có **114 traces**, prompt `day13-chat`
có versions `[1, 2]` với labels `production` / `staging` / `latest`; cả 4 trace ID nêu trên đều
tồn tại và trả về đúng cặp label/version như đã khai (`21cfce66…` trả `production` v2 — đúng là
trace trước rollback).

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel có trong dashboard contract.` — ảnh `submission/evidence/r3-validate-dashboard.png`.
- Evidence dashboard: `submission/evidence/r3-dashboard-6panel.png`, cùng cặp before/after `r3-dashboard-before.png` và `r3-dashboard-after-ragslow.png`.
- Dashboard chạy bằng `streamlit run dashboard/app.py`: đọc `data/logs.jsonl`, lọc cửa sổ 60 phút gần nhất, tự refresh 30 giây, đủ 6 panel latency / traffic / errors / cost / tokens / quality kèm threshold line.
- SLO đã chọn và lý do: `config/slo.yaml` — `latency_p95_ms` 3000 ms @ 99.5%, `error_rate_pct` 2% @ 99.0% (error budget 1%), `daily_cost_usd` 2.5 USD, `quality_score_avg` 0.75 @ 95%. Lập luận đầy đủ trong [notes/r3-dashboard-slo.md](notes/r3-dashboard-slo.md).
- Alert rules và runbook: `config/alert_rules.yaml` (3 alert symptom-based, có owner và severity) + `docs/alerts.md` (runbook 3 bước theo đúng luồng Metrics → Traces → Logs). Ảnh `submission/evidence/r3-alert-rules.png`. Schema được test bởi `tests/test_alert_rules.py`.

Yêu cầu leader đã chốt với R3: alert latency đặt ngưỡng **2000 ms** khớp `latency_threshold_ms`
trong `config/challenge.json` (đo thực tế cho thấy sự cố đẩy p95 lên 2662 ms), trong khi SLO line
trên dashboard vẫn giữ 3000 ms theo contract. Alert cảnh báo sớm hơn SLO là có chủ đích.

## 6. Điều tra challenge

- Challenge ID: `day13-k4-observability-v1` (cohort K4, incident `rag_slow`, seed 1304, feature `monitoring`, ngưỡng 2000 ms)
- Triệu chứng từ metrics: latency p95 tăng từ **155 ms** lên **2662 ms**, vượt ngưỡng 2000 ms. Error rate giữ **0%**; cost/token/quality **không đổi** → loại trừ `tool_fail` và `cost_spike`, triệu chứng thuần latency.
- Trace ID liên quan: xem `evidence/r2-prompt-traces.md`; trong lần chạy xác nhận sau merge, tracing tắt nên bằng chứng là 5 correlation ID `monitoring` bên dưới.
- Log line/correlation ID liên quan: `req-cc91d8e9` (2662 ms), `req-9e65bc5f`, `req-2872c87a`, `req-fd24948a`, `req-303ff589` — tất cả `feature=monitoring`, session `k4-challenge-s01..s05`. Bảng đầy đủ trong `submission/evidence/r4-analyze-logs-challenge.md` và ảnh `r4-analyze-logs.png`.
- Root cause: bước retrieval bị chặn đồng bộ — `app/mock_rag.py` gọi `time.sleep(2.5)` khi cờ `rag_slow` bật, khiến mọi request qua `retrieve()` cộng thêm ~2,5 s trước khi gọi LLM.
- Yếu tố khuếch đại: `LabAgent.run()` là hàm đồng bộ gọi trực tiếp trong endpoint `async def chat`, nên `time.sleep` chặn event loop; với `--concurrency 5` các request xếp hàng nối đuôi. Client đo **13 328 ms** trong khi app tự ghi `latency_ms` = **2662 ms** — độ trễ người dùng thật lớn gấp ~5 lần con số app ghi lại.
- Fix action: tắt incident; đặt timeout cho vector store và trả fallback khi quá hạn; đưa `retrieve()` sang bất đồng bộ hoặc chạy `agent.run()` trong threadpool; cache kết quả retrieval.
- Preventive measure: alert p95 > 2000 ms duy trì 5 phút; panel latency p50/p95/p99 có threshold line; timeout + circuit breaker cho phụ thuộc ngoài; load test hồi quy `--concurrency 5` trước mỗi release; đo thêm latency ở tầng client thay vì chỉ tin `latency_ms` của app.

Chi tiết hai pha đo và cách tái lập: [notes/r4-incident.md](notes/r4-incident.md).
Số liệu baseline đối chứng: `submission/evidence/r4-analyze-logs-baseline.md`.

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Nguyễn Vũ Việt Anh | Correlation ID qua `contextvars`, enrich 5 field metadata, `scrub_event` đệ quy, pattern passport/địa chỉ VN, test PII | `5a5c6b8`, `07775d7`, `fdefc20`, `ece6447`, `a030ec6`, `a35057f` | Thứ tự processor của structlog quyết định file log có sạch hay không; và pattern PII quá rộng sẽ redact nhầm text kỹ thuật, làm mất manh mối khi điều tra |
| Nguyễn Minh Đạt | Langfuse tracing, prompt v1/v2 + label/rollback, log `prompt_resolved` nối trace ↔ log, `clear_contextvars` trong `finally` | `cc2ed89`, `332e77b`, `ca11fb0`, `6705b2d`, `36d1cdb` | Trace và log chỉ hữu ích khi nối được với nhau; một event log mang `trace_id` + `prompt_version` là cầu nối rẻ nhất giữa hai hệ thống |
| Nguyễn Văn Quân | Dashboard Streamlit 6 panel, `config/slo.yaml`, 3 alert rule + runbook `docs/alerts.md`, `tests/test_alert_rules.py` | `d34cac6`, `526dd5f`, `ce559da` | Ngưỡng alert và ngưỡng SLO không nhất thiết bằng nhau: alert phải kêu sớm hơn SLO thì mới còn thời gian xử lý trước khi cháy error budget |
| Nguyễn Kim Quy | Kế hoạch nhóm và luật merge, dựng môi trường, `scripts/analyze_logs.py` + `scripts/check_progress.py` và 14 test, điều tra challenge, merge 4 nhánh và hoàn thiện báo cáo | `cb5bacd`, `cd81f1a`, `e610025`, `01f2011`, `2d75bce`, `87dcc1b`, `08e1059`, `dbcbf68`, `246d93e`, `fe36808`, `e9d3be3` | Metric do app tự ghi có thể che giấu độ trễ người dùng thật khi tầng xử lý chặn event loop; phải đối chiếu nhiều tầng đo trước khi kết luận |

## 8. Ghi chú merge

`main` = R1 + R4 (`fe36808`) → fast-forward R3 (`ce559da`) → merge R2 (`e9d3be3`).
Ba conflict và cách xử lý:

| File | Giữ bản nào | Lý do |
|---|---|---|
| `app/pii.py` | main (R1, `a35057f`) | Bản R2 tách nhánh trước fix `a35057f`; pattern `(?i)[a-z]\d{7}` của R2 redact nhầm `X1234567` và `(?i)đường` redact nhầm "đường dẫn"/"đường truyền" |
| `config/alert_rules.yaml` | R3 | Ngưỡng 2000 ms khớp `latency_threshold_ms` của challenge (bản R2 để 3000 ms); owner đúng vai trò |
| `submission/REPORT.md` | main + gộp số liệu R2 | Bản R2 là template gốc, mất phần điều tra challenge |

Lấy nguyên từ R2: `prompt_resolved` trong `app/agent.py`, `scrub_event` chạy sau
`format_exc_info` trong `app/logging_config.py`, `clear_contextvars()` trong `finally` của
`app/middleware.py`.
