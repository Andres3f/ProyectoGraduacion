import { useState, useEffect } from 'react';
import api from '../services/api';

export default function OrdersPage() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get('/orders/')
      .then((res) => setOrders(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">📦 Pedidos</h1>
        <button className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-xl transition shadow">
          + Nuevo pedido
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Cargando pedidos...</div>
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
