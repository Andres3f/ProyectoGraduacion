import { useState, useEffect } from 'react';
import api from '../services/api';
import MapView from '../components/MapView';

function getErrorMessage(err) {
  const detail = err?.response?.data?.detail;
  if (!detail) return 'Ocurrió un error inesperado';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(' · ');
  return JSON.stringify(detail);
}

export default function MyRoutePage() {
  const [route, setRoute] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updating, setUpdating] = useState(null);

  const loadRoute = () => {
    setLoading(true);
    api
      .get('/routes/my-route')
      .then((res) => setRoute(res.data))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(loadRoute, []);

  const markStatus = async (stopId, status) => {
    setUpdating(stopId);
    setError(null);
    try {
      await api.put(`/route-stops/${stopId}/status`, null, {
        params: { status },
      });
      loadRoute();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setUpdating(null);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8 flex justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  if (error && !route) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">🚚 Mi Ruta</h1>
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 text-center">
          <p className="text-gray-500 mb-2">Aún no tienes una ruta asignada.</p>
          <p className="text-sm text-gray-400">
            Cuando el planificador genere una ruta para tu vehículo, aparecerá aquí.
          </p>
        </div>
      </div>
    );
  }

  const resolved = (route?.stops || []).every((s) =>
    ['entregado', 'fallido'].includes(s.status)
  );

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">🚚 Mi Ruta</h1>
          <p className="text-gray-500 text-sm mt-1">
            {route?.name || `Ruta #${route?.id}`} · {route?.stops?.length ?? 0}{' '}
            paradas · {route?.status}
          </p>
        </div>
        {resolved && (
          <span className="px-4 py-2 rounded-full bg-green-100 text-green-700 text-sm font-semibold">
            ✅ Ruta completada
          </span>
        )}
      </div>

      {error && (
        <div className="mb-4 bg-red-50 text-red-700 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      {/* Mapa pequeño con solo esta ruta */}
      {(route?.stops?.length ?? 0) > 0 && (
        <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 mb-6">
          <MapView routes={[{ ...route, stops: route.stops }]} />
        </div>
      )}

      {/* Lista de paradas en orden */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <ul className="divide-y divide-gray-100">
          {(route?.stops || []).map((stop, idx) => {
            const done = stop.status === 'entregado';
            const failed = stop.status === 'fallido';
            return (
              <li
                key={stop.id}
                className="flex flex-col sm:flex-row sm:items-center gap-3 px-4 sm:px-6 py-4"
              >
                <div className="flex items-center gap-3 sm:flex-1">
                  <span className="flex items-center justify-center w-8 h-8 rounded-full bg-brand-600 text-white text-sm font-bold shrink-0">
                    {idx + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="font-medium text-gray-900 truncate">
                      {stop.client_name}
                    </p>
                    <p className="text-sm text-gray-500 truncate">
                      {stop.address} · {stop.weight_kg} kg
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  {stop.status === 'pendiente' ? (
                    <>
                      <button
                        onClick={() => markStatus(stop.id, 'entregado')}
                        disabled={updating === stop.id}
                        className="px-3 py-1.5 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition"
                      >
                        {updating === stop.id ? '...' : '✅ Entregado'}
                      </button>
                      <button
                        onClick={() => markStatus(stop.id, 'fallido')}
                        disabled={updating === stop.id}
                        className="px-3 py-1.5 bg-red-500 hover:bg-red-600 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition"
                      >
                        {updating === stop.id ? '...' : '✖ Fallido'}
                      </button>
                    </>
                  ) : (
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        done
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {done ? '✅ Entregado' : '✖ Fallido'}
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
