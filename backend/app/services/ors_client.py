"""Cliente de OpenRouteService (ORS).

Combina la Matrix API (distancias/tiempos reales por carretera, usada por el
optimizador) y la Directions API (geometría por carretera + instrucciones de
manejo, usada por el mapa). Si ORS no está disponible o no hay API key, los
callers deben tener un fallback (Haversine / línea recta) — este módulo nunca
debe tumbar la optimización.
"""

import logging

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class ORSError(Exception):
    """Cualquier fallo al llamar a ORS: sin key, timeout, respuesta inválida."""


def get_distance_duration_matrix(locations: list[dict]) -> tuple[list[list[int]], list[list[int]]]:
    """Devuelve (matriz_distancia_metros, matriz_duracion_segundos) usando
    ORS Matrix API. `locations` es una lista de {"lat":.., "lng":..}.

    Lanza ORSError si algo falla; el caller (optimizer.py) debe capturarla
    y usar Haversine como fallback.
    """
    if not settings.ORS_API_KEY:
        raise ORSError("ORS_API_KEY no configurada")

    if len(locations) > 50:
        raise ORSError(f"ORS Matrix soporta hasta 50 puntos, se recibieron {len(locations)}")

    url = f"{settings.ORS_BASE_URL}/v2/matrix/{settings.ORS_PROFILE}"
    headers = {
        "Authorization": settings.ORS_API_KEY,
        "Content-Type": "application/json",
    }
    body = {
        # ORS espera [lon, lat], al revés de como lo guardamos nosotros.
        "locations": [[loc["lng"], loc["lat"]] for loc in locations],
        "metrics": ["distance", "duration"],
        "units": "m",
    }

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=settings.ORS_TIMEOUT_SECONDS)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise ORSError(f"Error de red/HTTP llamando a ORS: {e}") from e
    except ValueError as e:
        raise ORSError(f"Respuesta de ORS no es JSON válido: {e}") from e

    distances = data.get("distances")
    durations = data.get("durations")
    if distances is None or durations is None:
        raise ORSError(f"Respuesta de ORS sin 'distances'/'durations': {data}")

    # ORS puede devolver None en celdas sin ruta posible (islas, etc.) —
    # las convertimos a un valor grande para que el solver las evite.
    n = len(locations)
    dist_matrix = [[int(distances[i][j]) if distances[i][j] is not None else 999_000_000
                     for j in range(n)] for i in range(n)]
    dur_matrix = [[int(durations[i][j]) if durations[i][j] is not None else 999_000_000
                    for j in range(n)] for i in range(n)]
    return dist_matrix, dur_matrix


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