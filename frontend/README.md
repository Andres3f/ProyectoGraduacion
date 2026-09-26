# Frontend — Optirutas Jalapa

SPA de React 18 + Vite con Tailwind CSS y Leaflet. Consume la API del backend a
través de un cliente Axios con `/api` como ruta base y proxy en desarrollo.

Para la vista general del proyecto, la instalación con Docker y los roles, ver
el [README principal](../README.md). La referencia de la API está en el
[README del backend](../backend/README.md).

## Requisitos

- **Node.js** 16+ (probado en 18) y **npm**
- El backend corriendo en `http://localhost:8000`

## Instalación y arranque

```bash
cd frontend
npm install
npm run dev
```

La app queda en http://localhost:5173. El proxy de `vite.config.js` redirige
`/api` al backend en el puerto 8000, por eso en desarrollo no hace falta
configurar ninguna URL de API.

## Scripts

| Script | Qué hace |
|--------|----------|
| `npm run dev` | Servidor de desarrollo de Vite con proxy a la API |
| `npm run build` | Compila a `dist/` |
| `npm run preview` | Sirve la build de producción localmente |

No hay script de pruebas automatizadas ni de lint en el frontend. La
verificación es `npm run build`, que además falla si algún componente no
compila.

## Estructura

```
frontend/
├── src/
│   ├── main.jsx              # Monta la app y aplica el tema antes del render
│   ├── App.jsx               # Rutas y selección de página inicial por rol
│   ├── index.css             # Tailwind + estilos de Leaflet y del tema
│   ├── context/
│   │   ├── AuthContext.jsx   # Sesión: login, logout, restauración del token
│   │   └── ThemeContext.jsx  # Tema claro/oscuro y persistencia
│   ├── components/
│   │   ├── Navbar.jsx        # Menú por rol y toggle de tema
│   │   ├── MapView.jsx       # Mapa Leaflet: rutas, paradas, depósitos
│   │   ├── StatCard.jsx      # Tarjeta de indicador
│   │   └── ProtectedRoute.jsx# Puerta de acceso por rol
│   ├── pages/                # Una por módulo (ver tabla de rutas)
│   ├── services/
│   │   └── api.js            # Instancia Axios + refresco de token
│   └── ...
├── scripts/                  # Utilidades de mantenimiento del tema
├── Dockerfile
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
└── package.json
```

## Páginas y acceso por rol

Cada ruta está detrás de un `ProtectedRoute` con los roles permitidos. El
menú del Navbar muestra únicamente los módulos del rol con sesión iniciada.

| Ruta | Página | Roles |
|------|--------|-------|
| `/login` | `LoginPage` | público |
| `/` | según rol: `DashboardPage`, `MapPage`, `MyRoutePage` o `ManagerDashboardPage` | todos |
| `/orders` | `OrdersPage` | admin, planificador |
| `/routes` | `RoutesPage` | admin, planificador |
| `/map` | `MapPage` | admin, planificador |
| `/vehicles` | `VehiclesPage` | admin |
| `/clients` | `ClientsPage` | admin |
| `/depots` | `DepotsPage` | admin |
| `/reports` | `ReportsPage` | admin |
| `/users/new` | `AddUserPage` | admin |
| `/my-route` | `MyRoutePage` | conductor |
| `/dashboard-gerente` | `ManagerDashboardPage` | gerente, admin |

## Sesión y cliente HTTP

`services/api.js` centraliza las peticiones:

- `baseURL: '/api'`. **No** agregues el prefijo `/api` a mano en las rutas de
  las páginas: produciría `/api/api/...` y un 404. Es el error que se corrigió
  en la exportación de reportes del dashboard gerencial.
- Un interceptor de petición agrega `Authorization: Bearer <token>` leyendo el
  token de `localStorage`.
- Un interceptor de respuesta renueva el access token ante un 401 usando el
  `refresh_token` y reintenta la petición original una sola vez. Si la renovación
  falla, limpia la sesión y manda a `/login`.

## Modo oscuro

El tema se activa con la clase `dark` en `<html>`, que es lo que espera
`darkMode: 'class'` de `tailwind.config.js`.

- `context/ThemeContext.jsx` expone `theme` y `toggleTheme()`. El valor elegido
  se guarda en `localStorage` bajo la clave `theme`.
- En la primera visita, cuando no hay preferencia guardada, se respeta
  `prefers-color-scheme` del sistema.
