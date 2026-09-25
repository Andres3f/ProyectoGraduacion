import axios from 'axios';

// Instancia de Axios preconfigurada con la ruta base del backend
const api = axios.create({
  baseURL: '/api',
});

// Interceptor para agregar token JWT a cada request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;

// Interceptor para manejar errores 401 (sesión expirada).
// Primero intenta renovar con el refresh_token almacenado; si eso falla,
// limpia la sesión y redirige a /login (evitando bucle si ya está ahí).
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status;
    const originalRequest = error.config;

    // Solo renueva una vez por petición y evita renovaciones simultáneas
    if (status === 401 && originalRequest && !originalRequest._retry && !isRefreshing) {
      originalRequest._retry = true;
      isRefreshing = true;
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) throw new Error('no refresh token');
        // Pide un par de tokens nuevo con el refresh_token guardado
        const { data } = await axios.post('/api/auth/refresh', {
          refresh_token: refreshToken,
        });
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        // Reintenta la petición original con el token renovado
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch {
        // Renovación fallida: limpiar sesión y volver a /login
        localStorage.removeItem('token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        if (!window.location.pathname.startsWith('/login')) {
          window.location.href = '/login';
        }
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

export default api;
