import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/three')) return 'three';
        },
      },
    },
    // The 3D engine is a separate, cacheable download.
    chunkSizeWarningLimit: 650,
  },
});
