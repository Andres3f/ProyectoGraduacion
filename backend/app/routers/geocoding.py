"""Geocoding de direcciones — módulo compartido.

Convierte una dirección escrita en candidatos con coordenadas. Es usado tanto
por el formulario de clientes (ClientsPage) como por el de depósitos
(DepotsPage) para que el usuario confirme o ajuste visualmente el punto en el
mapa antes de guardar. Montado en ``/api/geocode``.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.services.ors_client import geocode_address

router = APIRouter(prefix="/api/geocode", tags=["Geocoding"])

logger = logging.getLogger(__name__)


# Geocoding de una dirección escrita: devuelve candidatos con coordenadas para
# que el usuario confirme visualmente en el mapa. Cualquier usuario autenticado
# puede usarlo.
@router.get("")
@router.get("/", include_in_schema=False)
def geocode_address_endpoint(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Convierte una dirección en candidatos con coordenadas (hasta 5)."""
    if len(q.strip()) < 5:
        raise HTTPException(
            status_code=400,
            detail="Escribe al menos 5 caracteres de la dirección",
        )
    # Foco de búsqueda: el depósito base (centro de Jalapa). Prioriza
    # resultados del área operativa, clave para direcciones cortas/ambiguas.
    focus = (settings.DEPOT_LAT, settings.DEPOT_LNG)
    try:
        results = geocode_address(q, focus_lat=focus[0], focus_lng=focus[1])
    except Exception as exc:
        # Si ORS y Nominatim fallan, no romper el formulario: respuesta vacía.
        logger.warning("Geocoding falló por completo: %s", exc)
        return {"results": []}
    return {"results": results}