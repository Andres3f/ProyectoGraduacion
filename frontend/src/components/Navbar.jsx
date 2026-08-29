import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const MENU_BY_ROLE = {
  admin: [
    { to: '/', label: 'Dashboard' },
    { to: '/orders', label: 'Pedidos' },
    { to: '/vehicles', label: 'Vehículos' },
    { to: '/clients', label: 'Clientes' },
    { to: '/reports', label: 'Reportes' },
    { to: '/users/new', label: 'Usuarios' },
  ],
  planificador: [
    { to: '/', label: 'Dashboard' },
    { to: '/orders', label: 'Pedidos' },
    { to: '/routes', label: 'Rutas' },
    { to: '/map', label: 'Mapa' },
  ],
  conductor: [
    { to: '/my-route', label: 'Mi Ruta' },
  ],
  gerente: [
    { to: '/dashboard-gerente', label: 'KPIs' },
  ],
};

export default function Navbar() {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  const links = MENU_BY_ROLE[user?.role] || [];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 flex items-center justify-between h-16">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 font-bold text-lg text-brand-700">
          🚛 Optirutas Jalapa
        </Link>

        {/* Links */}
        <div className="hidden md:flex items-center gap-1">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                pathname === l.to
                  ? 'bg-brand-100 text-brand-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {l.label}
            </Link>
          ))}
        </div>

        {/* User */}
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">
            {user?.full_name}{' '}
            <span className="inline-block px-2 py-0.5 rounded-full bg-brand-100 text-brand-700 text-xs font-semibold">
              {user?.role}
            </span>
          </span>
          <button
            onClick={logout}
            className="text-sm text-red-500 hover:text-red-700 font-medium"
          >
            Salir
          </button>
        </div>
      </div>
    </nav>
  );
}
