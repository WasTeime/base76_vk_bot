"""
HTTP-клиент к API магазина (basa76).
Все операции лояльности идут через REST.
"""
import os
import httpx

API_URL = os.environ["LOYALTY_API_URL"].rstrip("/")
API_KEY = os.environ["LOYALTY_API_KEY"]

_headers = {"X-Loyalty-Key": API_KEY, "Content-Type": "application/json"}


async def _post(path: str, json: dict) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{API_URL}{path}", json=json, headers=_headers)
        r.raise_for_status()
        return r.json()


async def _get(path: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{API_URL}{path}", headers=_headers)
        r.raise_for_status()
        return r.json()


async def get_user(vk_id: int) -> dict:
    return await _get(f"/api/loyalty/vk/me/{vk_id}")


async def register(vk_id: int, phone: str) -> dict:
    return await _post("/api/loyalty/vk/register", {"vk_id": str(vk_id), "phone": phone})


async def activate_first(vk_id: int) -> bool:
    res = await _post("/api/loyalty/vk/activate-first", {"vk_id": str(vk_id)})
    return res.get("ok", False)


async def activate_referral(vk_id: int) -> bool:
    res = await _post("/api/loyalty/vk/activate-referral", {"vk_id": str(vk_id)})
    return res.get("ok", False)


async def apply_ref_code(vk_id: int, ref_code: str) -> str:
    res = await _post("/api/loyalty/vk/apply-ref-code", {
        "vk_id": str(vk_id), "ref_code": ref_code
    })
    return res.get("result", "not_found")
