"""Поиск ветеринарных клиник через Overpass API (OpenStreetMap) — бесплатно."""

import logging
import math
from html import escape

import aiohttp

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


async def search_vet_clinics(lat: float, lon: float, radius_m: int = 5000, limit: int = 10) -> list[dict]:
    """Ищет ветклиники рядом с координатами.

    Returns:
        [{"name", "lat", "lon", "distance_m", "phone", "website",
          "opening_hours", "address", "rating_info"}]
    """
    query = f"""
    [out:json][timeout:10];
    (
      node["amenity"="veterinary"](around:{radius_m},{lat},{lon});
      way["amenity"="veterinary"](around:{radius_m},{lat},{lon});
      node["healthcare"="veterinary"](around:{radius_m},{lat},{lon});
    );
    out body center;
    """

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OVERPASS_URL,
                data={"data": query},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Overpass API error: {resp.status}")
                    return []
                data = await resp.json()

        clinics = []
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            c_lat = el.get("lat") or el.get("center", {}).get("lat")
            c_lon = el.get("lon") or el.get("center", {}).get("lon")

            if not c_lat or not c_lon:
                continue

            dist = _haversine(lat, lon, c_lat, c_lon)
            name = tags.get("name", tags.get("name:ru", "Ветклиника"))

            clinics.append(
                {
                    "name": name,
                    "lat": c_lat,
                    "lon": c_lon,
                    "distance_m": int(dist),
                    "phone": tags.get("phone", tags.get("contact:phone", "")),
                    "website": tags.get("website", tags.get("contact:website", "")),
                    "opening_hours": tags.get("opening_hours", ""),
                    "address": _build_address(tags),
                }
            )

        clinics.sort(key=lambda c: c["distance_m"])
        return clinics[:limit]

    except Exception as e:
        logger.error(f"Ошибка поиска клиник: {e}")
        return []


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние между двумя точками (метры)."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _build_address(tags: dict) -> str:
    """Собирает адрес из OSM-тегов."""
    parts = []
    street = tags.get("addr:street", "")
    house = tags.get("addr:housenumber", "")
    city = tags.get("addr:city", "")
    if street:
        parts.append(f"{street} {house}".strip())
    if city:
        parts.append(city)
    return ", ".join(parts) if parts else ""


def format_clinic_card(clinic: dict, idx: int) -> str:
    """Форматирует карточку клиники."""
    dist_km = clinic["distance_m"] / 1000
    safe_name = escape(clinic["name"])
    safe_address = escape(clinic["address"])
    safe_phone = escape(clinic["phone"])
    safe_hours = escape(clinic["opening_hours"])

    lines = [f"<b>{idx}. {safe_name}</b>"]
    lines.append(f"   📍 {dist_km:.1f} км")

    if clinic["address"]:
        lines.append(f"   🏠 {safe_address}")
    if clinic["phone"]:
        lines.append(f"   📞 {safe_phone}")
    if clinic["opening_hours"]:
        lines.append(f"   🕐 {safe_hours}")

    # Ссылки на карты
    lat, lon = clinic["lat"], clinic["lon"]
    lines.append(
        f'   🗺 <a href="https://yandex.ru/maps/?pt={lon},{lat}&z=17">Яндекс</a>'
        f' | <a href="https://www.google.com/maps?q={lat},{lon}">Google</a>'
        f' | <a href="https://2gis.ru/search/ветклиника/{lon},{lat}">2ГИС</a>'
    )

    return "\n".join(lines)


def _radius_label(radius_m: int) -> str:
    radius_km = radius_m / 1000
    if radius_km.is_integer():
        return f"{int(radius_km)} км"
    return f"{radius_km:.1f} км"


async def search_and_format(lat: float, lon: float, radius_m: int = 5000) -> str:
    """Ищет клиники и возвращает отформатированный текст."""
    clinics = await search_vet_clinics(lat, lon, radius_m)

    if not clinics:
        return (
            f"😕 Ветклиники не найдены в радиусе {_radius_label(radius_m)}.\n\n"
            "Попробуйте поискать на картах:\n"
            f'🗺 <a href="https://yandex.ru/maps/?text=ветклиника&ll={lon},{lat}&z=14">Яндекс Карты</a>\n'
            f'🗺 <a href="https://www.google.com/maps/search/vet+clinic/@{lat},{lon},14z">Google Maps</a>'
        )

    lines = [f"🏥 <b>Найдено ветклиник: {len(clinics)}</b>\n"]
    for i, c in enumerate(clinics, 1):
        lines.append(format_clinic_card(c, i))
        lines.append("")

    return "\n".join(lines)
