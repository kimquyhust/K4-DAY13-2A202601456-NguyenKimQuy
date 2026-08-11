# Kế hoạch nhóm — Day 13 Observability

Tài liệu này là **nguồn chuẩn duy nhất** về việc ai làm gì, sửa file nào và push lên branch nào.
Luật vàng chống conflict: **một file chỉ có một chủ sở hữu**. Cần đổi file của người khác → nhắn chủ file hoặc comment trong PR, **không tự sửa**.

## 1. Phân công

| Vai | Thành viên | Branch (đã tạo sẵn trên remote) | Phần chấm chính |
|---|---|---|---|
| **R1 — Logging & PII** | **Nguyễn Vũ Việt Anh** | `feat/logging-pii` | A1 (10đ) + B (40đ cá nhân) |
| **R2 — Tracing & Prompt Version** | **Nguyễn Minh Đạt** | `feat/tracing-prompt` | A1 (10đ) + B |
| **R3 — Dashboard, SLO & Alert** | **Nguyễn Văn Quân** | `feat/dashboard-slo-alert` | A1 (10đ) + B |
| **R4 — Incident, Report & Demo** | **Nguyễn Kim Quy (leader)** | `feat/incident-report` | A2 (10đ) + A3 (20đ) + B |

Leader kiêm release manager: review + merge mọi PR, và là người **duy nhất** được sửa file dùng chung (`requirements.txt`, `README.md`, `.gitignore`, `.env.example`, `submission/REPORT.md`).

## 2. Quy trình Git — mọi người làm giống nhau

Branch của bạn **đã tồn tại trên `origin`**, không tự tạo branch mới, không đổi tên.

```bash
# Lần đầu
git clone https://github.com/kimquyhust/K4-DAY13-2A202601456-NguyenKimQuy.git
cd K4-DAY13-2A202601456-NguyenKimQuy
git checkout <branch-của-bạn>        # ví dụ: git checkout feat/logging-pii

# Mỗi lần làm việc
git pull --rebase origin <branch-của-bạn>
# ... code ...
git add <chỉ file bạn sở hữu>
git commit -m "feat: ..."
git push origin <branch-của-bạn>

# Khi leader báo "main vừa merge R1"
git fetch origin
git rebase origin/main
git push --force-with-lease origin <branch-của-bạn>
```

Quy tắc bắt buộc:

1. **Không commit vào `main`.** Chỉ push lên branch của mình, leader merge.
2. **Không `git merge main`** vào branch feature — dùng `git rebase origin/main`.
3. **Không `git add .`** — luôn add đích danh file mình sở hữu, tránh vô tình kéo `.env` hoặc file người khác.
4. Commit nhỏ, message theo chuẩn `feat:` / `fix:` / `test:` / `docs:` / `chore:`.
   Rubric B2 chấm **commit đứng tên chính bạn** — không được commit hộ nhau, không gộp hết vào 1 commit cuối buổi.
5. Xong phần việc → push và báo leader trong nhóm chat để mở PR về `main`.
6. **Không commit**: `.env`, API key, `data/logs.jsonl`, `.venv/`, ảnh chứa PII chưa che.
7. **CẤM sửa `config/challenge.json`** — vi phạm [RULES.md](../RULES.md), mất điểm cả nhóm.

### Báo cáo cá nhân (điểm dễ conflict nhất)

Không ai viết thẳng vào `submission/REPORT.md`. Mỗi người viết file riêng của mình:

| Người | File notes |
|---|---|
| Việt Anh | `submission/notes/r1-logging-pii.md` |
| Minh Đạt | `submission/notes/r2-tracing-prompt.md` |
| Văn Quân | `submission/notes/r3-dashboard-slo.md` |
| Kim Quy | `submission/notes/r4-incident.md` |

Leader gộp vào `REPORT.md` cuối buổi. Ảnh evidence đặt tên có tiền tố vai trò: `submission/evidence/r1-*.png`, `r2-*.png`, `r3-*.png`, `r4-*.png`.

## 3. Bảng sở hữu file

