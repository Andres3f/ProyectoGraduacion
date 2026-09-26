import { useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

// Lista de roles disponibles para las nuevas cuentas del sistema.
const roles = [
  { value: 'admin', label: 'Administrador' },
  { value: 'planificador', label: 'Planificador' },
  { value: 'conductor', label: 'Conductor' },
  { value: 'gerente', label: 'Gerente' },
];

/* Página para crear nuevos usuarios del sistema (acceso restringido a administradores). */
export default function AddUserPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  // Estado del formulario con los datos del nuevo usuario (rol por defecto: planificador).
  const [form, setForm] = useState({
    email: '',
    full_name: '',
    password: '',
    role: 'planificador',
  });
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [loading, setLoading] = useState(false);

  // Guard: si el usuario actual no es admin, redirigir al inicio.
  if (user?.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  // Actualiza un campo del formulario a partir del evento del input.
  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  // Envía los datos del formulario al backend para crear el usuario.
  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      await api.post('/users', form);
      setSuccess('Usuario creado correctamente.');
      setTimeout(() => navigate('/'), 1200);
    } catch (err) {
      // Extrae el mensaje de error del backend (puede llegar como string o lista).
      const data = err?.response?.data;
      let message = 'No se pudo crear el usuario.';

      if (data?.detail) {
        if (Array.isArray(data.detail)) {
          message = data.detail
            .map((item) => item.msg || JSON.stringify(item))
            .join(' ');
        } else if (typeof data.detail === 'string') {
          message = data.detail;
        } else {
          message = JSON.stringify(data.detail);
        }
      } else if (err?.message) {
        message = err.message;
      }

      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">Crear nuevo usuario</h1>
      <p className="text-gray-500 dark:text-gray-400 mb-6">Solo los administradores pueden crear nuevas cuentas.</p>

      <div className="bg-white dark:bg-gray-800 p-6 rounded-3xl shadow-sm border border-gray-100 dark:border-gray-700">
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Campo de correo electrónico del nuevo usuario */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Correo electrónico</label>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              required
              className="w-full rounded-2xl border border-gray-200 dark:border-gray-700 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>

          {/* Campo de nombre completo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Nombre completo</label>
            <input
              type="text"
              name="full_name"
              value={form.full_name}
              onChange={handleChange}
              required
              className="w-full rounded-2xl border border-gray-200 dark:border-gray-700 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>

          {/* Campo de contraseña con longitud mínima de 6 caracteres */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Contraseña</label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              required
              minLength={6}
              className="w-full rounded-2xl border border-gray-200 dark:border-gray-700 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>

          {/* Selector de rol del nuevo usuario */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Rol</label>
            <select
              name="role"
              value={form.role}
              onChange={handleChange}
              className="w-full rounded-2xl border border-gray-200 dark:border-gray-700 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand-400"
            >
              {roles.map((role) => (
                <option key={role.value} value={role.value}>
                  {role.label}
                </option>
              ))}
            </select>
          </div>

          {/* Mensajes de error y éxito de la operación */}
          {error && <p className="text-sm text-red-500 dark:text-red-400">{error}</p>}
          {success && <p className="text-sm text-green-600 dark:text-green-400">{success}</p>}

          {/* Botón de envío; se deshabilita mientras se está guardando */}
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center rounded-2xl bg-brand-600 px-6 py-3 text-white font-semibold hover:bg-brand-700 dark:hover:bg-brand-500 transition disabled:cursor-not-allowed disabled:bg-brand-300"
          >
            {loading ? 'Creando...' : 'Crear usuario'}
          </button>
        </form>
      </div>
    </div>
  );
}