- `main.jsx` aplica la clase antes de montar React para que no se vea un
  destello del tema claro al recargar.
- `index.css` declara `color-scheme` para que los controles nativos (los
  `input type="time"` del formulario de pedidos, los `select` y las barras de
  scroll) también se pinten oscuros.

### Agregar vistas nuevas al tema

Las variantes `dark:` se aplicaron con un codemod, no a mano, para mantener la
tabla de traducción de colores consistente. Si agregas una pantalla:

```bash
# 1. Aplica la tabla de traducción a los .jsx de src/
node scripts/darkmode-codemod.mjs

# 2. Audita que no queden clases pegadas, faltantes ni duplicadas
node scripts/verify-darkmode.mjs

# 3. El script es idempotente: correrlo de nuevo no debe cambiar nada
```

Salida esperada del auditor:

```
pares base+dark correctos : N
variantes pegadas         : 0
clases base SIN dark      : 0
variantes dark duplicadas : 0
```

`scripts/undarkmode-codemod.mjs` hace lo contrario (quita las variantes `dark:`
y reconstruye el estado previo), por si necesitas revisar un diff separando el
tema de otra funcionalidad.

Los colores que ya funcionan igual en ambos temas (acentos de marca, los
`ring` de foco, los colores sólidos de los botones) están fuera de la tabla a
propósito: no se les añade variante.

## Mapa (Leaflet)

`components/MapView.jsx` dibuja rutas, paradas numeradas, pedidos sueltos y
depósitos.

- **Ttiles:** OpenStreetMap, sin API key. En modo oscuro no se cambia de
  proveedor (los basemaps de CartoDB piden clave) sino que se oscurece la capa
  de tiles con un filtro CSS aplicado **solo al pane de tiles**:
  ```css
  .dark-map-tiles {
    filter: invert(1) hue-rotate(180deg) brightness(0.95) contrast(0.9) saturate(0.75);
  }
  ```
  Aplicar el filtro al `.leaflet-container` completo invertiría también los
  marcadores y las polilíneas; por eso se hace sobre `tilePane` con
  `map.getPane('tilePane')`.
- Rutas de una sola parada: se dibujan igual, con el tramo depósito → entrega.
- Rutas `completada` y `cancelada`: el mapa del planificador las filtra para no
  ensuciar la planificación.
- El mapa del conductor recibe los depósitos para mostrar su punto de partida
  y de retorno.
- Popups, controles de zoom y barra de atribución: estilados en `index.css`.

## Convenciones

-Comentarios y nombres de identificadores en **español**, que es la convención
  que ya sigue el resto del proyecto.
- Tailwind para todo el estilo. Las clases de color siempre llevan su variante
  `dark:` correspondiente.
- Los servicios de API se consumen desde `services/api.js`; los `fetch` sueltos
  rompen el interceptor de token.

## Troubleshooting

### La app no carga datos / errores de red

El proxy `/api` del servidor de Vite apunta a `http://localhost:8000`. Si el
backend no está corriendo, todas las peticiones fallan. Comprueba:

```bash
curl http://localhost:8000/health
```

Si cambiaste el puerto del backend, actualiza el `target` de `vite.config.js`.

### El mapa no carga tiles

Verifica la conexión a `tile.openstreetmap.org`. Es la única dependencia
externa del mapa y no requiere clave ni registro. Si el mapa se ve blanco pero
el resto de la app funciona, casi siempre es eso.

### El mapa se ve con los marcadores invertidos en modo oscuro

El filtro de tiles no debe aplicarse al contenedor completo sino a `tilePane`.
Revisa que la clase siga en `.dark-map-tiles` sobre el pane, no sobre
`.leaflet-container`.

### Sale un destello blanco al recargar en modo oscuro

La clase `dark` debe aplicarse antes del render. Si alguien movió esa lógica
dentro de un `useEffect` de React, vuelve a ejecutarla en `main.jsx` antes de
`createRoot(...).render(...)`.

### Falla el build por clases de Tailwind

Si agregaste un archivo fuera de `src/` (por ejemplo uno generado), revisa el
array `content` de `tailwind.config.js`: solo escanea `./index.html` y
`./src/**/*.{js,jsx}`.

### Chunk grande en el build

Vite avisa cuando un bundle supera 500 kB (la librería de Leaflet + Chart.js).
No es un error. Si molesta, ajusta `build.chunkSizeWarningLimit` en
`vite.config.js` o divide con `manualChunks`.
