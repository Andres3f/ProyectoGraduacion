import { useEffect, useMemo, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar, Line, Pie } from 'react-chartjs-2';
import StatCard from '../components/StatCard';
import api from '../services/api';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
);

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}
function weekAgoStr() {
  const d = new Date();
  d.setDate(d.getDate() - 6);
  return d.toISOString().slice(0, 10);
}

function getErrorMessage(err) {
  const detail = err?.response?.data?.detail;
  if (!detail) return 'Ocurrió un error inesperado';
  if (typeof detail === 'string') return detail;
  return JSON.stringify(detail);
}

export default function ManagerDashboardPage() {
  const [dateFrom, setDateFrom] = useState(weekAgoStr());
  const [dateTo, setDateTo] = useState(todayStr());
  const [kpis, setKpis] = useState(null);
  const [routes, setRoutes] = useState([]);
  const [timeseries, setTimeseries] = useState({ dates: [], series: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .get('/dashboard/kpis', { params: { date_from: dateFrom, date_to: dateTo } })
      .then((res) => {
        setKpis(res.data);
        // Se refetch la lista de rutas del rango para el gráfico antes/después.
        api
          .get('/routes/')
          .then((r) =>
            setRoutes(r.data.filter((route) => {
              const d = new Date(route.created_at).toISOString().slice(0, 10);
              return d >= dateFrom && d <= dateTo;
            })))
          .catch(() => setRoutes([]));
        // Serie temporal para el gráfico de línea de evolución de reducción.
        api
          .get('/dashboard/kpis/timeseries', {
            params: { date_from: dateFrom, date_to: dateTo },
          })
          .then((t) => setTimeseries(t.data))
          .catch(() => setTimeseries({ dates: [], series: [] }));
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [dateFrom, dateTo]);

  const download = (format) => {
    const url = `/api/dashboard/export?format=${format}&date_from=${dateFrom}&date_to=${dateTo}`;
    api
      .get(url, { responseType: 'blob' })
      .then((res) => {
        const blobUrl = URL.createObjectURL(res.data);
        const link = document.createElement('a');
        const disposition = res.headers['content-disposition'] || '';
        const match = /filename="?([^"]+)"?/.exec(disposition);
        link.href = blobUrl;
        link.download = match ? match[1] : `optirutas_${dateFrom}_${dateTo}.${format}`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(blobUrl);
      })
      .catch((err) => setError(getErrorMessage(err)));
  };

  const chartData = useMemo(() => {
    const labels = routes.map((r) => r.name || `Ruta #${r.id}`);
    const before = routes.map((r) => r.distance_before_km ?? 0);
    const after = routes.map((r) => r.distance_after_km ?? 0);
    return {
      labels,
      datasets: [
        {
          label: 'Antes (sin optimizar)',
          data: before,
          backgroundColor: 'rgba(239, 68, 68, 0.7)',
        },
        {
          label: 'Después (optimizada)',
          data: after,
          backgroundColor: 'rgba(22, 163, 74, 0.7)',
        },
      ],
    };
  }, [routes]);

  const lineChartData = useMemo(() => {
    const dates = timeseries.dates || [];
    const reductionPcts = (timeseries.series || []).map(
      (s) => s.reduction_percentage ?? 0,
    );
    return {
      labels: dates,
      datasets: [
        {
          label: '% de reducción',
          data: reductionPcts,
          borderColor: 'rgba(22, 163, 74, 1)',
          backgroundColor: 'rgba(22, 163, 74, 0.15)',
          fill: true,
          tension: 0.3,
        },
      ],
    };
  }, [timeseries]);

  const pieChartData = useMemo(() => {
    const dist = kpis?.delivery_distribution ?? {
      entregado: 0,
      fallido: 0,
      pendiente: 0,
    };
    return {
      labels: ['Entregado', 'Fallido', 'Pendiente'],
      datasets: [
        {
          data: [dist.entregado ?? 0, dist.fallido ?? 0, dist.pendiente ?? 0],
          backgroundColor: [
            'rgba(22, 163, 74, 0.8)',
            'rgba(239, 68, 68, 0.8)',
            'rgba(234, 179, 8, 0.8)',
          ],
        },
      ],
    };
  }, [kpis]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">📈 Dashboard del Gerente</h1>
      <p className="text-gray-500 mb-6">
        Indicadores clave del negocio en un rango de fechas
      </p>

      <div className="flex flex-wrap items-end gap-3 mb-8">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Desde</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Hasta</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div className="flex gap-2 ml-auto">
          <button
            onClick={() => download('xlsx')}
            className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700"
          >
            Descargar Excel
          </button>
          <button
            onClick={() => download('pdf')}
            className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-semibold hover:bg-red-700"
          >
            Descargar PDF
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 text-red-700 text-sm rounded-lg p-3">{error}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-brand-500 border-t-transparent" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            <StatCard
              label="Distancia total (km)"
              value={kpis?.total_distance_km ?? 0}
              icon="🗺️"
              highlight
            />
            <StatCard
              label="Rutas totales"
              value={kpis?.total_routes ?? 0}
              icon="🚚"
            />
            <StatCard
              label="Tasa de entrega (%)"
              value={kpis ? `${kpis.delivery_rate_pct}%` : '0%'}
              icon="✅"
            />
            <StatCard
              label="A tiempo (%)"
              value={kpis ? `${kpis.on_time_rate_pct}%` : '0%'}
              icon="⏱️"
            />
            <StatCard
              label="Km promedio / ruta"
              value={kpis?.avg_km_per_route ?? 0}
              icon="📏"
            />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
            <StatCard
              label="Combustible ahorrado (l)"
              value={kpis?.fuel_liters_saved ?? 0}
              icon="⛽"
            />
            <StatCard
              label="Costo combustible ahorrado (Q)"
              value={kpis ? `Q${kpis.fuel_cost_saved_gtq}` : 'Q0'}
              icon="💰"
            />
            <StatCard
              label="Costo operativo ahorrado (Q)"
              value={kpis ? `Q${kpis.operational_cost_saved_gtq}` : 'Q0'}
              icon="🏦"
            />
          </div>

          <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Distancia antes vs después por ruta (km)
            </h2>
            {routes.length === 0 ? (
              <p className="text-gray-400 text-sm">No hay rutas en el rango seleccionado</p>
            ) : (
              <Bar
                data={chartData}
                options={{
                  responsive: true,
                  plugins: {
                    legend: { position: 'top' },
                  },
                  scales: {
                    y: { beginAtZero: true },
                  },
                }}
              />
            )}
          </div>

          <div className="grid md:grid-cols-2 gap-6 mt-6">
            <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Evolución de la reducción (%)
              </h2>
              {timeseries.dates.length === 0 ? (
                <p className="text-gray-400 text-sm">
                  No hay datos en el rango seleccionado
                </p>
              ) : (
                <Line
                  data={lineChartData}
                  options={{
                    responsive: true,
                    plugins: { legend: { position: 'top' } },
                    scales: { y: { beginAtZero: true } },
                  }}
                />
              )}
            </div>

            <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Distribución de entregas
              </h2>
              {(kpis?.delivery_distribution?.entregado ?? 0) +
                (kpis?.delivery_distribution?.fallido ?? 0) +
                (kpis?.delivery_distribution?.pendiente ?? 0) ===
              0 ? (
                <p className="text-gray-400 text-sm">
                  No hay paradas en el rango seleccionado
                </p>
              ) : (
                <Pie
                  data={pieChartData}
                  options={{
                    responsive: true,
                    plugins: { legend: { position: 'bottom' } },
                  }}
                />
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
