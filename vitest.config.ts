import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
      {
        find: "@/src/i18n/routing",
        replacement: fileURLToPath(new URL("./apps/web/test/mocks/i18n-routing.tsx", import.meta.url)),
      },
      {
        find: "next/navigation",
        replacement: fileURLToPath(new URL("./apps/web/test/mocks/next-navigation.ts", import.meta.url)),
      },
      {
        find: "next-intl/server",
        replacement: fileURLToPath(new URL("./apps/web/test/mocks/next-intl-server.ts", import.meta.url)),
      },
      {
        find: "next-intl",
        replacement: fileURLToPath(new URL("./apps/web/test/mocks/next-intl.ts", import.meta.url)),
      },
      {
        find: "next/navigation.js",
        replacement: fileURLToPath(new URL("./apps/web/test/mocks/next-navigation.ts", import.meta.url)),
      },
      {
        find: "@",
        replacement: fileURLToPath(new URL("./apps/web", import.meta.url)),
      },
    ],
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./apps/web/test/setup.ts"],
  },
});
