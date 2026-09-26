import { useEffect, useState } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import { useTheme } from '../context/ThemeContext';

// Coordenadas de referencia: centro de Jalapa para el mapa por defecto
const JALAPA_CENTER = [14.6339, -89.9886];

// Se usa el mismo proveedor de tiles en ambos temas (OpenStreetMap, sin API
// key). En modo oscuro las tiles se oscurecen con un filtro CSS aplicado
// únicamente a la capa de tiles: así los marcadores, las polilíneas de las
// rutas y los popups conservan sus colores originales.
const TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

// Alterna el filtro de la capa de tiles al cambiar de tema.
function DarkTileFilter() {
  const map = useMap();
  const { theme } = useTheme();
  useEffect(() => {
    const tilePane = map.getPane('tilePane');
    if (!tilePane) return;
    tilePane.classList.toggle('dark-map-tiles', theme === 'dark');
  }, [map, theme]);
  return null;
}

// Capa base del mapa + filtro de tema.
function ThemeTiles() {
  return (
    <>
      <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
      <DarkTileFilter />
    </>
  );
}

// Paleta de colores para diferenciar rutas/vehículos en el mapa
const COLORS = ['#2563eb', '#16a34a', '#dc2626', '#9333ea', '#ea580c'];

export const ROUTE_COLORS = COLORS;

