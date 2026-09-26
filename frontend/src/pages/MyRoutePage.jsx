import { useState, useEffect } from 'react';
import api from '../services/api';
import MapView, { RouteStepsPanel } from '../components/MapView';

// Normaliza los errores del backend a un mensaje legible para el conductor.
function getErrorMessage(err) {
  const detail = err?.response?.data?.detail;
  if (!detail) return 'Ocurrió un error inesperado';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(' · ');
  return JSON.stringify(detail);
}

/* Página del conductor: muestra su ruta asignada y permite marcar el estado de cada parada. */
export default function MyRoutePage() {
  const [route, setRoute] = useState(null);
  const [depots, setDepots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [closing, setClosing] = useState(false);
  const [error, setError] = useState(null);
  const [updating, setUpdating] = useState(null);
  // El conductor confirma que volvió al depósito: la ruta pasa a completada y
  // con ella desaparece el mapa del trayecto de regreso.
  const confirmReturn = async () => {
    setClosing(true);
    setError(null);
    try {
      const res = await api.put(`/routes/${route.id}/complete`);
      setRoute(res.data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setClosing(false);
    }
  };


  // Obtiene la ruta asignada al conductor autenticado y el depósito principal
  // (necesario para dibujar el pin de salida y llegada).
  const loadRoute = () => {
    setLoading(true);
    Promise.all([api.get('/routes/my-route'), api.get('/depots/')])
      .then(([routeRes, depotsRes]) => {
        setRoute(routeRes.data);
        setDepots(depotsRes.data);
        setError(null);
      })
      .catch((err) => {
        // Un 404 aquí significa que el conductor no tiene ninguna ruta (ni
        // activa ni completada); no es un fallo de la pantalla.
        if (err?.response?.status === 404) {
          setRoute(null);
          setError(null);
        } else {
          setError(getErrorMessage(err));
        }
      })
      .finally(() => setLoading(false));
  };

  // Carga la ruta al montar el componente.
  useEffect(loadRoute, []);

  // Actualiza el estado de una parada (entregado/fallido) en el backend.
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

  {/* Renderizado condicional: spinner mientras se carga la ruta */}
  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8 flex justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  {/* Si no hay ruta asignada (o hay error al obtenerla), se muestra un aviso */}
  if (error && !route) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">🚚 Mi Ruta</h1>
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-sm border border-gray-100 dark:border-gray-700 text-center">
          <p className="text-gray-500 dark:text-gray-400 mb-2">Aún no tienes una ruta asignada.</p>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            Cuando el planificador genere una ruta para tu vehículo, aparecerá aquí.
          </p>
        </div>
      </div>
    );
  }

  // Indica si todas las paradas ya fueron resueltas (entregadas o fallidas).
  const stops = route?.stops || [];
  const resolved = stops.length > 0 && stops.every((s) =>
    ['entregado', 'fallido'].includes(s.status)
  );
  // El mapa solo se muestra mientras el viaje está en marcha: al confirmar el
  // regreso al depósito la ruta queda completada y el mapa desaparece.
  const finished = route?.status === 'completada';
  const showMap = stops.length > 0 && !finished;
  const deliveredCount = stops.filter((s) => s.status === 'entregado').length;
  const failedCount = stops.filter((s) => s.status === 'fallido').length;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">🚚 Mi Ruta</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
            {route?.name || `Ruta #${route?.id}`} · {stops.length}{' '}
            paradas · {route?.status}
          </p>
        </div>
        {/* Insignia de resumen: al terminar todas las paradas, o al cerrar la ruta */}
        {finished ? (
          <span className="px-4 py-2 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm font-semibold">
            🏁 Ruta finalizada
          </span>
        ) : resolved ? (
          <span className="px-4 py-2 rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400 text-sm font-semibold">
            ✅ Entregas completadas · regresando al depósito
          </span>
        ) : null}
      </div>

      {error && (
        <div className="mb-4 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-400 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      {/* Panel de ruta finalizada: el mapa ya se ocultó porque el conductor
          confirmó su regreso al depósito. */}
      {finished && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-sm border border-gray-100 dark:border-gray-700 text-center mb-6">
          <p className="text-5xl mb-3" aria-hidden>🏭</p>
          <p className="text-gray-900 dark:text-gray-100 font-semibold mb-1">
            Volviste al depósito. ¡Ruta cerrada!
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {deliveredCount} entrega(s) realizadas
            {failedCount > 0 && ` · ${failedCount} fallida(s)`}
            {route?.total_distance_km != null &&
              ` · ${route.total_distance_km} km recorridos`}
          </p>
        </div>
      )}

      {/* Botón de cierre: solo aparece cuando ya no quedan paradas por resolver,
          para que el mapa siga visible durante el trayecto de regreso. */}
      {resolved && !finished && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border border-gray-100 dark:border-gray-700 mb-6">
          <p className="text-gray-700 dark:text-gray-300 text-sm mb-3">
            Ya hiciste todas las entregas. Cuando regreses al depósito, confirma
            el retorno para cerrar la ruta y quitar el mapa.
          </p>
          <button
            onClick={confirmReturn}
            disabled={closing}
            className="px-4 py-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition"
          >
            {closing ? 'Cerrando...' : '🏠 Ya regresé al depósito'}
          </button>
        </div>
      )}

      {/* Mapa pequeño con solo esta ruta (se oculta al cerrar la ruta) */}
      {showMap && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm border border-gray-100 dark:border-gray-700 mb-6">
          <MapView routes={[{ ...route, stops }]} depots={depots} />
          <RouteStepsPanel route={route} />
        </div>
      )}

      {/* Lista de paradas en orden */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
        <ul className="divide-y divide-gray-100 dark:divide-gray-700">
          {stops.map((stop, idx) => {
            // Estado actual de la parada para decidir qué mostrar.
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
                    <p className="font-medium text-gray-900 dark:text-gray-100 truncate">
                      {stop.client_name}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                      {stop.address} · {stop.weight_kg} kg
                    </p>
                    {/* Notas de entrega: instrucciones que el conductor debe leer
                        antes de llegar al punto (acceso, contacto, Etc.). */}
                    {stop.notes && (
                      <p className="mt-2 flex items-start gap-1.5 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-sm rounded-lg px-3 py-2">
                        <span aria-hidden>📝</span>
                        <span className="min-w-0">
                          <span className="font-semibold">Nota: </span>
                          {stop.notes}
                        </span>
                      </p>
                    )}
                  </div>
                </div>

                {/* Botones para marcar parada como entregada o fallida; si ya fue resuelta se muestra el estado */}
                <div className="flex items-center gap-2 flex-wrap">
                  {stop.status === 'pendiente' ? (
                    <>
                      <button
                        onClick={() => markStatus(stop.id, 'entregado')}
                        disabled={updating === stop.id}
                        className="px-3 py-1.5 bg-green-600 hover:bg-green-700 dark:hover:bg-green-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition"
                      >
                        {updating === stop.id ? '...' : '✅ Entregado'}
                      </button>
                      <button
                        onClick={() => markStatus(stop.id, 'fallido')}
                        disabled={updating === stop.id}
                        className="px-3 py-1.5 bg-red-500 hover:bg-red-600 dark:hover:bg-red-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition"
                      >
                        {updating === stop.id ? '...' : '✖ Fallido'}
                      </button>
                    </>
                  ) : (
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        done
                          ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400'
                          : 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-400'
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
