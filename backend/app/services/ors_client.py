"""Cliente de OpenRouteService (ORS).

Usa la Directions API de ORS para obtener la geometría real por carretera
(GeoJSON LineString) y las instrucciones de manejo tramo a tramo.

Si ORS no está disponible o no hay API key, los callers deben tener un
fallback (línea recta) — el sistema nunca debe fallar por esto.
"""

import logging

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class ORSError(Exception):
    """Error al comunicarse con OpenRouteService."""


def get_route_geometry(coordinates: list[dict]) -> dict:
    """Llama a ORS Directions API y devuelve geometría real + instrucciones.

    ``coordinates``: lista ordenada de {"lat":.., "lng":..} — la secuencia ya
    optimizada de paradas (incluyendo el depósito al inicio).

    Lanza ORSError si falla; el caller debe tener un fallback (línea recta).
    """
    if not settings.ORS_API_KEY:
        raise ORSError("ORS_API_KEY no configurada")

    url = f"{settings.ORS_BASE_URL}/v2/directions/{settings.ORS_PROFILE}/geojson"
    headers = {
        "Authorization": settings.ORS_API_KEY,
        "Content-Type": "application/json",
    }
    body = {"coordinates": [[c["lng"], c["lat"]] for c in coordinates]}

    try:
        resp = requests.post(
            url, json=body, headers=headers, timeout=settings.ORS_TIMEOUT_SECONDS
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise ORSError(f"Error llamando a ORS Directions: {e}") from e

    feature = data["features"][0]
    geometry = feature["geometry"]  # GeoJSON LineString — [lng, lat] siguiendo la calle
    props = feature["properties"]
    segments = props.get("segments", [])

    steps = []  # instrucciones de manejo, tipo "Gira a la derecha en 5ta Calle"
    for seg in segments:
        for step in seg.get("steps", []):
            steps.append({
                "instruction": step["instruction"],
                "distance_m": step["distance"],
                "duration_s": step["duration"],
            })

    return {
        "geometry": geometry,
        "distance_m": props["summary"]["distance"],
        "duration_s": props["summary"]["duration"],
        "steps": steps,
    }