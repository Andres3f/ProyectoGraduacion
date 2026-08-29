"""
Seed / datos de demostración — Optirutas Jalapa.

Crea un set de datos realistas (usuarios por rol, clientes, vehículos,
pedidos y rutas optimizadas) para poder probar y demostrar el sistema desde el
primer arranque.

Mantenido de forma **idempotente**: correr varias veces no duplica datos.
Se ejecuta de forma automática (solo el admin) al arrancar la app a través de
``create_initial_admin``; el resto de datos se generan con ``seed_demo_data``
(manual o programático).

Uso manual:
    python -m app.seed
"""

import logging
import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User, RoleEnum
from app.models.client import Client
from app.models.vehicle import Vehicle
from app.models.order import Order, OrderStatus
from app.models.route import Route, RouteStatus
from app.models.route_stop import RouteStop
from app.auth.passwords import hash_password
from app.services.geo import point_wkt
from app.services.optimizer import optimize_routes

logger = logging.getLogger(__name__)

random.seed(42)  # resultados reproducibles

# ── Credenciales por defecto ─────────────────────────────────
USERS = [
    # (email, full_name, password, role)
    ("admin@optirutas.com", "Administrador", "Admin123!", RoleEnum.admin),
    ("planificador@optirutas.com", "Planificador", "Planif123!", RoleEnum.planificador),
    ("conductor@optirutas.com", "Conductor Demo", "Conduc123!", RoleEnum.conductor),
    ("gerente@optirutas.com", "Gerente", "Gerente123!", RoleEnum.gerente),
]

# Área urbana de Jalapa (centro aprox. 14.6339, -89.9886, variación ±0.03)
JALAPA_CENTER_LAT = 14.6339
JALAPA_CENTER_LNG = -89.9886
LAT_SPREAD = 0.03
LNG_SPREAD = 0.03

VEHICLES = [
    # (placa, descripción, capacidad_kg, capacidad_m3)
    ("R-101", "Camión 5 ton", 5000, 20),
    ("R-102", "Camión 8 ton", 8000, 30),
    ("R-103", "Camión 10 ton", 10000, 40),
    ("R-104", "Camión 3 ton", 3000, 12),
    ("R-105", "Camión 6 ton", 6000, 24),
]

QUINTAL_KG = 45.5  # 1 quintal ≈ 45.5 kg
ZONAS = ["Centro", "San José", "El Carmen", "Las Flores", "Vista Hermosa",
         "La Reforma", "Buenos Aires", "San Antonio"]

NUM_CLIENTS = 30
NUM_ORDERS = 100
NUM_ROUTES = 20


# ── Helpers get_or_create ─────────────────────────────────────


def _get_or_create_user(db: Session, email, full_name, password, role) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _get_or_create_client(db: Session, name: str) -> Client:
    client = db.query(Client).filter(Client.name == name).first()
    if client:
        return client
    lat = JALAPA_CENTER_LAT + random.uniform(-LAT_SPREAD, LAT_SPREAD)
    lng = JALAPA_CENTER_LNG + random.uniform(-LNG_SPREAD, LNG_SPREAD)
    client = Client(
        name=name,
        address=f"Calle {random.randint(1, 40)} Av {random.randint(1, 20)}, Jalapa",
        zone=random.choice(ZONAS),
        latitude=round(lat, 6),
        longitude=round(lng, 6),
        geom=point_wkt(lng, lat),
    )
    db.add(client)
    db.flush()
    return client


def _get_or_create_vehicle(db: Session, plate, description, cap_kg, cap_m3, driver_id) -> Vehicle:
    vehicle = db.query(Vehicle).filter(Vehicle.plate == plate).first()
    if vehicle:
        return vehicle
    vehicle = Vehicle(
        plate=plate,
        description=description,
        capacity_kg=cap_kg,
        capacity_m3=cap_m3,
        driver_id=driver_id,
        status="disponible",
        is_active=True,
    )
    db.add(vehicle)
    db.flush()
    return vehicle


def _persist_route(db: Session, vehicle, route_data, route_index: int) -> Route:
    """Persiste una ruta optimizada a partir del resultado de `optimize_routes`."""
    route = Route(
        name=f"Ruta-{route_index + 1}",
        vehicle_id=vehicle.id,
        driver_id=vehicle.driver_id,
        total_distance_km=route_data["total_distance_km"],
        total_weight_kg=route_data["total_weight_kg"],
        status=RouteStatus.planificada,
        optimized_at=datetime.now(),
    )
    db.add(route)
    db.flush()

    for stop in route_data["stops"]:
        db.add(RouteStop(
            route_id=route.id,
            order_id=stop["order_id"],
            sequence=stop["sequence"],
            eta=stop.get("eta"),
            distance_from_previous_km=stop.get("distance_from_previous_km"),
            status="entregado" if random.random() < 0.5 else "pendiente",
            delivered_at=(
                stop.get("eta") or datetime.now()
                if random.random() < 0.5 else None
            ),
        ))
    return route


