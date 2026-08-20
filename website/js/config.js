/* ============================================================
   𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 — Site config
   ТОХИРУУЛГА: зөвхөн энэ файлаас өөрчилнө.

   SERVER_INVITE_URL — AETHER Discord серверийн join холбоос (бүх товчин дээр).
   BOT_INVITE_URL — Ботыг сервертээ нэмэх OAuth2 холбоос.
   Client ID-ээ Discord Developer Portal-оос (https://discord.com/developers/applications)
   аваарай.
   ============================================================ */
window.AETHER_CONFIG = {
  BOT_NAME: '𝓐𝓮𝓽𝓱𝓮𝓻  蒼穹',
  SERVER_INVITE_URL: 'https://discord.gg/Nu8ubdpZ2',
  BOT_INVITE_URL: 'https://discord.com/oauth2/authorize?client_id=1493212321231802408&permissions=8&scope=bot%20applications.commands',
  INVITE_URL: 'https://discord.gg/Nu8ubdpZ2',
  GITHUB: 'https://github.com/ZERO1zx1/gurtendev',
  /*
   * БОТЫН ЖИНХЭНЭ STATUS (Online / Offline):
   * Supabase bot_status таблицыг heartbeat эх үүсвэр болгоно.
   * Бот асаахад main.py дахь heartbeat loop 60 сек тутам
   * Supabase-д "last_ping" бичдэг → сайт эндээс уншиж харуулна.
   * Бот унтарвал last_ping хуучирч, сайт автоматаар "Offline" +
   * "сүүлд X цагын өмнө асаагдсан" гэж харуулна.
   */
  HEARTBEAT_URL: 'https://onpxpvemmjesobxpilgd.supabase.co/rest/v1/bot_status?id=eq.1&select=*',
  HEARTBEAT_APIKEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9ucHhwdmVtbWplc29ieHBpbGdkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY2ODQ2OTcsImV4cCI6MjEwMjI2MDY5N30.Wh5O6JJLuYbykLBbfHSuvrj2-sC_AqlkWp0ix3X_jMk',
  HEARTBEAT_TIMEOUT_MS: 120000,   // мс — 2 минутаас дээш ping ирэхгүй бол Offline
  HEARTBEAT_POLL_MS: 60000,       // мс — 60 сек тутам дахин шалгана
};
