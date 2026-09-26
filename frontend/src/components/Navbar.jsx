import { useEffect, useState } from 'react';
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

// Estilo común de los enlaces: el activo se resalta con el color de marca y
// el resto en gris. Se comparte para que el menú de escritorio y el desplegable
// de móvil se vean idénticos.
function linkClasses(isActive) {
  return isActive
    ? 'bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300'
    : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700';
}

// Icono de tres líneas que abre el menú en pantallas pequeñas.
function MenuIcon() {
  return (
    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  );
}

// Icono de cruz que cierra el menú una vez abierto.
function CloseIcon() {
  return (
    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

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
  // Controla si el desplegable de navegación móvil está abierto
  const [open, setOpen] = useState(false);
  // Los enlaces del menú dependen del rol del usuario actual
  const links = MENU_BY_ROLE[user?.role] || [];

  // Cierra el menú móvil al cambiar de página para no tapar el contenido nuevo
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur border-b border-gray-200 dark:border-gray-700 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 flex items-center justify-between h-16">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 font-bold text-lg text-brand-700 dark:text-brand-300 dark:text-brand-400">
          🚛 Optirutas Jalapa
        </Link>

        {/* Links de escritorio: ocultos en móvil, donde manda el desplegable */}
        <div className="hidden md:flex items-center gap-1">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              // Resalta el enlace activo según la ruta actual
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${linkClasses(pathname === l.to)}`}
            >
              {l.label}
            </Link>
          ))}
        </div>

        {/* User */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Nombre y rol del usuario logueado (se ocultan en pantallas muy
              pequeñas para dejar sitio al botón del menú) */}
          <span className="hidden sm:inline text-sm text-gray-500 dark:text-gray-400">
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
          {/* Botón hamburguesa: sustituye a los links en móvil */}
          <button
            onClick={() => setOpen((v) => !v)}
            aria-label={open ? 'Cerrar menú' : 'Abrir menú'}
            aria-expanded={open}
            className="md:hidden p-2 -mr-2 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            {open ? <CloseIcon /> : <MenuIcon />}
          </button>
        </div>
      </div>

      {/* Menú desplegable de móvil: se superpone al contenido, por eso el
          <main> no necesita padding extra */}
      {open && (
        <div className="md:hidden border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-lg">
          <div className="px-2 py-2 flex flex-col">
            {links.map((l) => (
              <Link
                key={l.to}
                to={l.to}
                className={`px-3 py-3 rounded-lg text-sm font-medium transition-colors ${linkClasses(pathname === l.to)}`}
              >
                {l.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </nav>
  );
}