| File / thư mục | Chủ sở hữu |
|---|---|
| `app/middleware.py`, `app/logging_config.py`, `app/pii.py`, `app/main.py` | Việt Anh |
| `tests/test_pii.py`, `tests/test_validate_logs.py`, `tests/test_chat_observability.py` | Việt Anh |
| `app/tracing.py`, `app/prompt_management.py`, `app/agent.py` | Minh Đạt |
| `tests/test_tracing_adapter.py`, `tests/test_prompt_management.py`, `tests/test_agent_prompt_trace.py` | Minh Đạt |
| `config/alert_rules.yaml`, `config/slo.yaml`, `config/dashboard.yaml` | Văn Quân |
| `docs/alerts.md`, `docs/dashboard-spec.md`, `dashboard/**` (thư mục mới) | Văn Quân |
| `tests/test_dashboard_validator.py`, `tests/test_alert_rules.py` (file mới) | Văn Quân |
| `submission/REPORT.md`, `docs/TEAM_PLAN.md`, `docs/mock-debug-qa.md` | Kim Quy |
| `requirements.txt`, `README.md`, `.gitignore`, `.env.example` | Kim Quy |
| `app/metrics.py`, `app/schemas.py`, `app/incidents.py`, `app/challenge.py`, `app/mock_*.py`, `scripts/**` | Không ai sửa (cần thì báo leader) |
| `config/challenge.json` | **CẤM sửa** |

## 4. Setup chung — ai cũng phải làm trước (15 phút đầu)

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env                 # Windows: Copy-Item .env.example .env
```

Leader đã chạy thử toàn bộ trên macOS + Python 3.12: cài đặt sạch, `pytest` xanh, `validate_dashboard.py` báo 6/6. Nếu `pip install` báo `ResolutionImpossible` ở lần đầu, chạy lại lệnh đó một lần nữa là được.

**Kiểm tra port 8000 trước khi chạy:** `scripts/load_test.py` và `scripts/inject_incident.py` hard-code `http://127.0.0.1:8000`. Nếu máy bạn đã có app khác chiếm port đó (`lsof -nP -iTCP:8000 -sTCP:LISTEN`), phải tắt app kia trước, nếu không load test sẽ bắn nhầm đích.

Điền key Langfuse do Lab Coach cấp vào `.env` (không commit). Sau đó:

```bash
uvicorn app.main:app --reload --env-file .env    # terminal 1
python scripts/load_test.py                      # terminal 2
python scripts/validate_logs.py                  # lưu điểm baseline vào notes
python scripts/validate_dashboard.py             # phải in "HỢP LỆ: 6/6 panel"
python -m pytest -q
```

---

## 5. Task card — Nguyễn Vũ Việt Anh (R1 · `feat/logging-pii`)

**Ưu tiên cao nhất, phải xong sớm nhất.** Cả Văn Quân và leader đều phụ thuộc vào cấu trúc log của bạn.

**Định nghĩa hoàn thành:** `python scripts/validate_logs.py` in `Estimated Score: 100/100`, `Potential PII leaks detected: 0`, `Unique correlation IDs` ≥ 10, và `python -m pytest -q` xanh.

### Việc 1 — Correlation ID trong [app/middleware.py](../app/middleware.py#L13-L30)

Bốn TODO ở dòng 13, 16, 20, 28:

- Gọi `clear_contextvars()` ngay đầu `dispatch` — nếu thiếu, context của request trước sẽ dính sang request sau khi chạy `--concurrency 5`.
- `correlation_id = request.headers.get("x-request-id") or f"req-{uuid.uuid4().hex[:8]}"` — ưu tiên header của client, không có mới sinh mới, đúng format `req-<8 hex>`.
- `bind_contextvars(correlation_id=correlation_id)` — bind **trước** khi gọi `call_next`.
- Sau `call_next`: `response.headers["x-request-id"] = correlation_id` và `response.headers["x-response-time-ms"] = f"{(time.perf_counter() - start) * 1000:.1f}"`.

### Việc 2 — Bật PII scrubbing tại [app/logging_config.py:45](../app/logging_config.py#L45)

Bỏ comment `scrub_event` trong list processor và đặt **trước** `JsonlFileProcessor()` — nếu đặt sau, console sạch nhưng file `data/logs.jsonl` mới là thứ validator đọc.

