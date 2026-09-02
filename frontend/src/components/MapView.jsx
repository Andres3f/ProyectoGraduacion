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

const JALAPA_CENTER = [14.6339, -89.9886];

const COLORS = ['#2563eb', '#16a34a', '#dc2626', '#9333ea', '#ea580c'];

export const ROUTE_COLORS = COLORS;

function numberedIcon(number, color) {
  return L.divIcon({
    className: '',
    html: `<div style="width:30px;height:30px;border-radius:50%;background:${color};color:white;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,.3);">${number}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -15],
  });
}

function FitBounds({ routes }) {
  const map = useMap();
  const positions = routes.flatMap((r) => r.stops ?? []).flatMap((s) => [
    s.lat,
    s.lng,
  ]);
  const key = positions.join(',');
  useEffect(() => {
    if (positions.length > 1) {
      const bounds = routes
        .flatMap((r) => r.stops ?? [])
        .map((s) => [s.lat, s.lng]);
      map.fitBounds(bounds, { padding: [40, 40] });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, key]);
  return null;
}

export default function MapView({ routes = [], markers = [], onSelectStop }) {
  const hasRouteStops = routes.some((r) => (r.stops?.length ?? 0) > 1);

  return (
    <MapContainer
      center={JALAPA_CENTER}
      zoom={13}
      className="h-[500px] rounded-xl shadow-lg z-0"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {hasRouteStops && <FitBounds routes={routes} />}

      {/* Polilíneas por vehículo */}
      {routes.map((route, i) => {
        if (route.stops?.length < 2) return null;

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

        // Fallback: línea recta punteada entre paradas (aproximación).
        return (
          <Polyline
            key={`line-${route.id || i}`}
            positions={route.stops.map((s) => [s.lat, s.lng])}
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
        (route.stops ?? []).map((stop, idx) => (
          <Marker
            key={`${route.id || i}-${indexKey(stop)}`}
            position={[stop.lat, stop.lng]}
            icon={numberedIcon(idx + 1, COLORS[i % COLORS.length])}
            eventHandlers={{
              click: () => onSelectStop && onSelectStop(route, stop),
            }}
          >
            <Popup>
              <div className="flex items-center justify-between gap-2">
                <strong>{stop.client_name}</strong>
                {stop.eta && (
                  <span className="text-xs text-gray-500">
                    {new Date(stop.eta).toLocaleTimeString('es-GT', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                )}
              </div>
              <p className="text-sm">Parada {idx + 1}</p>
              {stop.address && <p className="text-xs text-gray-500">{stop.address}</p>}
              {stop.weight_kg != null && (
                <p className="text-xs">⚖️ {stop.weight_kg} kg</p>
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

function indexKey(s) {
  return s.order_id ?? s.id ?? `${s.lat}-${s.lng}`;
}

export function RouteStepsPanel({ route }) {
  const [open, setOpen] = useState(true);
  const steps = route?.steps || [];
  if (!steps.length) return null;

  return (
    <div className="mt-4 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
      >
        <span className="font-semibold text-gray-900">🧭 Instrucciones de manejo</span>
        <span className="text-gray-400">{open ? '▼' : '▲'}</span>
      </button>
      {open && (
        <ol className="divide-y divide-gray-100 max-h-72 overflow-y-auto">
          {steps.map((s, i) => (
            <li key={i} className="flex items-start gap-3 px-4 py-2.5 text-sm">
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-brand-100 text-brand-700 text-xs font-bold shrink-0">
                {i + 1}
              </span>
              <div className="min-w-0">
                <p className="text-gray-800">{s.instruction}</p>
                <p className="text-xs text-gray-400">
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
