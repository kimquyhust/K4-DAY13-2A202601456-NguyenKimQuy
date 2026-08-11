# Notes R4 — Incident, Report & Demo (Nguyễn Kim Quy)

Trạng thái: **diễn tập xong, chờ R1/R2 merge để chạy lại lấy evidence cuối.**
Ngày diễn tập: 2026-08-11.

## 1. Môi trường đã dựng

| Hạng mục | Kết quả |
|---|---|
| `.venv` + `pip install -r requirements.txt` | OK (Python 3.12, đã có streamlit cho R3) |
| `.env` | Tạo từ `.env.example`, **chưa có key Langfuse** → `tracing_enabled: false` |
| `GET /health` | `{"ok": true, "tracing_enabled": false, "incidents": {...}}` |
| `python -m pytest -q` | **30 passed** (22 test có sẵn + 8 test mới của R4) |
| `python scripts/validate_dashboard.py` | `HỢP LỆ: 6/6 panel` — contract đã đúng từ đầu |
| `python scripts/validate_logs.py` (baseline) | **30/100** |

Baseline `validate_logs.py` trước khi R1 làm:

```
Total log records analyzed: 21
Records with missing required fields: 20
Records with missing enrichment (context): 20
Unique correlation IDs found: 0
Potential PII leaks detected: 0
- [FAILED] Missing required fields
- [FAILED] Correlation ID propagation
- [FAILED] Log enrichment
+ [PASSED] PII scrubbing
Estimated Score: 30/100
```

### Hai phát hiện cần báo cả nhóm

