# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- **Tên**: `high_p95_latency`
- **Severity**: P2
- **SLI/SLO liên quan**: `latency_p95_ms` (SLO ≤ 3000 ms)
- **Điều kiện và thời gian duy trì**: p95 latency > 3000 ms duy trì 5 phút
- **Ảnh hưởng tới người dùng**: Người dùng gặp tình trạng phản hồi chậm, thời gian chờ câu trả lời kéo dài gây gián đoạn trải nghiệm chat.
- **Ba bước kiểm tra đầu tiên**:
  1. **Metrics**: Kiểm tra endpoint `/metrics` hoặc panel `latency` trên Dashboard để xác định p95 latency vượt 3000ms.
  2. **Traces**: Kiểm tra danh sách trace trên Langfuse, tìm các trace có latency lớn nhất và xem chi tiết các span (đặc biệt là bước retrieval) để tìm nút thắt.
  3. **Logs**: Truy vấn `data/logs.jsonl` theo `correlation_id` hoặc tìm sự kiện `response_sent` có `latency_ms` lớn để đối soát chi tiết request.
- **Mitigation tạm thời**: Tắt incident thử nghiệm nếu đang bật (`/incidents/<name>/disable`), áp dụng timeout cho bước vector search retrieval, hoặc kích hoạt fallback cache.
- **Owner**: Nguyễn Văn Quân

## Alert 2

- **Tên**: `elevated_error_rate`
- **Severity**: P1
- **SLI/SLO liên quan**: `error_rate_pct` (SLO ≤ 2%)
- **Điều kiện và thời gian duy trì**: error rate > 2% duy trì 5 phút
- **Ảnh hưởng tới người dùng**: Người dùng nhận kết quả lỗi (HTTP 500), không thể gửi tin nhắn hoặc nhận phản hồi từ hệ thống AI.
- **Ba bước kiểm tra đầu tiên**:
  1. **Metrics**: Kiểm tra endpoint `/metrics` hoặc panel `errors` trên Dashboard để xác định error rate % và phân loại lỗi theo `error_type`.
  2. **Traces**: Tìm các trace bị gắn nhãn ERROR trên Langfuse để xem traceback exception cụ thể từ LLM service hay database.
  3. **Logs**: Tra cứu `data/logs.jsonl` lọc các sự kiện `request_failed` để xem thông tin chi tiết `error_type` và `detail`.
- **Mitigation tạm thời**: Chuyển hướng traffic sang model/service dự phòng (fallback agent), làm mới kết nối API key hoặc khởi động lại ứng dụng API server.
- **Owner**: Nguyễn Văn Quân

## Alert 3

- **Tên**: `quality_drop`
- **Severity**: P3
- **SLI/SLO liên quan**: `quality_score_avg` (SLO ≥ 0.75)
- **Điều kiện và thời gian duy trì**: mean quality_score < 0.75 duy trì 15 phút
- **Ảnh hưởng tới người dùng**: Chất lượng câu trả lời bị sụt giảm, thông tin trả về thiếu chính xác hoặc chứa câu trả lời bị redacted/không đúng ngữ cảnh.
- **Ba bước kiểm tra đầu tiên**:
  1. **Metrics**: Xem panel `quality` trên Dashboard để xác nhận xu hướng điểm số chất lượng giảm dưới ngưỡng 0.75.
  2. **Traces**: Kiểm tra các trace tương ứng trên Langfuse để xem prompt metadata (`prompt_name`, `prompt_version`, `prompt_label`) đang được sử dụng.
  3. **Logs**: Tra cứu `data/logs.jsonl` kiểm tra các dòng log `response_sent` để đọc giá trị `quality_score` và `answer_preview`.
- **Mitigation tạm thời**: Rollback prompt label `production` về phiên bản prompt ổn định trước đó trên Langfuse, hoặc kiểm tra dữ liệu context RAG.
- **Owner**: Nguyễn Văn Quân
