/* ============================================================
   𝓐𝓮𝓽𝓱𝓮𝓻 蒼Қ — Command catalog (from bot source code, 2026-08-16)
   Categories mirror the real cog grouping of the bot.
   ============================================================ */
const COMMANDS = [
  // ---------------- Economy ----------------
  { name: 'daily',        cat: 'Economy',    icon: '📅', desc: 'Өдөр бүрийн мөнгөний урамшуулал', descEN:"Claim your daily coin reward", args:[], example:'A!daily'},
  { name: 'work',         cat: 'Economy',    icon: '💼', desc: 'Ажиллаж мөнгө ол', descEN:"Work to earn coins", args:[], example:'A!work'},
  { name: 'balance',      cat: 'Economy',    icon: '💳', desc: 'Таны мөнгөн дүн', descEN:"View your coin balance", args:[], example:'A!balance'},
  { name: 'pay',          cat: 'Economy',    icon: '💸', desc: 'Нөгөө хүн рүү мөнгө шилжүүл', descEN:"Send coins to another user", args:[{'key':'user', req:true}, {'key':'amount', req:true}], example:'A!pay @user 500'},
  { name: 'rob',          cat: 'Economy',    icon: '🦹', desc: 'Нэгнээсээ хулгайлах (эрсдэлтэй!)', descEN:"Attempt to rob another user (risky!)", args:[{'key':'user', req:true}], example:'A!rob @user'},
  { name: 'workphrase',   cat: 'Economy',    icon: '📝', desc: 'Ажлын үгсийн жагсаалт тохируулах', descEN:"Customize your work phrases", args:[], example:'A!workphrase'},
  { name: 'addmoney',     cat: 'Economy',    icon: '➕', desc: 'Хэрэглэгчид мөнгө нэмэх (админ)', descEN:"Add coins to a user (admin)", args:[{'key':'user', req:true}, {'key':'amount', req:true}], example:'A!addmoney @user 1000'},
  { name: 'removemoney',  cat: 'Economy',    icon: '➖', desc: 'Хэрэглэгчээс мөнгө хасах (админ)', descEN:"Remove coins from a user (admin)", args:[{'key':'user', req:true}, {'key':'amount', req:true}], example:'A!removemoney @user 500'},
  { name: 'market',       cat: 'Economy',    icon: '🏪', desc: 'Кафегийн дэлгүүр, хоол/уух зүйлс', descEN:"Browse the cafe shop items", args:[], example:'A!market'},
  { name: 'dine',         cat: 'Economy',    icon: '🍽️', desc: 'Кафед хоол идэх', descEN:"Eat a meal at the cafe (spend coins)", args:[{'key':'item'}], example:'A!dine burger'},
  { name: 'cafe',         cat: 'Economy',    icon: '☕', desc: 'Кафегийн цэс ба мэдээлэл', descEN:"View cafe menu and info", args:[], example:'A!cafe'},

  // ---------------- Leveling ----------------
  { name: 'rank',         cat: 'Leveling',   icon: '🏅', desc: 'Таны түвшин ба XP', descEN:"View your rank and XP", args:[], example:'A!rank'},
  { name: 'grank',        cat: 'Leveling',   icon: '📊', desc: 'Server-ийн XP жагсаалт', descEN:"View the global XP leaderboard", args:[], example:'A!grank'},
  { name: 'leaderboard',  cat: 'Leveling',   icon: '🏆', desc: 'Түвшингийн тэргүүнүүд', descEN:"Show the top users by rank", args:[], example:'A!leaderboard'},
  { name: 'serveractivity', cat: 'Leveling', icon: '📈', desc: 'Server-ийн идэвхтэй байдал', descEN:"View server activity stats", args:[], example:'A!serveractivity'},
  { name: 'addxp',        cat: 'Leveling',   icon: '✨', desc: 'Хэрэглэгчид XP нэмэх (админ)', descEN:"Add XP to a user (admin)", args:[{'key':'user', req:true}, {'key':'amount', req:true}], example:'A!addxp @user 100'},
  { name: 'removexp',     cat: 'Leveling',   icon: '📉', desc: 'XP хасах (админ)', descEN:"Remove XP from a user (admin)", args:[{'key':'user', req:true}, {'key':'amount', req:true}], example:'A!removexp @user 50'},
  { name: 'leveling_setup', cat: 'Leveling', icon: '⚙️', desc: 'Leveling-ийн тохиргоо (админ)', descEN:"Configure leveling settings (admin)", args:[], example:'A!leveling_setup'},
  { name: 'invites',      cat: 'Leveling',   icon: '📨', desc: 'Таны урилгууд ба XP урамшуулал', descEN:"View your invites and invite XP", args:[], example:'A!invites'},
  { name: 'inviter',      cat: 'Leveling',   icon: '🔗', desc: 'Хэн таныг урьсныг харах', descEN:"See who invited you", args:[], example:'A!inviter'},

  // ---------------- Social / Marriage ----------------
  { name: 'propose',      cat: 'Social',     icon: '💍', desc: 'Хайртай хүнээсээ гэрлэлтийн санал тавь', descEN:"Propose marriage to someone", args:[{'key':'user', req:true}], example:'A!propose @user'},
  { name: 'marry',        cat: 'Social',     icon: '💑', desc: 'Гэрлэх', descEN:"Marry your partner", args:[], example:'A!marry'},
  { name: 'divorce',      cat: 'Social',     icon: '💔', desc: 'Салалт', descEN:"End your marriage", args:[], example:'A!divorce'},
  { name: 'spouse',       cat: 'Social',     icon: '👫', desc: 'Таны ханийн мэдээлэл', descEN:"View your spouse info", args:[], example:'A!spouse'},
  { name: 'love',         cat: 'Social',     icon: '❤️', desc: 'Хайрын хэмжээ харах', descEN:"Check your love level", args:[{'key':'user', req:true}], example:'A!love @user'},
  { name: 'gift',         cat: 'Social',     icon: '🎁', desc: 'Ханиандаа бэлэг өгөх', descEN:"Send a gift to your spouse", args:[{'key':'user', req:true}, {'key':'item', req:true}], example:'A!gift @user rose'},
  { name: 'adopt',        cat: 'Social',     icon: '👶', desc: 'Хүүхэд үрчлэх', descEN:"Adopt a child", args:[], example:'A!adopt'},
  { name: 'disown',       cat: 'Social',     icon: '🚪', desc: 'Хүүхдээсээ татгалзах', descEN:"Disown a child", args:[{'key':'child', req:true}], example:'A!disown @child'},
  { name: 'children',     cat: 'Social',     icon: '🧸', desc: 'Таны хүүхдүүд', descEN:"List your children", args:[], example:'A!children'},
  { name: 'makeparent',   cat: 'Social',     icon: '👨‍👩‍👧', desc: 'Гэр бүлийн эцэг/эх болгох', descEN:"Assign parents to a child (admin)", args:[{'key':'user', req:true}], example:'A!makeparent @user'},
  { name: 'familytree',   cat: 'Social',     icon: '🌳', desc: 'Гэр бүлийн мод', descEN:"View your family tree", args:[{'key':'user'}], example:'A!familytree @user'},
  { name: 'tree',         cat: 'Social',     icon: '🍀', desc: 'Гэр бүлийн модны товчлол', descEN:"Family tree summary", args:[], example:'A!tree'},
  { name: 'fulltree',     cat: 'Social',     icon: '🌲', desc: 'Бүрэн гэр бүлийн мод', descEN:"Full family tree view", args:[{'key':'user'}], example:'A!fulltree @user'},
  { name: 'marriage_setup', cat: 'Social',   icon: '🔧', desc: 'Гэрлэлийн тохиргоо (админ)', descEN:"Marriage system settings (admin)", args:[], example:'A!marriage_setup'},
  { name: 'marriagepro',  cat: 'Social',     icon: '🏛️', desc: 'Гэрлэлийн профиль', descEN:"Your marriage profile", args:[], example:'A!marriagepro'},
  { name: 'confess',      cat: 'Social',     icon: '🤫', desc: 'Аноним илчлэл', descEN:"Anonymous confession in the channel", args:[], example:'A!confess'},

  // ---------------- Games ----------------
  { name: 'gamble',       cat: 'Games',      icon: '🎰', desc: 'Шуудайнд мөнгө тавих', descEN:"Gambling with buttons (high/low)", args:[{'key':'amount', req:true}], example:'A!gamble 500'},
  { name: 'coinflip',     cat: 'Games',      icon: '🪙', desc: 'Зоос шидэх', descEN:"Flip a coin (heads/tails)", args:[{'key':'side', req:true}, {'key':'amount', req:true}], example:'A!coinflip heads 200'},
  { name: 'slots',        cat: 'Games',      icon: '🎰', desc: 'Слот машин', descEN:"Play the slot machine", args:[], example:'A!slots'},
  { name: 'roulette',     cat: 'Games',      icon: '🎡', desc: 'Рулетка', descEN:"Play roulette", args:[{'key':'bet', req:true}, {'key':'amount', req:true}], example:'A!roulette red 100'},
  { name: 'dice',         cat: 'Games',      icon: '🎲', desc: 'Шоо шидэх', descEN:"Roll dice against the bot", args:[], example:'A!dice'},
  { name: 'rps',          cat: 'Games',      icon: '✊', desc: 'Чулуу-цаас-хайч', descEN:"Rock-paper-scissors vs the bot", args:[{'key':'user', req:true}, {'key':'amount', req:true}], example:'A!rps @user 100'},
  { name: 'mines',        cat: 'Games',      icon: '💣', desc: 'Уурхайн тоглоом', descEN:"Minesweeper-style mine game", args:[{'key':'bet', req:true}, {'key':'amount', req:true}], example:'A!mines hard 200'},
  { name: 'counting',     cat: 'Games',      icon: '🔢', desc: 'Тоо тоолох дуулаан', descEN:"Counting challenge (1,2,3...) with members", args:[], example:'A!counting'},
  { name: 'count_stats_server', cat: 'Games', icon: '📊', desc: 'Тооллын статистик', descEN:"Server counting stats", args:[], example:'A!count_stats_server'},
  { name: 'pvp',          cat: 'Games',      icon: '⚔️', desc: 'Тоглогч хоорондын тулаан', descEN:"Duel another player", args:[{'key':'user', req:true}, {'key':'amount', req:true}], example:'A!pvp @user 300'},
  { name: 'trade',        cat: 'Games',      icon: '🔄', desc: 'Бараа солилцоо', descEN:"Trade items with another user", args:[{'key':'user', req:true}], example:'A!trade @user'},
  { name: 'marketplace',  cat: 'Games',      icon: '🏬', desc: 'Зарын зах зээл', descEN:"Open the item marketplace", args:[], example:'A!marketplace'},
  { name: 'mp',           cat: 'Games',      icon: '🛍️', desc: 'Marketplace-ийн товчлол', descEN:"Marketplace shortcut", args:[], example:'A!mp'},
  { name: 'stock',        cat: 'Games',      icon: '📈', desc: 'Хувьцааны мэдээлэл', descEN:"View stock market info", args:[{'key':'ticker', req:true}], example:'A!stock AAPL'},
  { name: 'graph',        cat: 'Games',      icon: '📉', desc: 'Хувьцааны график', descEN:"View stock price chart", args:[{'key':'ticker', req:true}], example:'A!graph AAPL'},
  { name: 'buy',          cat: 'Games',      icon: '🛒', desc: 'Хувьцаа худалдаж авах', descEN:"Buy stocks", args:[{'key':'ticker', req:true}, {'key':'shares', req:true}], example:'A!buy AAPL 10'},
  { name: 'sell',         cat: 'Games',      icon: '💹', desc: 'Хувьцаа зарах', descEN:"Sell your stocks", args:[{'key':'ticker', req:true}, {'key':'shares', req:true}], example:'A!sell AAPL 5'},
  { name: 'stock_ticker', cat: 'Games',      icon: '📋', desc: 'Хувьцааны жагсаалт', descEN:"List available tickers", args:[], example:'A!stock_ticker'},
  { name: 'stock_leaderboard', cat: 'Games', icon: '🥇', desc: 'Хувьцааны лидерборд', descEN:"Stock profit leaderboard", args:[], example:'A!stock_leaderboard'},
  { name: 'mafia',        cat: 'Games',      icon: '🕵️', desc: 'Mafia тоглоом', descEN:"Join a Mafia game round", args:[], example:'A!mafia'},
  { name: 'mafiacreate',  cat: 'Games',      icon: '🎭', desc: 'Mafia тоглоом үүсгэх (админ)', descEN:"Create a Mafia game (admin)", args:[], example:'A!mafiacreate'},
  { name: 'mafiastart',   cat: 'Games',      icon: '▶️', desc: 'Mafia-г эхлүүлэх (админ)', descEN:"Start the Mafia game (admin)", args:[], example:'A!mafiastart'},
  { name: 'mafiaend',     cat: 'Games',      icon: '⏹️', desc: 'Mafia-г дуусгах (админ)', descEN:"End the Mafia game (admin)", args:[], example:'A!mafiaend'},
  { name: 'giveaway',     cat: 'Games',      icon: '🎉', desc: 'Сугалаа явуулах', descEN:"Start a giveaway", args:[], example:'A!giveaway'},
  { name: 'reroll',       cat: 'Games',      icon: '🔄', desc: 'Сугалааг дахин татах', descEN:"Reroll the giveaway", args:[{'key':'msgid', req:true}], example:'A!reroll 1234567890'},
  { name: 'end',          cat: 'Games',      icon: '🔚', desc: 'Сугалааг эрт дуусгах', args:[{"key":"message","req":false}], example:'A!end', descEN:"End a giveaway early"},

  // ---------------- Moderation ----------------
  { name: 'ban',          cat: 'Moderation', icon: '🔨', desc: 'Серверээс банлах', descEN:"Ban a user from the server", args:[{'key':'user', req:true}, {'key':'reason'}], example:'A!ban @user spam'},
  { name: 'unban',        cat: 'Moderation', icon: '🔓', desc: 'Баныг авах', descEN:"Unban a user", args:[{'key':'user', req:true}], example:'A!unban @user'},
  { name: 'kick',         cat: 'Moderation', icon: '🦶', desc: 'Хөөх', descEN:"Kick a user from the server", args:[{'key':'user', req:true}, {'key':'reason'}], example:'A!kick @user'},
  { name: 'timeout',      cat: 'Moderation', icon: '⏸️', desc: 'Түр хугацаагаар хаах', descEN:"Timeout a user temporarily", args:[{'key':'user', req:true}, {'key':'duration', req:true}], example:'A!timeout @user 10m'},
  { name: 'untimeout',    cat: 'Moderation', icon: '▶️', desc: 'Timeout-ыг авах' , args:[{'key':'user', req:true}], example:'A!untimeout @user', descEN:"Remove a member's timeout"},
  { name: 'warn',         cat: 'Moderation', icon: '⚠️', desc: 'Сануулга өгөх', descEN:"Issue a warning (admin)", args:[{'key':'user', req:true}, {'key':'reason'}], example:'A!warn @user'},
  { name: 'unwarn',       cat: 'Moderation', icon: '✅', desc: 'Сануулгыг авах' , args:[{'key':'user', req:true}, {'key':'warnid', req:true}], example:'A!unwarn @user 1', descEN:"Remove a specific warning from a member"},
  { name: 'warnings',     cat: 'Moderation', icon: '📃', desc: 'Таны сануулгууд', descEN:"View a user's warnings", args:[{'key':'user', req:true}], example:'A!warnings @user'},
  { name: 'warnedusers',  cat: 'Moderation', icon: '👥', desc: 'Сануулгатай хүмүүс (админ)' , args:[], example:'A!warnedusers', descEN:"Show all warned members in the server"},
  { name: 'clear',        cat: 'Moderation', icon: '🗑️', desc: 'Мессеж цэвэрлэх (purge)', descEN:"Bulk-delete messages", args:[{'key':'amount', req:true}], example:'A!clear 25'},
  { name: 'lock',         cat: 'Moderation', icon: '🔒', desc: 'Суваг түгжих', descEN:"Lock a channel (admin)", args:[{'key':'channel'}], example:'A!lock'},
  { name: 'unlock',       cat: 'Moderation', icon: '🔓', desc: 'Суваг тайлах', descEN:"Unlock a channel (admin)", args:[{'key':'channel'}], example:'A!unlock'},
  { name: 'banlist',      cat: 'Moderation', icon: '📋', desc: 'Бан жагсаалт' , args:[], example:'A!banlist', descEN:"Show the list of banned users"},
  { name: 'set_log_channel', cat: 'Moderation', icon: '📢', desc: 'Mod-log сувгийг тохируулах' , args:[], example:'A!set_log_channel', descEN:"Set the moderation log channel"},

  // ---------------- Admin ----------------
  { name: 'status',       cat: 'Admin',      icon: '🩺', desc: 'Ботын CPU/RAM/системийн төлөв' , args:[], example:'A!status', descEN:"Show current bot status, uptime and health"},
  { name: 'info',         cat: 'Admin',      icon: 'ℹ️', desc: 'Ботын мэдээлэл' , args:[], example:'A!info', descEN:"Show detailed bot information and version"},
  { name: 'rolelist',     cat: 'Admin',      icon: '🎭', desc: 'Серверийн ролийн жагсаалт' , args:[], example:'A!rolelist', descEN:"List all roles in the server with member counts"},
  { name: 'announce',     cat: 'Admin',      icon: '📣', desc: 'Мэдэгдэл илгээх' , args:[{'key':'channel', req:true}, {'key':'message', req:true}], example:'A!announce #announcements Hello!', descEN:"Send an announcement embed to a channel"},
  { name: 'greeting_set', cat: 'Admin',      icon: '👋', desc: 'Welcome/Goodbye тохируулах' , args:[], example:'A!greeting_set', descEN:"Configure the welcome message (channel, text, image)"},
  { name: 'greeting_status', cat: 'Admin',   icon: '✅', desc: 'Тавилгын төлөв харах' , args:[], example:'A!greeting_status', descEN:"Show current greeting configuration"},
  { name: 'greeting_toggle', cat: 'Admin',   icon: '🔀', desc: 'Тавилгыг асаах/унтраах' , args:[], example:'A!greeting_toggle', descEN:"Enable or disable welcome messages"},
  { name: 'greeting_reset', cat: 'Admin',    icon: '🔁', desc: 'Тавилгыг шинэчлэх' , args:[], example:'A!greeting_reset', descEN:"Reset greeting settings to defaults"},
  { name: 'setup',        cat: 'Admin',      icon: '🚀', desc: 'Ботын анхны тохируулга' , args:[], example:'A!setup', descEN:"Interactive bot setup wizard for the server"},
  { name: 'panel',        cat: 'Admin',      icon: '🎛️', desc: 'Ботын удирдлагын самбар' , args:[], example:'A!panel', descEN:"Show the admin control panel embed"},
  { name: 'stats',        cat: 'Admin',      icon: '📊', desc: 'Дэлгэрэнгүй статистик' , args:[], example:'A!stats', descEN:"Show detailed server statistics"},
  { name: 'staff_setup',  cat: 'Admin',      icon: '👮', desc: 'Staff баг тохируулах' , args:[], example:'A!staff_setup', descEN:"Configure staff tracking for the server"},
  { name: 'staff_status', cat: 'Admin',      icon: '📟', desc: 'Staff-ийн төлөв' , args:[], example:'A!staff_status', descEN:"Show staff activity status"},
  { name: 'staff_counts', cat: 'Admin',      icon: '🔢', desc: 'Staff-ийн тоо' , args:[], example:'A!staff_counts', descEN:"Show message/count statistics per staff member"},
  { name: 'addlabel',     cat: 'Admin',      icon: '🏷️', desc: 'Staff шошго нэмэх' , args:[], example:'A!addlabel', descEN:"Add a custom label/template"},
  { name: 'removelabel',  cat: 'Admin',      icon: '✂️', desc: 'Staff шошго устгах' , args:[], example:'A!removelabel', descEN:"Remove a custom label/template"},
  { name: 'avatar_config', cat: 'Admin',     icon: '🖼️', desc: 'Аватар logger тохиргоо' , args:[], example:'A!avatar_config', descEN:"Configure the avatar change logger"},
  { name: 'confess_setup', cat: 'Admin',     icon: '🕵️', desc: 'Confessions тохируулах' , args:[], example:'A!confess_setup', descEN:"Configure the anonymous confession channel"},
  { name: 'confess_stats', cat: 'Admin',     icon: '📊', desc: 'Confessions статистик' , args:[], example:'A!confess_stats', descEN:"Show confession statistics"},
  { name: 'confess_delete', cat: 'Admin',    icon: '🗑️', desc: 'Илчлэл устгах' , args:[{'key':'msgid', req:true}], example:'A!confess_delete 1234567890', descEN:"Delete a confession message by ID"},
  { name: 'confess_blacklist', cat: 'Admin', icon: '⛔', desc: 'Илчлэлийн хар жагсаалт' , args:[], example:'A!confess_blacklist', descEN:"Manage the confession user blacklist"},
  { name: 'counting_setup', cat: 'Admin',    icon: '⚙️', desc: 'Counting тохируулах' , args:[], example:'A!counting_setup', descEN:"Configure the counting channel rules"},
  { name: 'count_stats_user', cat: 'Admin',  icon: '👤', desc: 'Хэрэглэгчийн тооллын статистик' , args:[{'key':'user', req:true}], example:'A!count_stats_user @user', descEN:"Show a member's counting statistics"},
  { name: 'voicesetup',   cat: 'Admin',      icon: '🎙️', desc: 'Temp voice тохируулах' , args:[], example:'A!voicesetup', descEN:"Configure the temporary voice channel system"},
  { name: 'voicesettings', cat: 'Admin',     icon: '🔊', desc: 'Voice багийн тохиргоо' , args:[], example:'A!voicesettings', descEN:"Show current temporary voice settings"},
  { name: 'template_create', cat: 'Admin',   icon: '📄', desc: 'Загвар үүсгэх', descEN:"Create an embed template (admin)", args:[{'key':'name', req:true}], example:'A!template_create VIP'},
  { name: 'template_edit', cat: 'Admin',     icon: '✏️', desc: 'Загвар засах', descEN:"Edit a template (admin)", args:[{'key':'name', req:true}], example:'A!template_edit VIP'},
  { name: 'template_delete', cat: 'Admin',   icon: '❌', desc: 'Загвар устгах', descEN:"Delete a template (admin)", args:[{'key':'name', req:true}], example:'A!template_delete VIP'},
  { name: 'template_list', cat: 'Admin',     icon: '📑', desc: 'Загварууд харах', descEN:"List saved templates", args:[], example:'A!template_list'},
  { name: 'template_preview', cat: 'Admin',  icon: '👁️', desc: 'Загвар урьдчилж харах', descEN:"Preview a template (admin)", args:[{'key':'name', req:true}], example:'A!template_preview VIP'},

  // ---------------- Utility ----------------
  { name: 'help',         cat: 'Utility',    icon: '❓', desc: 'Бүх командыг ангиллаар нь', descEN:"List all commands by category", args:[], example:'A!help'},
  { name: 'invite',       cat: 'Utility',    icon: '📨', desc: 'Урилгын холбоос', descEN:"Get the bot invite link", args:[], example:'A!invite'},
  { name: 'avatar',       cat: 'Utility',    icon: '🖼️', desc: 'Хүний аватар харах', args:[{"key":"user","req":false}], example:'A!avatar', descEN:"View a user's avatar"},
  { name: 'boost',        cat: 'Utility',    icon: '🚀', desc: 'Boost мэдээлэл', descEN:"Server boost info", args:[], example:'A!boost'},
  { name: 'partners',     cat: 'Utility',    icon: '🤝', desc: 'Партнер серверүүд', descEN:"Partner server list", args:[], example:'A!partners'},
  { name: 'entries',      cat: 'Utility',    icon: '🎟️', desc: 'Сугалааны оролцогчид', descEN:"Giveaway entries list", args:[], example:'A!entries'},
  { name: 'list',         cat: 'Utility',    icon: '📄', desc: 'Жагсаалт харах', descEN:"View various lists", args:[], example:'A!list'},
  { name: 'relationship', cat: 'Utility',    icon: '💞', desc: 'Гэр бүлийн холбоо', args:[{"key":"a","req":true},{"key":"b","req":true}], example:'A!relationship @u1 @u2', descEN:"Relationship between two users"},
  { name: 'placeholders', cat: 'Utility',    icon: '📌', desc: 'Placeholder мэдээлэл', descEN:"Placeholder info", args:[], example:'A!placeholders'},
  { name: 'codes',        cat: 'Utility',    icon: '🔑', desc: 'Промо кодууд', args:[{"key":"code","req":true}], example:'A!codes FREE100', descEN:"Redeem a promo code"},
  { name: 'autoaccept',   cat: 'Utility',    icon: '✔️', desc: 'Автомат зөвшөөрөл', descEN:"Toggle auto-accept flows", args:[], example:'A!autoaccept'},
  { name: 'cancel',       cat: 'Utility',    icon: '🛑', desc: 'Урсгал цуцлах', descEN:"Cancel any active flow", args:[], example:'A!cancel'},
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
  all:        { label: 'Бүгд',        labelEN: 'All',           color: '#89B4FA', icon: '🗂️' },
  Economy:    { label: 'Economy',     labelEN: 'Economy',       color: '#89B4FA', icon: '💰' },
  Leveling:   { label: 'Leveling',    labelEN: 'Leveling',      color: '#94E2D5', icon: '📊' },
  Social:     { label: 'Гэр бүл',     labelEN: 'Family',        color: '#F38BA8', icon: '💍' },
  Games:      { label: 'Тоглоом',     labelEN: 'Games',         color: '#FAB387', icon: '🎲' },
  Moderation: { label: 'Модерац',     labelEN: 'Moderation',    color: '#A6E3A1', icon: '🛡️' },
  Admin:      { label: 'Админ',       labelEN: 'Admin',         color: '#B4BEFE', icon: '⚙️' },
  Utility:    { label: 'Бусад',       labelEN: 'Utility',       color: '#8C8FA1', icon: '🔧' },
};
