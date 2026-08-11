# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 30/100
- Tổng số traces: 12 trace cho phần tracing/prompt (10 trace chạy hai label và 2 trace kiểm chứng rollback)
- Số PII leak còn lại:
- Link/đường dẫn dashboard:

## 3. Logging và tracing

- Evidence correlation ID:
- Evidence PII redaction:
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name: `day13-chat` (text prompt; đúng ba biến `{{feature}}`, `{{docs}}`, `{{message}}`)
- Version/label baseline: v1 / `production`
- Version/label candidate: v2 / `staging`
- Trace ID của mỗi version:
  - production/v1: [`bc9879625e05c9689bffaddd8ced2518`](https://cloud.langfuse.com/project/cmsob02dn0100ad0hubskvz4q/traces/bc9879625e05c9689bffaddd8ced2518)
  - staging/v2: [`33fce3f382906a3ad4554ede9e1f3175`](https://cloud.langfuse.com/project/cmsob02dn0100ad0hubskvz4q/traces/33fce3f382906a3ad4554ede9e1f3175)
- Bằng chứng đổi label hoặc rollback:
  - Trước rollback, chuyển `production` sang v2: [`21cfce66c33bfe447919b18a21f516a1`](https://cloud.langfuse.com/project/cmsob02dn0100ad0hubskvz4q/traces/21cfce66c33bfe447919b18a21f516a1)
  - Sau rollback, `production` trở về v1: [`79009643d7361472c8a95cdf2f60bb29`](https://cloud.langfuse.com/project/cmsob02dn0100ad0hubskvz4q/traces/79009643d7361472c8a95cdf2f60bb29)

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`:
- Evidence dashboard:
- SLO đã chọn và lý do:
- Alert rules và runbook:

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| | | | |
