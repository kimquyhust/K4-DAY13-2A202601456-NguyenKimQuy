from __future__ import annotations

import hashlib
import re

PII_PATTERNS: dict[str, str] = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "phone_vn": r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)",
    "cccd": r"\b\d{12}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    # Hộ chiếu VN dùng tiền tố B/C/N/P; [A-Z] chung sẽ nuốt cả mã kỹ thuật kiểu "X1234567".
    "passport_vn": r"\b[BCNP]\d{7}\b",
    # Không dùng (?i) toàn cục: inline flag của Python áp cho cả pattern và vô hiệu hoá [A-Z],
    # khiến "đường dẫn", "đường truyền" bị coi là địa chỉ. Sau từ khoá phải là số hoặc tên riêng viết hoa.
    "address_vn": (
        r"(?:[Ss]ố nhà|[Nn]gõ|[Nn]gách)\s*\d+[^,;\n]*"
        r"|(?:[Đđ]ường|[Pp]hố|[Pp]hường|[Xx]ã|[Qq]uận|[Hh]uyện)"
        r"\s+(?:\d+|[A-ZĐÀ-Ỹ][^\s,;]*(?:\s+[A-ZĐÀ-Ỹ][^\s,;]*)*)"
    ),
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
