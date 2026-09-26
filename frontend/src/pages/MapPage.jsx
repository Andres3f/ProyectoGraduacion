import { useState, useEffect } from 'react';
import api from '../services/api';
import MapView, { ROUTE_COLORS, RouteStepsPanel } from '../components/MapView';

/* Estados de ruta que ya no se dibujan en el mapa: una ruta completada ya fue
   entregada en su totalidad y una cancelada nunca se ejecutó, así que ninguna
   aporta información operativa en el mapa. */
const HIDDEN_ROUTE_STATUSES = ['completada', 'cancelada'];

/* Página del mapa: visualiza las rutas optimizadas y sus paradas sobre el mapa. */
export default function MapPage() {
  const [routes, setRoutes] = useState([]);
  const [orders, setOrders] = useState([]);
  const [depots, setDepots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [loadError, setLoadError] = useState(null);

  // Carga en paralelo rutas, pedidos y depósitos al montar la página.
  useEffect(() => {
    Promise.all([api.get('/routes/'), api.get('/orders/'), api.get('/depots/')])
      .then(([routesRes, ordersRes, depotsRes]) => {
        setRoutes(routesRes.data);
        setOrders(ordersRes.data);
        setDepots(depotsRes.data);
      })
      .catch((err) => {
        const detail = err?.response?.data?.detail;
        setLoadError(
          typeof detail === 'string' ? detail : 'No se pudo cargar el mapa.'
        );
      })
      .finally(() => setLoading(false));
  }, []);

  // El backend entrega en cada stop solo `order_id`. Combinamos con los
  // pedidos (que traen coordenadas y datos del cliente) para poder pintarlos.
  const orderById = {};
  orders.forEach((o) => (orderById[o.id] = o));

  // Enriquecimiento de rutas: se completan las paradas con datos del pedido
  // correspondiente (coordenadas, cliente, dirección y peso) para poder pintarlas.
  // Las rutas ya completadas (entregadas) o canceladas se excluyen del mapa.
  const enrichedRoutes = routes
    .filter((r) => !HIDDEN_ROUTE_STATUSES.includes(r.status))
    .map((r) => ({
      ...r,
      stops: (r.stops || [])
        .map((s) => {
          const o = orderById[s.order_id];
          return {
            ...s,
            lat: s.lat ?? o?.latitude ?? 0,
            lng: s.lng ?? o?.longitude ?? 0,
            client_name: s.client_name || o?.client_name || '',
            address: s.address || o?.address || '',
            weight_kg: s.weight_kg ?? o?.weight_kg ?? 0,
            notes: s.notes ?? o?.notes ?? '',
          };
        })
        .filter((s) => s.lat && s.lng),
    }))
    .filter((r) => r.stops.length > 0);

  // Asigna un color por ruta (reutilizando la paleta de colores del mapa).
  const vehicles = enrichedRoutes.reduce((acc, r, i) => {
    acc[r.id] = { color: ROUTE_COLORS[i % ROUTE_COLORS.length] };
    return acc;
  }, {});

  // Al seleccionar una parada, guarda el detalle para el panel lateral.
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

  {/* Contador total de puntos de entrega y rutas a mostrar */}
  const stopCount = enrichedRoutes.reduce((acc, r) => acc + r.stops.length, 0);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        📍 Mapa de rutas optimizadas
      </h1>

      {/* Aviso si falló la carga de datos del mapa */}
      {loadError && (
        <div className="mb-4 bg-yellow-50 text-yellow-800 text-sm rounded-lg p-3">
          {loadError}
        </div>
      )}

      {loading ? (
        /* Indicador de carga mientras se obtienen rutas y pedidos */
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-brand-500 border-t-transparent" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className={`${selected ? 'lg:col-span-2' : ''} bg-white rounded-2xl p-4 shadow-sm border border-gray-100`}>
            {/* Mapa con las rutas y panel de pasos de la ruta seleccionada */}
            <MapView routes={enrichedRoutes} depots={depots} onSelectStop={handleSelectStop} />
            <RouteStepsPanel route={selected?.route} />
            {/* Leyenda de colores por ruta */}
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
                <span>
                  {routes.length > 0
                    ? 'Todas las rutas ya fueron completadas o canceladas, por lo que no hay nada activo en el mapa.'
                    : 'No hay rutas con paradas para mostrar.'}
                </span>
              )}
            </div>
          </div>

          {/* Panel lateral con el detalle de la parada seleccionada */}
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
                {selected.stop.notes && (
                  <p className="flex items-start gap-1.5 bg-amber-50 border border-amber-200 text-amber-900 text-sm rounded-lg px-3 py-2">
                    <span aria-hidden>📝</span>
                    <span>
                      <span className="font-semibold">Nota: </span>
                      {selected.stop.notes}
                    </span>
                  </p>
                )}
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
