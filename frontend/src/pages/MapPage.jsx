import { useState, useEffect } from 'react';
import api from '../services/api';
import MapView from '../components/MapView';

export default function MapPage() {
  const [orders, setOrders] = useState([]);

  useEffect(() => {
    api
      .get('/orders/')
      .then((res) => setOrders(res.data))
      .catch(() => {});
  }, []);

  const markers = orders.map((o) => ({
    lat: o.latitude,
    lng: o.longitude,
    label: o.client_name,
    detail: `${o.weight_kg} kg · ${o.address}`,
  }));

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">📍 Mapa de pedidos</h1>
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100">
        <MapView markers={markers} />
      </div>
      <p className="text-sm text-gray-400 mt-3">
        Mostrando {markers.length} puntos de entrega en Jalapa
      </p>
    </div>
  );
}
