# R2 — Tracing & Prompt Version (Nguyễn Minh Đạt)

Branch: `feat/tracing-prompt` · Commit: `cc2ed89`, `332e77b`, `ca11fb0`, `6705b2d`, `36d1cdb`.
Kết quả: **12 trace** trên Langfuse (10 trace chạy hai label + 2 trace kiểm chứng rollback),
`validate_logs.py` **100/100**, `pytest -q` **45 passed** sau merge.

File sở hữu: `app/tracing.py`, `app/prompt_management.py`, phần tracing trong `app/agent.py`,
`tests/test_tracing_adapter.py`, `tests/test_prompt_management.py`, `tests/test_agent_prompt_trace.py`.

## Việc 1 — Adapter tracing không làm chết app (`app/tracing.py`)

`observe` và `get_client` được import trong `try/except ImportError`; nếu chưa cài `langfuse`
thì `observe` trở thành decorator rỗng và `get_client()` trả `_DummyClient` nuốt mọi lời gọi.
`tracing_enabled()` chỉ trả `True` khi **vừa** có SDK **vừa** có đủ `LANGFUSE_PUBLIC_KEY` và
`LANGFUSE_SECRET_KEY`. Nhờ vậy app chạy được cả khi không có key — đúng yêu cầu README, và
test chạy được trong CI không cần secret.

## Việc 2 — Prompt v1/v2 và label (`app/prompt_management.py`)

- Prompt `day13-chat` là **text prompt**, đúng ba biến `{{feature}}`, `{{docs}}`, `{{message}}`.
- `resolve_prompt()` gọi `client.get_prompt(name, label=..., type="text", fallback=...,
  cache_ttl_seconds=60, fetch_timeout_seconds=2, max_retries=0)`.
- Ba tham số cuối là chủ ý: Langfuse là **dependency ngoài**, nếu nó chậm thì không được kéo
  theo latency của `/chat`. Timeout 2 s + không retry + cache 60 s giữ chi phí quan sát ở mức
  bounded. Đây đúng bài học của challenge R4 (một phụ thuộc chậm đủ sức phá p95).
- Mọi nhánh hỏng đều trả `ResolvedPrompt` hợp lệ với `source="local-fallback"` và
  `fetch_error` ghi tên exception — không raise ra ngoài, nhưng vẫn để lại dấu vết để điều tra.
- `is_fallback` được kiểm riêng: SDK trả prompt fallback im lặng khi fetch hỏng, nếu không
  check thì log sẽ báo version thật trong khi thực tế đang chạy prompt local.

## Việc 3 — Gắn metadata vào trace và generation (`app/agent.py`)

`LabAgent.run` được bọc `@observe(as_type="generation", capture_input=False, capture_output=False)`.
Tắt capture input/output là quyết định về PII: nội dung người dùng không được đẩy nguyên văn
lên Langfuse; thay vào đó chỉ gửi `query_preview` đã qua `summarize_text()` (tức đã scrub).

- `update_current_trace()`: `user_id=hash_user_id(user_id)` (hash, không phải ID gốc),
  `session_id`, `tags`, và metadata `prompt_name` / `prompt_label` / `prompt_version` / `prompt_source`.
- `update_current_generation()`: `model`, `doc_count`, `query_preview`, cùng bộ 4 field prompt,
  và truyền `prompt=` để Langfuse tự liên kết generation với đúng phiên bản prompt.

## Việc 4 — Nối trace ↔ log bằng event `prompt_resolved`

Đây là phần quan trọng nhất của role. Trace và log là hai hệ thống riêng; nếu không có khoá
chung thì lúc điều tra phải dò tay theo timestamp. Vì vậy `agent.py` ghi một event log ngay
sau khi resolve prompt:

```json
{"event": "prompt_resolved", "service": "agent", "correlation_id": "req-4c7481f7",
 "payload": {"prompt_name": "day13-chat", "prompt_label": "production",
             "prompt_version": "local-v1", "prompt_source": "local", "trace_id": null}}
```

Record này mang **cả** `correlation_id` (kế thừa từ contextvars của R1) **và** `trace_id`, nên
đi được hai chiều: từ log ra trace, và từ trace về đúng dòng log. `trace_id` lấy qua
`getattr(client, "get_current_trace_id", lambda: None)()` để không vỡ khi client là dummy.

Nhờ event này, `scripts/analyze_logs.py` của R4 in được luôn mục "Prompt version đang phục vụ".

## Việc 5 — Hai chỗ sửa ngoài phạm vi trace (đã báo leader)

- `app/logging_config.py`: chuyển `scrub_event` xuống **sau** `format_exc_info` (vẫn trước
  `JsonlFileProcessor`). Lý do: exception được `format_exc_info` render thành string; nếu scrub
  chạy trước thì traceback chứa PII sẽ lọt vào file. Thêm nhánh xử lý `tuple`.
- `app/middleware.py`: bọc `call_next` trong `try/finally` và gọi `clear_contextvars()` ở
  `finally`. Nếu request ném exception, contextvars của request lỗi sẽ dính sang request kế
  tiếp trong cùng task — chạy `--concurrency 5` là thấy correlation ID sai chỗ.

## Rollback đã thực hiện

1. `production` đang trỏ v1 → trace `bc9879625e05c9689bffaddd8ced2518`.
2. Đổi label `production` sang v2 → trace `21cfce66c33bfe447919b18a21f516a1` (version 2).
3. Rollback `production` về v1 → trace `79009643d7361472c8a95cdf2f60bb29` (version 1).

Không phải deploy lại app: label là con trỏ ở phía Langfuse, app đọc theo label nên rollback
có hiệu lực trong vòng `cache_ttl_seconds` (60 s).

## Câu hỏi chấm

- **Trace, span, generation khác gì nhau:** trace là toàn bộ một request; span là một bước bên
  trong; generation là span đặc biệt mô tả một lần gọi model (có model, token, cost, prompt).
- **Vì sao gắn version vào metadata thay vì đặt tên prompt kèm số:** label là con trỏ đổi được
  mà không phải sửa code; tên kèm số sẽ khoá cứng version vào source, rollback phải deploy lại.
- **Vì sao `capture_input=False`:** input chứa PII của người dùng; app chỉ gửi preview đã scrub.
- **Nếu Langfuse chết thì sao:** `resolve_prompt` bắt exception, trả prompt local, `/chat` vẫn
  200; log ghi `prompt_source: "local-fallback"` và `fetch_error` để biết đang chạy fallback.

## Evidence

- [`../evidence/r2-prompt-traces.md`](../evidence/r2-prompt-traces.md) — 4 trace ID + link Langfuse.
- ⏳ Còn thiếu 3 ảnh phải chụp tay từ giao diện Langfuse: `r2-trace-list.png`,
  `r2-trace-waterfall.png`, `r2-rollback-before.png` + `r2-rollback-after.png`.

## Self-check

```bash
python -m pytest -q tests/test_tracing_adapter.py tests/test_prompt_management.py \
                   tests/test_agent_prompt_trace.py     # 7 passed
grep prompt_resolved data/logs.jsonl | head -1          # có prompt_name/label/version/trace_id
```
