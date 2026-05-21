import { useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const roles = [
  { value: 'admin', label: 'Administrador' },
  { value: 'planificador', label: 'Planificador' },
  { value: 'conductor', label: 'Conductor' },
  { value: 'gerente', label: 'Gerente' },
];

export default function AddUserPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: '',
    full_name: '',
    password: '',
    role: 'planificador',
  });
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [loading, setLoading] = useState(false);

  if (user?.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

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
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Crear nuevo usuario</h1>
      <p className="text-gray-500 mb-6">Solo los administradores pueden crear nuevas cuentas.</p>

      <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Correo electrónico</label>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              required
              className="w-full rounded-2xl border border-gray-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Nombre completo</label>
            <input
              type="text"
              name="full_name"
              value={form.full_name}
              onChange={handleChange}
              required
              className="w-full rounded-2xl border border-gray-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Contraseña</label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              required
              minLength={6}
              className="w-full rounded-2xl border border-gray-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Rol</label>
            <select
              name="role"
              value={form.role}
              onChange={handleChange}
              className="w-full rounded-2xl border border-gray-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand-400"
            >
              {roles.map((role) => (
                <option key={role.value} value={role.value}>
                  {role.label}
                </option>
              ))}
            </select>
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}
          {success && <p className="text-sm text-green-600">{success}</p>}

          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center rounded-2xl bg-brand-600 px-6 py-3 text-white font-semibold hover:bg-brand-700 transition disabled:cursor-not-allowed disabled:bg-brand-300"
          >
            {loading ? 'Creando...' : 'Crear usuario'}
          </button>
        </form>
      </div>
    </div>
  );
}
