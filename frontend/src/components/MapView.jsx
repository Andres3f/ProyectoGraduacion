import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';

const JALAPA_CENTER = [14.6347, -89.9889];

export default function MapView({ markers = [], route = [] }) {
  return (
    <MapContainer center={JALAPA_CENTER} zoom={13} className="h-[500px] rounded-xl shadow-lg">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {markers.map((m, i) => (
        <Marker key={i} position={[m.lat, m.lng]}>
          <Popup>
            <strong>{m.label || `Parada ${i + 1}`}</strong>
            {m.detail && <p className="text-sm">{m.detail}</p>}
          </Popup>
        </Marker>
      ))}
      {route.length > 1 && (
        <Polyline
          positions={route.map((r) => [r.lat, r.lng])}
          pathOptions={{ color: '#16a34a', weight: 4 }}
        />
      )}
    </MapContainer>
  );
}
