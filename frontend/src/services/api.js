import axios from 'axios';

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

// Interceptor para manejar errores 401 (sesión expirada).
// Evita un bucle de redirección si el usuario ya se encuentra en /login: solo
// limpia la sesión y redirige cuando no está en la página de login.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    if (status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      const isOnAuth = window.location.pathname.startsWith('/login');
      if (!isOnAuth) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
