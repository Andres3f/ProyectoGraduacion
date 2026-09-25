import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

// Ruta protegida: redirige a /login si no hay sesión y a "/" si el rol
// del usuario no está permitido. Renderiza el contenido anidado (Outlet).
export default function ProtectedRoute({ allowedRoles }) {
  const { user } = useAuth();

  // Sin usuario autenticado -> a la página de login
  if (!user) return <Navigate to="/login" replace />;

  // Rol del usuario no permitido en esta ruta -> a la raíz
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  // Sesión y rol válidos -> muestra la ruta hijo
  return <Outlet />;
}
