"""HTTP-клиент для взаимодействия бота с backend API."""

from __future__ import annotations

import logging
from datetime import date, datetime

import httpx
from zoo_shared.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
_BASE = _settings.BACKEND_URL

_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(base_url=_BASE, timeout=30.0)
    return _client


async def init() -> None:
    await get_client()


async def close() -> None:
    await close_client()


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


# ══════════════ PETS ══════════════


async def list_pets(user_id: int) -> list[dict]:
    c = await get_client()
    r = await c.get(f"/pets/by_user/{user_id}")
    r.raise_for_status()
    return r.json()


async def get_pet(pet_id: int, user_id: int) -> dict | None:
    c = await get_client()
    r = await c.get(f"/pets/{pet_id}", params={"user_id": user_id})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


async def create_pet(
    user_id: int,
    name: str,
    species: str,
    breed: str = "",
    birth_date: date | None = None,
    weight: float | None = None,
    photo_file_id: str | None = None,
) -> dict:
    c = await get_client()
    body: dict = {
        "user_id": user_id,
        "name": name,
        "species": species,
        "breed": breed,
    }
    if birth_date:
        body["birth_date"] = birth_date.isoformat()
    if weight is not None:
        body["weight"] = weight
    if photo_file_id:
        body["photo_file_id"] = photo_file_id
    r = await c.post("/pets/", json=body)
    r.raise_for_status()
    return r.json()


async def update_pet(pet_id: int, user_id: int, **fields) -> dict | None:
    c = await get_client()
    r = await c.patch(f"/pets/{pet_id}", params={"user_id": user_id}, json=fields)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


async def delete_pet(pet_id: int, user_id: int) -> bool:
    c = await get_client()
    r = await c.delete(f"/pets/{pet_id}", params={"user_id": user_id})
    return r.status_code == 204


async def get_pet_stats(pet_id: int, user_id: int) -> dict | None:
    c = await get_client()
    r = await c.get(f"/pets/{pet_id}/stats", params={"user_id": user_id})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


async def get_pet_export(pet_id: int, user_id: int) -> dict | None:
    c = await get_client()
    r = await c.get(f"/pets/{pet_id}/export", params={"user_id": user_id})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


async def get_pet_count(user_id: int) -> int:
    c = await get_client()
    r = await c.get(f"/pets/count/{user_id}")
    r.raise_for_status()
    return r.json()["count"]


# ══════════════ REMINDERS ══════════════


async def list_reminders(user_id: int) -> list[dict]:
    c = await get_client()
    r = await c.get(f"/reminders/by_user/{user_id}")
    r.raise_for_status()
    return r.json()


async def get_reminder(reminder_id: int, user_id: int) -> dict | None:
    c = await get_client()
    r = await c.get(f"/reminders/{reminder_id}", params={"user_id": user_id})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


async def create_reminder(
    user_id: int,
    pet_id: int,
    title: str,
    description: str = "",
    category: str = "custom",
    remind_at: datetime | None = None,
    repeat: str = "once",
) -> dict:
    c = await get_client()
    body = {
        "user_id": user_id,
        "pet_id": pet_id,
        "title": title,
        "description": description,
        "category": category,
        "remind_at": remind_at.isoformat() if remind_at else datetime.utcnow().isoformat(),
        "repeat": repeat,
    }
    r = await c.post("/reminders/", json=body)
    r.raise_for_status()
    return r.json()


async def pause_reminder(reminder_id: int, user_id: int) -> dict | None:
    c = await get_client()
    r = await c.patch(f"/reminders/{reminder_id}/pause", params={"user_id": user_id})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


async def resume_reminder(reminder_id: int, user_id: int) -> dict | None:
    c = await get_client()
    r = await c.patch(f"/reminders/{reminder_id}/resume", params={"user_id": user_id})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


async def delete_reminder(reminder_id: int, user_id: int) -> bool:
    c = await get_client()
    r = await c.delete(f"/reminders/{reminder_id}", params={"user_id": user_id})
    return r.status_code == 204


# ══════════════ MEDICAL ══════════════


async def list_vaccinations(pet_id: int, user_id: int) -> list[dict]:
    c = await get_client()
    r = await c.get(f"/medical/vaccinations/{pet_id}", params={"user_id": user_id})
    r.raise_for_status()
    return r.json()


