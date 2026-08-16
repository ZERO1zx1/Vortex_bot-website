/* ============================================================
   𝓐𝓮𝓽𝓱𝓮𝓻 蒼Қ — Command catalog (from bot source code, 2026-08-16)
   Categories mirror the real cog grouping of the bot.
   ============================================================ */
const COMMANDS = [
  // ---------------- Economy ----------------
  { name: 'daily',        cat: 'Economy',    icon: '📅', desc: 'Өдөр бүрийн мөнгөний урамшуулал' },
  { name: 'work',         cat: 'Economy',    icon: '💼', desc: 'Ажиллаж мөнгө ол' },
  { name: 'balance',      cat: 'Economy',    icon: '💳', desc: 'Таны мөнгөн дүн' },
  { name: 'pay',          cat: 'Economy',    icon: '💸', desc: 'Нөгөө хүн рүү мөнгө шилжүүл' },
  { name: 'rob',          cat: 'Economy',    icon: '🦹', desc: 'Нэгнээсээ хулгайлах (эрсдэлтэй!)' },
  { name: 'workphrase',   cat: 'Economy',    icon: '📝', desc: 'Ажлын үгсийн жагсаалт тохируулах' },
  { name: 'addmoney',     cat: 'Economy',    icon: '➕', desc: 'Хэрэглэгчид мөнгө нэмэх (админ)' },
  { name: 'removemoney',  cat: 'Economy',    icon: '➖', desc: 'Хэрэглэгчээс мөнгө хасах (админ)' },
  { name: 'market',       cat: 'Economy',    icon: '🏪', desc: 'Кафегийн дэлгүүр, хоол/уух зүйлс' },
  { name: 'dine',         cat: 'Economy',    icon: '🍽️', desc: 'Кафед хоол идэх' },
  { name: 'cafe',         cat: 'Economy',    icon: '☕', desc: 'Кафегийн цэс ба мэдээлэл' },

  // ---------------- Leveling ----------------
  { name: 'rank',         cat: 'Leveling',   icon: '🏅', desc: 'Таны түвшин ба XP' },
  { name: 'grank',        cat: 'Leveling',   icon: '📊', desc: 'Server-ийн XP жагсаалт' },
  { name: 'leaderboard',  cat: 'Leveling',   icon: '🏆', desc: 'Түвшингийн тэргүүнүүд' },
  { name: 'serveractivity', cat: 'Leveling', icon: '📈', desc: 'Server-ийн идэвхтэй байдал' },
  { name: 'addxp',        cat: 'Leveling',   icon: '✨', desc: 'Хэрэглэгчид XP нэмэх (админ)' },
  { name: 'removexp',     cat: 'Leveling',   icon: '📉', desc: 'XP хасах (админ)' },
  { name: 'leveling_setup', cat: 'Leveling', icon: '⚙️', desc: 'Leveling-ийн тохиргоо (админ)' },
  { name: 'invites',      cat: 'Leveling',   icon: '📨', desc: 'Таны урилгууд ба XP урамшуулал' },
  { name: 'inviter',      cat: 'Leveling',   icon: '🔗', desc: 'Хэн таныг урьсныг харах' },

  // ---------------- Social / Marriage ----------------
  { name: 'propose',      cat: 'Social',     icon: '💍', desc: 'Хайртай хүнээсээ гэрлэлтийн санал тавь' },
  { name: 'marry',        cat: 'Social',     icon: '💑', desc: 'Гэрлэх' },
  { name: 'divorce',      cat: 'Social',     icon: '💔', desc: 'Салалт' },
  { name: 'spouse',       cat: 'Social',     icon: '👫', desc: 'Таны ханийн мэдээлэл' },
  { name: 'love',         cat: 'Social',     icon: '❤️', desc: 'Хайрын хэмжээ харах' },
  { name: 'gift',         cat: 'Social',     icon: '🎁', desc: 'Ханиандаа бэлэг өгөх' },
  { name: 'adopt',        cat: 'Social',     icon: '👶', desc: 'Хүүхэд үрчлэх' },
  { name: 'disown',       cat: 'Social',     icon: '🚪', desc: 'Хүүхдээсээ татгалзах' },
  { name: 'children',     cat: 'Social',     icon: '🧸', desc: 'Таны хүүхдүүд' },
  { name: 'makeparent',   cat: 'Social',     icon: '👨‍👩‍👧', desc: 'Гэр бүлийн эцэг/эх болгох' },
  { name: 'familytree',   cat: 'Social',     icon: '🌳', desc: 'Гэр бүлийн мод' },
  { name: 'tree',         cat: 'Social',     icon: '🍀', desc: 'Гэр бүлийн модны товчлол' },
  { name: 'fulltree',     cat: 'Social',     icon: '🌲', desc: 'Бүрэн гэр бүлийн мод' },
  { name: 'marriage_setup', cat: 'Social',   icon: '🔧', desc: 'Гэрлэлийн тохиргоо (админ)' },
  { name: 'marriagepro',  cat: 'Social',     icon: '🏛️', desc: 'Гэрлэлийн профиль' },
  { name: 'confess',      cat: 'Social',     icon: '🤫', desc: 'Аноним илчлэл' },

  // ---------------- Games ----------------
  { name: 'gamble',       cat: 'Games',      icon: '🎰', desc: 'Шуудайнд мөнгө тавих' },
  { name: 'coinflip',     cat: 'Games',      icon: '🪙', desc: 'Зоос шидэх' },
  { name: 'slots',        cat: 'Games',      icon: '🎰', desc: 'Слот машин' },
  { name: 'roulette',     cat: 'Games',      icon: '🎡', desc: 'Рулетка' },
  { name: 'dice',         cat: 'Games',      icon: '🎲', desc: 'Шоо шидэх' },
  { name: 'rps',          cat: 'Games',      icon: '✊', desc: 'Чулуу-цаас-хайч' },
  { name: 'mines',        cat: 'Games',      icon: '💣', desc: 'Уурхайн тоглоом' },
  { name: 'counting',     cat: 'Games',      icon: '🔢', desc: 'Тоо тоолох дуулаан' },
  { name: 'count_stats_server', cat: 'Games', icon: '📊', desc: 'Тооллын статистик' },
  { name: 'pvp',          cat: 'Games',      icon: '⚔️', desc: 'Тоглогч хоорондын тулаан' },
  { name: 'trade',        cat: 'Games',      icon: '🔄', desc: 'Бараа солилцоо' },
  { name: 'marketplace',  cat: 'Games',      icon: '🏬', desc: 'Зарын зах зээл' },
  { name: 'mp',           cat: 'Games',      icon: '🛍️', desc: 'Marketplace-ийн товчлол' },
  { name: 'stock',        cat: 'Games',      icon: '📈', desc: 'Хувьцааны мэдээлэл' },
  { name: 'graph',        cat: 'Games',      icon: '📉', desc: 'Хувьцааны график' },
  { name: 'buy',          cat: 'Games',      icon: '🛒', desc: 'Хувьцаа худалдаж авах' },
  { name: 'sell',         cat: 'Games',      icon: '💹', desc: 'Хувьцаа зарах' },
  { name: 'stock_ticker', cat: 'Games',      icon: '📋', desc: 'Хувьцааны жагсаалт' },
  { name: 'stock_leaderboard', cat: 'Games', icon: '🥇', desc: 'Хувьцааны лидерборд' },
  { name: 'mafia',        cat: 'Games',      icon: '🕵️', desc: 'Mafia тоглоом' },
  { name: 'mafiacreate',  cat: 'Games',      icon: '🎭', desc: 'Mafia тоглоом үүсгэх (админ)' },
  { name: 'mafiastart',   cat: 'Games',      icon: '▶️', desc: 'Mafia-г эхлүүлэх (админ)' },
  { name: 'mafiaend',     cat: 'Games',      icon: '⏹️', desc: 'Mafia-г дуусгах (админ)' },
  { name: 'giveaway',     cat: 'Games',      icon: '🎉', desc: 'Сугалаа явуулах' },
  { name: 'reroll',       cat: 'Games',      icon: '🔄', desc: 'Сугалааг дахин татах' },
  { name: 'end',          cat: 'Games',      icon: '🔚', desc: 'Сугалааг эрт дуусгах' },

  // ---------------- Moderation ----------------
  { name: 'ban',          cat: 'Moderation', icon: '🔨', desc: 'Серверээс банлах' },
  { name: 'unban',        cat: 'Moderation', icon: '🔓', desc: 'Баныг авах' },
  { name: 'kick',         cat: 'Moderation', icon: '🦶', desc: 'Хөөх' },
  { name: 'timeout',      cat: 'Moderation', icon: '⏸️', desc: 'Түр хугацаагаар хаах' },
  { name: 'untimeout',    cat: 'Moderation', icon: '▶️', desc: 'Timeout-ыг авах' },
  { name: 'warn',         cat: 'Moderation', icon: '⚠️', desc: 'Сануулга өгөх' },
  { name: 'unwarn',       cat: 'Moderation', icon: '✅', desc: 'Сануулгыг авах' },
  { name: 'warnings',     cat: 'Moderation', icon: '📃', desc: 'Таны сануулгууд' },
  { name: 'warnedusers',  cat: 'Moderation', icon: '👥', desc: 'Сануулгатай хүмүүс (админ)' },
  { name: 'clear',        cat: 'Moderation', icon: '🗑️', desc: 'Мессеж цэвэрлэх (purge)' },
  { name: 'lock',         cat: 'Moderation', icon: '🔒', desc: 'Суваг түгжих' },
  { name: 'unlock',       cat: 'Moderation', icon: '🔓', desc: 'Суваг тайлах' },
  { name: 'banlist',      cat: 'Moderation', icon: '📋', desc: 'Бан жагсаалт' },
  { name: 'set_log_channel', cat: 'Moderation', icon: '📢', desc: 'Mod-log сувгийг тохируулах' },

  // ---------------- Admin ----------------
  { name: 'status',       cat: 'Admin',      icon: '🩺', desc: 'Ботын CPU/RAM/системийн төлөв' },
  { name: 'info',         cat: 'Admin',      icon: 'ℹ️', desc: 'Ботын мэдээлэл' },
  { name: 'rolelist',     cat: 'Admin',      icon: '🎭', desc: 'Серверийн ролийн жагсаалт' },
  { name: 'announce',     cat: 'Admin',      icon: '📣', desc: 'Мэдэгдэл илгээх' },
  { name: 'greeting_set', cat: 'Admin',      icon: '👋', desc: 'Welcome/Goodbye тохируулах' },
  { name: 'greeting_status', cat: 'Admin',   icon: '✅', desc: 'Тавилгын төлөв харах' },
  { name: 'greeting_toggle', cat: 'Admin',   icon: '🔀', desc: 'Тавилгыг асаах/унтраах' },
  { name: 'greeting_reset', cat: 'Admin',    icon: '🔁', desc: 'Тавилгыг шинэчлэх' },
  { name: 'setup',        cat: 'Admin',      icon: '🚀', desc: 'Ботын анхны тохируулга' },
  { name: 'panel',        cat: 'Admin',      icon: '🎛️', desc: 'Ботын удирдлагын самбар' },
  { name: 'stats',        cat: 'Admin',      icon: '📊', desc: 'Дэлгэрэнгүй статистик' },
  { name: 'staff_setup',  cat: 'Admin',      icon: '👮', desc: 'Staff баг тохируулах' },
  { name: 'staff_status', cat: 'Admin',      icon: '📟', desc: 'Staff-ийн төлөв' },
  { name: 'staff_counts', cat: 'Admin',      icon: '🔢', desc: 'Staff-ийн тоо' },
  { name: 'addlabel',     cat: 'Admin',      icon: '🏷️', desc: 'Staff шошго нэмэх' },
  { name: 'removelabel',  cat: 'Admin',      icon: '✂️', desc: 'Staff шошго устгах' },
  { name: 'avatar_config', cat: 'Admin',     icon: '🖼️', desc: 'Аватар logger тохиргоо' },
  { name: 'confess_setup', cat: 'Admin',     icon: '🕵️', desc: 'Confessions тохируулах' },
  { name: 'confess_stats', cat: 'Admin',     icon: '📊', desc: 'Confessions статистик' },
  { name: 'confess_delete', cat: 'Admin',    icon: '🗑️', desc: 'Илчлэл устгах' },
  { name: 'confess_blacklist', cat: 'Admin', icon: '⛔', desc: 'Илчлэлийн хар жагсаалт' },
  { name: 'counting_setup', cat: 'Admin',    icon: '⚙️', desc: 'Counting тохируулах' },
  { name: 'count_stats_user', cat: 'Admin',  icon: '👤', desc: 'Хэрэглэгчийн тооллын статистик' },
  { name: 'voicesetup',   cat: 'Admin',      icon: '🎙️', desc: 'Temp voice тохируулах' },
  { name: 'voicesettings', cat: 'Admin',     icon: '🔊', desc: 'Voice багийн тохиргоо' },
  { name: 'template_create', cat: 'Admin',   icon: '📄', desc: 'Загвар үүсгэх' },
  { name: 'template_edit', cat: 'Admin',     icon: '✏️', desc: 'Загвар засах' },
  { name: 'template_delete', cat: 'Admin',   icon: '❌', desc: 'Загвар устгах' },
  { name: 'template_list', cat: 'Admin',     icon: '📑', desc: 'Загварууд харах' },
  { name: 'template_preview', cat: 'Admin',  icon: '👁️', desc: 'Загвар урьдчилж харах' },

  // ---------------- Utility ----------------
  { name: 'help',         cat: 'Utility',    icon: '❓', desc: 'Бүх командыг ангиллаар нь' },
  { name: 'invite',       cat: 'Utility',    icon: '📨', desc: 'Урилгын холбоос' },
  { name: 'avatar',       cat: 'Utility',    icon: '🖼️', desc: 'Хүний аватар харах' },
  { name: 'boost',        cat: 'Utility',    icon: '🚀', desc: 'Boost мэдээлэл' },
  { name: 'partners',     cat: 'Utility',    icon: '🤝', desc: 'Партнер серверүүд' },
  { name: 'entries',      cat: 'Utility',    icon: '🎟️', desc: 'Сугалааны оролцогчид' },
  { name: 'list',         cat: 'Utility',    icon: '📄', desc: 'Жагсаалт харах' },
  { name: 'relationship', cat: 'Utility',    icon: '💞', desc: 'Гэр бүлийн холбоо' },
  { name: 'placeholders', cat: 'Utility',    icon: '📌', desc: 'Placeholder мэдээлэл' },
  { name: 'codes',        cat: 'Utility',    icon: '🔑', desc: 'Промо кодууд' },
  { name: 'autoaccept',   cat: 'Utility',    icon: '✔️', desc: 'Автомат зөвшөөрөл' },
  { name: 'cancel',       cat: 'Utility',    icon: '🛑', desc: 'Урсгал цуцлах' },
];

/* Dedupe (guard) and export */
const seen = new Set();
window.COMMAND_LIST = COMMANDS.filter(c => {
  if (seen.has(c.name)) return false;
  seen.add(c.name);
  return true;
});
window.COMMAND_CATS = ['all', 'Economy', 'Leveling', 'Social', 'Games', 'Moderation', 'Admin', 'Utility'];

/* Category metadata: mongolian label, theme color, emoji */
window.CAT_META = {
  all:        { label: 'Бүгд',        color: '#89B4FA', icon: '🗂️' },
  Economy:    { label: 'Economy',     color: '#89B4FA', icon: '💰' },
  Leveling:   { label: 'Leveling',    color: '#94E2D5', icon: '📊' },
  Social:     { label: 'Гэр бүл',     color: '#F38BA8', icon: '💍' },
  Games:      { label: 'Тоглоом',     color: '#FAB387', icon: '🎲' },
  Moderation: { label: 'Модерац',     color: '#A6E3A1', icon: '🛡️' },
  Admin:      { label: 'Админ',       color: '#B4BEFE', icon: '⚙️' },
  Utility:    { label: 'Бусад',       color: '#8C8FA1', icon: '🔧' },
};