// Crea un marcador circular numerado con el color del vehículo/ruta
function numberedIcon(number, color) {
  return L.divIcon({
    className: '',
    html: `<div style="width:30px;height:30px;border-radius:50%;background:${color};color:white;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,.3);">${number}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -15],
  });
}

// Ícono distintivo para los depósitos (punto de salida/regreso de las rutas).
const DEPOT_ICON = L.divIcon({
  className: '',
  html: '<div style="background:#1f2937;color:white;border-radius:6px;padding:4px 8px;font-size:11px;font-weight:600;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,.4);white-space:nowrap;">🏭 Depósito</div>',
  iconAnchor: [8, 20],
});

// Normaliza las coordenadas de una parada a [lat, lng]
// (soporta tanto `lat/lng` como `latitude/longitude`)
function stopCoords(s) {
  return [s.lat ?? s.latitude, s.lng ?? s.longitude];
}

// Verifica que una parada tenga coordenadas numéricas válidas
function stopCoordsWithin(s) {
  const [lat, lng] = stopCoords(s);
  return Number.isFinite(lat) && Number.isFinite(lng);
}

// Ajusta automáticamente el encuadre del mapa para que todas las
// paradas de las rutas y los depósitos queden visibles con un margen de 40px.
function FitBounds({ routes, depots }) {
  const map = useMap();
  const bounds = [
    ...routes.flatMap(
      (r) =>
        (r.stops ?? []).map(stopCoords).filter((c) => c.every(Number.isFinite))
    ),
    ...depots.map((d) => [d.latitude, d.longitude]),
  ];
  const key = bounds.flat().join(',');
  useEffect(() => {
    if (bounds.length > 1) {
      map.fitBounds(bounds, { padding: [40, 40] });
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }
  }, [map, key]);
  return null;
}

// Resuelve el depósito de una ruta: el asignado (route.depot_id) o, si no
// existe, el depósito predeterminado del sistema.
function depotForRoute(route, depots) {
  if (route?.depot_id) {
    const found = depots.find((d) => d.id === route.depot_id);
    if (found) return found;
  }
  return depots.find((d) => d.is_default) || null;
}

// Componente principal del mapa: dibuja rutas, paradas numeradas y pedidos sueltos.
export default function MapView({ routes = [], markers = [], depots = [], onSelectStop }) {
  const hasRouteStops = routes.some((r) => (r.stops?.length ?? 0) > 0);

  return (
    <MapContainer
      center={JALAPA_CENTER}
      zoom={13}
      className="h-[500px] rounded-xl shadow-lg z-0"
    >
      {/* Capa base del mapa, adaptada al tema */}
      <ThemeTiles />

      {(hasRouteStops || depots.length > 0) && (
        <FitBounds routes={routes} depots={depots} />
      )}

      {/* Depósitos: punto de partida de las rutas */}
      {depots.map((d) => (
        <Marker
          key={`depot-${d.id}`}
          position={[d.latitude, d.longitude]}
          icon={DEPOT_ICON}
        >
          <Popup>
            <strong>{d.name}</strong>
            {d.is_default && (
              <span className="block text-xs text-gray-500 dark:text-gray-400">predeterminado</span>
            )}
            {d.address && <p className="text-xs text-gray-500 dark:text-gray-400">{d.address}</p>}
          </Popup>
        </Marker>
      ))}

      {/* Polilíneas por vehículo */}
      {routes.map((route, i) => {
        const validStops = (route.stops ?? []).filter((s) =>
          stopCoordsWithin(s)
        );
        // Una sola parada también es una ruta válida: se dibuja el tramo
        // depósito -> punto de entrega (y el regreso en el fallback).
        if (validStops.length < 1) return null;

        if (route.route_geometry?.coordinates?.length > 1) {
          // Geometría real de ORS: GeoJSON LineString [[lng,lat], ...]
          const positions = route.route_geometry.coordinates.map(
            ([lng, lat]) => [lat, lng]
          );
          return (
            <Polyline
              key={`line-${route.id || i}`}
              positions={positions}
              pathOptions={{ color: COLORS[i % COLORS.length], weight: 4 }}
            />
          );
        }

        // Fallback: línea recta punteada desde el depósito de la ruta, por
        // cada parada y de regreso al depósito (aproximación).
        const depot = depotForRoute(route, depots);
        const depotPos = depot
          ? [[depot.latitude, depot.longitude]]
          : [];
        return (
          <Polyline
            key={`line-${route.id || i}`}
            positions={[
              ...depotPos,
              ...validStops.map(stopCoords),
              ...depotPos,
            ]}
            pathOptions={{
              color: COLORS[i % COLORS.length],
              weight: 4,
              dashArray: '6 6',
            }}
          />
        );
      })}

      {/* Paradas numeradas por vehículo */}
      {routes.map((route, i) =>
        (route.stops ?? [])
          .filter((s) => stopCoordsWithin(s))
          .map((stop, idx) => (
          <Marker
            key={`${route.id || i}-${indexKey(stop)}`}
            position={stopCoords(stop)}
            icon={numberedIcon(idx + 1, COLORS[i % COLORS.length])}
            eventHandlers={{
              // Al hacer clic en una parada informa al componente padre
              click: () => onSelectStop && onSelectStop(route, stop),
            }}
          >
            <Popup>
              <div className="flex items-center justify-between gap-2">
                <strong>{stop.client_name}</strong>
                {stop.eta && (
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {new Date(stop.eta).toLocaleTimeString('es-GT', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                )}
              </div>
              <p className="text-sm">Parada {idx + 1}</p>
              {stop.address && <p className="text-xs text-gray-500 dark:text-gray-400">{stop.address}</p>}
              {stop.weight_kg != null && (
                <p className="text-xs">⚖️ {stop.weight_kg} kg</p>
              )}
              {stop.notes && (
                <p className="mt-1 text-xs bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-200 rounded px-1.5 py-1">
                  📝 {stop.notes}
                </p>
              )}
            </Popup>
          </Marker>
        ))
      )}

      {/* Pedidos sueltos (opcional) */}
      {markers.map((m, i) => (
        <Marker key={`m-${i}`} position={[m.lat, m.lng]}>
          <Popup>
            <strong>{m.label || `Parada ${i + 1}`}</strong>
            {m.detail && <p className="text-sm">{m.detail}</p>}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}

// Genera una clave única para cada parada (por pedido, id o coordenadas)
function indexKey(s) {
  const [lat, lng] = stopCoords(s);
  return s.order_id ?? s.id ?? `${lat}-${lng}`;
}

// Panel colapsable con las instrucciones de manejo paso a paso de una ruta.
export function RouteStepsPanel({ route }) {
  const [open, setOpen] = useState(true);
  const steps = route?.steps || [];
  if (!steps.length) return null;

  return (
    <div className="mt-4 bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
      {/* Botón para expandir/colapsar las instrucciones */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
      >
        <span className="font-semibold text-gray-900 dark:text-gray-100">🧭 Instrucciones de manejo</span>
        <span className="text-gray-400 dark:text-gray-500">{open ? '▼' : '▲'}</span>
      </button>
      {open && (
        <ol className="divide-y divide-gray-100 dark:divide-gray-700 max-h-72 overflow-y-auto">
          {/* Cada indicación muestra distancia y duración estimada */}
          {steps.map((s, i) => (
            <li key={i} className="flex items-start gap-3 px-4 py-2.5 text-sm">
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300 text-xs font-bold shrink-0">
                {i + 1}
              </span>
              <div className="min-w-0">
                <p className="text-gray-800 dark:text-gray-100">{s.instruction}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500">
                  {(s.distance_m / 1000).toFixed(2)} km ·{' '}
                  {Math.round(s.duration_s / 60)} min
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
