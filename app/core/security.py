from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import HTTPException

limiter = Limiter(key_func=get_remote_address)

# كلمات ممنوعة — بيانات حساسة
_SENSITIVE = [
    "password", "passwd", "باسورد",
    "credit card", "cvv", "ssn", "رقم قومي",
    "api_key", "secret", "token",
]

# أوامر SQL خطرة
_SQL_INJECT = [
    "drop ", "delete ", "insert ", "update ",
    "exec(", "xp_", "union select", "'; ",
]


def sanitize(text: str) -> str:
    """
    يتحقق من النص ويرفضه لو فيه:
    - بيانات حساسة
    - SQL injection محتمل
    """
    low = text.lower()

    for term in _SENSITIVE:
        if term in low:
            raise HTTPException(status_code=400, detail="الرسالة تحتوي على كلمات غير مسموح بها.")

    for cmd in _SQL_INJECT:
        if cmd in low:
            raise HTTPException(status_code=400, detail="مدخل غير صالح.")

    # حد النص
    cleaned = text.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="الرسالة فاضية.")

    return cleaned