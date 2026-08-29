import { useState, useEffect } from 'react';
import api from '../services/api';

function getErrorMessage(err) {
  const detail = err?.response?.data?.detail;
  if (!detail) return 'Ocurrió un error inesperado';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(' · ');
  return JSON.stringify(detail);
}

const EMPTY = {
  plate: '',
  description: '',
  capacity_kg: '',
  capacity_m3: '',
  status: 'disponible',
  is_active: true,
  driver_id: '',
};

export default function VehiclesPage() {
  const [vehicles, setVehicles] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);

  const loadData = () => {
    setLoading(true);
    api
      .get('/vehicles/')
      .then((res) => setVehicles(res.data))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
    api
      .get('/users/')
      .then((res) => setDrivers(res.data.filter((u) => u.role === 'conductor')))
      .catch(() => {});
  };

  useEffect(loadData, []);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY);
    setError(null);
    setShowForm(true);
  };

  const openEdit = (v) => {
    setEditing(v);
    setForm({
      plate: v.plate,
      description: v.description || '',
      capacity_kg: v.capacity_kg,
      capacity_m3: v.capacity_m3,
      status: v.status,
      is_active: v.is_active,
      driver_id: v.driver_id ?? '',
    });
    setError(null);
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    const payload = {
      plate: form.plate,
      description: form.description || null,
      capacity_kg: Number(form.capacity_kg),
      capacity_m3: Number(form.capacity_m3 || 0),
      driver_id: form.driver_id ? Number(form.driver_id) : null,
    };
    try {
      if (editing) {
        await api.put(`/vehicles/${editing.id}`, {
          ...payload,
          status: form.status,
          is_active: form.is_active,
        });
      } else {
        await api.post('/vehicles/', payload);
      }
      setShowForm(false);
      loadData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (v) => {
    if (!window.confirm(`¿Eliminar el vehículo ${v.plate}?`)) return;
    setError(null);
    try {
      await api.delete(`/vehicles/${v.id}`);
      loadData();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const driverName = (id) =>
    drivers.find((d) => d.id === id)?.full_name || '—';

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">🚛 Vehículos</h1>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-xl transition shadow"
        >
          + Nuevo vehículo
        </button>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 text-red-700 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">
                {editing ? 'Editar vehículo' : 'Nuevo vehículo'}
              </h2>
              <button
                onClick={() => setShowForm(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Placa * (ej. C-4567)
                </label>
                <input
                  required
                  value={form.plate}
                  onChange={(e) => setForm({ ...form, plate: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                  placeholder="C-4567"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descripción
                </label>
                <input
                  value={form.description}
                  onChange={(e) =>
                    setForm({ ...form, description: e.target.value })
                  }
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                  placeholder="Camión 5 ton"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Capacidad (kg) *
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    required
                    value={form.capacity_kg}
                    onChange={(e) =>
                      setForm({ ...form, capacity_kg: e.target.value })
                    }
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Capacidad (m³)
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    value={form.capacity_m3}
                    onChange={(e) =>
                      setForm({ ...form, capacity_m3: e.target.value })
                    }
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Conductor asignado
                </label>
                <select
                  value={form.driver_id}
                  onChange={(e) =>
                    setForm({ ...form, driver_id: e.target.value })
                  }
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                >
                  <option value="">Sin conductor</option>
                  {drivers.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.full_name}
                    </option>
                  ))}
                </select>
              </div>
              {editing && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Estado
                    </label>
                    <select
                      value={form.status}
                      onChange={(e) =>
                        setForm({ ...form, status: e.target.value })
                      }
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                    >
                      <option value="disponible">Disponible</option>
                      <option value="en_ruta">En ruta</option>
                      <option value="mantenimiento">Mantenimiento</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Activo
                    </label>
                    <select
                      value={form.is_active}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          is_active: e.target.value === 'true',
                        })
                      }
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                    >
                      <option value="true">Sí</option>
                      <option value="false">No</option>
                    </select>
                  </div>
                </div>
              )}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-xl transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-sm font-medium rounded-xl transition shadow"
                >
                  {saving ? 'Guardando...' : editing ? 'Guardar cambios' : 'Crear'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-brand-500 border-t-transparent" />
        </div>
      ) : vehicles.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          No hay vehículos registrados
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
              <tr>
                <th className="px-6 py-3 text-left">Placa</th>
                <th className="px-6 py-3 text-left">Descripción</th>
                <th className="px-6 py-3 text-right">Capacidad</th>
                <th className="px-6 py-3 text-left">Conductor</th>
                <th className="px-6 py-3 text-center">Estado</th>
                <th className="px-6 py-3 text-center">Activo</th>
                <th className="px-6 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {vehicles.map((v) => (
                <tr key={v.id} className="hover:bg-gray-50 transition">
                  <td className="px-6 py-4 font-medium">{v.plate}</td>
                  <td className="px-6 py-4 text-gray-500">
                    {v.description || '—'}
                  </td>
                  <td className="px-6 py-4 text-right">
                    {v.capacity_kg} kg
                  </td>
                  <td className="px-6 py-4">{driverName(v.driver_id)}</td>
                  <td className="px-6 py-4 text-center">
                    <span className="inline-block px-2 py-1 rounded-full text-xs font-semibold bg-brand-100 text-brand-700">
                      {v.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-center">
                    {v.is_active ? (
                      <span className="text-green-600">●</span>
                    ) : (
                      <span className="text-red-400">●</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right space-x-2">
                    <button
                      onClick={() => openEdit(v)}
                      className="text-brand-600 hover:underline"
                    >
                      Editar
                    </button>
                    <button
                      onClick={() => handleDelete(v)}
                      className="text-red-500 hover:underline"
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
