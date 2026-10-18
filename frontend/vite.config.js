import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// In dev, Vite forwards /api calls to the backend ports from docker-compose.
export default defineConfig({ plugins: [react()], server: { port: 5173, proxy: {
  "/api/users": "http://localhost:8001", "/api/shows": "http://localhost:8002", "/api/events": "http://localhost:8002", "/api/cities": "http://localhost:8002",
  "/api/bookings": "http://localhost:8003", "/api/admin": "http://localhost:8003" } } });
