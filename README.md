# Optirutas Jalapa

**Sistema inteligente de optimización de rutas de reparto** para distribuidores de cemento en Jalapa, Guatemala.

Optirutas utiliza algoritmos avanzados de optimización (Google OR-Tools) para calcular las rutas más eficientes, reduciendo tiempo de viaje, costos de combustible y mejorando la satisfacción del cliente.

## Características principales

- **Optimización de rutas** mediante Google OR-Tools
- **Gestión de pedidos** y asignación automática a vehículos
- **Visualización en mapa** con Leaflet en tiempo real
- **Control de usuarios** con autenticación JWT y roles RBAC
- **Datos geoespaciales** con PostGIS para cálculos de distancia precisos
- **Interfaz responsiva** con diseño moderno (Tailwind CSS)
- **Deploy simplificado** con Docker Compose

## Requisitos del sistema

- **Docker** 20.10+ y **Docker Compose** 2.0+
- **Python** 3.10+ (para desarrollo local)
- **Node.js** 16+ (para desarrollo frontend)
- **PostgreSQL** 15 (incluido en Docker Compose)
- **4GB RAM** mínimo

## Instalación rápida

### Opción 1: Con Docker Compose (Recomendado)

```bash
# 1. Clonar el repositorio
git clone <repo-url> && cd optirutas-jalapa

# 2. Configurar variables de entorno
cp .env.example .env

# 3. Levantar contenedores
docker compose up --build

# 4. Acceder a la aplicación
# Frontend:  http://localhost:5173
# API Docs:  http://localhost:8000/docs
# API Health: http://localhost:8000/health
```

