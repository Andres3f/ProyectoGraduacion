import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import OrdersPage from './pages/OrdersPage';
import RoutesPage from './pages/RoutesPage';
import MapPage from './pages/MapPage';
import AddUserPage from './pages/AddUserPage';
import MyRoutePage from './pages/MyRoutePage';
import VehiclesPage from './pages/VehiclesPage';
import ClientsPage from './pages/ClientsPage';
import DepotsPage from './pages/DepotsPage';
import ReportsPage from './pages/ReportsPage';
import ManagerDashboardPage from './pages/ManagerDashboardPage';

// Redirigir al usuario al dashboard según su rol:
// gerente -> KPIs, conductor -> su ruta, resto -> dashboard general.
function HomeByRole() {
  const { user } = useAuth();
  if (user.role === 'gerente') return <ManagerDashboardPage />;
  if (user.role === 'conductor') return <MyRoutePage />;
  return <DashboardPage />;
}

// Componente raíz: define la navegación por roles y la estructura general de la app.
function App() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {user && <Navbar />}
      <main className={user ? 'pt-16' : ''}>
        <Routes>
          {/* Si el usuario ya está autenticado, no puede entrar a /login */}
          <Route
            path="/login"
            element={user ? <Navigate to="/" /> : <LoginPage />}
          />
          {/* Ruta raíz accesible para todos los roles autenticados */}
          <Route element={<ProtectedRoute allowedRoles={['admin', 'planificador', 'gerente', 'conductor']} />}>
            <Route path="/" element={<HomeByRole />} />
          </Route>
          {/* Módulos operativos disponibles para admin y planificador */}
          <Route element={<ProtectedRoute allowedRoles={['admin', 'planificador']} />}>
            <Route path="/orders" element={<OrdersPage />} />
            <Route path="/routes" element={<RoutesPage />} />
            <Route path="/map" element={<MapPage />} />
          </Route>
          {/* Módulos administrativos, solo para el rol admin */}
          <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
            <Route path="/vehicles" element={<VehiclesPage />} />
            <Route path="/clients" element={<ClientsPage />} />
            <Route path="/depots" element={<DepotsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/users/new" element={<AddUserPage />} />
          </Route>
          {/* Zona exclusiva del conductor */}
          <Route element={<ProtectedRoute allowedRoles={['conductor']} />}>
            <Route path="/my-route" element={<MyRoutePage />} />
          </Route>
          {/* Dashboard de KPIs para gerente (y admin) */}
          <Route element={<ProtectedRoute allowedRoles={['gerente', 'admin']} />}>
            <Route path="/dashboard-gerente" element={<ManagerDashboardPage />} />
          </Route>
          {/* Cualquier ruta desconocida vuelve a la raíz */}
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;