async def create_vaccination(
    user_id: int, pet_id: int, name: str, date_done: date,
    next_date: date | None = None, notes: str = "",
) -> dict:
    c = await get_client()
    body = {
        "pet_id": pet_id,
        "name": name,
        "date_done": date_done.isoformat(),
        "notes": notes,
    }
    if next_date:
        body["next_date"] = next_date.isoformat()
    r = await c.post("/medical/vaccinations", params={"user_id": user_id}, json=body)
    r.raise_for_status()
    return r.json()


async def delete_vaccination(vac_id: int, user_id: int) -> bool:
    c = await get_client()
    r = await c.delete(f"/medical/vaccinations/{vac_id}", params={"user_id": user_id})
    return r.status_code == 204


async def list_vet_visits(pet_id: int, user_id: int) -> list[dict]:
    c = await get_client()
    r = await c.get(f"/medical/vet_visits/{pet_id}", params={"user_id": user_id})
    r.raise_for_status()
    return r.json()


async def create_vet_visit(
    user_id: int, pet_id: int, visit_date: date,
    diagnosis: str = "", treatment: str = "", notes: str = "",
) -> dict:
    c = await get_client()
    body = {
        "pet_id": pet_id,
        "visit_date": visit_date.isoformat(),
        "diagnosis": diagnosis,
        "treatment": treatment,
        "notes": notes,
    }
    r = await c.post("/medical/vet_visits", params={"user_id": user_id}, json=body)
    r.raise_for_status()
    return r.json()


async def delete_vet_visit(visit_id: int, user_id: int) -> bool:
    c = await get_client()
    r = await c.delete(f"/medical/vet_visits/{visit_id}", params={"user_id": user_id})
    return r.status_code == 204


async def list_weight_records(pet_id: int, user_id: int) -> list[dict]:
    c = await get_client()
    r = await c.get(f"/medical/weight/{pet_id}", params={"user_id": user_id})
    r.raise_for_status()
    return r.json()


async def create_weight_record(user_id: int, pet_id: int, weight: float) -> dict:
    c = await get_client()
    body = {"pet_id": pet_id, "weight": weight}
    r = await c.post("/medical/weight", params={"user_id": user_id}, json=body)
    r.raise_for_status()
    return r.json()


async def list_documents(pet_id: int, user_id: int) -> list[dict]:
    c = await get_client()
    r = await c.get(f"/medical/documents/{pet_id}", params={"user_id": user_id})
    r.raise_for_status()
    return r.json()


async def create_document(
    user_id: int, pet_id: int, doc_type: str, file_id: str, description: str = "",
) -> dict:
    c = await get_client()
    r = await c.post(
        "/medical/documents",
        params={"user_id": user_id, "pet_id": pet_id, "doc_type": doc_type,
                "file_id": file_id, "description": description},
    )
    r.raise_for_status()
    return r.json()


async def delete_document(doc_id: int, user_id: int) -> bool:
    c = await get_client()
    r = await c.delete(f"/medical/documents/{doc_id}", params={"user_id": user_id})
    return r.status_code == 204


async def get_calendar(user_id: int) -> dict:
    c = await get_client()
    r = await c.get(f"/medical/calendar/{user_id}")
    r.raise_for_status()
    return r.json()


# ══════════════ FOOD / WATER / ALLERGIES ══════════════


async def list_food_entries(pet_id: int, user_id: int, days: int = 7) -> list[dict]:
    c = await get_client()
    r = await c.get(f"/food/entries/{pet_id}", params={"user_id": user_id, "days": days})
    r.raise_for_status()
    return r.json()


async def create_food_entry(
    user_id: int, pet_id: int, food_name: str,
    portion: str = "", portion_grams: float | None = None, notes: str = "",
) -> dict:
    c = await get_client()
    body: dict = {"pet_id": pet_id, "food_name": food_name, "portion": portion, "notes": notes}
    if portion_grams is not None:
        body["portion_grams"] = portion_grams
    r = await c.post("/food/entries", params={"user_id": user_id}, json=body)
    r.raise_for_status()
    return r.json()


