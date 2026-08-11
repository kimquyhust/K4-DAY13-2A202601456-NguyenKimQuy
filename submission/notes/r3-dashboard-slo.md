# Báo cáo cá nhân — Nguyễn Văn Quân (Role R3: Dashboard, SLO & Alert)

## 1. Tổng quan công việc
Phụ trách xây dựng hệ thống giám sát trực quan (Dashboard), định nghĩa quy tắc cảnh báo (Alert Rules), biên soạn tài liệu hướng dẫn xử lý sự cố (Runbook) và xác định chỉ số mục tiêu mức độ dịch vụ (SLO) cho hệ thống Day 13 Observability.

- **Branch**: `feat/dashboard-slo-alert`
- **File sở hữu**: `dashboard/app.py`, `config/alert_rules.yaml`, `config/slo.yaml`, `docs/alerts.md`, `tests/test_alert_rules.py`, `submission/notes/r3-dashboard-slo.md`.

---

## 2. Chi tiết triển khai

### A. Dashboard trực quan (`dashboard/app.py`)
Đã triển khai giao diện ứng dụng Streamlit trong `dashboard/app.py` tuân thủ 100% hợp đồng contract trong `config/dashboard.yaml`:
- **Nguồn dữ liệu**: Đọc file `data/logs.jsonl` và tự động lọc dữ liệu trong **60 phút gần nhất**.
- **Tự động refresh**: Cấu hình tự động cập nhật mỗi 30 giây (`streamlit_autorefresh`).
- **Đủ 6 Panel theo Contract**:
  1. `latency`: Đo phần trăm Latency (p50, p95, p99) của sự kiện `response_sent`. Tái sử dụng hàm `percentile` từ `app.metrics`. Đánh dấu ngưỡng p95 ≤ 3000 ms.
  2. `traffic`: Đếm số lượng `request_received` và tính tốc độ request/phút. Ngưỡng rate_per_minute ≥ 1.0.
  3. `errors`: Tính % Error Rate (`request_failed` / `request_received`) và biểu đồ cột phân loại theo `error_type`. Ngưỡng error_rate_pct ≤ 2%.
  4. `cost`: Tổng chi phí `cost_usd` tích lũy theo phút và tổng cửa sổ. Ngưỡng total ≤ 2.5 USD.
  5. `tokens`: Phân tích tổng số token đầu vào (`tokens_in`) và đầu ra (`tokens_out`). Ngưỡng total ≤ 50,000 tokens.
  6. `quality`: Tính trung bình điểm chất lượng `quality_score`. Ngưỡng mean ≥ 0.75.

### B. Cấu hình Alert Rules (`config/alert_rules.yaml`)
Thay thế toàn bộ chuỗi `TODO` bằng 3 quy tắc cảnh báo dựa trên triệu chứng (symptom-based):
1. **`high_p95_latency`** (Severity: `P2`): Kích hoạt khi latency p95 > 2000 ms duy trì liên tục trong 5 phút. Đây là ngưỡng cảnh báo sớm khớp `latency_threshold_ms` của challenge; dashboard vẫn giữ SLO line 3000 ms theo contract. Owner: `Nguyễn Văn Quân`.
2. **`elevated_error_rate`** (Severity: `P1`): Kích hoạt khi tỷ lệ lỗi > 2% duy trì liên tục trong 5 phút. Owner: `Nguyễn Văn Quân`.
3. **`quality_drop`** (Severity: `P3`): Kích hoạt khi điểm chất lượng trung bình < 0.75 duy trì liên tục trong 15 phút. Owner: `Nguyễn Văn Quân`.

### C. Runbooks xử lý sự cố (`docs/alerts.md`)
Biên soạn tài liệu Runbook cho cả 3 cảnh báo với 3 bước kiểm tra đầu tiên tuân thủ nghiêm ngặt quy trình **Metrics → Traces → Logs**:
- **Bước 1 (Metrics)**: Kiểm tra thông số tổng quan tại `/metrics` hoặc quan sát trên Streamlit Dashboard.
- **Bước 2 (Traces)**: Mở giao diện Langfuse để lọc các trace chậm/lỗi, phân tích latency từng span (retrieval, agent execution) và tra cứu trace ID.
- **Bước 3 (Logs)**: Tra cứu chi tiết log record trong `data/logs.jsonl` theo `correlation_id` để đọc full payload và thông tin exception detail.

### D. Mục tiêu SLO & Lập luận (`config/slo.yaml`)
- `latency_p95_ms` (Objective: 3000 ms, Target: 99.5%): Đảm bảo 99.5% tổng số request được phản hồi dưới 3s trong cửa sổ 28 ngày để duy trì trải nghiệm chat mượt mà.
- `error_rate_pct` (Objective: 2%, Target: 99.0%): Cho phép Error Budget 1% để xử lý đợt bảo trì hoặc sự cố gián đoạn tạm thời.
- `daily_cost_usd` (Objective: $2.5, Target: 100.0%): Kiểm soát nghiêm ngặt ngân sách không vượt quá $2.50/ngày.
- `quality_score_avg` (Objective: 0.75, Target: 95.0%): Duy trì chất lượng câu trả lời cao cho 95% thời gian vận hành.

---

## 3. Kết quả kiểm thử & Bằng chứng (Evidence)

### Kiểm tra hợp lệ bằng Script & Pytest
- `python scripts/validate_dashboard.py` -> In kết quả `HỢP LỆ: 6/6 panel có trong dashboard contract.`
- `python -m pytest -q -p no:cacheprovider` -> Tất cả **45 unit tests** đều PASS (2 cảnh báo deprecation của FastAPI, không có lỗi test).

### Bằng chứng hình ảnh (Nộp tại `submission/evidence/`)
- `r3-validate-dashboard.png`: Màn hình terminal chạy validator dashboard thành công 6/6 panel.
- `r3-dashboard-6panel.png`: Ảnh chụp giao diện Streamlit Dashboard hiển thị trọn vẹn 6 panel với đầy đủ thông số, đơn vị và đường ngưỡng threshold.
- `r3-dashboard-before.png`: Dữ liệu baseline trên Dashboard trước khi kích hoạt incident practice.
- `r3-dashboard-after-ragslow.png`: Dữ liệu trên Dashboard sau khi kích hoạt incident `--scenario rag_slow` (thấy rõ p95 latency vượt ngưỡng cảnh báo challenge 2000 ms).
- `r3-alert-rules.png`: Cấu hình file `config/alert_rules.yaml` và `docs/alerts.md` hợp lệ không còn TODO.
