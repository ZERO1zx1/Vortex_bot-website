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
  BOT_INVITE_URL: 'https://discord.com/oauth2/authorize?client_id=1493212321231802408&permissions=0&scope=bot%20applications.commands',
  INVITE_URL: 'https://discord.gg/Nu8ubdpZ2',
  GITHUB: 'null',
  /*
   * БОТЫН ЖИНХЭНЭ STATUS (Online / Offline):
   * Supabase bot_status хүснэгт heartbeat эх үүсвэр боловч browser
   * зөвхөн FastAPI backend-ийн sanitized /api/status-ийг дуудна.
   * Бот асаахад main.py дахь heartbeat loop 60 сек тутам
   * Supabase-д "last_ping" бичдэг → сайт эндээс уншиж харуулна.
   * Бот унтарвал last_ping хуучирч, сайт автоматаар "Offline" +
   * "сүүлд X цагын өмнө асаагдсан" гэж харуулна.
   */
HEARTBEAT_POLL_MS: 60000,       // мс — 60 сек тутам дахин шалгана
  /*
   * SUPABASE heartbeat (backend байхгүй үед шууд уншилт):
   * Бот 60 сек тутам bot_status(id=1) рүү "last_ping" бичдэг.
   * Сайт эхлээд FastAPI /api/status-ыг дуудаж, амжилтгүй бол
   * доорх URL + publishable (ANON) key-ээр Supabase REST-ийг
   * шууд уншина. Энэ key зөвхөн anon role (RLS: зөвхөн id=1),
   * сервис/service role биш — public сайтад тавих нь аюулгүй.
   */
  SUPABASE_URL: 'https://onpxpvemmjesobxpilgd.supabase.co',
  SUPABASE_ANON_KEY: 'sb_publishable_688p57WyjJ6G1FkUmZp9ww_YhuVMpoQ',
  /*
   * BACKEND API (FastAPI — backend/ фолдер, Railway дээр deploy):
   * Railway дээр deploy хийж domain авсныхаа дараа энд бичнэ, жишээ:
   *   API_BASE_URL: 'https://aether-backend.up.railway.app',
   * API_BASE_URL хоосон байхад status нь дээрх Supabase-аас уншигдана.
   * Service role key browser bundle-д хэзээ ч байрлуулж болохгүй.
   */
  API_BASE_URL: '',
};
