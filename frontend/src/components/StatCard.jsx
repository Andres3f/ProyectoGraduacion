// Tarjeta reutilizable para mostrar una métrica o valor estadístico.
export default function StatCard({ label, value, icon, highlight }) {
  return (
    // Si `highlight` está activo, la tarjeta se resalta con el color de marca
    <div
      className={`bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-sm border ${
        highlight ? 'border-brand-500 bg-brand-50 dark:bg-gray-800' : 'border-gray-100 dark:border-gray-700'
      }`}
    >
      {icon && <div className="text-2xl mb-1">{icon}</div>}
      <p
        className={`text-xl font-bold ${
          highlight ? 'text-brand-700 dark:text-brand-300' : 'text-gray-900 dark:text-gray-100'
        }`}
      >
        {value}
      </p>
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
    </div>
  );
}
