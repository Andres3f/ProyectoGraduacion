"""Regenera la geometría por calle (route_geometry + steps) de las rutas que
no la tienen guardada (rutas creadas cuando ORS/OSRM no respondía).

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
from app.models.route import Route
from app.services.ors_client import ORSError, get_route_geometry
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    db = SessionLocal()
    try:
        routes = [
            r
            for r in db.query(Route).all()
            if r.route_geometry is None or r.route_geometry == "null"
        ]
        if not routes:
            logger.info("No hay rutas sin geometría. Nada que hacer.")
            return

        updated = 0
        for route in routes:
            stops = sorted(route.stops, key=lambda s: s.sequence)
            coords = [{"lat": settings.DEPOT_LAT, "lng": settings.DEPOT_LNG}]
            coords += [
                {"lat": s.order.latitude, "lng": s.order.longitude}
                for s in stops
                if s.order and s.order.latitude is not None
            ]
            if len(coords) < 2:
                logger.warning(
                    "Ruta #%s no tiene coordenadas suficientes; se omite.", route.id
                )
                continue

            try:
                geo = get_route_geometry(coords)
            except ORSError as exc:
                logger.warning("Ruta #%s: no se pudo generar geometría: %s", route.id, exc)
                continue

            route.route_geometry = geo["geometry"]
            route.steps = geo["steps"]
            route.total_duration_min = round(geo["duration_s"] / 60, 1)
            route.distance_source = "osrm"
            db.add(route)
            updated += 1
            logger.info(
                "Ruta #%s: geometría regenerada (%s puntos, %s pasos, %.1f km).",
                route.id,
                len(geo["geometry"].get("coordinates", [])),
                len(geo["steps"]),
                geo["distance_m"] / 1000,
            )

        db.commit()
        logger.info("Listo: %s rutas actualizadas.", updated)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())