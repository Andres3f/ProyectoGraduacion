import { createContext, useContext, useState, useEffect } from 'react';

// Contexto global del tema visual (claro / oscuro). El valor por defecto
// evita que un componente se rompa si se usa fuera del ThemeProvider.
const ThemeContext = createContext({ theme: 'light', toggleTheme: () => {} });

// Clave de persistencia y clase que Tailwind usa para activar las variantes
// `dark:` (ver darkMode en tailwind.config.js).
const STORAGE_KEY = 'theme';
const DARK_CLASS = 'dark';

// Aplica la clase `dark` al <html> para que las variantes `dark:` del CSS
// entren en efecto de inmediato.
function applyTheme(theme) {
  document.documentElement.classList.toggle(DARK_CLASS, theme === 'dark');
}

// Devuelve el tema inicial: la elección guardada si existe; si nunca se eligió,
// la preferencia del sistema operativo.
function initialTheme() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === 'dark' || saved === 'light') return saved;
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';
}

// Proveedor de tema: expone el tema activo y la función para alternarlo.
export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(initialTheme);

  // Sincroniza la clase del <html> con el estado en cada cambio.
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // Alterna entre claro y oscuro y guarda la preferencia para la próxima visita.
  const toggleTheme = () =>
    setTheme((current) => {
      const next = current === 'dark' ? 'light' : 'dark';
      localStorage.setItem(STORAGE_KEY, next);
      return next;
    });

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

// Hook para acceder al tema desde cualquier componente.
export const useTheme = () => useContext(ThemeContext);
