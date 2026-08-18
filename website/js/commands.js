/* ============================================================
   𝓐𝓮𝓽𝓱𝓮𝓻 蒼Қ — Command catalog (from bot source code, 2026-08-16)
   Categories mirror the real cog grouping of the bot.
   ============================================================ */
const COMMANDS = [
  // ---------------- Economy ----------------
  { name: 'daily',        cat: 'Economy',    icon: '📅', desc: 'Өдөр бүрийн мөнгөний урамшуулал', args:[], example:'', descEN:"Claim your daily coin reward"},
  { name: 'work',         cat: 'Economy',    icon: '💼', desc: 'Ажиллаж мөнгө ол', args:[], example:'', descEN:"Work to earn coins"},
  { name: 'balance',      cat: 'Economy',    icon: '💳', desc: 'Таны мөнгөн дүн', args:[{"key":"user","req":false}], example:'A!balance', descEN:"View your coin balance"},
  { name: 'pay',          cat: 'Economy',    icon: '💸', desc: 'Нөгөө хүн рүү мөнгө шилжүүл', args:[{"key":"user","req":true},{"key":"amount","req":true}], example:'A!pay @friend 1000', descEN:"Send coins to another user"},
  { name: 'rob',          cat: 'Economy',    icon: '🦹', desc: 'Нэгнээсээ хулгайлах (эрсдэлтэй!)', args:[{"key":"user","req":true}], example:'A!rob @target', descEN:"Attempt to rob another user (risky!)"},
  { name: 'workphrase',   cat: 'Economy',    icon: '📝', desc: 'Ажлын үгсийн жагсаалт тохируулах', args:[], example:'', descEN:"Customize your work phrases"},
  { name: 'addmoney',     cat: 'Economy',    icon: '➕', desc: 'Хэрэглэгчид мөнгө нэмэх (админ)', args:[{"key":"user","req":true},{"key":"amount","req":true}], example:'/addmoney @user 5000', descEN:"Add coins to a user (admin)"},
  { name: 'removemoney',  cat: 'Economy',    icon: '➖', desc: 'Хэрэглэгчээс мөнгө хасах (админ)', args:[{"key":"user","req":true},{"key":"amount","req":true}], example:'/removemoney @user 1000', descEN:"Remove coins from a user (admin)"},
  { name: 'market',       cat: 'Economy',    icon: '🏪', desc: 'Кафегийн дэлгүүр, хоол/уух зүйлс', args:[], example:'', descEN:"Browse the cafe shop items"},
  { name: 'dine',         cat: 'Economy',    icon: '🍽️', desc: 'Кафед хоол идэх', args:[{"key":"item","req":false}], example:'A!dine pizza', descEN:"Eat a meal at the cafe (spend coins)"},
  { name: 'cafe',         cat: 'Economy',    icon: '☕', desc: 'Кафегийн цэс ба мэдээлэл', args:[], example:'', descEN:"View cafe menu and info"},

  // ---------------- Leveling ----------------
  { name: 'rank',         cat: 'Leveling',   icon: '🏅', desc: 'Таны түвшин ба XP', args:[{"key":"user","req":false}], example:'A!rank', descEN:"View your rank and XP"},
  { name: 'grank',        cat: 'Leveling',   icon: '📊', desc: 'Server-ийн XP жагсаалт', args:[{"key":"user","req":false}], example:'A!grank', descEN:"View the global XP leaderboard"},
  { name: 'leaderboard',  cat: 'Leveling',   icon: '🏆', desc: 'Түвшингийн тэргүүнүүд', args:[], example:'', descEN:"Show the top users by rank"},
  { name: 'serveractivity', cat: 'Leveling', icon: '📈', desc: 'Server-ийн идэвхтэй байдал', args:[], example:'', descEN:"View server activity stats"},
  { name: 'addxp',        cat: 'Leveling',   icon: '✨', desc: 'Хэрэглэгчид XP нэмэх (админ)', args:[{"key":"user","req":true},{"key":"amount","req":true}], example:'/addxp @user 500', descEN:"Add XP to a user (admin)"},
  { name: 'removexp',     cat: 'Leveling',   icon: '📉', desc: 'XP хасах (админ)', args:[{"key":"user","req":true},{"key":"amount","req":true}], example:'/removexp @user 200', descEN:"Remove XP from a user (admin)"},
  { name: 'leveling_setup', cat: 'Leveling', icon: '⚙️', desc: 'Leveling-ийн тохиргоо (админ)', args:[], example:'', descEN:"Configure leveling settings (admin)"},
  { name: 'invites',      cat: 'Leveling',   icon: '📨', desc: 'Таны урилгууд ба XP урамшуулал', args:[], example:'', descEN:"View your invites and invite XP"},
  { name: 'inviter',      cat: 'Leveling',   icon: '🔗', desc: 'Хэн таныг урьсныг харах', args:[{"key":"user","req":false}], example:'A!inviter', descEN:"See who invited you"},

  // ---------------- Social / Marriage ----------------
  { name: 'propose',      cat: 'Social',     icon: '💍', desc: 'Хайртай хүнээсээ гэрлэлтийн санал тавь', args:[{"key":"user","req":true}], example:'A!propose @love', descEN:"Propose marriage to someone"},
  { name: 'marry',        cat: 'Social',     icon: '💑', desc: 'Гэрлэх', args:[{"key":"user","req":true}], example:'A!marry @partner', descEN:"Marry your partner"},
  { name: 'divorce',      cat: 'Social',     icon: '💔', desc: 'Салалт', args:[], example:'', descEN:"End your marriage"},
  { name: 'spouse',       cat: 'Social',     icon: '👫', desc: 'Таны ханийн мэдээлэл', args:[{"key":"user","req":false}], example:'A!spouse', descEN:"View your spouse info"},
  { name: 'love',         cat: 'Social',     icon: '❤️', desc: 'Хайрын хэмжээ харах', args:[{"key":"user","req":true}], example:'A!love @spouse', descEN:"Check your love level"},
  { name: 'gift',         cat: 'Social',     icon: '🎁', desc: 'Ханиандаа бэлэг өгөх', args:[{"key":"item","req":true}], example:'A!gift ring', descEN:"Send a gift to your spouse"},
  { name: 'adopt',        cat: 'Social',     icon: '👶', desc: 'Хүүхэд үрчлэх', args:[{"key":"name","req":true}], example:'A!adopt Lhagva', descEN:"Adopt a child"},
  { name: 'disown',       cat: 'Social',     icon: '🚪', desc: 'Хүүхдээсээ татгалзах', args:[{"key":"child","req":true}], example:'A!disown Lhagva', descEN:"Disown a child"},
  { name: 'children',     cat: 'Social',     icon: '🧸', desc: 'Таны хүүхдүүд', args:[], example:'', descEN:"List your children"},
  { name: 'makeparent',   cat: 'Social',     icon: '👨‍👩‍👧', desc: 'Гэр бүлийн эцэг/эх болгох', args:[{"key":"child","req":true},{"key":"parent","req":true}], example:'A!makeparent Lhagva @mom', descEN:"Assign parents to a child (admin)"},
  { name: 'familytree',   cat: 'Social',     icon: '🌳', desc: 'Гэр бүлийн мод', args:[], example:'', descEN:"View your family tree"},
  { name: 'tree',         cat: 'Social',     icon: '🍀', desc: 'Гэр бүлийн модны товчлол', args:[], example:'', descEN:"Family tree summary"},
  { name: 'fulltree',     cat: 'Social',     icon: '🌲', desc: 'Бүрэн гэр бүлийн мод', args:[], example:'', descEN:"Full family tree view"},
  { name: 'marriage_setup', cat: 'Social',   icon: '🔧', desc: 'Гэрлэлийн тохиргоо (админ)', args:[], example:'', descEN:"Marriage system settings (admin)"},
  { name: 'marriagepro',  cat: 'Social',     icon: '🏛️', desc: 'Гэрлэлийн профиль', args:[], example:'', descEN:"Your marriage profile"},
  { name: 'confess',      cat: 'Social',     icon: '🤫', desc: 'Аноним илчлэл', args:[{"key":"text","req":true}], example:'A!confess I like...', descEN:"Anonymous confession in the channel"},

  // ---------------- Games ----------------
  { name: 'gamble',       cat: 'Games',      icon: '🎰', desc: 'Шуудайнд мөнгө тавих', args:[{"key":"amount","req":false}], example:'A!gamble 500', descEN:"Gambling with buttons (high/low)"},
  { name: 'coinflip',     cat: 'Games',      icon: '🪙', desc: 'Зоос шидэх', args:[{"key":"side","req":true}], example:'A!coinflip heads', descEN:"Flip a coin (heads/tails)"},
  { name: 'slots',        cat: 'Games',      icon: '🎰', desc: 'Слот машин', args:[{"key":"amount","req":true}], example:'A!slots 200', descEN:"Play the slot machine"},
  { name: 'roulette',     cat: 'Games',      icon: '🎡', desc: 'Рулетка', args:[{"key":"bet","req":true}], example:'A!roulette red', descEN:"Play roulette"},
  { name: 'dice',         cat: 'Games',      icon: '🎲', desc: 'Шоо шидэх', args:[{"key":"amount","req":false}], example:'A!dice 100', descEN:"Roll dice against the bot"},
  { name: 'rps',          cat: 'Games',      icon: '✊', desc: 'Чулуу-цаас-хайч', args:[{"key":"move","req":true}], example:'A!rps rock', descEN:"Rock-paper-scissors vs the bot"},
  { name: 'mines',        cat: 'Games',      icon: '💣', desc: 'Уурхайн тоглоом', args:[{"key":"amount","req":false}], example:'A!mines 300', descEN:"Minesweeper-style mine game"},
  { name: 'counting',     cat: 'Games',      icon: '🔢', desc: 'Тоо тоолох дуулаан', args:[], example:'', descEN:"Counting challenge (1,2,3...) with members"},
  { name: 'count_stats_server', cat: 'Games', icon: '📊', desc: 'Тооллын статистик', args:[], example:'', descEN:"Server counting stats"},
  { name: 'pvp',          cat: 'Games',      icon: '⚔️', desc: 'Тоглогч хоорондын тулаан', args:[{"key":"opponent","req":true}], example:'A!pvp @rival', descEN:"Duel another player"},
  { name: 'trade',        cat: 'Games',      icon: '🔄', desc: 'Бараа солилцоо', args:[{"key":"user","req":true}], example:'A!trade @friend', descEN:"Trade items with another user"},
  { name: 'marketplace',  cat: 'Games',      icon: '🏬', desc: 'Зарын зах зээл', args:[], example:'', descEN:"Open the item marketplace"},
  { name: 'mp',           cat: 'Games',      icon: '🛍️', desc: 'Marketplace-ийн товчлол', args:[], example:'', descEN:"Marketplace shortcut"},
  { name: 'stock',        cat: 'Games',      icon: '📈', desc: 'Хувьцааны мэдээлэл', args:[], example:'', descEN:"View stock market info"},
  { name: 'graph',        cat: 'Games',      icon: '📉', desc: 'Хувьцааны график', args:[{"key":"ticker","req":false}], example:'A!graph AETH', descEN:"View stock price chart"},
  { name: 'buy',          cat: 'Games',      icon: '🛒', desc: 'Хувьцаа худалдаж авах', args:[{"key":"ticker","req":true},{"key":"amount","req":true}], example:'A!buy AETH 10', descEN:"Buy stocks"},
  { name: 'sell',         cat: 'Games',      icon: '💹', desc: 'Хувьцаа зарах', args:[{"key":"ticker","req":true},{"key":"amount","req":true}], example:'A!sell AETH 5', descEN:"Sell your stocks"},
  { name: 'stock_ticker', cat: 'Games',      icon: '📋', desc: 'Хувьцааны жагсаалт', args:[], example:'', descEN:"List available tickers"},
  { name: 'stock_leaderboard', cat: 'Games', icon: '🥇', desc: 'Хувьцааны лидерборд', args:[], example:'', descEN:"Stock profit leaderboard"},
  { name: 'mafia',        cat: 'Games',      icon: '🕵️', desc: 'Mafia тоглоом', args:[{"key":"player","req":false}], example:'A!mafia', descEN:"Join a Mafia game round"},
  { name: 'mafiacreate',  cat: 'Games',      icon: '🎭', desc: 'Mafia тоглоом үүсгэх (админ)', args:[], example:'', descEN:"Create a Mafia game (admin)"},
  { name: 'mafiastart',   cat: 'Games',      icon: '▶️', desc: 'Mafia-г эхлүүлэх (админ)', args:[], example:'', descEN:"Start the Mafia game (admin)"},
  { name: 'mafiaend',     cat: 'Games',      icon: '⏹️', desc: 'Mafia-г дуусгах (админ)', args:[], example:'', descEN:"End the Mafia game (admin)"},
  { name: 'giveaway',     cat: 'Games',      icon: '🎉', desc: 'Сугалаа явуулах', args:[{"key":"prize","req":true},{"key":"duration","req":true}], example:'A!giveaway Nitro 24h', descEN:"Start a giveaway"},
  { name: 'reroll',       cat: 'Games',      icon: '🔄', desc: 'Сугалааг дахин татах', args:[{"key":"message","req":false}], example:'A!reroll', descEN:"Reroll the giveaway"},
  { name: 'end',          cat: 'Games',      icon: '🔚', desc: 'Сугалааг эрт дуусгах', args:[{"key":"message","req":false}], example:'A!end', descEN:"End a giveaway early"},

  // ---------------- Moderation ----------------
  { name: 'ban',          cat: 'Moderation', icon: '🔨', desc: 'Серверээс банлах', args:[{"key":"user","req":true},{"key":"reason","req":false}], example:'/ban @user Spam', descEN:"Ban a user from the server"},
  { name: 'unban',        cat: 'Moderation', icon: '🔓', desc: 'Баныг авах', args:[{"key":"user","req":true}], example:'/unban @user', descEN:"Unban a user"},
  { name: 'kick',         cat: 'Moderation', icon: '🦶', desc: 'Хөөх', args:[{"key":"user","req":true},{"key":"reason","req":false}], example:'/kick @user', descEN:"Kick a user from the server"},
  { name: 'timeout',      cat: 'Moderation', icon: '⏸️', desc: 'Түр хугацаагаар хаах', args:[{"key":"user","req":true},{"key":"duration","req":true}], example:'/timeout @user 10m', descEN:"Timeout a user temporarily"},
  { name: 'untimeout',    cat: 'Moderation', icon: '▶️', desc: 'Timeout-ыг авах' },
  { name: 'warn',         cat: 'Moderation', icon: '⚠️', desc: 'Сануулга өгөх', args:[{"key":"user","req":true},{"key":"reason","req":false}], example:'/warn @user Breaking rules', descEN:"Issue a warning (admin)"},
  { name: 'unwarn',       cat: 'Moderation', icon: '✅', desc: 'Сануулгыг авах' },
  { name: 'warnings',     cat: 'Moderation', icon: '📃', desc: 'Таны сануулгууд', args:[{"key":"user","req":true}], example:'/warnings @user', descEN:"View a user's warnings"},
  { name: 'warnedusers',  cat: 'Moderation', icon: '👥', desc: 'Сануулгатай хүмүүс (админ)' },
  { name: 'clear',        cat: 'Moderation', icon: '🗑️', desc: 'Мессеж цэвэрлэх (purge)', args:[{"key":"amount","req":true}], example:'/clear 50', descEN:"Bulk-delete messages"},
  { name: 'lock',         cat: 'Moderation', icon: '🔒', desc: 'Суваг түгжих', args:[], example:'', descEN:"Lock a channel (admin)"},
  { name: 'unlock',       cat: 'Moderation', icon: '🔓', desc: 'Суваг тайлах', args:[], example:'', descEN:"Unlock a channel (admin)"},
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
  { name: 'template_create', cat: 'Admin',   icon: '📄', desc: 'Загвар үүсгэх', args:[], example:'', descEN:"Create an embed template (admin)"},
  { name: 'template_edit', cat: 'Admin',     icon: '✏️', desc: 'Загвар засах', args:[{"key":"template","req":true}], example:'', descEN:"Edit a template (admin)"},
  { name: 'template_delete', cat: 'Admin',   icon: '❌', desc: 'Загвар устгах', args:[{"key":"template","req":true}], example:'', descEN:"Delete a template (admin)"},
  { name: 'template_list', cat: 'Admin',     icon: '📑', desc: 'Загварууд харах', args:[], example:'', descEN:"List saved templates"},
  { name: 'template_preview', cat: 'Admin',  icon: '👁️', desc: 'Загвар урьдчилж харах', args:[{"key":"template","req":true}], example:'', descEN:"Preview a template (admin)"},

  // ---------------- Utility ----------------
  { name: 'help',         cat: 'Utility',    icon: '❓', desc: 'Бүх командыг ангиллаар нь', args:[], example:'', descEN:"List all commands by category"},
  { name: 'invite',       cat: 'Utility',    icon: '📨', desc: 'Урилгын холбоос', args:[], example:'', descEN:"Get the bot invite link"},
  { name: 'avatar',       cat: 'Utility',    icon: '🖼️', desc: 'Хүний аватар харах', args:[{"key":"user","req":false}], example:'A!avatar', descEN:"View a user's avatar"},
  { name: 'boost',        cat: 'Utility',    icon: '🚀', desc: 'Boost мэдээлэл', args:[], example:'', descEN:"Server boost info"},
  { name: 'partners',     cat: 'Utility',    icon: '🤝', desc: 'Партнер серверүүд', args:[], example:'', descEN:"Partner server list"},
  { name: 'entries',      cat: 'Utility',    icon: '🎟️', desc: 'Сугалааны оролцогчид', args:[], example:'', descEN:"Giveaway entries list"},
  { name: 'list',         cat: 'Utility',    icon: '📄', desc: 'Жагсаалт харах', args:[], example:'', descEN:"View various lists"},
  { name: 'relationship', cat: 'Utility',    icon: '💞', desc: 'Гэр бүлийн холбоо', args:[{"key":"a","req":true},{"key":"b","req":true}], example:'A!relationship @u1 @u2', descEN:"Relationship between two users"},
  { name: 'placeholders', cat: 'Utility',    icon: '📌', desc: 'Placeholder мэдээлэл', args:[], example:'', descEN:"Placeholder info"},
  { name: 'codes',        cat: 'Utility',    icon: '🔑', desc: 'Промо кодууд', args:[{"key":"code","req":true}], example:'A!codes FREE100', descEN:"Redeem a promo code"},
  { name: 'autoaccept',   cat: 'Utility',    icon: '✔️', desc: 'Автомат зөвшөөрөл', args:[], example:'', descEN:"Toggle auto-accept flows"},
  { name: 'cancel',       cat: 'Utility',    icon: '🛑', desc: 'Урсгал цуцлах', args:[], example:'', descEN:"Cancel any active flow"},
];

/* Command policy: Admin and Moderation are slash-only; all other public commands use the text prefix. */
const TYPED_COMMANDS = COMMANDS.map(c => ({
  ...c,
  type: (c.cat === 'Admin' || c.cat === 'Moderation') ? 'slash' : 'text',
}));
/* Dedupe (guard) and export */
const seen = new Set();
window.COMMAND_LIST = TYPED_COMMANDS.filter(c => {
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
