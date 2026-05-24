"""
Отправка SMS через smsc.ru
Документация: https://smsc.ru/api/http/
"""
import os
import random
import time
import httpx
import logging

SMSC_LOGIN    = os.environ.get("SMSC_LOGIN", "")
SMSC_PASSWORD = os.environ.get("SMSC_PASSWORD", "")
SMS_TTL_SEC   = 5 * 60  # код действителен 5 минут

# {vk_id: {"phone": "+7...", "code": "1234", "expires": 12345.6}}
_pending: dict[int, dict] = {}

log = logging.getLogger(__name__)


def is_enabled() -> bool:
    return bool(SMSC_LOGIN and SMSC_PASSWORD)


def generate_code() -> str:
    return f"{random.randint(1000, 9999)}"


async def send_code(phone: str, code: str) -> bool:
    """Отправляет SMS с кодом. Возвращает True если успешно."""
    if not is_enabled():
        log.warning("SMSC credentials not set, skipping SMS")
        return False
    text = f"Код подтверждения для База 76: {code}"
    params = {
        "login":   SMSC_LOGIN,
        "psw":     SMSC_PASSWORD,
        "phones":  phone,
        "mes":     text,
        "fmt":     3,  # JSON ответ
        "charset": "utf-8",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get("https://smsc.ru/sys/send.php", params=params)
        data = r.json()
        if "error" in data:
            log.error(f"SMSC error: {data}")
            return False
        log.info(f"SMS sent to {phone}: id={data.get('id')}, cost={data.get('cost')}")
        return True


def store_pending(vk_id: int, phone: str, code: str) -> None:
    _pending[vk_id] = {"phone": phone, "code": code, "expires": time.time() + SMS_TTL_SEC}


def verify(vk_id: int, code: str) -> str | None:
    """
    Возвращает phone если код верный, иначе None.
    После успешной верификации запись удаляется.
    """
    data = _pending.get(vk_id)
    if not data:
        return None
    if time.time() > data["expires"]:
        _pending.pop(vk_id, None)
        return None
    if data["code"] != code.strip():
        return None
    _pending.pop(vk_id, None)
    return data["phone"]


def get_pending_phone(vk_id: int) -> str | None:
    data = _pending.get(vk_id)
    if not data or time.time() > data["expires"]:
        return None
    return data["phone"]


def clear_pending(vk_id: int) -> None:
    _pending.pop(vk_id, None)
