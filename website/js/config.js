/* ============================================================
   𝓐𝓮𝓽𝓱𝓮𝓻 蒼Қ — Site config
   ТОХИРУУЛГА: зөвхөн энэ файлаас өөрчилнө.

   INVITE_URL — Ботын жинхэнэ invite холбоос.
   Нэмэх: https://discord.com/oauth2/authorize?client_id=БОТЫН_CLIENT_ID&permissions=8&scope=bot%20applications.commands
   Client ID-ээ Discord Developer Portal-оос (https://discord.com/developers/applications)
   аваарай.
   ============================================================ */
window.AETHER_CONFIG = {
  BOT_NAME: '𝓐𝓮𝓽𝓱𝓮𝓻  蒼Қ',
  INVITE_URL: 'https://discord.com/oauth2/authorize?client_id=1493212321231802408&permissions=8&scope=bot%20applications.commands',
  GITHUB: 'https://github.com/ZERO1zx1/gurtendev',
  /*
   * БОТЫН ЖИНХЭНЭ STATUS (Online / Offline):
   * Ботын main.py-д жижиг heartbeat server нэмсэн бол энд URL-оо бичнэ.
   * Жишээ: "http://89.19.xx.xx:9001/heartbeat" (VPS) эсвэл "" (хоосон бол manual mode)
   * Хариу ирэхгүй бол (timeout / CORS / бот унтарсан) сайт автоматаар "Offline" гэж харуулна.
   */
  HEARTBEAT_URL: '',
  HEARTBEAT_TIMEOUT_MS: 6000,   // мс — энэ хугацаанд хариу ирэхгүй бол Offline
  HEARTBEAT_POLL_MS: 60000,     // мс — 60 сек тутам дахин шалгана
};
