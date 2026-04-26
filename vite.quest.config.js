import { defineConfig } from "vite";
import { iwsdkDev } from "@iwsdk/vite-plugin-dev";
import fs from "node:fs";

const apiTarget = process.env.QUEST_API_TARGET || "http://127.0.0.1:8010";
const host = process.env.QUEST_HOST || "0.0.0.0";
const port = Number(process.env.QUEST_PORT || "5173");
const pfxPath = process.env.QUEST_HTTPS_PFX;
const pfxPassword = process.env.QUEST_HTTPS_PFX_PASSWORD || "";
const certPath = process.env.QUEST_HTTPS_CERT;
const keyPath = process.env.QUEST_HTTPS_KEY;
const https =
  pfxPath
    ? {
        pfx: fs.readFileSync(pfxPath),
        passphrase: pfxPassword,
      }
    : certPath && keyPath
    ? {
        cert: fs.readFileSync(certPath),
        key: fs.readFileSync(keyPath),
      }
    : undefined;

export default defineConfig({
  server: {
    host,
    port,
    strictPort: false,
    https,
    hmr: {
      protocol: https ? "wss" : "ws",
      host: process.env.QUEST_HMR_HOST || undefined,
      clientPort: Number(process.env.QUEST_HMR_CLIENT_PORT || port),
    },
    proxy: {
      "/api": apiTarget,
      "/v1": apiTarget,
      "/sessions": apiTarget,
    },
  },
  build: {
    rollupOptions: {
      input: "viewer/quest-iw-demo/index.html",
    },
  },
  plugins: [
    iwsdkDev({
      emulator: {
        device: "metaQuest3",
        activation: "localhost",
      },
      ai: {
        mode: "agent",
        tools: [],
        screenshotSize: { width: 900, height: 900 },
      },
    }),
  ],
});