async def delete_food_entry(entry_id: int, user_id: int) -> bool:
    c = await get_client()
    r = await c.delete(f"/food/entries/{entry_id}", params={"user_id": user_id})
    return r.status_code == 204


async def clear_food_entries(pet_id: int, user_id: int) -> None:
    c = await get_client()
    r = await c.delete(f"/food/entries/clear/{pet_id}", params={"user_id": user_id})
    r.raise_for_status()


async def list_water_entries(pet_id: int, user_id: int, days: int = 7) -> list[dict]:
    c = await get_client()
    r = await c.get(f"/food/water/{pet_id}", params={"user_id": user_id, "days": days})
    r.raise_for_status()
    return r.json()


async def create_water_entry(user_id: int, pet_id: int, amount_ml: int) -> dict:
    c = await get_client()
    body = {"pet_id": pet_id, "amount_ml": amount_ml}
    r = await c.post("/food/water", params={"user_id": user_id}, json=body)
    r.raise_for_status()
    return r.json()


async def delete_water_entry(entry_id: int, user_id: int) -> bool:
    c = await get_client()
    r = await c.delete(f"/food/water/{entry_id}", params={"user_id": user_id})
    return r.status_code == 204


async def clear_water_entries(pet_id: int, user_id: int) -> None:
    c = await get_client()
    r = await c.delete(f"/food/water/clear/{pet_id}", params={"user_id": user_id})
    r.raise_for_status()


async def list_allergies(pet_id: int, user_id: int) -> list[dict]:
    c = await get_client()
    r = await c.get(f"/food/allergies/{pet_id}", params={"user_id": user_id})
    r.raise_for_status()
    return r.json()


async def list_allergies_by_user(user_id: int) -> list[dict]:
    c = await get_client()
    r = await c.get(f"/food/allergies/by_user/{user_id}")
    r.raise_for_status()
    return r.json()


async def create_allergy(
    user_id: int, pet_id: int, allergen: str, reaction: str = "", notes: str = "",
) -> dict:
    c = await get_client()
    body = {"pet_id": pet_id, "allergen": allergen, "reaction": reaction, "notes": notes}
    r = await c.post("/food/allergies", params={"user_id": user_id}, json=body)
    r.raise_for_status()
    return r.json()


async def delete_allergy(allergy_id: int, user_id: int) -> bool:
    c = await get_client()
    r = await c.delete(f"/food/allergies/{allergy_id}", params={"user_id": user_id})
    return r.status_code == 204


async def get_daily_summary(pet_id: int, user_id: int) -> dict:
    c = await get_client()
    r = await c.get(f"/food/daily/{pet_id}", params={"user_id": user_id})
    r.raise_for_status()
    return r.json()


# ══════════════ SUBSCRIPTIONS ══════════════


async def get_subscription_status(user_id: int) -> dict:
    c = await get_client()
    r = await c.get(f"/subscriptions/status/{user_id}")
    r.raise_for_status()
    return r.json()


async def get_user_settings(user_id: int) -> dict:
    c = await get_client()
    r = await c.get(f"/subscriptions/settings/{user_id}")
    r.raise_for_status()
    return r.json()


async def get_plan_tier(user_id: int) -> str:
    c = await get_client()
    r = await c.get(f"/subscriptions/plan_tier/{user_id}")
    r.raise_for_status()
    return r.json()["plan_tier"]


async def check_premium(user_id: int) -> bool:
    c = await get_client()
    r = await c.get(f"/subscriptions/is_premium/{user_id}")
    r.raise_for_status()
    return r.json()["is_premium"]


async def check_ai_limit(user_id: int) -> tuple[bool, int]:
    c = await get_client()
    r = await c.post(f"/subscriptions/check_ai_limit/{user_id}")
    r.raise_for_status()
    data = r.json()
    return data["allowed"], data["remaining"]


async def refund_ai_limit(user_id: int) -> None:
    c = await get_client()
    await c.post(f"/subscriptions/refund_ai_limit/{user_id}")


async def check_pet_limit(user_id: int) -> tuple[bool, int]:
    c = await get_client()
    r = await c.get(f"/subscriptions/check_pet_limit/{user_id}")
    r.raise_for_status()
    data = r.json()
    return data["allowed"], data["remaining"]


