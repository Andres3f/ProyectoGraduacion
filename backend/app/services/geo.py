"""Utilidades geográficas compartidas."""

from geoalchemy2 import WKTElement


def point_wkt(longitude: float, latitude: float, srid: int = 4326) -> WKTElement:
    """Crea un elemento WKT POINT (lon lat) para columnas PostGIS."""
    # PostGIS (y WKT en general) espera el orden longitud, latitud.
    return WKTElement(f"POINT({longitude} {latitude})", srid=srid)