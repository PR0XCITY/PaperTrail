const BACKEND_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function startKeepAlive() {
  const ping = async () => {
    try {
      await fetch(`${BACKEND_URL}/health`);
    } catch (_) {}
  };
  ping();
  setInterval(ping, 10 * 60 * 1000);
}
