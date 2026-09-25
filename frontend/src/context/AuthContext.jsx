import { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

// Contexto global de autenticación (sesión del usuario)
const AuthContext = createContext(null);

// Proveedor de autenticación: guarda el usuario en estado y expone
// login/logout a toda la aplicación.
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Al montar, restaura la sesión si existe un token guardado:
  // valida el token con el backend y carga los datos del usuario.
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      api
        .get('/users/me')
        .then((res) => setUser(res.data))
        .catch(() => {
          // Token inválido o expirado: limpia la sesión local
          localStorage.removeItem('token');
          localStorage.removeItem('refresh_token');
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      // Sin token previo, no hay sesión que restaurar
      setLoading(false);
    }
  }, []);

  // Inicia sesión: valida credenciales, guarda tokens y carga el usuario
  const login = async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    localStorage.setItem('token', res.data.access_token);
    localStorage.setItem('refresh_token', res.data.refresh_token);
    const me = await api.get('/users/me');
    setUser(me.data);
    return me.data;
  };

  // Cierra sesión: elimina los tokens y el usuario del estado
  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  // Mientras se comprueba la sesión inicial mostrar un spinner
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// Hook para acceder al contexto de autenticación desde cualquier componente
export const useAuth = () => useContext(AuthContext);
