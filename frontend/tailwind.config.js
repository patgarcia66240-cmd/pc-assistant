export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}"
  ],
  theme: {
    extend: {
      // Reflet lumineux qui balaie les blocs "skeleton" de chargement (voir
      // src/components/Skeleton.jsx) — translateX(-100%) -> translateX(100%) via le parent
      // -translate-x-full + cette animation, sur un bloc positionné en absolute inset-0.
      keyframes: {
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        shimmer: 'shimmer 1.6s ease-in-out infinite',
      },
    }
  },
  plugins: []
}
