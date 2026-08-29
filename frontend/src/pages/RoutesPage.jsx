import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import StatCard from '../components/StatCard';

function getErrorMessage(err, fallback) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(' · ');
  return err?.response?.status === 403
    ? 'No tienes permisos para realizar esta acción.'
    : err?.response?.status === 500
    ? 'Error interno del servidor. Inténtalo de nuevo.'
    : fallback;
}

export default function RoutesPage() {
  const [routes, setRoutes] = useState([]);
  const [orders, setOrders] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);

  const [selectedOrders, setSelectedOrders] = useState([]);
  const [selectedVehicles, setSelectedVehicles] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const loadData = () => {
    setLoading(true);
    setLoadError(null);
    api
      .get('/routes/')
      .then((res) => setRoutes(res.data))
      .catch((err) => setLoadError(getErrorMessage(err, 'No se pudo cargar las rutas.')))
      .finally(() => setLoading(false));
    api
      .get('/orders/')
      .then((res) => setOrders(res.data))
      .catch((err) => setLoadError((prev) => prev || getErrorMessage(err, 'No se pudo cargar los pedidos.')));
    api
      .get('/vehicles/')
      .then((res) => setVehicles(res.data))
      .catch((err) => setLoadError((prev) => prev || getErrorMessage(err, 'No se pudo cargar los vehículos.')));
  };

  useEffect(loadData, []);

  const pendingOrders = orders.filter((o) => o.status === 'pendiente');

  const toggleOrder = (id) =>
    setSelectedOrders((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );

  const toggleVehicle = (id) =>
    setSelectedVehicles((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );

  const plateFor = (vehicleId) =>
    vehicles.find((v) => v.id === vehicleId)?.plate || `#${vehicleId}`;

  const handleOptimize = async () => {
    setError(null);
    setResult(null);
    setOptimizing(true);
    try {
      const res = await api.post('/routes/optimize', {
        order_ids: selectedOrders,
        vehicle_ids: selectedVehicles,
      });
      setResult(res.data);
      loadData();
    } catch (err) {
      setError(getErrorMessage(err, 'No se pudieron generar las rutas.'));
    } finally {
      setOptimizing(false);
    }
  };

  const metrics = result?.metrics;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">🗺️ Rutas optimizadas</h1>
        <Link
          to="/map"
          className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-xl transition"
        >
          📍 Ver en mapa
        </Link>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 text-red-700 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      {loadError && (
        <div className="mb-4 bg-yellow-50 text-yellow-800 text-sm rounded-lg p-3">
          {loadError}
        </div>
      )}

      {/* Selección pedidos y vehículos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">
            📦 Pedidos pendientes
            <span className="ml-2 text-sm font-normal text-gray-400">
              ({selectedOrders.length} seleccionados)
            </span>
          </h2>
          {pendingOrders.length === 0 ? (
            <p className="text-sm text-gray-400">No hay pedidos pendientes.</p>
          ) : (
            <div className="max-h-64 overflow-y-auto border border-gray-100 rounded-xl divide-y divide-gray-100">
              {pendingOrders.map((o) => (
                <label
                  key={o.id}
                  className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 cursor-pointer text-sm"
                >
                  <input
                    type="checkbox"
                    checked={selectedOrders.includes(o.id)}
                    onChange={() => toggleOrder(o.id)}
                    className="accent-brand-600"
                  />
                  <span className="font-medium">
                    #{o.id} · {o.client_name}
                  </span>
                  <span className="ml-auto text-gray-400">
                    {o.weight_kg} kg
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">
            🚛 Vehículos disponibles
            <span className="ml-2 text-sm font-normal text-gray-400">
              ({selectedVehicles.length} seleccionados)
            </span>
          </h2>
          {vehicles.filter((v) => v.is_active).length === 0 ? (
            <p className="text-sm text-gray-400">No hay vehículos activos.</p>
          ) : (
            <div className="max-h-64 overflow-y-auto border border-gray-100 rounded-xl divide-y divide-gray-100">
              {vehicles
                .filter((v) => v.is_active)
                .map((v) => (
                  <label
                    key={v.id}
                    className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 cursor-pointer text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={selectedVehicles.includes(v.id)}
                      onChange={() => toggleVehicle(v.id)}
                      className="accent-brand-600"
                    />
                    <span className="font-medium">{v.plate}</span>
                    <span className="ml-auto text-gray-400">
                      {v.capacity_kg} kg cap.
                    </span>
                  </label>
                ))}
            </div>
          )}
        </div>
      </div>

      <button
        onClick={handleOptimize}
        disabled={optimizing || selectedOrders.length === 0 || selectedVehicles.length === 0}
        className="w-full mb-8 py-3 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition shadow-lg shadow-brand-500/25"
      >
        {optimizing ? 'Generando rutas...' : '⚡ Generar rutas óptimas'}
      </button>

      {optimizing && (
        <div className="flex flex-col items-center justify-center py-12 text-gray-500">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-brand-500 border-t-transparent mb-4" />
          <p>Optimizando rutas... esto puede tardar unos segundos.</p>
        </div>
      )}

      {/* Métricas antes/después (OPT-17) */}
      {result?.success && metrics && !optimizing && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            📊 Comparación de la optimización
          </h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              icon="📏"
              label="Distancia antes"
              value={`${metrics.distance_before_km} km`}
            />
            <StatCard
              icon="🚀"
              label="Distancia después"
              value={`${metrics.distance_after_km} km`}
            />
            <StatCard
              icon="📉"
              label="Reducción"
              value={
                metrics.reduction_percentage > 0
                  ? `${metrics.reduction_percentage}%`
                  : 'Sin reducción'
              }
              highlight={metrics.reduction_percentage > 0}
            />
            <StatCard
              icon="💰"
              label="Ahorro estimado"
              value={`Q${metrics.estimated_fuel_savings_gtq}`}
            />
          </div>
        </div>
      )}

      {result?.success && !optimizing && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            🗺️ Rutas generadas
          </h2>
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
                <tr>
                  <th className="px-6 py-3 text-left">Ruta</th>
                  <th className="px-6 py-3 text-left">Vehículo</th>
                  <th className="px-6 py-3 text-center">Paradas</th>
                  <th className="px-6 py-3 text-right">Distancia (km)</th>
                  <th className="px-6 py-3 text-right">Peso (kg)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {result.routes.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50 transition">
                    <td className="px-6 py-4 font-medium">
                      {r.name || `Ruta #${r.id}`}
                    </td>
                    <td className="px-6 py-4">
                      {plateFor(r.vehicle_id)}
                      <span className="ml-1 text-gray-400 text-xs">
                        (#{r.vehicle_id})
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center">
                      {r.stops?.length ?? 0}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {r.total_distance_km ?? '—'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {r.total_weight_kg ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {result?.success === false && !optimizing && (
        <div className="mb-8 bg-yellow-50 text-yellow-800 text-sm rounded-lg p-4">
          <p className="font-semibold mb-1">⚠️ {result.message || 'No se pudieron asignar todos los pedidos.'}</p>
          <p>
            Pedidos sin asignar:{' '}
            {result.unassigned_order_ids?.length
              ? result.unassigned_order_ids.join(', ')
              : 'ninguno'}
          </p>
        </div>
      )}

      {result?.success && result?.unassigned_order_ids?.length > 0 && !optimizing && (
        <div className="mb-8 bg-yellow-50 text-yellow-800 text-sm rounded-lg p-4">
          ⚠️ {result.unassigned_order_ids.length} pedido(s) no pudieron asignarse
          por restricciones de capacidad o ventanas de tiempo:{' '}
          {result.unassigned_order_ids.join(', ')}
        </div>
      )}

      {/* Lista de rutas existentes */}
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        Rutas anteriores
      </h2>
      {loading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-brand-500 border-t-transparent" />
        </div>
      ) : routes.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          No hay rutas creadas. Usa el botón para optimizar una nueva ruta.
        </div>
      ) : (
        <div className="grid gap-4">
          {routes.map((r) => (
            <div
              key={r.id}
              className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-900">
                  {r.name || `Ruta #${r.id}`}
                </h3>
                <span className="px-3 py-1 rounded-full text-xs font-semibold bg-brand-100 text-brand-700">
                  {r.status}
                </span>
              </div>
              <div className="flex flex-wrap gap-6 mt-3 text-sm text-gray-500">
                <span>🚛 {plateFor(r.vehicle_id)}</span>
                <span>📏 {r.total_distance_km ?? '—'} km</span>
                <span>⏱ {r.total_duration_min ?? '—'} min</span>
                <span>⚖️ {r.total_weight_kg ?? '—'} kg</span>
                <span>📍 {r.stops?.length ?? 0} paradas</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
