import { useLocation } from 'react-router-dom';

export default function PlaceholderPage({ title }) {
  const { pathname } = useLocation();

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">
        {title || 'Página en construcción'}
      </h1>
      <p className="text-gray-500">
        Esta sección ({pathname}) aún está en desarrollo y se habilitará en un
        próximo sprint.
      </p>
    </div>
  );
}
