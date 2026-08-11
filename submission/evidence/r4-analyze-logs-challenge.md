# Phân tích log — bằng chứng điều tra

- Nguồn: `data/logs.jsonl` · filter feature: `monitoring`
- Số bản ghi: request_received=5, response_sent=5, request_failed=0

## Metrics rút từ log

| Chỉ số | Giá trị |
|---|---|
| Latency p50 | 2661 ms |
| Latency p95 | 2662 ms (VƯỢT NGƯỠNG 2000 ms) |
| Latency p99 | 2662 ms |
| Latency max | 2662 ms |
| Error rate | 0.00% |
| Tổng cost | 0.011700 USD |
| Tokens in / out | 175 / 745 |
| Quality trung bình | 0.840 |

## 5 request chậm nhất — mở trace theo thứ tự này

| latency_ms | correlation_id | feature | session_id | ts |
|---:|---|---|---|---|
| 2662 | `req-cc91d8e9` | monitoring | k4-challenge-s05 | 2026-08-11T13:19:38.252352Z |
| 2661 | `req-9e65bc5f` | monitoring | k4-challenge-s03 | 2026-08-11T13:19:40.917138Z |
| 2661 | `req-2872c87a` | monitoring | k4-challenge-s04 | 2026-08-11T13:19:43.582491Z |
| 2660 | `req-fd24948a` | monitoring | k4-challenge-s02 | 2026-08-11T13:19:32.920046Z |
| 2660 | `req-303ff589` | monitoring | k4-challenge-s01 | 2026-08-11T13:19:35.584706Z |

## Prompt version đang phục vụ

- name: `day13-chat` · label: `production` · version: `local-v1` · source: `local`
- trace_id mẫu: `None`

