# R1 — Logging & PII (Nguyễn Vũ Việt Anh)

Branch: `feat/logging-pii` · Kết quả `python scripts/validate_logs.py`: **100/100, 0 PII leak, 10 unique correlation IDs**. `pytest -q`: **25 passed**.

## Việc 1 — Correlation ID (app/middleware.py)

Lan truyền bằng **structlog `contextvars`** (nơi bất biến theo async task) chứ không truyền tham số qua từng handler:

- `clear_contextvars()` ngay đầu `dispatch` — chống context của request trước rò sang request sau khi chạy `--concurrency 5`.
- `correlation_id = request.headers.get("x-request-id") or f"req-{uuid.uuid4().hex[:8]}"` — ưu tiên header client, không có mới sinh mới, format `req-<8 hex>`.
- `bind_contextvars(correlation_id=...)` **trước** `call_next` để mọi log trong xử lý request đều mang ID.
- Sau `call_next`: ghi `x-request-id` và `x-response-time-ms` vào response header.

## Việc 2 — PII scrubbing (app/logging_config.py)

Bật `scrub_event` **trước** `JsonlFileProcessor()` trong list processor. Vị trí quyết định: nếu đặt sau, file `data/logs.jsonl` vẫn còn PII nguyên văn (console có thể sạch nhưng validator trừ 30 điểm). Processor chain có thứ tự — scrub phải chạy trước render/ghi file.

## Việc 3 — Enrich log (app/main.py)

`bind_contextvars(user_id_hash=hash_user_id(body.user_id), session_id, feature, model, env)` đặt **trước** `log.info("request_received", ...)`. Vì bind vào contextvars nên cả 3 event `request_received`, `response_sent`, `request_failed` đều kế thừa metadata — nhánh `except` không thiếu field (validator yêu cầu mọi record `service == "api"` có đủ 5 field enrichment).

## Việc 4 + 5 — PII patterns & tests (app/pii.py, tests/test_pii.py)

- Thêm `passport_vn` (`\b[A-Z]\d{7}\b`) và `address_vn` (keyword `số nhà|đường|phường|quận` + phần địa chỉ theo sau).
- Thêm test mới: scrub passport VN, scrub địa chỉ VN, và correlation ID format `req-[0-9a-f]{8}`.
- Pattern tránh quá rộng để không phá test cũ và không làm `quality_score` bị trừ do answer chứa `[REDACTED`.

## Việc 6 (bonus) — Scrub đệ quy

`scrub_event` giờ quét **đệ quy mọi field string** trong `event_dict` (dict lồng nhau + list), không chỉ `payload` và `event`.

## Câu hỏi chấm

- **Cơ chế lan truyền:** `contextvars` gắn giá trị theo async context/task, giữ đúng correlation ID suốt vòng đời request mà không cần truyền tay. Không dùng tham số vì sẽ phải sửa signature mọi function log.
- **Hash user_id:** user_id là định danh cá nhân (PII), hash (SHA-256, 12 hex đầu) giữ khả năng trace theo người nhưng không lộ danh tính — kết hợp giữa useful và safe.
- **Thứ tự processor:** processor chạy theo thứ tự trong list; scrubbing trước khi render file mới bảo vệ cả hai sink (console + file).
- **Redaction ≠ masking ≠ hashing:** redaction thay giá trị bằng placeholder cố định, mất thông tin gốc; masking che một phần (giữ đuôi/hiển thị một phần, reverse có thể dò); hashing là hàm một chiều giữ khả năng đối chiếu nhưng không lộ giá trị.

## Evidence

- `submission/evidence/r1-validate-logs.png` — kết quả 100/100, 0 PII leak, 10 correlation ID.
- `submission/evidence/r1-log-correlation-id.png` — 1 dòng JSON log đủ 6 field.
- `submission/evidence/r1-pii-redacted.png` — dòng log có `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]` (query 1, 5, 9).

## Self-check

```bash
rm -f data/logs.jsonl
uvicorn app.main:app --env-file .env &
python scripts/load_test.py --concurrency 5
python scripts/validate_logs.py        # 100/100
grep -c "MISSING" data/logs.jsonl      # 0
grep -E "student@vinuni|0987654321|4111 1111" data/logs.jsonl  # rỗng
python -m pytest -q                    # 25 passed
```