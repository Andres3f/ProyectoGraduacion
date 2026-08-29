import { useState, useEffect } from 'react';
import api from '../services/api';

function getErrorMessage(err) {
  const detail = err?.response?.data?.detail;
  if (!detail) return 'Ocurrió un error inesperado';
  if (typeof detail === 'string') return detail;
  return JSON.stringify(detail);
}

export default function ReportsPage() {
  const [routes, setRoutes] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.get('/routes/'), api.get('/vehicles/'), api.get('/users/')])
      .then(([routesRes, vehiclesRes, usersRes]) => {
        setRoutes(routesRes.data);
        setVehicles(vehiclesRes.data);
        setUsers(usersRes.data);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  const vehiclePlate = (id) =>
    vehicles.find((v) => v.id === id)?.plate || `#${id}`;
  const driverName = (id) =>
    users.find((u) => u.id === id)?.full_name || '—';

  const totalKm = routes.reduce((acc, r) => acc + (r.total_distance_km || 0), 0);
  const totalStops = routes.reduce((acc, r) => acc + (r.stops?.length || 0), 0);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">📊 Reportes globales</h1>
      <p className="text-gray-500 mb-6">Todas las rutas del sistema</p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <p className="text-2xl font-bold text-gray-900">{routes.length}</p>
          <p className="text-sm text-gray-500">Rutas totales</p>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <p className="text-2xl font-bold text-gray-900">{totalKm.toFixed(2)} km</p>
          <p className="text-sm text-gray-500">Distancia acumulada</p>
        </div>
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <p className="text-2xl font-bold text-gray-900">{totalStops}</p>
          <p className="text-sm text-gray-500">Paradas totales</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 text-red-700 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-brand-500 border-t-transparent" />
        </div>
      ) : routes.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          No hay rutas registradas
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
              <tr>
                <th className="px-6 py-3 text-left">Ruta</th>
                <th className="px-6 py-3 text-center">Estado</th>
                <th className="px-6 py-3 text-left">Vehículo</th>
                <th className="px-6 py-3 text-left">Conductor</th>
                <th className="px-6 py-3 text-right">Distancia (km)</th>
                <th className="px-6 py-3 text-center">Paradas</th>
                <th className="px-6 py-3 text-left">Fecha</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {routes.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50 transition">
                  <td className="px-6 py-4 font-medium">
                    {r.name || `Ruta #${r.id}`}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span className="inline-block px-2 py-1 rounded-full text-xs font-semibold bg-brand-100 text-brand-700">
                      {r.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">{vehiclePlate(r.vehicle_id)}</td>
                  <td className="px-6 py-4">{driverName(r.driver_id)}</td>
                  <td className="px-6 py-4 text-right">
                    {r.total_distance_km ?? '—'}
                  </td>
                  <td className="px-6 py-4 text-center">
                    {r.stops?.length ?? 0}
                  </td>
                  <td className="px-6 py-4 text-gray-500">
                    {r.optimized_at
                      ? new Date(r.optimized_at).toLocaleDateString()
                      : new Date(r.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