### Opción 2: Desarrollo local

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (en otra terminal)
cd frontend
npm install
npm run dev
```

## Datos de demostración (seed)

El sistema arranca creando automáticamente el usuario `admin`. Para cargar un
set de datos realistas de Jalapa (4 usuarios por rol, ~30 clientes, 5
vehículos, ~100 pedidos y 20 rutas optimizadas) y poder ver el dashboard del
Gerente desde el primer arranque, ejecuta:

```bash
cd backend
source venv/bin/activate  # o venv\Scripts\activate en Windows
python -m app.seed
```

El seed es **idempotente**: correrlo varias veces no duplica datos.

Credenciales de demostración:

| Rol | Email | Contraseña |
|-----|-------|------------|
| Administrador | `admin@optirutas.com` | `Admin123!` |
| Planificador | `planificador@optirutas.com` | `Planif123!` |
| Conductor | `conductor@optirutas.com` | `Conduc123!` |
| Gerente | `gerente@optirutas.com` | `Gerente123!` |

## Estructura del proyecto

```
optirutas-jalapa/
├── backend/                       # API FastAPI
│   ├── app/
│   │   ├── auth/                 # Autenticación JWT y RBAC
│   │   ├── models/               # Modelos SQLAlchemy
│   │   │   ├── user.py
│   │   │   ├── order.py
│   │   │   ├── vehicle.py
│   │   │   └── route.py
│   │   ├── schemas/              # Validación Pydantic
│   │   ├── routers/              # Endpoints API
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── orders.py
│   │   │   ├── vehicles.py
│   │   │   ├── routes.py
│   │   │   └── optimizer.py
│   │   ├── services/             # Lógica de negocio
│   │   │   └── optimizer.py      # OR-Tools integración
│   │   ├── config.py             # Configuración
│   │   ├── database.py           # Conexión DB
│   │   └── main.py               # Aplicación principal
│   ├── alembic/                  # Migraciones de base de datos
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                      # Aplicación React + Vite
│   ├── src/
│   │   ├── components/           # Componentes reutilizables
│   │   │   ├── MapView.jsx
│   │   │   ├── Navbar.jsx
│   │   │   └── ProtectedRoute.jsx
│   │   ├── context/              # Context API
│   │   │   └── AuthContext.jsx
│   │   ├── pages/                # Páginas
│   │   │   ├── LoginPage.jsx
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── OrdersPage.jsx
│   │   │   ├── RoutesPage.jsx
│   │   │   └── MapPage.jsx
│   │   ├── services/             # API client
│   │   │   └── api.js
│   │   ├── index.css
│   │   └── main.jsx
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
├── data/                         # Datos de prueba
│   └── pedidos_jalapa.csv
├── docker-compose.yml
├── .env.example
├── README.md
└── .gitignore
```

## Optimización de rutas (Sprint 3)

El motor de optimización (`backend/app/services/optimizer.py`) resuelve un
**VRP con capacidad y ventanas de tiempo** (CVRP + Time Windows) usando
Google OR-Tools. A diferencia del TSP de un solo vehículo original, ahora:

- Se asignan pedidos a **varios vehículos** respetando la capacidad en kg.
- Se respetan las **ventanas de tiempo** de entrega de cada pedido.
- Si un pedido no cabe por capacidad u horario, **no rompe la ruta**: se
  devuelve en `unassigned_order_ids` para que el usuario vea qué falló
  (respuesta HTTP 200, no un 500).

### Decisión técnica: OSRM vs Haversine corregido

Para calcular distancias se usa **distancia Haversine (línea recta)
multiplicada por un factor de corrección de calles** (por defecto `× 1.3`),
configurable vía `ROAD_DISTANCE_FACTOR`. Se eligió esta opción por:

- **Simplicidad de despliegue**: no requiere levantar un servidor OSRM.
- **Alcance de tesis**: es suficiente y defendible para zonas urbanas.
- **Determinismo**: reproducible en pruebas sin dependencia de red.

Si en el futuro se requiere precisión por calles, se puede migrar a un
contenedor OSRM propio con el mapa de Guatemala y sustituir
`_build_distance_matrix`. La configuración relacionada vive en
`app/config.py` (velocidad promedio, hora de salida, costo por km, etc.).

### Endpoint de optimización

Se mantiene **`POST /api/routes/optimize`** (más RESTful que `/api/optimize`).
Solicitud:

```json
{ "order_ids": [1, 2, 3], "vehicle_ids": [1, 2] }
```

Respuesta: lista de rutas (una por vehículo usado), `unassigned_order_ids`,
`success`, `message` y `metrics` (distancias antes/después, % de reducción y
ahorro estimado de combustible).

### Persistencia de paradas

Las paradas se persisten en la tabla **`route_stops`** (una fila por parada
en una ruta), consultables desde la relación `Route.stops`. La columna
`routes.stops` (JSON) se conserva como *snapshot* por compatibilidad con el
frontend antiguo y se eliminará en Sprint 4.

## Autenticación y Roles (RBAC)

| Rol | Descripción | Permisos principales |
|-----|-------------|----------------------|
| **admin** | Administrador system | CRUD completo, gestión de usuarios, configuración |
| **planificador** | Planificador de rutas | Crear/editar pedidos, optimizar rutas, ver analytics |
| **conductor** | Conductor del vehículo | Ver rutas asignadas, actualizar estado de entrega |
| **gerente** | Gerente de operaciones | Ver dashboards, reportes, listar usuarios |

## Stack tecnológico

| Aspecto | Tecnologías |
|--------|------------|
| **Backend API** | FastAPI, Uvicorn, Pydantic |
| **ORM & BD** | SQLAlchemy, GeoAlchemy2, PostgreSQL 15, PostGIS |
| **Optimización** | Google OR-Tools, Python 3.10+ |
| **Migraciones** | Alembic |
| **Frontend** | React 18, Vite, TypeScript (opcional) |
| **Estilos** | Tailwind CSS 3, PostCSS |
| **Navegación** | React Router 6 |
| **Mapeo** | Leaflet.js |
| **API Client** | Axios |
| **Seguridad** | JWT, bcrypt |
| **Infra** | Docker Compose, Docker |

## Endpoints principales de API

### Autenticación
- `POST /api/auth/login` - Iniciar sesión
- `POST /api/auth/register` - Registro de usuario
- `POST /api/auth/refresh` - Refrescar token

### Usuarios
- `GET /api/users` - Listar usuarios
- `GET /api/users/{user_id}` - Obtener usuario
- `PUT /api/users/{user_id}` - Actualizar usuario
- `DELETE /api/users/{user_id}` - Eliminar usuario

### Pedidos
- `GET /api/orders` - Listar pedidos
- `POST /api/orders` - Crear pedido
- `PUT /api/orders/{order_id}` - Actualizar pedido
- `DELETE /api/orders/{order_id}` - Eliminar pedido

### Rutas & Optimización
- `GET /api/routes` - Listar rutas
- `POST /api/routes/optimize` - Optimizar rutas (OR-Tools)
- `PUT /api/routes/{route_id}` - Actualizar ruta
- `GET /api/routes/{route_id}/directions` - Obtener direcciones

### Vehículos
- `GET /api/vehicles` - Listar vehículos
- `POST /api/vehicles` - Agregar vehículo
- `PUT /api/vehicles/{vehicle_id}` - Actualizar vehículo

**Documentación interactiva:** http://localhost:8000/docs (Swagger UI)

## Variables de entorno

Copiar `.env.example` a `.env` y configurar:

```env
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/optirutas

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Backend
DEBUG=False
BACKEND_URL=http://localhost:8000

# Frontend
VITE_API_BASE_URL=http://localhost:8000/api

# Google OR-Tools
SOLVER_TIME_LIMIT=30

# Email (opcional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-password
```

## Testing

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm run test
```

## Troubleshooting

### Error de conexión a PostgreSQL
```
Solución: Verificar que docker compose está corriendo
docker compose ps
docker compose logs postgres
```

### Puerto 8000 ya en uso
```bash
# Cambiar puerto en docker-compose.yml o
lsof -i :8000  # Encontrar proceso
kill -9 <PID>
```

### Frontend no se conecta al backend
- Verificar `VITE_API_BASE_URL` en `.env`
- Confirmar que backend está corriendo: `curl http://localhost:8000/health`
- Revisar CORS en `backend/app/main.py`

## Documentación adicional

- [API Docs Swagger](http://localhost:8000/docs) - Documentación interactiva
- [Backend README](./backend/README.md) - Detalles de configuración backend
- [Frontend README](./frontend/README.md) - Detalles de configuración frontend

## Contribución

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/xx`)
3. Commit tus cambios (`git commit -m 'Add some xx'`)
4. Push a la rama (`git push origin feature/xx`)
5. Abrir un Pull Request