**Đo thực tế của leader:** baseline đã `[PASSED] PII scrubbing` với 0 leak **dù processor còn đang comment**, vì `/chat` chỉ log preview qua `summarize_text()` và hàm này đã gọi `scrub_text()` ([app/pii.py:22-24](../app/pii.py#L22-L24)). Nên khi trình bày, đừng nói "bật processor nên hết PII" — vai trò thật của `scrub_event` là **defense-in-depth** cho những field không đi qua `summarize_text` (ví dụ log bạn tự thêm sau này). Đây gần như chắc chắn là một câu hỏi khi chấm.

### Việc 3 — Enrich log tại [app/main.py:47](../app/main.py#L47)

```python
bind_contextvars(
    user_id_hash=hash_user_id(body.user_id),
    session_id=body.session_id,
    feature=body.feature,
    model=agent.model,
    env=os.getenv("APP_ENV", "dev"),
)
```

Đặt **trước** `log.info("request_received", ...)` để cả ba event `request_received`, `response_sent`, `request_failed` đều có đủ metadata — [validate_logs.py](../scripts/validate_logs.py) kiểm **mọi** record có `service == "api"`, thiếu ở nhánh `except` cũng bị trừ 20 điểm. `hash_user_id` và `os` đã được import sẵn.

### Việc 4 — Bổ sung pattern tại [app/pii.py:11](../app/pii.py#L11)

Thêm tối thiểu 2 pattern: hộ chiếu VN (`\b[A-Z]\d{7}\b`), và từ khóa địa chỉ (`số nhà`, `đường`, `phường`, `quận` + phần text theo sau). Cân nhắc thêm mã số thuế / số tài khoản.
Thêm xong chạy `pytest tests/test_pii.py` ngay — pattern quá rộng sẽ phá test cũ và làm hỏng `quality_score` (agent trừ điểm khi answer chứa `[REDACTED`, xem [app/agent.py:106](../app/agent.py#L106)).

### Việc 5 — Test riêng của bạn

Thêm vào `tests/test_pii.py` case cho pattern mới, và một test khẳng định correlation ID sinh ra đúng format `req-` + 8 ký tự hex.

### Việc 6 (bonus, làm nếu còn thời gian)

Cho `scrub_event` quét đệ quy mọi field string trong `event_dict`, không chỉ `payload` và `event` — ghi vào notes như một cải tiến để lấy điểm bonus.

### Cách tự kiểm tra

```bash
rm -f data/logs.jsonl                             # xoá log cũ để đo sạch
uvicorn app.main:app --reload --env-file .env
python scripts/load_test.py                       # terminal khác
python scripts/validate_logs.py
grep -c "MISSING" data/logs.jsonl                 # phải ra 0
grep -E "student@vinuni|0987654321|4111 1111" data/logs.jsonl   # phải không ra gì
python -m pytest -q
```

Ba query số 1, 5, 9 trong `data/sample_queries.jsonl` cố tình chứa email, số điện thoại và số thẻ — dùng đúng ba dòng này làm bằng chứng redaction.

### Evidence phải nộp

`r1-validate-logs.png` (kết quả 100/100), `r1-log-correlation-id.png` (một dòng JSON log đủ `correlation_id` + `user_id_hash` + `session_id` + `feature` + `model` + `env`), `r1-pii-redacted.png` (dòng log có `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]`).

### Commit gợi ý

```
feat: propagate correlation id through request lifecycle
feat: register PII scrubbing processor before file sink
feat: enrich chat logs with user, session and model context
feat: extend PII patterns for passport and address
test: cover new PII patterns and correlation id format
docs: add r1 logging and pii notes
```

### Sẽ bị hỏi khi chấm

Correlation ID lan truyền bằng cơ chế gì và vì sao dùng contextvars thay vì tham số? Vì sao hash `user_id` chứ không log thẳng? Thứ tự processor ảnh hưởng thế nào tới kết quả redaction? Redaction khác masking và hashing ở đâu?

---

## 6. Task card — Nguyễn Minh Đạt (R2 · `feat/tracing-prompt`)

**Định nghĩa hoàn thành:** ≥10 trace có metadata trên Langfuse; prompt `day13-chat` có v1 + v2 gắn label; trace hiển thị đúng `prompt_name` / `prompt_label` / `prompt_version` với `prompt_source: langfuse`; có bằng chứng rollback.

### Việc 1 — Kết nối Langfuse

Điền `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` vào `.env` (key do Lab Coach cấp, **không commit**). Kiểm tra:

```bash
curl http://127.0.0.1:8000/health     # phải trả "tracing_enabled": true
```

Nếu `false` → thiếu key hoặc chưa cài `langfuse`; xem [app/tracing.py:34](../app/tracing.py#L34).

### Việc 2 — Tạo prompt v1 và v2 trên Langfuse

Tên prompt phải đúng `day13-chat` (khớp `LANGFUSE_PROMPT_NAME`), type `text`.

- **v1 → label `production`**: bản baseline ngắn gọn.
- **v2 → label `staging`**: bản candidate, thêm ràng buộc như "không lặp lại thông tin cá nhân trong câu hỏi", "trả lời dựa trên Docs được cung cấp".

Template **bắt buộc** dùng đúng ba biến `{{feature}}`, `{{docs}}`, `{{message}}` — [app/prompt_management.py:62-66](../app/prompt_management.py#L62-L66) gọi `compile(feature=..., docs=..., message=...)`, sai tên biến là trace sẽ rơi về `local-fallback`.

### Việc 3 — Chạy cùng input với hai label

```bash
# .env: LANGFUSE_PROMPT_LABEL=production
python scripts/load_test.py            # rồi restart uvicorn
# .env: LANGFUSE_PROMPT_LABEL=staging
python scripts/load_test.py
```

Phải restart uvicorn sau khi đổi `.env`. Lưu lại **2 trace ID** đại diện cho 2 label, mở từng trace kiểm tra metadata có đủ `prompt_name`, `prompt_label`, `prompt_version`, `prompt_source`.

### Việc 4 — Rollback

Gán label `production` cho v2 → chạy 1 request → xác nhận trace ghi version 2 → trả label `production` về v1 → chạy lại 1 request → xác nhận trace ghi version 1. Chụp cả hai bước, ghi rõ trace ID trước/sau vào notes.

### Việc 5 — Đủ 10+ trace

```bash
python scripts/load_test.py --concurrency 5
```

Chạy 2–3 lần, chụp màn hình danh sách trace và một trace waterfall đầy đủ.

### Việc 6 — Phần code duy nhất của bạn: nối trace ↔ log

Trong [app/agent.py](../app/agent.py), sau khi `resolve_prompt` trả về, ghi thêm một log có cấu trúc:

```python
log.info(
    "prompt_resolved",
    service="agent",
    payload={
        "prompt_name": prompt.name,
        "prompt_label": prompt.label,
        "prompt_version": prompt.version,
        "prompt_source": prompt.source,
        "trace_id": getattr(langfuse_client, "get_current_trace_id", lambda: None)(),
    },
)
```

Dùng `getattr(...)` để không vỡ khi chạy bằng dummy client trong test (xem [app/tracing.py:19-27](../app/tracing.py#L19-L27)). Import logger từ `app.logging_config` — **chỉ import, không sửa file đó** (file của Việt Anh).

Đây là mảnh ghép leader cần để chứng minh luồng Metrics → Traces → Logs trong challenge, nên hãy làm sớm và báo leader khi xong.

Sau khi sửa: `pytest tests/test_agent_prompt_trace.py tests/test_prompt_management.py -q`.

### Evidence phải nộp

`r2-trace-list-10.png`, `r2-trace-waterfall.png`, `r2-prompt-v1-trace.png`, `r2-prompt-v2-trace.png`, `r2-rollback-before.png`, `r2-rollback-after.png`.

### Commit gợi ý

```
feat: log resolved prompt version with trace id for log-trace correlation
test: assert prompt metadata falls back safely without langfuse
docs: add r2 tracing and prompt versioning notes
```

### Sẽ bị hỏi khi chấm

Trace, span và generation khác nhau thế nào? Vì sao cần prompt versioning thay vì sửa thẳng prompt trong code? `prompt_source: local-fallback` xảy ra khi nào và vì sao app vẫn phải chạy được khi Langfuse chết? Rollback prompt khác deploy lại code ở điểm nào?

---

## 7. Task card — Nguyễn Văn Quân (R3 · `feat/dashboard-slo-alert`)

**Lưu ý:** [config/dashboard.yaml](../config/dashboard.yaml) **đã hợp lệ 6/6 panel** — đây là contract chấm điểm, đừng sửa để "cho đẹp". Việc của bạn là dựng dashboard **chạy thật** đúng contract, và hoàn thiện alert/SLO.

**Định nghĩa hoàn thành:** `python scripts/validate_dashboard.py` in `HỢP LỆ: 6/6 panel`; dashboard chạy được và chụp được ảnh 6 panel; `config/alert_rules.yaml` và `docs/alerts.md` không còn chữ `TODO`; `pytest` xanh.

### Việc 1 — Dựng dashboard thật trong thư mục mới `dashboard/app.py`

Streamlit đã có trong `requirements.txt`. Đọc `data/logs.jsonl`, lọc 60 phút gần nhất, dựng đúng 6 panel:

| Panel | Nguồn | Phép tính | Threshold hiển thị |
|---|---|---|---|
| `latency` | `response_sent.latency_ms` | p50 / p95 / p99 | đường p95 ≤ 3000 ms |
| `traffic` | đếm `request_received` | count + request/phút | ≥ 1 req/phút |
| `errors` | `request_failed` ÷ `request_received` | error rate % + breakdown theo `error_type` | ≤ 2% |
| `cost` | `response_sent.cost_usd` | tổng theo phút + tổng cửa sổ | ≤ 2.5 USD |
| `tokens` | `tokens_in`, `tokens_out` | tổng từng field | ≤ 50000 |
| `quality` | `quality_score` | mean | ≥ 0.75 |

Yêu cầu bắt buộc để lấy điểm ảnh: hiện **tên panel**, **time range 60 phút**, **đơn vị**, **đường threshold**, và tự refresh 30 giây (`st.autorefresh` hoặc tương đương).
Dùng lại `from app.metrics import percentile` để số p95 trên dashboard khớp đúng `/metrics` — quan trọng khi leader demo.

Chạy: `streamlit run dashboard/app.py`.

### Việc 2 — Điền [config/alert_rules.yaml](../config/alert_rules.yaml)

Thay toàn bộ `TODO` bằng 3 alert **symptom-based** (dựa trên triệu chứng người dùng / SLO, không dựa vào tên hàm nội bộ):

| name | condition | severity | owner |
|---|---|---|---|
| `high_p95_latency` | p95 latency > 3000 ms duy trì 5 phút | P2 | (tên thật một thành viên) |
| `elevated_error_rate` | error rate > 2% duy trì 5 phút | P1 | (tên thật) |
| `quality_drop` | mean quality_score < 0.75 duy trì 15 phút | P3 | (tên thật) |

Giữ nguyên key `runbook` trỏ đúng anchor trong `docs/alerts.md`.

### Việc 3 — Điền [docs/alerts.md](alerts.md)

Đủ 3 runbook, mỗi cái điền hết các trường. **Ba bước kiểm tra đầu tiên bắt buộc theo thứ tự Metrics → Traces → Logs** (đây chính là luồng leader sẽ demo, phải khớp nhau).

### Việc 4 — Chốt [config/slo.yaml](../config/slo.yaml)

Xoá dòng `note: Replace with your group's target`, ghi lý do nhóm chọn từng con số (vì sao p95 3000 ms chứ không phải 1000 ms, vì sao error budget 2%). Ghi phần lập luận vào notes.

### Việc 5 — Test mới `tests/test_alert_rules.py`

Chặn nộp nhầm file còn TODO:

- Không còn chuỗi `TODO` trong `config/alert_rules.yaml`.
- Mỗi alert có đủ `name`, `severity`, `condition`, `type`, `owner`, `runbook`.
- `severity` thuộc `{P1, P2, P3}`.
- Mỗi `runbook` anchor tồn tại trong `docs/alerts.md`.

### Việc 6 — Ảnh before/after với incident practice

```bash
python scripts/load_test.py --concurrency 5                      # baseline, chụp "before"
python scripts/inject_incident.py --scenario rag_slow
python scripts/load_test.py --concurrency 5                      # chụp "after", p95 phải tăng rõ
python scripts/inject_incident.py --scenario rag_slow --disable
```

**Dùng `--scenario rag_slow` (practice) cho phần của bạn.** Challenge chính thức do leader chạy, đừng chạy trước để khỏi làm bẩn dữ liệu baseline của leader.

### Evidence phải nộp

`r3-validate-dashboard.png`, `r3-dashboard-6panel.png`, `r3-dashboard-before.png`, `r3-dashboard-after-ragslow.png`, `r3-alert-rules.png`.

### Commit gợi ý

```
feat: add streamlit dashboard rendering six observability panels
feat: define three symptom-based alert rules with owners
docs: complete alert runbooks with metrics-traces-logs triage
chore: finalize group SLO targets
test: guard alert rules schema and runbook anchors
docs: add r3 dashboard and slo notes
```

### Sẽ bị hỏi khi chấm

p95 khác mean thế nào, vì sao dùng p95 chứ không dùng trung bình? Symptom-based khác cause-based alert ra sao? Vì sao alert cần "duy trì N phút"? Error budget là gì và 99.0% target nghĩa là bao nhiêu phút lỗi trong 28 ngày?

---

## 8. Task card — Nguyễn Kim Quy (R4 · `feat/incident-report`, leader)

### Trước buổi lab (đã xong)

Commit `chore:` trên `main`: `docs/TEAM_PLAN.md`, thêm `streamlit` vào `requirements.txt`, tạo `submission/notes/`. Tạo và push 3 branch cho 3 thành viên.

### Trong buổi — vai release manager

Merge PR theo thứ tự **R1 → R2/R3 → R4**. Ngay sau khi merge R1 vào `main`, **báo cả nhóm rebase** (`git fetch origin && git rebase origin/main`), vì R1 đổi cấu trúc log mà R3 và R4 phụ thuộc.
Khi review PR, kiểm ba thứ: không đụng file ngoài quyền sở hữu, không có `.env`/key, `pytest` xanh.

### Điều tra challenge — 10 điểm A2

`config/challenge.json` đã release: cohort K4, incident `rag_slow`, seed 1304, feature `monitoring`, `latency_threshold_ms: 2000`.

```bash
rm -f data/logs.jsonl                                   # đo sạch
uvicorn app.main:app --reload --env-file .env

# 1. Baseline sạch, trước khi bật incident
python scripts/load_test.py --challenge --concurrency 5
curl http://127.0.0.1:8000/metrics                      # ghi lại latency_p95 baseline

# 2. Bật incident chính thức — KHÔNG truyền --scenario, script tự đọc challenge.json
python scripts/inject_incident.py

# 3. Chạy input chính thức
python scripts/load_test.py --challenge --concurrency 5
curl http://127.0.0.1:8000/metrics                      # p95 tăng vọt

# 4. Tắt sau khi thu đủ evidence
python scripts/inject_incident.py --disable
```

Mỗi bước phải kèm bằng chứng cụ thể:

- **Metrics:** `latency_p95` vượt ngưỡng 2000 ms của challenge — ghi số trước/sau, không nói chung chung.
- **Traces:** mở trace chậm nhất trên Langfuse, chỉ ra span retrieval chiếm gần hết thời gian, ghi trace ID.
- **Logs:** `grep <correlation_id> data/logs.jsonl` lấy dòng `response_sent` có `latency_ms` tương ứng, cộng thêm dòng `prompt_resolved` do Minh Đạt thêm để chứng minh liên kết trace ↔ log.
- **Root cause:** bước retrieve trong RAG bị block đồng bộ — [app/mock_rag.py](../app/mock_rag.py) `sleep(2.5)` khi `rag_slow` bật, mọi request feature `monitoring` cộng thêm ~2.5s, đẩy tail latency vượt SLO trong khi error rate vẫn 0%.
- **Fix action:** tắt incident, đặt timeout cho vector store, gọi bất đồng bộ, cache kết quả retrieval theo query.
- **Preventive measure:** alert p95 > 2000 ms khớp `latency_threshold_ms` của challenge, panel latency trên dashboard, timeout + circuit breaker, load test hồi quy trước release.

### Hoàn tất

1. Gộp `submission/notes/*.md` của 4 người vào `submission/REPORT.md`, điền đủ mục 1→7. Bảng mục 7 phải có **link commit thật** của từng người.
2. Checklist nộp bài:
   ```bash
   python -m pytest -q
   python scripts/validate_logs.py
   python scripts/validate_dashboard.py
   git status --short
   git log --oneline --format='%an %s' | sort | uniq -c    # xác minh cả 4 người đều có commit
   ```
3. Rà secret/PII trước khi push:
   ```bash
   git grep -nE "sk-lf-|pk-lf-" -- . ':!docs'
   git log --stat | grep -i "\.env$"                       # phải không ra gì
   ```
4. Ghi commit SHA cuối vào REPORT.md, push `main`, nộp URL repo.
5. Demo 5 phút theo luồng **Metrics → Traces → Logs → Root cause**; mỗi thành viên tự nói phần mình làm (rubric A3 20đ và B1 20đ chấm đúng chỗ này).

## 9. Timeline 4 giờ

| Thời gian | Việt Anh (R1) | Minh Đạt (R2) | Văn Quân (R3) | Kim Quy (R4) |
|---|---|---|---|---|
| 0:00–0:30 | Setup + baseline `validate_logs` | Setup + nối Langfuse, `/health` true | Setup + đọc dashboard contract | Chia việc, xác nhận ai cũng chạy được app |
| 0:30–1:30 | **Xong 4 TODO logging/PII** → push → báo leader | Tạo prompt v1/v2, gắn label | Dựng `dashboard/app.py` từ log baseline | Review + merge PR R1, báo cả nhóm rebase |
| 1:30–2:30 | Test + evidence + notes | Chạy 2 label, rollback, thu 10+ trace, thêm log `prompt_resolved` | Alert rules + runbook + SLO + test mới | Review PR R2/R3, chuẩn bị kịch bản điều tra |
| 2:30–3:30 | Hỗ trợ leader đọc log | Hỗ trợ leader đọc trace | Chụp before/after dashboard | **Chạy challenge chính thức + điều tra** |
| 3:30–4:00 | Viết notes | Viết notes | Viết notes | Gộp REPORT, kiểm tra cuối, tập demo |

## 10. Rủi ro đã biết

- **Quên rebase sau khi R1 merge** → conflict ở `app/main.py`. Rebase ngay khi leader báo.
- **PII vẫn lọt dù đã bật `scrub_event`** → đặt sai vị trí processor, phải nằm trước `JsonlFileProcessor`.
- **Thiếu enrichment ở nhánh `except`** của `/chat` → mất 20 điểm validator dù case thành công vẫn đúng.
- **`prompt_source: local-fallback`** trong trace → sai key hoặc sai tên biến template, không phải lỗi code.
- **`data/logs.jsonl` cộng dồn qua nhiều lần chạy** → dashboard và validator lẫn dữ liệu cũ. Xoá file trước mỗi lần đo chính thức, nhất là trước baseline của challenge.
- **Chạy challenge sớm khi chưa merge R1** → log thiếu correlation ID, không chứng minh được luồng Metrics → Traces → Logs.
- **Port 8000 bị app khác chiếm** → load test chạy "thành công" nhưng bắn vào nhầm service. Kiểm tra `lsof -nP -iTCP:8000 -sTCP:LISTEN` trước khi đo.

## 11. Công cụ chung của nhóm

`scripts/analyze_logs.py` (leader viết) dựng lại toàn bộ bằng chứng từ `data/logs.jsonl` bằng một lệnh — p50/p95/p99, error rate và breakdown, cost, token, quality, danh sách request chậm nhất kèm `correlation_id` để mở trace, và prompt version đang phục vụ:

```bash
python scripts/analyze_logs.py                                   # toàn bộ log
python scripts/analyze_logs.py --feature monitoring --top 5      # lọc theo feature
python scripts/analyze_logs.py --threshold-ms 2000 --out submission/evidence/r4-log-analysis.md
```

Script tự cảnh báo khi log chưa có correlation ID (chưa merge R1) hoặc chưa có event `prompt_resolved` (chưa merge R2) — dùng được như checklist tích hợp nhanh. Ai cũng chạy được, nhưng file thuộc quyền sở hữu của leader.

## 12. Số đo tham chiếu từ lần diễn tập của leader (2026-08-11)

Dùng để đối chiếu, nếu máy bạn ra số lệch xa thì môi trường có vấn đề:

| Chỉ số | Bình thường | Khi bật `rag_slow` |
|---|---:|---:|
| latency p50 / p95 (`/metrics`) | 155 ms / 155 ms | 2659 ms / 2660 ms |
| latency client đo được (max, `--concurrency 5`) | ~835 ms | ~13 350 ms |
| error rate | 0% | 0% |
| tokens_out tổng / cost tổng | 664 / 0,0105 USD | 677 / 0,0107 USD |
| quality trung bình | 0,84 | 0,84 |
| `validate_logs.py` (trước khi R1 làm) | 30/100 | — |
| `pytest` | 30 passed | — |

Điểm đáng chú ý cho cả nhóm: chỉ latency đổi, còn error, cost, token và quality **không đổi** — chính điều đó loại trừ `tool_fail` và `cost_spike` và khoanh vùng thẳng vào tầng retrieval.
