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
import ReportsPage from './pages/ReportsPage';
import ManagerDashboardPage from './pages/ManagerDashboardPage';

function HomeByRole() {
  const { user } = useAuth();
  if (user.role === 'gerente') return <ManagerDashboardPage />;
  if (user.role === 'conductor') return <MyRoutePage />;
  return <DashboardPage />;
}

function App() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      {user && <Navbar />}
      <main className={user ? 'pt-16' : ''}>
        <Routes>
          <Route
            path="/login"
            element={user ? <Navigate to="/" /> : <LoginPage />}
          />
          <Route element={<ProtectedRoute allowedRoles={['admin', 'planificador', 'gerente', 'conductor']} />}>
            <Route path="/" element={<HomeByRole />} />
          </Route>
          <Route element={<ProtectedRoute allowedRoles={['admin', 'planificador']} />}>
            <Route path="/orders" element={<OrdersPage />} />
            <Route path="/routes" element={<RoutesPage />} />
            <Route path="/map" element={<MapPage />} />
          </Route>
          <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
            <Route path="/vehicles" element={<VehiclesPage />} />
            <Route path="/clients" element={<ClientsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/users/new" element={<AddUserPage />} />
          </Route>
          <Route element={<ProtectedRoute allowedRoles={['conductor']} />}>
            <Route path="/my-route" element={<MyRoutePage />} />
          </Route>
          <Route element={<ProtectedRoute allowedRoles={['gerente', 'admin']} />}>
            <Route path="/dashboard-gerente" element={<ManagerDashboardPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;