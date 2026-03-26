/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
        cement: {
          50: '#f8f6f4',
          100: '#ede8e3',
          200: '#ddd4cb',
          300: '#c4b5a5',
          400: '#ab9380',
          500: '#977b66',
          600: '#8a6c5a',
          700: '#73594b',
          800: '#5f4a41',
          900: '#4f3e37',
        },
      },
    },
  },
  plugins: [],
};
