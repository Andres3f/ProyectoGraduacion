import { useState, useEffect, useRef } from 'react';
import api from '../services/api';

function getErrorMessage(err, fallback) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && Array.isArray(detail.errors)) return detail.errors;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(' · ');
  return err?.response?.status === 403
    ? 'No tienes permisos para realizar esta acción.'
    : err?.response?.status === 500
    ? 'Error interno del servidor. Inténtalo de nuevo.'
    : fallback;
}

export default function OrdersPage() {
  const [orders, setOrders] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    client_id: '',
    weight_kg: '',
    volume_m3: '',
    time_window_start: '',
    time_window_end: '',
    service_time_min: '',
    notes: '',
  });

  const [uploadResult, setUploadResult] = useState(null);
  const [uploadErrors, setUploadErrors] = useState(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const loadData = () => {
    setLoading(true);
    api
      .get('/orders/')
      .then((res) => setOrders(res.data))
      .catch(() => setUploadErrors(['No se pudo cargar los pedidos']))
      .finally(() => setLoading(false));
    api
      .get('/clients/')
      .then((res) => setClients(res.data))
      .catch(() => {});
  };

  useEffect(loadData, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    setUploadErrors(null);
    try {
      await api.post('/orders/', {
        client_id: Number(form.client_id),
        weight_kg: Number(form.weight_kg),
        volume_m3: Number(form.volume_m3 || 0),
        time_window_start: form.time_window_start
          ? Number(form.time_window_start)
          : null,
        time_window_end: form.time_window_end ? Number(form.time_window_end) : null,
        service_time_min: form.service_time_min
          ? Number(form.service_time_min)
          : null,
        notes: form.notes || null,
      });
      setShowCreate(false);
      setForm({
        client_id: '',
        weight_kg: '',
        volume_m3: '',
        time_window_start: '',
        time_window_end: '',
        service_time_min: '',
        notes: '',
      });
      loadData();
    } catch (err) {
      setUploadErrors(getErrorMessage(err, 'No se pudo crear el pedido.'));
    } finally {
      setSaving(false);
    }
  };

  const handleUpload = async (file) => {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setUploading(true);
    setUploadResult(null);
    setUploadErrors(null);
    try {
      const res = await api.post('/orders/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setUploadResult(res.data);
      loadData();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const errs =
        detail && Array.isArray(detail.errors)
          ? detail.errors
          : getErrorMessage(err, ['Error al subir el archivo']);
      setUploadErrors(Array.isArray(errs) ? errs : [errs]);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-gray-900">📦 Pedidos</h1>
        <div className="flex gap-3">
          <label className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-xl cursor-pointer transition">
            ⬆️ Cargar CSV
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={(e) => handleUpload(e.target.files[0])}
            />
          </label>
          <button
            onClick={() => setShowCreate(true)}
            className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-xl transition shadow"
          >
            + Nuevo pedido
          </button>
        </div>
      </div>

      {uploading && (
        <div className="mb-4 bg-blue-50 text-blue-700 text-sm rounded-lg p-3">
          Subiendo archivo...
        </div>
      )}

      {uploadResult && (
        <div className="mb-4 bg-green-50 text-green-700 text-sm rounded-lg p-3">
          ✅ {uploadResult.created} pedido(s) creado(s) correctamente.
        </div>
      )}

      {uploadErrors && (
        <div className="mb-4 bg-red-50 text-red-700 text-sm rounded-lg p-3">
          <p className="font-semibold mb-1">No se pudo completar la operación:</p>
          {Array.isArray(uploadErrors) ? (
            <ul className="list-disc list-inside space-y-0.5">
              {uploadErrors.map((msg, i) => (
                <li key={i}>{msg}</li>
              ))}
            </ul>
          ) : (
            <p>{uploadErrors}</p>
          )}
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">Nuevo pedido</h2>
              <button
                onClick={() => setShowCreate(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Cliente *
                </label>
                <select
                  required
                  value={form.client_id}
                  onChange={(e) => setForm({ ...form, client_id: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                >
                  <option value="">Selecciona un cliente</option>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} — {c.zone || 'Jalapa'}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Peso (kg) *
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    required
                    value={form.weight_kg}
                    onChange={(e) =>
                      setForm({ ...form, weight_kg: e.target.value })
                    }
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                    placeholder="ej. 50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Volumen (m³)
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    value={form.volume_m3}
                    onChange={(e) =>
                      setForm({ ...form, volume_m3: e.target.value })
                    }
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                    placeholder="ej. 2"
                  />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Ventana inicio (min)
                  </label>
                  <input
                    type="number"
                    value={form.time_window_start}
                    onChange={(e) =>
                      setForm({ ...form, time_window_start: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Ventana fin (min)
                  </label>
                  <input
                    type="number"
                    value={form.time_window_end}
                    onChange={(e) =>
                      setForm({ ...form, time_window_end: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                    placeholder="480"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Servicio (min)
                  </label>
                  <input
                    type="number"
                    value={form.service_time_min}
                    onChange={(e) =>
                      setForm({ ...form, service_time_min: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                    placeholder="10"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notas
                </label>
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                  rows="2"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-xl transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-sm font-medium rounded-xl transition shadow"
                >
                  {saving ? 'Guardando...' : 'Crear pedido'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 flex justify-center">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-brand-500 border-t-transparent" />
        </div>
      ) : orders.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No hay pedidos registrados</div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
              <tr>
                <th className="px-6 py-3 text-left">ID</th>
                <th className="px-6 py-3 text-left">Cliente</th>
                <th className="px-6 py-3 text-left">Dirección</th>
                <th className="px-6 py-3 text-right">Peso (kg)</th>
                <th className="px-6 py-3 text-center">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {orders.map((o) => (
                <tr key={o.id} className="hover:bg-gray-50 transition">
                  <td className="px-6 py-4 font-medium">{o.id}</td>
                  <td className="px-6 py-4">{o.client_name}</td>
                  <td className="px-6 py-4 text-gray-500">{o.address}</td>
                  <td className="px-6 py-4 text-right">{o.weight_kg}</td>
                  <td className="px-6 py-4 text-center">
                    <span className="inline-block px-2 py-1 rounded-full text-xs font-semibold bg-brand-100 text-brand-700">
                      {o.status}
                    </span>
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
