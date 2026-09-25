import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import api from '../services/api';

// Normaliza los errores del backend a un mensaje legible para el usuario.
function getErrorMessage(err) {
  const detail = err?.response?.data?.detail;
  if (!detail) return 'Ocurrió un error inesperado';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(' · ');
  return JSON.stringify(detail);
}

// Valores por defecto del formulario de depósito (creación/edición).
const EMPTY = {
  name: '',
  address: '',
  latitude: '',
  longitude: '',
};

// Icono del marcador de confirmación en el mapa (estilo patio/almacén).
const PIN_ICON = L.divIcon({
  className: '',
  html: '<div style="width:26px;height:26px;border-radius:50%;background:#333;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;font-size:13px;">🏭</div>',
  iconSize: [26, 26],
  iconAnchor: [13, 13],
});

// Componente auxiliar: un clic sobre el mapa mueve el marcador ahí.
function MapClickPlacer({ onPick }) {
  useMapEvents({
    click: (e) => onPick(e.latlng.lat, e.latlng.lng),
  });
  return null;
}

/* Página de gestión de depósitos (punto de partida de los camiones).
   Solo Admin: fija el punto de partida haciendo clic en el mapa. */
export default function DepotsPage() {
  // Lista de depósitos y estados de carga/error.
  const [depots, setDepots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Estado del formulario (modal) de creación/edición.
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);

  // Estado del geocoding: resultados candidatos y banderas de búsqueda.
  const [geocodeResults, setGeocodeResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);

  // Obtiene la lista de depósitos desde el backend.
  const loadData = () => {
    setLoading(true);
    api
      .get('/depots/')
      .then((res) => setDepots(res.data))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  // Carga inicial de la lista de depósitos al montar el componente.
  useEffect(loadData, []);

  // Abre el formulario en modo creación con el depósito vacío.
  const openCreate = () => {
    setEditing(null);
    setForm({ ...EMPTY });
    setGeocodeResults([]);
    setSearched(false);
    setError(null);
    setShowForm(true);
  };

  // Abre el formulario en modo edición precargando los datos del depósito.
  const openEdit = (d) => {
    setEditing(d);
    setForm({
      name: d.name,
      address: d.address || '',
      latitude: d.latitude,
      longitude: d.longitude,
    });
    setGeocodeResults([]);
    setSearched(false);
    setError(null);
    setShowForm(true);
  };

  // Busca candidatos de coordenadas para la dirección escrita (geocoding).
  const handleSearchAddress = async () => {
    if (!form.address || form.address.trim().length < 5) return;
    setSearching(true);
    setError(null);
    try {
      const res = await api.get('/geocode', {
        params: { q: form.address.trim() },
      });
      setGeocodeResults(res.data.results);
      setSearched(true);
      // Preselecciona el mejor candidato, pero el usuario debe confirmarlo
      // visualmente en el mapa antes de guardar.
      if (res.data.results.length > 0) {
        const best = res.data.results[0];
        setForm((f) => ({ ...f, latitude: best.lat, longitude: best.lng }));
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSearching(false);
    }
  };

  // Coloca las coordenadas en el formulario (clic en un candidato o en el mapa).
  const pickCoords = (lat, lng) =>
    setForm((f) => ({ ...f, latitude: lat, longitude: lng }));

  // Envía el formulario: crea o actualiza el depósito según el modo actual.
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    const payload = {
      name: form.name,
      address: form.address || null,
      latitude: Number(form.latitude),
      longitude: Number(form.longitude),
    };
    try {
      if (editing) {
        await api.put(`/depots/${editing.id}`, payload);
      } else {
        await api.post('/depots/', payload);
      }
      setShowForm(false);
      loadData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  // Marca un depósito como predeterminado (único).
  const handleSetDefault = async (d) => {
    setError(null);
    try {
      await api.put(`/depots/${d.id}/set-default`);
      loadData();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  // Elimina el depósito tras confirmación del usuario.
  const handleDelete = async (d) => {
    if (!window.confirm(`¿Eliminar el depósito ${d.name}?`)) return;
    setError(null);
    try {
      await api.delete(`/depots/${d.id}`);
      loadData();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">🏭 Depósitos</h1>
          <p className="text-sm text-gray-500 mt-1">
            Punto de partida de los camiones para las rutas de reparto.
          </p>
        </div>
        {/* Botón para registrar un nuevo depósito */}
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-xl transition shadow"
        >
          + Nuevo depósito
        </button>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 text-red-700 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          {/* Modal con el formulario de creación/edición de depósito */}
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">
                {editing ? 'Editar depósito' : 'Nuevo depósito'}
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
                  Nombre *
                </label>
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                  placeholder="Ej. Patio Principal Jalapa"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Dirección
                </label>
                {/* Dirección + botón de geocoding para obtener coordenadas */}
                <div className="flex gap-2">
                  <input
                    value={form.address}
                    onChange={(e) => {
                      setForm({ ...form, address: e.target.value });
                      // La dirección cambió: los resultados previos ya no aplican.
                      setGeocodeResults([]);
                      setSearched(false);
                    }}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none"
                    placeholder="1 Avenida 9-28, Zona 1, Jalapa"
                  />
                  <button
                    type="button"
                    onClick={handleSearchAddress}
                    disabled={searching || form.address.trim().length < 5}
                    className="px-4 py-2.5 bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed text-gray-700 text-sm font-medium rounded-xl transition shrink-0"
                  >
                    {searching ? 'Buscando...' : '📍 Buscar en el mapa'}
                  </button>
                </div>

                {/* Candidatos sugeridos por el geocodificador */}
                {geocodeResults.length > 0 && (
                  <div className="mt-2 text-sm border rounded-xl p-2 bg-gray-50">
                    <p className="font-medium mb-1 text-gray-600">
                      Se encontraron varias coincidencias, elige la correcta:
                    </p>
                    {geocodeResults.map((r, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => pickCoords(r.lat, r.lng)}
                        className="block text-left w-full py-1 px-1 hover:bg-gray-100 rounded"
                      >
                        {r.label}
                        {r.confidence != null &&
                          ` (${Math.round(r.confidence * 100)}% confianza)`}
                      </button>
                    ))}
                  </div>
                )}
                {/* Sin resultados: se invita a ubicar el punto manualmente */}
                {searched && geocodeResults.length === 0 && (
                  <p className="mt-2 text-xs text-amber-600">
                    No se encontraron resultados. Haz clic en el mapa para ubicar
                    el punto manualmente.
                  </p>
                )}
              </div>
              <div>
                {/* Mapa de confirmación: SIEMPRE visible en el formulario. El
                    usuario confirma (clic/arrastrar) antes de poder guardar. */}
                <div className="mt-1">
                  <p className="block text-sm font-medium text-gray-700 mb-1">
                    Ubicación del depósito *
                  </p>
                  <MapContainer
                    center={
                      form.latitude
                        ? [Number(form.latitude), Number(form.longitude)]
                        : [14.6339, -89.9886]
                    }
                    zoom={16}
                    style={{ height: 260, minHeight: 0 }}
                    className="rounded-xl z-0"
                  >
                    <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                    <MapClickPlacer onPick={pickCoords} />
                    {form.latitude && form.longitude && (
                      <Marker
                        position={[
                          Number(form.latitude),
                          Number(form.longitude),
                        ]}
                        icon={PIN_ICON}
                        draggable
                        eventHandlers={{
                          dragend: (e) => {
                            const { lat, lng } = e.target.getLatLng();
                            pickCoords(lat, lng);
                          },
                        }}
                      />
                    )}
                  </MapContainer>
                  <p className="text-xs text-gray-500 mt-1">
                    Arrastra el marcador o haz clic en el mapa para fijar la
                    ubicación exacta.
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Latitud *
                  </label>
                  <input
                    type="number"
                    step="any"
                    readOnly
                    value={form.latitude}
                    aria-label="Latitud (autocompletada desde el mapa)"
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl bg-gray-50 text-gray-600 outline-none"
                    placeholder="14.6339"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Longitud *
                  </label>
                  <input
                    type="number"
                    step="any"
                    readOnly
                    value={form.longitude}
                    aria-label="Longitud (autocompletada desde el mapa)"
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl bg-gray-50 text-gray-600 outline-none"
                    placeholder="-89.9886"
                  />
                </div>
              </div>
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
                  // Obliga a fijar/confirmar la ubicación en el mapa antes de guardar.
                  disabled={!form.latitude || !form.longitude || saving}
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
        /* Indicador de carga mientras se obtienen los depósitos */
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-brand-500 border-t-transparent" />
        </div>
      ) : depots.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          No hay depósitos registrados
        </div>
      ) : (
        /* Tabla con la lista de depósitos y sus acciones */
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
              <tr>
                <th className="px-6 py-3 text-left">Nombre</th>
                <th className="px-6 py-3 text-left">Dirección</th>
                <th className="px-6 py-3 text-right">Lat</th>
                <th className="px-6 py-3 text-right">Lng</th>
                <th className="px-6 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {depots.map((d) => (
                <tr
                  key={d.id}
                  className={`hover:bg-gray-50 transition ${
                    d.is_default ? 'bg-brand-50/50' : ''
                  }`}
                >
                  <td className="px-6 py-4 font-medium">
                    {d.name}
                    {d.is_default && (
                      <span className="ml-2 inline-block px-2 py-0.5 rounded-full bg-brand-600 text-white text-xs font-semibold">
                        Predeterminado
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-gray-500">{d.address || '—'}</td>
                  <td className="px-6 py-4 text-right">{d.latitude}</td>
                  <td className="px-6 py-4 text-right">{d.longitude}</td>
                  <td className="px-6 py-4 text-right space-x-2">
                    <button
                      onClick={() => handleSetDefault(d)}
                      disabled={d.is_default}
                      className="text-brand-600 hover:underline disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      Usar como predeterminado
                    </button>
                    <button
                      onClick={() => openEdit(d)}
                      className="text-brand-600 hover:underline"
                    >
                      Editar
                    </button>
                    <button
                      onClick={() => handleDelete(d)}
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