export default function StatCard({ label, value, icon, highlight }) {
  return (
    <div
      className={`bg-white rounded-2xl p-5 shadow-sm border ${
        highlight ? 'border-brand-500 bg-brand-50' : 'border-gray-100'
      }`}
    >
      {icon && <div className="text-2xl mb-1">{icon}</div>}
      <p
        className={`text-xl font-bold ${
          highlight ? 'text-brand-700' : 'text-gray-900'
        }`}
      >
        {value}
      </p>
      <p className="text-sm text-gray-500">{label}</p>
    </div>
  );
}