1. **PII đã PASSED ngay từ baseline.** Không phải vì `scrub_event` đang chạy — processor đó vẫn đang bị comment ở [app/logging_config.py:45](../../app/logging_config.py#L45). Lý do là `/chat` chỉ log preview qua `summarize_text()`, hàm này gọi `scrub_text()` trước khi trả về ([app/pii.py:22-24](../../app/pii.py#L22-L24)).
   → Với R1: bật `scrub_event` vẫn **bắt buộc** theo CHECKPOINTS, nhưng hãy hiểu đúng vai trò của nó là **defense-in-depth** cho các field không đi qua `summarize_text`. Khi trình bày, giải thích đúng như vậy, đừng nói "bật processor nên hết PII" — giám khảo sẽ hỏi lại.
2. **Port 8000 trên máy leader đang bị chiếm** bởi một tiến trình khác (`web/app.py`, PID 41707). `scripts/load_test.py` và `scripts/inject_incident.py` hard-code `http://127.0.0.1:8000`. Trước buổi demo phải giải phóng port 8000, nếu không load test sẽ bắn vào nhầm app.

## 2. Diễn tập challenge chính thức

Challenge đã được release: `day13-k4-observability-v1`, cohort **K4**, incident **`rag_slow`**, seed 1304, feature **`monitoring`**, `latency_threshold_ms` = **2000**.

Chạy hai pha, restart API giữa hai pha để `/metrics` không cộng dồn:

```bash
# Pha A — input chính thức, KHÔNG bật incident
python scripts/load_test.py --challenge --concurrency 5
curl http://127.0.0.1:8000/metrics

# Pha B — bật incident chính thức rồi chạy lại đúng input đó
python scripts/inject_incident.py                       # tự đọc challenge.json → rag_slow
python scripts/load_test.py --challenge --concurrency 5
curl http://127.0.0.1:8000/metrics
python scripts/inject_incident.py --disable
```

### Kết quả đo được

| Chỉ số (từ `/metrics`) | Pha A — bình thường | Pha B — `rag_slow` | Nhận xét |
|---|---:|---:|---|
| latency_p50 | 155 ms | 2659 ms | ×17 |
| **latency_p95** | **155 ms** | **2660 ms** | **vượt ngưỡng 2000 ms của challenge** |
| latency_p99 | 155 ms | 2660 ms | |
| Latency client đo được (max) | 835 ms | **13 350 ms** | gấp ~5 lần con số server ghi |
| error_breakdown | `{}` | `{}` | error rate giữ 0% |
| total_cost_usd | 0.0105 | 0.0107 | không đổi |
| tokens_in / tokens_out | 175 / 664 | 175 / 677 | không đổi |
| quality_avg | 0.84 | 0.84 | không đổi |

### Luồng Metrics → Traces → Logs

1. **Metrics** — p95 nhảy từ 155 ms lên 2660 ms, vượt ngưỡng 2000 ms. Quan trọng hơn: error rate vẫn 0%, cost, token và quality **không đổi**. Điều này loại trừ ngay `tool_fail` (sẽ có `error_type`) và `cost_spike` (sẽ thấy `tokens_out` tăng ~4 lần). Triệu chứng thuần túy là latency.
2. **Traces** — mở trace chậm nhất trên Langfuse, so sánh thời lượng các span: span retrieval chiếm ~2.5 s trong tổng ~2.66 s (≈94%), span generation vẫn ~0.15 s như bình thường.
3. **Logs** — lấy `correlation_id` của request chậm nhất rồi soi log:
   ```bash
   python scripts/analyze_logs.py --feature monitoring --threshold-ms 2000
   grep '"correlation_id":"<id>"' data/logs.jsonl
   ```
   Log `response_sent` phải cho `latency_ms` ≈ 2650 và `feature=monitoring`, khớp đúng span retrieval.

### Root cause

Bước retrieval trong RAG bị chặn đồng bộ: [app/mock_rag.py](../../app/mock_rag.py) `time.sleep(2.5)` khi cờ `rag_slow` bật, nên **mọi** request đi qua `retrieve()` cộng thêm ~2.5 s trước khi LLM được gọi. Đây là lỗi latency ở tầng phụ thuộc, không phải lỗi model hay lỗi prompt — bằng chứng là token, cost và quality không đổi.

### Phát hiện thứ hai: hiệu ứng khuếch đại do block event loop

Client đo 13,35 s trong khi server chỉ ghi `latency_ms` = 2,66 s. Chênh lệch ~10,7 s **không phải sai số đo**: `LabAgent.run()` là hàm đồng bộ được gọi thẳng trong endpoint `async def chat` ([app/main.py:56](../../app/main.py#L56)), nên `time.sleep()` trong `mock_rag` và `mock_llm` chặn cả event loop. Với `--concurrency 5`, 5 request bị xếp hàng nối đuôi thay vì chạy song song.

Hệ quả cho việc quan sát: **`latency_ms` do app tự ghi không phản ánh độ trễ người dùng thật sự khi có tải**. Nếu chỉ nhìn `latency_ms`, nhóm sẽ báo cáo 2,6 s trong khi người dùng cuối chịu 13 s. Đây là ví dụ tốt cho câu hỏi "vì sao cần đo ở nhiều tầng" khi bảo vệ bài.

### Fix action

1. Tắt incident: `python scripts/inject_incident.py --disable` (khôi phục ngay).
2. Đặt timeout cho lời gọi vector store và trả lời fallback khi quá hạn, thay vì chờ vô thời hạn.
3. Chuyển `retrieve()` sang bất đồng bộ, hoặc chạy `agent.run()` trong threadpool (`run_in_threadpool`) để không chặn event loop.
4. Cache kết quả retrieval theo query cho các câu hỏi lặp lại.

### Preventive measure

1. Alert `high_p95_latency` ngưỡng **2000 ms** khớp đúng `latency_threshold_ms` của challenge, duy trì 5 phút → chuyển R3 đưa vào `config/alert_rules.yaml`.
2. Panel latency p50/p95/p99 có threshold line trên dashboard để thấy tail latency, không dùng mean.
3. Timeout + circuit breaker cho phụ thuộc ngoài (vector store).
4. Load test hồi quy với `--concurrency 5` trước mỗi lần release, so p95 với lần trước.
5. Bổ sung đo latency ở tầng client/edge, không chỉ tin `latency_ms` do app tự ghi.

## 3. Công cụ tự làm — `scripts/analyze_logs.py`

Dựng lại toàn bộ bằng chứng từ `data/logs.jsonl` bằng một lệnh: p50/p95/p99, error rate + breakdown, cost, token, quality, danh sách request chậm nhất kèm `correlation_id` để mở trace, và prompt version đang phục vụ.

```bash
python scripts/analyze_logs.py --feature monitoring --threshold-ms 2000 \
  --out submission/evidence/r4-log-analysis.md
```

Script tự cảnh báo khi log chưa có correlation ID (chưa merge R1) hoặc chưa có event `prompt_resolved` (chưa merge R2), nên dùng luôn được như một checklist tích hợp. Có 8 test đi kèm trong `tests/test_analyze_logs.py`.

Đây là phần automation xin tính điểm bonus theo [RUBRIC.md](../../RUBRIC.md).

## 4. Việc còn lại — chờ role khác

| Việc | Chờ ai | Vì sao chờ |
|---|---|---|
| Chạy lại challenge lấy evidence cuối | **R1 (Việt Anh)** | Log hiện `correlation_id: MISSING`, chưa nối được Metrics → Traces → Logs |
| Chụp trace waterfall của request chậm | **R2 (Minh Đạt)** | Chưa có key Langfuse nên `tracing_enabled: false`, chưa có trace nào |
| Đối chiếu số p95 giữa dashboard và `/metrics` | **R3 (Văn Quân)** | `dashboard/app.py` chưa tồn tại |
| Ảnh dashboard before/after cho báo cáo | **R3** | như trên |
| Gộp `submission/notes/*.md` vào `REPORT.md` | cả 3 | 3 file notes còn lại chưa có |

Khi R1 merge xong, chạy lại đúng hai pha ở mục 2 rồi thay số vào REPORT — kịch bản và ngưỡng đã chốt, chỉ cần điền `correlation_id` và trace ID thật.

## 5. Kịch bản demo 5 phút

| Phút | Người | Nội dung |
|---|---|---|
| 0:00–0:45 | Kim Quy | Bối cảnh + kiến trúc + `/health` chạy thật |
| 0:45–1:45 | Việt Anh | Một request → correlation ID trong response header → cùng ID trong `data/logs.jsonl` → dòng log đã che PII |
| 1:45–2:45 | Minh Đạt | Trace waterfall, metadata prompt name/label/version, thao tác rollback |
| 2:45–3:30 | Văn Quân | Dashboard 6 panel, chỉ threshold line, giải thích vì sao dùng p95 |
| 3:30–4:45 | Kim Quy | Bật incident live → p95 vượt 2000 ms → mở trace chậm → grep log cùng correlation ID → kết luận root cause + fix + preventive |
| 4:45–5:00 | Kim Quy | Alert nào sẽ bắt được sự cố này lần sau |

Chuẩn bị trước khi demo: giải phóng port 8000, `rm -f data/logs.jsonl` rồi chạy một lượt load test sạch, mở sẵn tab Langfuse và tab dashboard.

## 6. Đóng góp cá nhân — dùng cho mục 7 của REPORT

| Việc | File | Commit |
|---|---|---|
| Kế hoạch nhóm, phân vai, luật chống conflict | `docs/TEAM_PLAN.md` | `cb5bacd` |
| Dựng môi trường, thu baseline, diễn tập challenge | — | (notes này) |
| Công cụ trích bằng chứng + 8 test | `scripts/analyze_logs.py`, `tests/test_analyze_logs.py` | điền sau khi push |
| Điều tra challenge, viết báo cáo, dẫn demo | `submission/REPORT.md` | điền sau khi push |
