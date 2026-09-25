"""Cliente de OSRM (Open Source Routing Machine) para geometría real por calle.

Proveedor sin API key, usado como respaldo cuando ORS no está disponible o la
clave no tiene acceso (e.g. perfil ``driving-hgv`` requiere plan de pago).

Devuelve el mismo shape que ``ors_client.get_route_geometry`` para que el mapa
y el panel de instrucciones funcionen igual con ambos proveedores:
    {"geometry": <GeoJSON LineString>, "distance_m": float,
     "duration_s": float, "steps": [{"instruction","distance_m","duration_s"}]}

Nota: ``https://router.project-osrm.org`` es el servidor público de pruebas
(limitado a ~500 peticiones/día). Para producción convendría alojar un OSRM
propio y apuntar ``OSRM_BASE_URL`` a él.
"""

import logging

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class OSRMError(Exception):
    """Cualquier fallo al llamar a OSRM."""


# Palabras para construir instrucciones en español a partir del maneuver de OSRM.
_NOTA_ADVERBIO = {
    "left": "a la izquierda",
    "right": "a la derecha",
    "slight left": "ligeramente a la izquierda",
    "slight right": "ligeramente a la derecha",
    "sharp left": "bruscamente a la izquierda",
    "sharp right": "bruscamente a la derecha",
    "straight": "de frente",
    "uturn": "en U",
}

_TIPO_VERBO = {
    "depart": "Salir hacia",
    "turn": "Gire",
    "continue": "Continúe",
    "merge": "Incorpórese",
    "roundabout": "Tome la rotonda y salga",
    "roundabout turn": "Tome la rotonda y salga",
    "exit roundabout": "Salga de la rotonda",
    "fork": "En el cruce manténgase",
    "on ramp": "Tome la rampa",
    "off ramp": "Salga por la rampa",
    "end of road": "Al final de la vía gire",
    "new name": "Continúe por",
    "arrive": "Llegó a su destino",
    "notification": "Continúe",
}


def _step_to_instruction(step: dict) -> str:
    """Traduce un step de OSRM a una instrucción en español (estilo optimizador)."""
    maneuver = step.get("maneuver", {})
    tipo = maneuver.get("type", "turn")
    modifier = maneuver.get("modifier", "straight")
    name = (step.get("name") or "").strip()

    verbo = _TIPO_VERBO.get(tipo, "Continúe")
    adverbio = _NOTA_ADVERBIO.get(modifier, "")

    if tipo == "arrive":
        return verbo
    if tipo == "depart":
        return f"{verbo} {name}" if name else verbo

    if adverbio and verbo not in ("Incorpórese", "Salga de la rotonda", "Tome la rotonda y salga"):
        base = f"{verbo} {adverbio}"
    elif tipo in ("roundabout", "roundabout turn", "exit roundabout", "fork", "on ramp", "off ramp", "end of road", "new name"):
        base = verbo
    else:
        base = f"{verbo} {adverbio}".strip()

    return f"{base} en {name}" if name else base.strip()


def get_route_geometry(coordinates: list[dict]) -> dict:
    """Devuelve geometría real por carretera + instrucciones usando OSRM.

    ``coordinates``: lista ordenada de {"lat":.., "lng":..} (depósito primero).
    Lanza OSRMError si falla; el caller decide el fallback (línea recta).
    """
    if len(coordinates) < 2:
        raise OSRMError("OSRM requiere al menos 2 coordenadas")

    # OSRM recorre puntos "lng,lat" separados por ';' en la URL misma.
    points = ";".join(f"{c['lng']},{c['lat']}" for c in coordinates)
    # overview=full da la geometría completa; steps=true las instrucciones.
    url = (
        f"{settings.OSRM_BASE_URL}/route/v1/driving/{points}"
        f"?overview=full&geometries=geojson&steps=true"
    )

    try:
        resp = requests.get(url, timeout=settings.ORS_TIMEOUT_SECONDS)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise OSRMError(f"Error de red/HTTP llamando a OSRM: {e}") from e
    except ValueError as e:
        raise OSRMError(f"Respuesta de OSRM no es JSON válido: {e}") from e

    if data.get("code") != "Ok" or not data.get("routes"):
        raise OSRMError(f"OSRM no pudo calcular la ruta: {data.get('message', data)}")

    route = data["routes"][0]
    geometry = route.get("geometry")
    if not geometry or not geometry.get("coordinates"):
        raise OSRMError("OSRM devolvió una ruta sin geometría")

    # Convierte cada step de OSRM en una instrucción en español.
    steps = []
    for leg in route.get("legs", []):
        for step in leg.get("steps", []):
            steps.append({
                "instruction": _step_to_instruction(step),
                "distance_m": step.get("distance", 0),
                "duration_s": step.get("duration", 0),
            })

    return {
        "geometry": geometry,
        "distance_m": route.get("distance", 0),
        "duration_s": route.get("duration", 0),
        "steps": steps,
    }