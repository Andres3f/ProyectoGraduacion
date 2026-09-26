import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import './index.css';

// Aplica el tema guardado (o la preferencia del sistema) antes de montar React,
// para que no haya destello del tema claro al recargar en modo oscuro.
const savedTheme = localStorage.getItem('theme');
const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches;
if (savedTheme === 'dark' || (savedTheme !== 'light' && prefersDark)) {
  document.documentElement.classList.add('dark');
}

// Punto de entrada de la app: monta React en #root envolviendo la app con
// el router (navegación), el AuthProvider (sesión) y el ThemeProvider (tema),
// ambos disponibles globalmente.
// StrictMode ayuda a detectar efectos con problemas en desarrollo.
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
);