async def grant_premium(user_id: int, days: int, plan_tier: str = "pro") -> bool:
    c = await get_client()
    r = await c.post("/subscriptions/grant", json={"user_id": user_id, "days": days, "plan_tier": plan_tier})
    r.raise_for_status()
    return r.json()["ok"]


async def revoke_premium(user_id: int) -> bool:
    c = await get_client()
    r = await c.post(f"/subscriptions/revoke/{user_id}")
    r.raise_for_status()
    return r.json()["ok"]


async def can_use_pdf_export(user_id: int) -> bool:
    c = await get_client()
    r = await c.get(f"/subscriptions/can_pdf/{user_id}")
    r.raise_for_status()
    return r.json()["allowed"]


async def can_use_weather(user_id: int) -> bool:
    c = await get_client()
    r = await c.get(f"/subscriptions/can_weather/{user_id}")
    r.raise_for_status()
    return r.json()["allowed"]


async def can_use_voice_notes(user_id: int) -> bool:
    c = await get_client()
    r = await c.get(f"/subscriptions/can_voice/{user_id}")
    r.raise_for_status()
    return r.json()["allowed"]


async def update_user_settings(user_id: int, **fields) -> None:
    c = await get_client()
    await c.patch(f"/subscriptions/settings/{user_id}", params=fields)


# ══════════════ PAYMENTS ══════════════


async def mark_payment_processed(
    provider: str, payment_id: str, user_id: int, plan_key: str,
) -> tuple[bool, bool]:
    c = await get_client()
    r = await c.post("/payments/mark_processed", json={
        "provider": provider, "payment_id": payment_id,
        "user_id": user_id, "plan_key": plan_key,
    })
    r.raise_for_status()
    data = r.json()
    return data["ok"], data["duplicate"]


async def upsert_pending_payment(
    provider: str, payment_id: str, user_id: int, plan_key: str,
    amount_value: str = "", currency: str = "", status: str = "pending",
) -> None:
    c = await get_client()
    await c.post("/payments/upsert_pending", json={
        "provider": provider, "payment_id": payment_id,
        "user_id": user_id, "plan_key": plan_key,
        "amount_value": amount_value, "currency": currency, "status": status,
    })


async def update_pending_payment(
    provider: str, payment_id: str, status: str,
    last_error: str = "", completed: bool = False,
) -> None:
    c = await get_client()
    await c.post("/payments/update_pending", json={
        "provider": provider, "payment_id": payment_id,
        "status": status, "last_error": last_error, "completed": completed,
    })


async def get_pending_payment(provider: str, payment_id: str) -> dict | None:
    c = await get_client()
    r = await c.get(f"/payments/pending/{provider}/{payment_id}")
    r.raise_for_status()
    return r.json()


# ══════════════ ANALYTICS ══════════════


async def track_event(
    user_id: int, event_name: str, source: str = "", payload: dict | None = None,
) -> None:
    try:
        c = await get_client()
        await c.post("/analytics/track", json={
            "user_id": user_id, "event_name": event_name,
            "source": source, "payload": payload,
        })
    except Exception as e:
        logger.warning("Failed to track event %s: %s", event_name, e)


async def track_user_activity(user_id: int, source: str = "") -> None:
    try:
        c = await get_client()
        await c.post(f"/analytics/track_activity/{user_id}", params={"source": source})
    except Exception as e:
        logger.warning("Failed to track activity: %s", e)


async def get_funnel_report(days: int = 7) -> str:
    c = await get_client()
    r = await c.get("/analytics/funnel", params={"days": days})
    r.raise_for_status()
    return r.json()["report"]


# ══════════════ SERVICES ══════════════


async def is_ai_operational() -> bool:
    c = await get_client()
    r = await c.get("/services/health/ai")
    r.raise_for_status()
    return r.json()["operational"]


async def is_card_payment_operational() -> bool:
    c = await get_client()
    r = await c.get("/services/health/card_payment")
    r.raise_for_status()
    return r.json()["operational"]


async def get_weather(city: str) -> dict | None:
    c = await get_client()
    r = await c.get(f"/services/weather/{city}")
    r.raise_for_status()
    return r.json()["data"]


