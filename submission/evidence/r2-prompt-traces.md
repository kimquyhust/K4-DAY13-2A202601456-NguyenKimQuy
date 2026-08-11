# R2 — Trace và prompt version (bằng chứng dạng text)

Nguồn: nhánh `feat/tracing-prompt` (commit `332e77b`, `ca11fb0`, `36d1cdb`), do Nguyễn Minh Đạt bàn giao.
Project Langfuse: `cmsob02dn0100ad0hubskvz4q` trên `cloud.langfuse.com`.

## Prompt

- Prompt name: `day13-chat` — text prompt, đúng ba biến `{{feature}}`, `{{docs}}`, `{{message}}`.
- v1 → label `production` (baseline).
- v2 → label `staging` (candidate).

## Trace ID theo từng version

| Mục đích | Label / version | Trace ID |
|---|---|---|
| Baseline | `production` / v1 | [`bc9879625e05c9689bffaddd8ced2518`](https://cloud.langfuse.com/project/cmsob02dn0100ad0hubskvz4q/traces/bc9879625e05c9689bffaddd8ced2518) |
| Candidate | `staging` / v2 | [`33fce3f382906a3ad4554ede9e1f3175`](https://cloud.langfuse.com/project/cmsob02dn0100ad0hubskvz4q/traces/33fce3f382906a3ad4554ede9e1f3175) |
| Trước rollback (đẩy `production` sang v2) | `production` / v2 | [`21cfce66c33bfe447919b18a21f516a1`](https://cloud.langfuse.com/project/cmsob02dn0100ad0hubskvz4q/traces/21cfce66c33bfe447919b18a21f516a1) |
| Sau rollback (`production` trở về v1) | `production` / v1 | [`79009643d7361472c8a95cdf2f60bb29`](https://cloud.langfuse.com/project/cmsob02dn0100ad0hubskvz4q/traces/79009643d7361472c8a95cdf2f60bb29) |

Tổng: 12 trace — 10 trace chạy hai label và 2 trace kiểm chứng rollback.

## Cách trace nối được với log

`app/agent.py` ghi event `prompt_resolved` ngay sau khi resolve prompt, mang theo cả
`prompt_name`, `prompt_label`, `prompt_version`, `prompt_source` và `trace_id` hiện hành.
Nhờ vậy một dòng log trong `data/logs.jsonl` chỉ ra được đúng trace trên Langfuse, và
ngược lại. Ví dụ một record thật (chạy local, không bật Langfuse nên `trace_id` là `null`):

```json
{"service": "agent", "payload": {"prompt_name": "day13-chat", "prompt_label": "production",
 "prompt_version": "local-v1", "prompt_source": "local", "trace_id": null},
 "event": "prompt_resolved", "feature": "qa", "correlation_id": "req-4c7481f7",
 "model": "claude-sonnet-4-5", "user_id_hash": "2055254ee30a", "session_id": "s01",
 "env": "dev", "level": "info", "ts": "2026-08-11T13:18:44.265309Z"}
```

Khi có `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` trong `.env`, trường `trace_id` được
điền bằng trace ID thật, cho phép đi thẳng từ log → trace.

Test bảo vệ hành vi này: `tests/test_agent_prompt_trace.py`.

## Ảnh chụp từ giao diện Langfuse

- `r2-trace-list.png` — danh sách trace, mỗi dòng có Metadata, Trace Tags (`lab`, `claude-sonnet-4-5`), Session ID `s01`–`s10` và Cost.
- `r2-trace-prompt-metadata.png` — chi tiết một trace: `Prompt: day13-chat - v1`, `Session: r2-two-labels`, latency 2.09 s, và bảng metadata có `prompt_name`, `prompt_label`, `prompt_version`, `prompt_source`, `query_preview`, `doc_count`.
- `r2-rollback-before.png` — label `production` đang gắn trên **v2**.
- `r2-rollback-after.png` — sau rollback, `production` về **v1**; v2 chỉ còn `latest` + `staging`.

## Kiểm chứng lại bằng API (2026-08-11)

`auth_check()` trả `True` với host `https://cloud.langfuse.com`. Truy vấn `trace.list` và
`prompts.list` cho kết quả:

- Tổng **114 traces** trong project.
- Phân bố theo `(prompt_label, prompt_version)`: `production/1` → 77, `production/2` → 1,
  `staging/2` → 5, `production/local-v1` → 31 (các lần chạy fallback trước khi cấu hình xong key).
- Prompt `day13-chat`: versions `[1, 2]`, labels `['latest', 'production', 'staging']`.
- Cả 4 trace ID trong bảng trên đều `trace.get` thành công và trả đúng cặp label/version đã khai.

Con số `production/2` = 1 chính là trace `21cfce66c33bfe447919b18a21f516a1` — bằng chứng
`production` đã từng trỏ v2 trước khi rollback.
