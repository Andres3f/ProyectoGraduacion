import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

// Menú de navegación según el rol del usuario autenticado.
// Cada rol ve únicamente los módulos a los que tiene acceso.
const MENU_BY_ROLE = {
  admin: [
    { to: '/', label: 'Dashboard' },
    { to: '/orders', label: 'Pedidos' },
    { to: '/vehicles', label: 'Vehículos' },
    { to: '/clients', label: 'Clientes' },
    { to: '/depots', label: 'Depósitos' },
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

// Botón que alterna entre tema claro y oscuro; el icono refleja el tema
// activo (luna para ir a oscuro, sol para volver a claro).
function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      onClick={toggleTheme}
      title={isDark ? 'Activar tema claro' : 'Activar tema oscuro'}
      aria-label={isDark ? 'Activar tema claro' : 'Activar tema oscuro'}
      className="text-lg leading-none px-2 py-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 dark:text-gray-400 dark:hover:text-gray-100 dark:hover:bg-gray-700 transition-colors"
    >
      {isDark ? '☀️' : '🌙'}
    </button>
  );
}

// Barra de navegación superior: muestra logo, enlaces según rol, usuario y botón de salir.
export default function Navbar() {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  // Los enlaces del menú dependen del rol del usuario actual
  const links = MENU_BY_ROLE[user?.role] || [];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur border-b border-gray-200 dark:border-gray-700 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 flex items-center justify-between h-16">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 font-bold text-lg text-brand-700 dark:text-brand-300 dark:text-brand-400">
          🚛 Optirutas Jalapa
        </Link>

        {/* Links */}
        <div className="hidden md:flex items-center gap-1">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              // Resalta el enlace activo según la ruta actual
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                pathname === l.to
                  ? 'bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300 dark:bg-brand-900 dark:text-brand-300'
                  : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-700'
              }`}
            >
              {l.label}
            </Link>
          ))}
        </div>

        {/* User */}
        <div className="flex items-center gap-3">
          {/* Nombre y rol del usuario logueado */}
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {user?.full_name}{' '}
            <span className="inline-block px-2 py-0.5 rounded-full bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300 dark:bg-brand-900 dark:text-brand-300 text-xs font-semibold">
              {user?.role}
            </span>
          </span>
          <ThemeToggle />
          {/* Cierra la sesión del usuario */}
          <button
            onClick={logout}
            className="text-sm text-red-500 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 font-medium"
          >
            Salir
          </button>
        </div>
      </div>
    </nav>
  );
}
