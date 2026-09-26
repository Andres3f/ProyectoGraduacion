"""Regenera la geometría por calle (route_geometry + route_geometry_return +
steps) de las rutas que no la tienen guardada (rutas creadas cuando ORS/OSRM no
respondía). También completa la geometría de regreso de las rutas que solo
tienen la de ida.

Uso (desde backend/):
    python -m scripts.backfill_routes_geometry
"""
import logging
import sys

from app.database import SessionLocal
import app.models.user  # noqa: F401  (registra los mappers de SQLAlchemy)
import app.models.order  # noqa: F401
import app.models.vehicle  # noqa: F401
import app.models.route  # noqa: F401
import app.models.route_stop  # noqa: F401
import app.models.client  # noqa: F401
import app.models.depot  # noqa: F401
from app.models.route import Route
from app.models.depot import Depot
from app.services.ors_client import ORSError, get_route_geometry
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    db = SessionLocal()
    try:
        # Selecciona las rutas sin geometría de ida y las que tienen ida pero
        # les falta el regreso (creadas antes de separar ambos tramos).
        routes = [
            r
            for r in db.query(Route).all()
            if r.route_geometry is None
            or r.route_geometry == "null"
            or r.route_geometry_return is None
        ]
        if not routes:
            logger.info("No hay rutas sin geometría. Nada que hacer.")
            return

        updated = 0
        for route in routes:
            # Construye la secuencia de paradas en orden de visita.
            stops = sorted(route.stops, key=lambda s: s.sequence)
            stop_coords = [
                {"lat": s.order.latitude, "lng": s.order.longitude}
                for s in stops
                if s.order and s.order.latitude is not None
            ]
            if not stop_coords:
                logger.warning(
                    "Ruta #%s no tiene paradas con coordenadas; se omite.", route.id
                )
                continue

            # El depósito de la ruta; si no tiene, el predeterminado de la BD.
            depot = db.get(Depot, route.depot_id) if route.depot_id else None
            if depot is None:
                depot = db.query(Depot).filter(Depot.is_default == True).first()
            depot_coords = {
                "lat": depot.latitude if depot else settings.DEPOT_LAT,
                "lng": depot.longitude if depot else settings.DEPOT_LNG,
            }
            # Los dos tramos por separado: depósito -> paradas (ida) y
            # última parada -> depósito (vuelta).
            coords_out = [depot_coords] + stop_coords
            coords_back = stop_coords + [depot_coords]

            try:
                geo_out = get_route_geometry(coords_out)
                geo_back = get_route_geometry(coords_back)
            except ORSError as exc:
                logger.warning("Ruta #%s: no se pudo generar geometría: %s", route.id, exc)
                continue

            # Persiste ambas geometrías, los pasos de cada trayecto y la
            # duración total de la ida y vuelta.
            route.route_geometry = geo_out["geometry"]
            route.route_geometry_return = geo_back["geometry"]
            route.steps = [{**s, "leg": "ida"} for s in geo_out["steps"]] + [
                {**s, "leg": "vuelta"} for s in geo_back["steps"]
            ]
            route.total_duration_min = round(
                (geo_out["duration_s"] + geo_back["duration_s"]) / 60, 1
            )
            route.distance_source = "osrm"
            db.add(route)
            updated += 1
            logger.info(
                "Ruta #%s: geometría regenerada (ida %s puntos, vuelta %s puntos, %s pasos, %.1f km).",
                route.id,
                len(geo_out["geometry"].get("coordinates", [])),
                len(geo_back["geometry"].get("coordinates", [])),
                len(route.steps),
                (geo_out["distance_m"] + geo_back["distance_m"]) / 1000,
            )

        # Aplica todos los cambios en una sola transacción al final.
        db.commit()
        logger.info("Listo: %s rutas actualizadas.", updated)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())