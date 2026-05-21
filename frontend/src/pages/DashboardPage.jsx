import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const stats = [
  { label: 'Pedidos hoy', value: '—', icon: '📦' },
  { label: 'Rutas activas', value: '—', icon: '🗺️' },
  { label: 'Vehículos', value: '—', icon: '🚛' },
  { label: 'Entregas', value: '—', icon: '✅' },
];

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">
        ¡Hola, {user?.full_name}!
      </h1>
      <p className="text-gray-500 mb-8">Panel de control · Optirutas Jalapa</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        {stats.map((s) => (
          <div
            key={s.label}
            className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition"
          >
            <div className="text-3xl mb-2">{s.icon}</div>
            <p className="text-2xl font-bold text-gray-900">{s.value}</p>
            <p className="text-sm text-gray-500">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Acceso rápido
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
          <Link
            to="/orders"
            className="flex items-center gap-3 p-4 rounded-xl bg-brand-50 hover:bg-brand-100 transition"
          >
            <span className="text-2xl">📋</span>
            <span className="font-medium text-brand-700">Ver pedidos</span>
          </Link>
          <Link
            to="/routes"
            className="flex items-center gap-3 p-4 rounded-xl bg-brand-50 hover:bg-brand-100 transition"
          >
            <span className="text-2xl">🗺️</span>
            <span className="font-medium text-brand-700">Optimizar rutas</span>
          </Link>
          <Link
            to="/map"
            className="flex items-center gap-3 p-4 rounded-xl bg-brand-50 hover:bg-brand-100 transition"
          >
            <span className="text-2xl">📍</span>
            <span className="font-medium text-brand-700">Ver mapa</span>
          </Link>
        </div>

        {user?.role === 'admin' && (
          <Link
            to="/users/new"
            className="inline-flex items-center justify-center rounded-2xl bg-brand-600 px-6 py-3 text-white font-semibold hover:bg-brand-700 transition"
          >
            ➕ Agregar nuevo usuario
          </Link>
        )}
      </div>
    </div>
  );
}
