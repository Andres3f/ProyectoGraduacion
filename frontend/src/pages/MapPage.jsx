import { useState, useEffect } from 'react';
import api from '../services/api';
import MapView, { ROUTE_COLORS } from '../components/MapView';

export default function MapPage() {
  const [routes, setRoutes] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    Promise.all([api.get('/routes/'), api.get('/orders/')])
      .then(([routesRes, ordersRes]) => {
        setRoutes(routesRes.data);
        setOrders(ordersRes.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // El backend entrega en cada stop solo `order_id`. Combinamos con los
  // pedidos (que traen coordenadas y datos del cliente) para poder pintarlos.
  const orderById = {};
  orders.forEach((o) => (orderById[o.id] = o));

  const enrichedRoutes = routes
    .map((r) => ({
      ...r,
      stops: (r.stops || [])
        .map((s) => {
          const o = orderById[s.order_id];
          return o
            ? {
                ...s,
                lat: o.latitude,
                lng: o.longitude,
                client_name: o.client_name,
                address: o.address,
                weight_kg: o.weight_kg,
              }
            : null;
        })
        .filter(Boolean),
    }))
    .filter((r) => r.stops.length > 0);

  const vehicles = enrichedRoutes.reduce((acc, r, i) => {
    acc[r.id] = { color: ROUTE_COLORS[i % ROUTE_COLORS.length] };
    return acc;
  }, {});

  const handleSelectStop = (route, stop) => {
    setSelected({
      route,
      stop,
      color: vehicles[route.id]?.color,
      index:
        (route.stops || []).findIndex(
          (s) => (s.order_id ?? s.id) === (stop.order_id ?? stop.id)
        ) + 1,
    });
  };

  const stopCount = enrichedRoutes.reduce((acc, r) => acc + r.stops.length, 0);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        📍 Mapa de rutas optimizadas
      </h1>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-brand-500 border-t-transparent" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className={`${selected ? 'lg:col-span-2' : ''} bg-white rounded-2xl p-4 shadow-sm border border-gray-100`}>
            <MapView routes={enrichedRoutes} onSelectStop={handleSelectStop} />
            <div className="flex flex-wrap gap-3 mt-3 text-sm text-gray-500">
              {enrichedRoutes.map((r, i) => (
                <span key={r.id} className="flex items-center gap-1.5">
                  <span
                    className="inline-block w-3 h-3 rounded-full"
                    style={{ background: ROUTE_COLORS[i % ROUTE_COLORS.length] }}
                  />
                  {r.name || `Ruta #${r.id}`}
                </span>
              ))}
              {enrichedRoutes.length === 0 && (
                <span>No hay rutas con paradas para mostrar.</span>
              )}
            </div>
          </div>

          {selected && (
            <aside className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 h-fit">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold text-gray-900">Detalle de parada</h2>
                <button
                  onClick={() => setSelected(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <span
                    className="inline-flex items-center justify-center w-6 h-6 rounded-full text-white text-xs font-bold"
                    style={{ background: selected.color }}
                  >
                    {selected.index}
                  </span>
                  <span className="font-semibold text-gray-900">
                    {selected.stop.client_name}
                  </span>
                </div>
                <p className="text-gray-500">{selected.stop.address}</p>
                <div className="pt-2 border-t border-gray-100 space-y-1">
                  <p>
                    <span className="text-gray-400">Ruta:</span>{' '}
                    {selected.route.name || `#${selected.route.id}`} (parada{' '}
                    {selected.index} de {selected.route.stops.length})
                  </p>
                  {selected.stop.weight_kg != null && (
                    <p>
                      <span className="text-gray-400">Peso:</span>{' '}
                      {selected.stop.weight_kg} kg
                    </p>
                  )}
                  {selected.stop.eta && (
                    <p>
                      <span className="text-gray-400">ETA:</span>{' '}
                      {new Date(selected.stop.eta).toLocaleString()}
                    </p>
                  )}
                </div>
              </div>
            </aside>
          )}
        </div>
      )}

      <p className="text-sm text-gray-400 mt-3">
        Mostrando {stopCount} puntos de entrega en {enrichedRoutes.length}{' '}
        ruta(s) en Jalapa
      </p>
    </div>
  );
}