# ── Functions públicas ────────────────────────────────────────


def create_initial_admin() -> None:
    """Crea (únicamente) el usuario admin si no existe ninguno.

    Se llama automáticamente en el arranque de la app (lifespan). No genera el
    resto de los datos de demo; para eso usa `seed_demo_data`.
    """
    db: Session = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.role == RoleEnum.admin).first()
        if existing_admin:
            logger.info("✅ Ya existe un usuario admin (%s). Seed omitido.", existing_admin.email)
            return
        admin = User(
            email="admin@optirutas.com",
            full_name="Administrador",
            hashed_password=hash_password("Admin123!"),
            role=RoleEnum.admin,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        logger.info("🌱 Usuario admin creado: admin@optirutas.com / Admin123!")
    except Exception as e:
        db.rollback()
        logger.warning("⚠️ No se pudo crear el admin: %s", e)
    finally:
        db.close()


def seed_demo_data() -> dict:
    """Genera (idempotente) los datos de demostración completos.

    Returns:
        dict con contadores de lo que se creó (para no duplicar en llamadas
        repetidas): usuarios, clientes, vehículos, pedidos y rutas creados.
    """
    db: Session = SessionLocal()
    created = {"users": 0, "clients": 0, "vehicles": 0, "orders": 0, "routes": 0}
    try:
        # ── Usuarios por rol ─────────────────────────────────
        driver = None
        for email, name, pwd, role in USERS:
            existed = db.query(User).filter(User.email == email).first()
            _get_or_create_user(db, email, name, pwd, role)
            if not existed:
                created["users"] += 1
            if role == RoleEnum.conductor:
                driver = db.query(User).filter(User.email == email).first()

        # ── Clientes (30) ────────────────────────────────────
        clients = []
        for i in range(NUM_CLIENTS):
            name = f"Cliente {i + 1}"
            existed = db.query(Client).filter(Client.name == name).first()
            c = _get_or_create_client(db, name)
            if not existed:
                created["clients"] += 1
            clients.append(c)

        # ── Vehículos (5) ────────────────────────────────────
        vehicles = []
        for i, (plate, desc, cap_kg, cap_m3) in enumerate(VEHICLES):
            existed = db.query(Vehicle).filter(Vehicle.plate == plate).first()
            v = _get_or_create_vehicle(db, plate, desc, cap_kg, cap_m3,
                                       driver.id if i == 0 else None)
            if not existed:
                created["vehicles"] += 1
            vehicles.append(v)

        db.commit()

        # ── Pedidos (~100) ───────────────────────────────────
        if db.query(Order).count() == 0:
            for _ in range(NUM_ORDERS):
                client = random.choice(clients)
                quintales = random.randint(1, 20)
                db.add(Order(
                    client_id=client.id,
                    client_name=client.name,
                    address=client.address,
                    latitude=client.latitude,
                    longitude=client.longitude,
                    geom=client.geom,
                    weight_kg=round(quintales * QUINTAL_KG, 1),
                    volume_m3=round(random.uniform(0.5, 4.0), 2),
                    status=OrderStatus.pendiente,
                    service_time_min=15,
                    created_by=db.query(User)
                    .filter(User.role == RoleEnum.planificador)
                    .first().id,
                ))
            db.commit()
            created["orders"] = NUM_ORDERS
            logger.info("📦 Creados %s pedidos", NUM_ORDERS)

        # ── Rutas optimizadas (20) ──────────────────────────
        pendientes = db.query(Order).filter(
            Order.status == OrderStatus.pendiente
        ).all()
        if pendientes and db.query(Route).count() < NUM_ROUTES:
            random.shuffle(pendientes)
            chunk = min(len(pendientes), NUM_ROUTES * 5)
            pool = pendientes[:chunk]
            route_number = db.query(Route).count()

            for k in range(NUM_ROUTES):
                subset = pool[k * 5:(k + 1) * 5]
                if not subset:
                    break
                veh = random.choice(vehicles)
                result = optimize_routes(subset, [veh])
                if not result["success"] or not result["routes"]:
                    continue
                route_data = result["routes"][0]
                _persist_route(db, veh, route_data, route_number)
                route_number += 1
                db.query(Order).filter(
                    Order.id.in_([s["order_id"] for s in route_data["stops"]])
                ).update({Order.status: OrderStatus.en_ruta}, synchronize_session=False)
            db.commit()
            created["routes"] = route_number

        logger.info("🌱 Seed completado: %s", created)
    except Exception as e:
        db.rollback()
        logger.error("⚠️ Error en seed_demo_data: %s", e)
        raise
    finally:
        db.close()
    return created


def main() -> None:
    """Entry point para `python -m app.seed`."""
    logging.basicConfig(level=logging.INFO)
    seed_demo_data()


if __name__ == "__main__":
    main()
