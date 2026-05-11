import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@next": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules")) {
            if (id.includes("html2canvas")) {
              return "pdf-html2canvas";
            }
            if (id.includes("jspdf") || id.includes("dompurify")) {
              return "pdf-jspdf";
            }
            if (id.includes("react-grid-layout") || id.includes("react-resizable")) {
              return "dashboard-grid";
            }
            if (id.includes("recharts")) {
              return "recharts";
            }
            if (id.includes("/node_modules/react-dom/") || id.includes("/node_modules/react/") || id.includes("/node_modules/scheduler/")) {
              return "react-vendor";
            }
            if (id.includes("axios")) {
              return "network";
            }
              if (
                id.includes("@mui/") ||
                id.includes("@emotion/")
              ) {
                return "mui";
              }
            return "vendor";
          }

          if (id.includes("/src/features/dashboards/export/export-dashboard.ts")) {
            return "pdf-export";
          }

          if (id.includes("/src/features/dashboards/components/share-dialog.tsx")) {
            return "dashboard-share";
          }
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
});