async def get_weather_alert(weather_data: dict, species: str, pet_name: str = "") -> str | None:
    c = await get_client()
    r = await c.post("/services/weather/alert", json={
        "weather_data": weather_data, "species": species, "pet_name": pet_name,
    })
    r.raise_for_status()
    return r.json()["alert"]


async def get_food_norm(species: str, weight_kg: float | None = None, age_months: int | None = None) -> dict:
    c = await get_client()
    r = await c.post("/services/norms/food", json={
        "species": species, "weight_kg": weight_kg, "age_months": age_months,
    })
    r.raise_for_status()
    return r.json()


async def get_progress_bar(current: float, target: float, width: int = 10) -> str:
    c = await get_client()
    r = await c.post("/services/norms/progress_bar", json={
        "current": current, "target": target, "width": width,
    })
    r.raise_for_status()
    return r.json()["bar"]


async def get_feeding_chart(pet_name: str, entries: list[dict]) -> bytes | None:
    import base64
    c = await get_client()
    r = await c.post("/services/charts/feeding", json={"pet_name": pet_name, "entries": entries})
    r.raise_for_status()
    img = r.json()["image"]
    return base64.b64decode(img) if img else None


async def get_timeline_chart(pet_name: str, entries: list[dict]) -> bytes | None:
    import base64
    c = await get_client()
    r = await c.post("/services/charts/timeline", json={"pet_name": pet_name, "entries": entries})
    r.raise_for_status()
    img = r.json()["image"]
    return base64.b64decode(img) if img else None


async def list_voice_notes(user_id: int) -> list[dict]:
    c = await get_client()
    r = await c.get(f"/services/voice_notes/by_user/{user_id}")
    r.raise_for_status()
    return r.json()


async def create_voice_note(
    pet_id: int, user_id: int, file_id: str, transcription: str = "",
) -> dict:
    c = await get_client()
    r = await c.post(
        "/services/voice_notes",
        params={"pet_id": pet_id, "user_id": user_id, "file_id": file_id, "transcription": transcription},
    )
    r.raise_for_status()
    return r.json()


async def delete_voice_note(note_id: int, user_id: int) -> None:
    c = await get_client()
    await c.delete(f"/services/voice_notes/{note_id}", params={"user_id": user_id})


# ══════════════ FEATURE PERMISSIONS ══════════════


async def check_feature_permission(user_id: int, feature: str) -> bool:
    c = await get_client()
    r = await c.get(f"/subscriptions/check_feature/{user_id}", params={"feature": feature})
    r.raise_for_status()
    return r.json()["allowed"]


async def toggle_weather_notify(user_id: int) -> dict:
    c = await get_client()
    r = await c.post(f"/subscriptions/toggle_weather/{user_id}")
    r.raise_for_status()
    return r.json()


async def list_pending_payments(provider: str) -> list[dict]:
    c = await get_client()
    r = await c.get(f"/payments/pending_list/{provider}")
    r.raise_for_status()
    return r.json()


async def get_medical_calendar(user_id: int) -> dict:
    c = await get_client()
    r = await c.get(f"/medical/calendar/{user_id}")
    r.raise_for_status()
    return r.json()


async def get_norms(user_id: int) -> dict:
    c = await get_client()
    r = await c.get(f"/services/norms/{user_id}")
    r.raise_for_status()
    return r.json()


# ══════════════ ADMIN ══════════════


async def admin_overview() -> dict:
    c = await get_client()
    r = await c.get("/admin/overview")
    r.raise_for_status()
    return r.json()


async def admin_finance() -> dict:
    c = await get_client()
    r = await c.get("/admin/finance")
    r.raise_for_status()
    return r.json()


async def admin_users(limit: int = 8, offset: int = 0, query: str | None = None) -> dict:
    c = await get_client()
    params: dict = {"limit": limit, "offset": offset}
    if query:
        params["query"] = query
    r = await c.get("/admin/users", params=params)
    r.raise_for_status()
    return r.json()


async def admin_user_detail(user_id: int) -> dict | None:
    c = await get_client()
    r = await c.get(f"/admin/users/{user_id}")
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


async def admin_broadcast_targets() -> list[int]:
    c = await get_client()
    r = await c.get("/admin/broadcast/targets")
    r.raise_for_status()
    return r.json()["user_ids"]
