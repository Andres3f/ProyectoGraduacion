import { useState, useEffect } from 'react';
import api from '../services/api';

export default function RoutesPage() {
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get('/routes/')
      .then((res) => setRoutes(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">🗺️ Rutas optimizadas</h1>
        <button className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-xl transition shadow">
          + Optimizar nueva ruta
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Cargando rutas...</div>
      ) : routes.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
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
              <div className="flex gap-6 mt-3 text-sm text-gray-500">
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
