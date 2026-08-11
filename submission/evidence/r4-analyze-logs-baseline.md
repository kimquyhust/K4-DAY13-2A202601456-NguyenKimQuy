# Phân tích log — bằng chứng điều tra

- Nguồn: `data/logs.jsonl` · filter feature: `tất cả`
- Số bản ghi: request_received=10, response_sent=10, request_failed=0

## Metrics rút từ log

| Chỉ số | Giá trị |
|---|---|
| Latency p50 | 153 ms |
| Latency p95 | 155 ms (trong ngưỡng 2000 ms) |
| Latency p99 | 155 ms |
| Latency max | 155 ms |
| Error rate | 0.00% |
| Tổng cost | 0.021315 USD |
| Tokens in / out | 330 / 1355 |
| Quality trung bình | 0.880 |

## 5 request chậm nhất — mở trace theo thứ tự này

| latency_ms | correlation_id | feature | session_id | ts |
|---:|---|---|---|---|
| 155 | `req-5d0f269c` | qa | s02 | 2026-08-11T13:18:44.576344Z |
| 155 | `req-4eb9785f` | summary | s03 | 2026-08-11T13:18:44.735621Z |
| 155 | `req-dde1a11f` | summary | s06 | 2026-08-11T13:18:45.207875Z |
| 155 | `req-20aa260b` | qa | s08 | 2026-08-11T13:18:45.521729Z |
| 153 | `req-37794112` | qa | s09 | 2026-08-11T13:18:45.678477Z |

## Prompt version đang phục vụ

- name: `day13-chat` · label: `production` · version: `local-v1` · source: `local`
- trace_id mẫu: `None`

