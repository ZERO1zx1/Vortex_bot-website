import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Firebase Hosting serves `website/dist` (see ../firebase.json).
 * `base: '/'` keeps every asset reference absolute so the SPA rewrite
 * (`** -> /index.html`) resolves correctly on deep links.
 */
export default defineConfig({
  base: "/",
  plugins: [react()],
  // Static, non-hashed-at-build assets (logo, staff avatars, sprite sheet).
  publicDir: "public",
  build: {
    outDir: "dist",
    assetsDir: "assets",
    sourcemap: false,
    // Keeps the generated catalog out of the entry chunk so a catalog-only
    // change does not invalidate the whole JS bundle hash.
    //
    // Vite 8 deprecates the function form of manualChunks (the object form
    // is removed). The object form below is equivalent and works on both
    // Vite 7 and Vite 8.
    rollupOptions: {
      output: {
        manualChunks: {
          commands: ["/src/data/commands.js"],
          vendor: ["react", "react-dom", "react-dom/client"],
        },
      },
    },
  },
  server: {
    port: 5173,
    strictPort: false,
  },
});
