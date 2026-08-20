import discord
from discord.ext import commands
from discord import app_commands, ui
from utils.branding import BOT_NAME, BOT_FOOTER

# ═══════════════════════════════════════════════════════════════════════════════
# БҮХ КОМАНДЫН ДЭЛГЭРЭНГҮЙ ТОДОРХОЙЛОЛТ (шинэчлэгдсэн, алдаагүй)
# ═══════════════════════════════════════════════════════════════════════════════
COMMAND_INFO = {
    # ── Эдийн засаг ──
    "balance": {
        "category": "Эдийн засаг",
        "description_en": "Check your wallet and bank balance.",
        "description_mn": "Таны гар дээрх мөнгө болон банкны үлдэгдлийг харна.",
        "usage": "A!balance [@хэрэглэгч]",
        "examples": ["A!balance", "A!balance @Bold"],
    },
    "work": {
        "category": "Эдийн засаг",
        "description_en": "Work to earn money. Higher level = better job.",
        "description_mn": "Ажил хийж мөнгө олох. Түвшин өндөр байх тусмаа сайн ажил.",
        "usage": "A!work [өөрийн текст]",
        "examples": ["A!work", "A!work кофе чанаж байна"],
    },
    "daily": {
        "category": "Эдийн засаг",
        "description_en": "Claim your daily reward once every 24 hours.",
        "description_mn": "24 цаг тутамд нэг удаа өдрийн урамшуулал авах.",
        "usage": "A!daily",
        "examples": ["A!daily"],
    },
    "deposit": {
        "category": "Эдийн засаг",
        "description_en": "Deposit money into your bank account.",
        "description_mn": "Гар дээрх мөнгөө банкинд хийх.",
        "usage": "A!deposit <дүн/all>",
        "examples": ["A!deposit 5000", "A!deposit all"],
    },
    "withdraw": {
        "category": "Эдийн засаг",
        "description_en": "Withdraw money from your bank account.",
        "description_mn": "Банкнаас мөнгө гаргах.",
        "usage": "A!withdraw <дүн/all>",
        "examples": ["A!withdraw 5000", "A!withdraw all"],
    },
    "transfer": {
        "category": "Эдийн засаг",
        "description_en": "Send money to another user.",
        "description_mn": "Бусад хэрэглэгчид мөнгө илгээх.",
        "usage": "A!transfer @хэрэглэгч <дүн/all>",
        "examples": ["A!transfer @Bold 5000", "A!transfer @Bold all"],
    },
    "bankprotect": {
        "category": "Эдийн засаг",
        "description_en": "Protect your bank from robbers for 2 hours.",
        "description_mn": "Банкаа 2 цагийн турш дээрэмчдээс хамгаална.",
        "usage": "A!bankprotect",
        "examples": ["A!bankprotect"],
    },
    "eat": {
        "category": "Эдийн засаг",
        "description_en": "Eat food to reduce hunger.",
        "description_mn": "Өлсгөлөнгөө багасгахын тулд хоол идэх.",
        "usage": "A!eat",
        "examples": ["A!eat"],
    },
    "relax": {
        "category": "Эдийн засаг",
        "description_en": "Relax to reduce mood/stress.",
        "description_mn": "Амарч, уур бухимдлаа багасгах.",
        "usage": "A!relax",
        "examples": ["A!relax"],
    },

    # ── Тоглоом ──
    "gamble": {
        "category": "Тоглоом",
        "description_en": "Gamble your money with a 30% chance to win.",
        "description_mn": "30% хожих магадлалтай мөрийтэй тоглоом.",
        "usage": "A!gamble <дүн/all>",
        "examples": ["A!gamble 1000", "A!gamble all"],
    },
    "coinflip": {
        "category": "Тоглоом",
        "description_en": "Flip a coin and bet on heads or tails.",
        "description_mn": "Зоос шидэж, heads эсвэл tails гэж таах.",
        "usage": "A!coinflip <heads/tails> <дүн>",
        "examples": ["A!coinflip heads 500", "A!coinflip tails all"],
    },
    "slot": {
        "category": "Тоглоом",
        "description_en": "Play the slot machine. 3 same symbols = JACKPOT!",
        "description_mn": "Слот машин тоглох. 3 ижил тэмдэгт = JACKPOT!",
        "usage": "A!slot <дүн>",
        "examples": ["A!slot 1000", "A!slot 5000"],
    },
    "roulette": {
        "category": "Тоглоом",
        "description_en": "Play roulette. Bet on red, black, or green.",
        "description_mn": "Рулет тоглох. Улаан, хар, ногоон дээр бооцоо тавих.",
        "usage": "A!roulette <red/black/green> <дүн>",
        "examples": ["A!roulette red 1000", "A!roulette green 500"],
    },
    "dice": {
        "category": "Тоглоом",
        "description_en": "Guess the dice roll (1-6) to win 6x your bet.",
        "description_mn": "Шооны тоог тааж (1-6) бооцооны 6 дахин хожих.",
        "usage": "A!dice <1-6> <дүн>",
        "examples": ["A!dice 3 500", "A!dice 6 1000"],
    },
    "rps": {
        "category": "Тоглоом",
        "description_en": "Play Rock Paper Scissors against the bot.",
        "description_mn": "Боттой чулуу, даавуу, хайч тоглох.",
        "usage": "A!rps <rock/paper/scissors> <дүн>",
        "examples": ["A!rps rock 500", "A!rps scissors 1000"],
    },
    "numberguess": {
        "category": "Тоглоом",
        "description_en": "Guess a number (1-10) within 10 seconds.",
        "description_mn": "Ботны бодсон тоог (1-10) 10 секундэд таах.",
        "usage": "A!numberguess <дүн>",
        "examples": ["A!numberguess 500"],
    },
    "trivia": {
        "category": "Тоглоом",
        "description_en": "Answer a trivia question to earn XP.",
        "description_mn": "Асуултанд зөв хариулж XP авах.",
        "usage": "A!trivia",
        "examples": ["A!trivia"],
    },

    # ── Казино ──
    "blackjack": {
        "category": "Казино",
        "description_en": "Play Blackjack against the dealer. Get close to 21.",
        "description_mn": "Дилертэй блэкжэк тоглох. 21-д ойртох.",
        "usage": "A!blackjack <дүн>",
        "examples": ["A!blackjack 500", "A!blackjack all"],
    },
    "highlow": {
        "category": "Казино",
        "description_en": "Guess if the next number is higher or lower.",
        "description_mn": "Дараагийн тоо өмнөхөөсөө их эсвэл бага эсэхийг таах.",
        "usage": "A!highlow <дүн> [higher/lower]",
        "examples": ["A!highlow 500", "A!highlow 1000 higher"],
    },
    "rob": {
        "category": "Казино",
        "description_en": "Attempt to rob another user. 30% success rate.",
        "description_mn": "Хэрэглэгчийг дээрэмдэх оролдлого. 30% амжилттай.",
        "usage": "A!rob @хэрэглэгч",
        "examples": ["A!rob @Bold"],
    },
    "hack": {
        "category": "Казино",
        "description_en": "Hack a user's bank account. Low success rate.",
        "description_mn": "Банкны данс хакердах. Амжилт багатай.",
        "usage": "A!hack @хэрэглэгч",
        "examples": ["A!hack @Bold"],
    },

    # ── Хөгжилтэй ──
    "hug": {"category": "Хөгжилтэй", "description_en": "Hug someone!", "description_mn": "Хэн нэгнийг тэврэх!", "usage": "A!hug [@хэрэглэгч]", "examples": ["A!hug", "A!hug @Bold"]},
    "kiss": {"category": "Хөгжилтэй", "description_en": "Kiss someone!", "description_mn": "Хэн нэгнийг үнсэх!", "usage": "A!kiss [@хэрэглэгч]", "examples": ["A!kiss", "A!kiss @Bold"]},
    "slap": {"category": "Хөгжилтэй", "description_en": "Slap someone!", "description_mn": "Хэн нэгнийг алгадах!", "usage": "A!slap [@хэрэглэгч]", "examples": ["A!slap", "A!slap @Bold"]},
    "pat": {"category": "Хөгжилтэй", "description_en": "Pat someone's head.", "description_mn": "Хэн нэгний толгойг илэх.", "usage": "A!pat [@хэрэглэгч]", "examples": ["A!pat", "A!pat @Bold"]},
    "cuddle": {"category": "Хөгжилтэй", "description_en": "Cuddle with someone!", "description_mn": "Хэн нэгэнтэй зууралдах!", "usage": "A!cuddle [@хэрэглэгч]", "examples": ["A!cuddle", "A!cuddle @Bold"]},
    "bite": {"category": "Хөгжилтэй", "description_en": "Bite someone playfully.", "description_mn": "Хэн нэгнийг зөөлөн хазах.", "usage": "A!bite [@хэрэглэгч]", "examples": ["A!bite", "A!bite @Bold"]},
    "poke": {"category": "Хөгжилтэй", "description_en": "Poke someone to get their attention.", "description_mn": "Хэн нэгнийг хатгаж анхаарлыг нь татах.", "usage": "A!poke [@хэрэглэгч]", "examples": ["A!poke", "A!poke @Bold"]},
    "wave": {"category": "Хөгжилтэй", "description_en": "Wave at someone.", "description_mn": "Хэн нэгэнд даллах.", "usage": "A!wave [@хэрэглэгч]", "examples": ["A!wave", "A!wave @Bold"]},
    "punch": {"category": "Хөгжилтэй", "description_en": "Punch someone!", "description_mn": "Хэн нэгнийг цохих!", "usage": "A!punch [@хэрэглэгч]", "examples": ["A!punch", "A!punch @Bold"]},
    "boop": {"category": "Хөгжилтэй", "description_en": "Boop someone's nose.", "description_mn": "Хэн нэгний хамарт буп хийх.", "usage": "A!boop [@хэрэглэгч]", "examples": ["A!boop", "A!boop @Bold"]},
    "bully": {"category": "Хөгжилтэй", "description_en": "Bully someone (just for fun).", "description_mn": "Хэн нэгнийг хошигнон булимдах.", "usage": "A!bully [@хэрэглэгч]", "examples": ["A!bully", "A!bully @Bold"]},
    "handhold": {"category": "Хөгжилтэй", "description_en": "Hold hands with someone.", "description_mn": "Хэн нэгэнтэй гар барих.", "usage": "A!handhold [@хэрэглэгч]", "examples": ["A!handhold", "A!handhold @Bold"]},
    "stare": {"category": "Хөгжилтэй", "description_en": "Stare intently at someone.", "description_mn": "Хэн нэгнийг ширтэх.", "usage": "A!stare [@хэрэглэгч]", "examples": ["A!stare", "A!stare @Bold"]},
    "highfive": {"category": "Хөгжилтэй", "description_en": "Give someone a high-five.", "description_mn": "Хэн нэгэнд өндөр тавих.", "usage": "A!highfive [@хэрэглэгч]", "examples": ["A!highfive", "A!highfive @Bold"]},
    "snuggle": {"category": "Хөгжилтэй", "description_en": "Snuggle up with someone.", "description_mn": "Хэн нэгэнтэй зууран дулаацах.", "usage": "A!snuggle [@хэрэглэгч]", "examples": ["A!snuggle", "A!snuggle @Bold"]},
    "cry": {"category": "Хөгжилтэй", "description_en": "Cry...", "description_mn": "Уйлах...", "usage": "A!cry", "examples": ["A!cry"]},
    "dance": {"category": "Хөгжилтэй", "description_en": "Show off your dance moves.", "description_mn": "Бүжиглэх чадвараа харуулах.", "usage": "A!dance", "examples": ["A!dance"]},
    "laugh": {"category": "Хөгжилтэй", "description_en": "Laugh out loud!", "description_mn": "Чангаар инээх!", "usage": "A!laugh", "examples": ["A!laugh"]},
    "sleep": {"category": "Хөгжилтэй", "description_en": "Go to sleep.", "description_mn": "Унтах.", "usage": "A!sleep", "examples": ["A!sleep"]},
    "think": {"category": "Хөгжилтэй", "description_en": "Ponder something deeply.", "description_mn": "Гүн бодолд автах.", "usage": "A!think", "examples": ["A!think"]},
    "angry": {"category": "Хөгжилтэй", "description_en": "Express anger.", "description_mn": "Уурлах сэтгэлээ илэрхийлэх.", "usage": "A!angry", "examples": ["A!angry"]},
    "happy": {"category": "Хөгжилтэй", "description_en": "Show how happy you are!", "description_mn": "Аз жаргалтай байгаагаа харуулах!", "usage": "A!happy", "examples": ["A!happy"]},
    "gif": {"category": "Хөгжилтэй", "description_en": "Search and post a random GIF.", "description_mn": "Санамсаргүй GIF хайж оруулах.", "usage": "A!gif <хайлт>", "examples": ["A!gif cat", "A!gif hello"]},
    "meme": {"category": "Хөгжилтэй", "description_en": "Get a random meme from Reddit.", "description_mn": "Reddit-ээс санамсаргүй мийм авах.", "usage": "A!meme", "examples": ["A!meme"]},
    "8ball": {"category": "Хөгжилтэй", "description_en": "Ask the magic 8-ball a question.", "description_mn": "Шидэт бөмбөлөгөөс асуулт асуух.", "usage": "A!8ball <асуулт>", "examples": ["A!8ball би өнөөдөр азтай юу?"]},
    "dog": {"category": "Хөгжилтэй", "description_en": "Get a random dog picture.", "description_mn": "Санамсаргүй нохойн зураг авах.", "usage": "A!dog", "examples": ["A!dog"]},
    "cat": {"category": "Хөгжилтэй", "description_en": "Get a random cat picture.", "description_mn": "Санамсаргүй муурны зураг авах.", "usage": "A!cat", "examples": ["A!cat"]},
    "fox": {"category": "Хөгжилтэй", "description_en": "Get a random fox picture.", "description_mn": "Санамсаргүй үнэгний зураг авах.", "usage": "A!fox", "examples": ["A!fox"]},

    # ── Түвшин / XP ──
    "rank": {
        "category": "Түвшин",
        "description_en": "Check your or someone's level rank card.",
        "description_mn": "Өөрийн эсвэл бусдын түвшний картыг харах.",
        "usage": "A!rank [@хэрэглэгч]",
        "examples": ["A!rank", "A!rank @Bold"],
    },
    "leaderboard": {
        "category": "Түвшин",
        "description_en": "Show the server level leaderboard.",
        "description_mn": "Серверийн түвшний самбарыг харуулах.",
        "usage": "A!leaderboard",
        "examples": ["A!leaderboard"],
    },
    "levelsetup": {
        "category": "Түвшин",
        "description_en": "Open the interactive leveling settings panel (admin only).",
        "description_mn": "Интерактив түвшний тохиргооны самбар нээх (зөвхөн админ).",
        "usage": "A!levelsetup",
        "examples": ["A!levelsetup"],
    },
    "addxp": {
        "category": "Түвшин",
        "description_en": "Add XP to a user (owner/co-owner only).",
        "description_mn": "Хэрэглэгчид XP нэмэх (зөвхөн эзэмшигч/co-owner).",
        "usage": "A!addxp @хэрэглэгч <тоо>",
        "examples": ["A!addxp @Bold 500"],
    },
    "removexp": {
        "category": "Түвшин",
        "description_en": "Remove XP from a user (owner/co-owner only).",
        "description_mn": "Хэрэглэгчээс XP хасах (зөвхөн эзэмшигч/co-owner).",
        "usage": "A!removexp @хэрэглэгч <тоо>",
        "examples": ["A!removexp @Bold 200"],
    },
    "setxp": {
        "category": "Түвшин",
        "description_en": "Set a user's exact XP (owner/co-owner only).",
        "description_mn": "Хэрэглэгчийн XP-г яг тодорхой тохируулах (эзэмшигч/co-owner).",
        "usage": "A!setxp @хэрэглэгч <тоо>",
        "examples": ["A!setxp @Bold 5000"],
    },
    "resetxp": {
        "category": "Түвшин",
        "description_en": "Reset a user's XP to zero (owner/co-owner only).",
        "description_mn": "Хэрэглэгчийн XP-г тэглэх (эзэмшигч/co-owner).",
        "usage": "A!resetxp @хэрэглэгч",
        "examples": ["A!resetxp @Bold"],
    },
    "imagelink": {
        "category": "Түвшин",
        "description_en": "Set the rank card background image (URL or attachment).",
        "description_mn": "Түвшний картын дэвсгэр зургийг тохируулах (URL эсвэл хавсралт).",
        "usage": "A!imagelink <URL> / гэрэл зургийг хавсаргах",
        "examples": ["A!imagelink https://...", "A!imagelink (зураг хавсаргах)"],
    },
    "toggleleveling": {
        "category": "Түвшин",
        "description_en": "Enable/disable the entire leveling system.",
        "description_mn": "Түвшний системийг бүрэн асаах/унтраах.",
        "usage": "A!toggleleveling",
        "examples": ["A!toggleleveling"],
    },
    "exception": {
        "category": "Түвшин",
        "description_en": "Manage XP exceptions (channels/users that don't earn XP).",
        "description_mn": "XP олгохгүй байх онцгой тохиргоог удирдах (суваг/хэрэглэгч).",
        "usage": "A!exception add/remove <channel/user> @обьект",
        "examples": ["A!exception add channel #general", "A!exception remove user @Bold"],
    },
    "exceptions": {
        "category": "Түвшин",
        "description_en": "List all current XP exceptions.",
        "description_mn": "Одоогийн бүх XP онцгой тохиргоог харах.",
        "usage": "A!exceptions",
        "examples": ["A!exceptions"],
    },

    # ── Даалгавар (Quests) ──
    "quest": {
        "category": "Даалгавар",
        "description_en": "Quest system: new, status, claim, refresh, history.",
        "description_mn": "Даалгаврын систем: шинэ, статус, авах, сэргээх, түүх.",
        "usage": "A!quest <new/status/claim/refresh/history>",
        "examples": ["A!quest new", "A!quest status", "A!quest claim q123456"],
    },

    # ── Модераци ──
    "warn": {
        "category": "Модераци",
        "description_en": "Warn a member.",
        "description_mn": "Гишүүнд анхааруулга өгөх.",
        "usage": "A!warn @хэрэглэгч <шалтгаан>",
        "examples": ["A!warn @Bold спам"],
    },
    "warnings": {
        "category": "Модераци",
        "description_en": "Check a member's warnings.",
        "description_mn": "Гишүүний анхааруулгуудыг шалгах.",
        "usage": "A!warnings @хэрэглэгч",
        "examples": ["A!warnings @Bold"],
    },
    "kick": {
        "category": "Модераци",
        "description_en": "Kick a member from the server.",
        "description_mn": "Гишүүнийг серверээс хөөх.",
        "usage": "A!kick @хэрэглэгч [шалтгаан]",
        "examples": ["A!kick @Bold", "A!kick @Bold дүрэм зөрчсөн"],
    },
    "ban": {
        "category": "Модераци",
        "description_en": "Ban a member from the server.",
        "description_mn": "Гишүүнийг серверээс бан хийх.",
        "usage": "A!ban @хэрэглэгч [шалтгаан]",
        "examples": ["A!ban @Bold", "A!ban @Bold дүрэм зөрчсөн"],
    },
    "unban": {
        "category": "Модераци",
        "description_en": "Unban a user by ID.",
        "description_mn": "ID-аар хэрэглэгчийн банг цуцлах.",
        "usage": "A!unban <хэрэглэгчийн ID>",
        "examples": ["A!unban 123456789"],
    },
    "timeout": {
        "category": "Модераци",
        "description_en": "Timeout (mute) a member for a duration.",
        "description_mn": "Гишүүнийг тодорхой хугацаагаар түр хаах.",
        "usage": "A!timeout @хэрэглэгч <хугацаа> [шалтгаан]",
        "examples": ["A!timeout @Bold 10m спам"],
    },
    "untimeout": {
        "category": "Модераци",
        "description_en": "Remove a timeout early.",
        "description_mn": "Түр хаалтыг хугацаанаас өмнө цуцлах.",
        "usage": "A!unmute @хэрэглэгч",
        "examples": ["A!unmute @Bold"],
    },
    "lock": {
        "category": "Модераци",
        "description_en": "Lock a text channel.",
        "description_mn": "Текст сувгийг түгжих.",
        "usage": "A!lock [суваг]",
        "examples": ["A!lock", "A!lock #general"],
    },
    "unlock": {
        "category": "Модераци",
        "description_en": "Unlock a text channel.",
        "description_mn": "Түгжигдсэн сувгийг онгойлгох.",
        "usage": "A!unlock [суваг]",
        "examples": ["A!unlock", "A!unlock #general"],
    },
    "clear": {
        "category": "Модераци",
        "description_en": "Bulk delete recent messages (1-100).",
        "description_mn": "Сүүлийн мессежүүдийг олноор устгах (1-100).",
        "usage": "A!clear <тоо>",
        "examples": ["A!clear 10"],
    },

    # ── Гэр бүл ──
    "propose": {
        "category": "Гэр бүл",
        "description_en": "Propose marriage to someone.",
        "description_mn": "Хэн нэгэнд гэрлэх санал тавих.",
        "usage": "A!propose @хэрэглэгч",
        "examples": ["A!propose @Bold"],
    },
    "divorce": {
        "category": "Гэр бүл",
        "description_en": "Divorce your current spouse(s).",
        "description_mn": "Одоогийн хань(иуд)-аас салах.",
        "usage": "A!divorce [@хэрэглэгч]",
        "examples": ["A!divorce", "A!divorce @Bold"],
    },
    "spouse": {
        "category": "Гэр бүл",
        "description_en": "See your current spouse(s).",
        "description_mn": "Одоогийн хань(иуд)-аа харах.",
        "usage": "A!spouse",
        "examples": ["A!spouse"],
    },
    "love": {
        "category": "Гэр бүл",
        "description_en": "Send love points to your partner.",
        "description_mn": "Ханьдаа хайрын оноо илгээх.",
        "usage": "A!love @хэрэглэгч",
        "examples": ["A!love @Bold"],
    },
    "gift": {
        "category": "Гэр бүл",
        "description_en": "Send a gift to your partner.",
        "description_mn": "Ханьдаа бэлэг өгөх.",
        "usage": "A!gift <flower/chocolate/ring/necklace/teddy>",
        "examples": ["A!gift flower", "A!gift ring"],
    },
    "adopt": {
        "category": "Гэр бүл",
        "description_en": "Adopt a user as your child.",
        "description_mn": "Хэрэглэгчийг хүүхдээ болгон өргөмжлөх.",
        "usage": "A!adopt @хэрэглэгч",
        "examples": ["A!adopt @Bold"],
    },
    "disown": {
        "category": "Гэр бүл",
        "description_en": "Disown a child.",
        "description_mn": "Хүүхдээсээ татгалзах.",
        "usage": "A!disown @хэрэглэгч",
        "examples": ["A!disown @Bold"],
    },
    "familytree": {
        "category": "Гэр бүл",
        "description_en": "Show your family tree as an image.",
        "description_mn": "Гэр бүлийн модыг зураг хэлбэрээр харах.",
        "usage": "A!familytree [@хэрэглэгч]",
        "examples": ["A!familytree", "A!familytree @Bold"],
    },
    "marriagepro": {
        "category": "Гэр бүл",
        "description_en": "View marriage card with love level.",
        "description_mn": "Хайр сэтгэлийн түвшинтэй гэрлэлтийн карт үзэх.",
        "usage": "A!marriagepro [@хэрэглэгч]",
        "examples": ["A!marriagepro", "A!marriagepro @Bold"],
    },

    # ── Админ / Удирдлага ──
    "admin-panel": {
        "category": "Админ",
        "description_en": "Open the economy admin settings panel.",
        "description_mn": "Эдийн засгийн админ тохиргооны самбар нээх.",
        "usage": "A!admin-panel",
        "examples": ["A!admin-panel"],
    },
    "role": {
        "category": "Админ",
        "description_en": "Manage permanent roles. Sub: give, remove.",
        "description_mn": "Байнгын үүрэг удирдах. Дэд: give, remove.",
        "usage": "A!role give @хэрэглэгч @үүрэг",
        "examples": ["A!role give @Bold @Member"],
    },
    "temprole": {
        "category": "Админ",
        "description_en": "Manage temporary roles. Sub: give, remove.",
        "description_mn": "Түр үүрэг удирдах. Дэд: give, remove.",
        "usage": "A!temprole give @хэрэглэгч @үүрэг 1h",
        "examples": ["A!temprole give @Bold @VIP 30m"],
    },
    "giveaway": {
        "category": "Админ",
        "description_en": "Create/manage giveaways. Sub: start, end, reroll.",
        "description_mn": "Гивэвэй үүсгэх/удирдах.",
        "usage": "A!giveaway start",
        "examples": ["A!giveaway start"],
    },
    "invites": {
        "category": "Админ",
        "description_en": "Invite tracking and leaderboard.",
        "description_mn": "Урилгын бүртгэл, самбар.",
        "usage": "A!invites leaderboard",
        "examples": ["A!invites leaderboard"],
    },

    # ── Хэрэгсэл ──
    "avatar": {
        "category": "Хэрэгсэл",
        "description_en": "Display user's avatar.",
        "description_mn": "Хэрэглэгчийн профайл зургийг харуулах.",
        "usage": "A!avatar [@хэрэглэгч]",
        "examples": ["A!avatar", "A!avatar @Bold"],
    },
    "profile": {
        "category": "Хэрэгсэл",
        "description_en": "Display user's full profile card (money, level, job, etc.).",
        "description_mn": "Хэрэглэгчийн бүрэн профайл картыг харуулах (мөнгө, түвшин, ажил г.м).",
        "usage": "A!profile [@хэрэглэгч]",
        "examples": ["A!profile", "A!profile @Bold"],
    },
    "inventory": {
        "category": "Хэрэгсэл",
        "description_en": "Display user's inventory card.",
        "description_mn": "Хэрэглэгчийн инвентар картыг харуулах.",
        "usage": "A!inventory",
        "examples": ["A!inventory"],
    },
    "ping": {
        "category": "Хэрэгсэл",
        "description_en": "Check bot latency.",
        "description_mn": "Ботын хариу хүлээх хугацааг шалгах.",
        "usage": "A!ping",
        "examples": ["A!ping"],
    },
    "serverinfo": {
        "category": "Хэрэгсэл",
        "description_en": "Show server information.",
        "description_mn": "Серверийн мэдээлэл харуулах.",
        "usage": "A!serverinfo",
        "examples": ["A!serverinfo"],
    },

    # ── Тусгай / Бусад ──
    "mines": {
        "category": "Тоглоом",
        "description_en": "Play Minesweeper-style game for money.",
        "description_mn": "Уурхайн тоглоом (Mines) мөнгөтэй тоглох.",
        "usage": "A!mines <дүн>",
        "examples": ["A!mines 500"],
    },
    "pvp": {
        "category": "Тоглоом",
        "description_en": "Duel another player (Rock-Paper-Scissors style).",
        "description_mn": "Өөр тоглогчтой тулаан хийх (довтолгоо/хамгаалалт).",
        "usage": "A!pvp @хэрэглэгч <дүн>",
        "examples": ["A!pvp @Bold 500"],
    },
    "cafe": {
        "category": "Хоол",
        "description_en": "Open the cafe to buy food and drinks.",
        "description_mn": "Хоол унд захиалах кафе нээх.",
        "usage": "A!cafe",
        "examples": ["A!cafe"],
    },
    "dine": {
        "category": "Хоол",
        "description_en": "Eat food from your inventory to get buffs.",
        "description_mn": "Инвентариас хоол идэж, түр хүчин чадал авах.",
        "usage": "A!dine <дугаар>",
        "examples": ["A!dine 1"],
    },
    "shop": {
        "category": "Дэлгүүр",
        "description_en": "Open the shop to buy items.",
        "description_mn": "Бараа худалдан авах дэлгүүр нээх.",
        "usage": "A!shop",
        "examples": ["A!shop"],
    },
    "marketplace": {
        "category": "Дэлгүүр",
        "description_en": "Buy/sell items from other players.",
        "description_mn": "Бусад тоглогчдоос бараа худалдах/худалдан авах зах зээл.",
        "usage": "A!marketplace panel",
        "examples": ["A!marketplace panel"],
    },
    "stock": {
        "category": "Дэлгүүр",
        "description_en": "View and manage shop stock (admin).",
        "description_mn": "Дэлгүүрийн нөөцийг харж удирдах (админ).",
        "usage": "A!stock status",
        "examples": ["A!stock status"],
    },
    "confess": {
        "category": "Нууц",
        "description_en": "Send an anonymous confession.",
        "description_mn": "Нэрээ нууцлан захиа илгээх.",
        "usage": "A!confess",
        "examples": ["A!confess"],
    },
    "counting": {
        "category": "Тоглоом",
        "description_en": "Counting game (set channel, etc.)",
        "description_mn": "Тоолох тоглоом (суваг тохируулах гэх мэт).",
        "usage": "A!counting_setup",
        "examples": ["A!counting_setup"],
    },
    "voicesetup": {
        "category": "Админ",
        "description_en": "Setup temporary voice channels.",
        "description_mn": "Түр дуут суваг тохируулах.",
        "usage": "A!voicesetup",
        "examples": ["A!voicesetup"],
    },
}

# ════════════════════ ИНТЕРАКТИВ САМБАР ════════════════════
class HelpView(ui.View):
    def __init__(self, ctx, categories: list, default_category: str = "Эдийн засаг"):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.categories = categories
        self.current_category = default_category

    async def send_embed(self, interaction: discord.Interaction):
        embed = self.build_embed(self.current_category)
        for child in self.children:
            if isinstance(child, ui.Button):
                child.disabled = (child.label == self.current_category)
        await interaction.response.edit_message(embed=embed, view=self)

    def build_embed(self, category: str):
        emoji = CATEGORY_EMOJIS.get(category, "📁")
        color = CATEGORY_COLORS.get(category, 0x1e1e2f)

        commands = [(cmd, info) for cmd, info in COMMAND_INFO.items() if info["category"] == category]

        embed = discord.Embed(
            title=f"{emoji}  {category}",
            description=f"📋 **{len(commands)} тушаал**  •  {CATEGORY_COUNT_INFO}",
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(
            name="📌 Командын жагсаалт",
            value=(
                f"{'═' * 32}\n"
                f"📂 **Ангилал:** {emoji} {category}\n"
                f"🤖 **Бот:** {BOT_NAME}\n"
                f"📊 **Нийт тушаал:** {len(COMMAND_INFO)}\n"
                f"{'═' * 32}"
            ),
            inline=False,
        )
        if not commands:
            embed.add_field(name="📭 Хоосон", value="Энэ ангилалд тушаал байхгүй байна.", inline=False)
        else:
            MAX_FIELD = 1000
            chunks, current, size = [], [], 0
            for cmd, info in commands:
                line = f"▸ **`{cmd}`** — {info['description_mn']}\n  ↳ `{info['usage']}`\n"
                if size + len(line) > MAX_FIELD and current:
                    chunks.append("".join(current))
                    current, size = [], 0
                current.append(line)
                size += len(line)
            if current:
                chunks.append("".join(current))
            for i, chunk in enumerate(chunks, start=1):
                embed.add_field(
                    name=f"{'📑' if len(chunks) > 1 else '📋'} Бүлэг {i}/{len(chunks)}",
                    value=chunk.strip(),
                    inline=False,
                )
        embed.set_author(name=str(self.ctx.author), icon_url=self.ctx.author.display_avatar.url)
        if self.ctx.guild and self.ctx.guild.icon:
            embed.set_thumbnail(url=self.ctx.guild.icon.url)
        embed.set_footer(text=f"{BOT_NAME} · Тусламжийн самбар · 180с дараа дуусна", icon_url=self.bot.user.display_avatar.url if self.bot.user else None)
        return embed

    # ── Эгнээ 0 ──
    @ui.button(label="Эдийн засаг", emoji="💰", style=discord.ButtonStyle.blurple, row=0)
    async def economy_btn(self, interaction, button): self.current_category = "Эдийн засаг"; await self.send_embed(interaction)

    @ui.button(label="Тоглоом", emoji="🎲", style=discord.ButtonStyle.green, row=0)
    async def games_btn(self, interaction, button): self.current_category = "Тоглоом"; await self.send_embed(interaction)

    @ui.button(label="Казино", emoji="🎰", style=discord.ButtonStyle.red, row=0)
    async def casino_btn(self, interaction, button): self.current_category = "Казино"; await self.send_embed(interaction)

    @ui.button(label="Хөгжилтэй", emoji="🎉", style=discord.ButtonStyle.success, row=0)
    async def fun_btn(self, interaction, button): self.current_category = "Хөгжилтэй"; await self.send_embed(interaction)

    # ── Эгнээ 1 ──
    @ui.button(label="Түвшин", emoji="⭐", style=discord.ButtonStyle.primary, row=1)
    async def levels_btn(self, interaction, button): self.current_category = "Түвшин"; await self.send_embed(interaction)

    @ui.button(label="Даалгавар", emoji="🎯", style=discord.ButtonStyle.success, row=1)
    async def quests_btn(self, interaction, button): self.current_category = "Даалгавар"; await self.send_embed(interaction)

    @ui.button(label="Модераци", emoji="🛡️", style=discord.ButtonStyle.danger, row=1)
    async def mod_btn(self, interaction, button): self.current_category = "Модераци"; await self.send_embed(interaction)

    @ui.button(label="Гэр бүл", emoji="💒", style=discord.ButtonStyle.secondary, row=1)
    async def marriage_btn(self, interaction, button): self.current_category = "Гэр бүл"; await self.send_embed(interaction)

    # ── Эгнээ 2 ──
    @ui.button(label="Админ", emoji="⚙️", style=discord.ButtonStyle.secondary, row=2)
    async def admin_btn(self, interaction, button): self.current_category = "Админ"; await self.send_embed(interaction)

    @ui.button(label="Хэрэгсэл", emoji="🔧", style=discord.ButtonStyle.secondary, row=2)
    async def utility_btn(self, interaction, button): self.current_category = "Хэрэгсэл"; await self.send_embed(interaction)

    @ui.button(label="Хоол", emoji="🍔", style=discord.ButtonStyle.secondary, row=2)
    async def food_btn(self, interaction, button): self.current_category = "Хоол"; await self.send_embed(interaction)

    @ui.button(label="Дэлгүүр", emoji="🛒", style=discord.ButtonStyle.secondary, row=2)
    async def shop_btn(self, interaction, button): self.current_category = "Дэлгүүр"; await self.send_embed(interaction)


# Категорийн тохиргоо
CATEGORY_EMOJIS = {
    "Эдийн засаг": "💰",
    "Тоглоом": "🎲",
    "Казино": "🎰",
    "Хөгжилтэй": "🎉",
    "Модераци": "🛡️",
    "Түвшин": "⭐",
    "Гэр бүл": "💒",
    "Админ": "⚙️",
    "Хэрэгсэл": "🔧",
    "Хоол": "🍔",
    "Дэлгүүр": "🛒",
    "Нууц": "🤫",
    "Даалгавар": "🎯",
}

CATEGORY_COLORS = {
    "Эдийн засаг": 0xfab387,
    "Тоглоом": 0xf9e2af,
    "Казино": 0xcba6f7,
    "Хөгжилтэй": 0xff69b4,
    "Модераци": 0xf38ba8,
    "Түвшин": 0xa6e3a1,
    "Гэр бүл": 0xff10f0,
    "Админ": 0x89b4fa,
    "Хэрэгсэл": 0x6c7086,
    "Хоол": 0xffa500,
    "Дэлгүүр": 0x00ffcc,
    "Нууц": 0x9b59b6,
    "Даалгавар": 0xfab387,
}

# Тусламжийн самбарын мэдээллийн мөрөнд ашиглана (COMMAND_INFO-ийн дараа тооцно)
CATEGORY_COUNT_INFO = f"{len(CATEGORY_EMOJIS)} ангилал · нийт {len(COMMAND_INFO)} тушаал"


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='help', description="Командын тусламж (ангилал эсвэл дэлгэрэнгүй)")
    @app_commands.describe(command="Тусламж авах тушаалын нэр (хоосон орхивол ангиллын самбар)")
    async def help_command(self, ctx, *, command: str = None):
        if command is None:
            categories = list(CATEGORY_EMOJIS.keys())
            view = HelpView(ctx, categories, default_category="Эдийн засаг")
            embed = view.build_embed("Эдийн засаг")
            await ctx.send(embed=embed, view=view)
        else:
            cmd_key = command.lower().strip()
            info = COMMAND_INFO.get(cmd_key)
            if not info:
                suggestions = [k for k in COMMAND_INFO if k.startswith(cmd_key[:2])]
                hint = ""
                if suggestions:
                    hint = "\n\n💡 **Ойролцоо тушаалууд:** " + ", ".join(f"`{s}`" for s in suggestions[:5])
                embed = discord.Embed(
                    title="❌ Тушаал олдсонгүй",
                    description=f"`{cmd_key}` нэртэй тушаал байхгүй байна.{hint}",
                    color=0xf38ba8
                )
                return await ctx.send(embed=embed)

            cat_emoji = CATEGORY_EMOJIS.get(info["category"], "📁")
            cat_color = CATEGORY_COLORS.get(info["category"], 0x89B4FA)
            embed = discord.Embed(
                title=f"{cat_emoji}  `{cmd_key}`",
                description=(
                    f"**{info['description_mn']}**\n"
                    f"*{info['description_en']}*"
                ),
                color=cat_color,
            )
            embed.add_field(
                name="📂 Ангилал",
                value=f"{cat_emoji} {info['category']}",
                inline=True,
            )
            embed.add_field(
                name="⚙️ Хэрэглэх хэлбэр",
                value=f"```\n{info['usage']}\n```",
                inline=True,
            )
            if info.get("examples"):
                examples = "\n".join(f"`{ex}`" for ex in info["examples"])
                embed.add_field(name="📝 Жишээ", value=examples, inline=False)
            embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
            embed.set_footer(text=f"{BOT_NAME} · Тусламжийн систем · {BOT_FOOTER}")
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Help(bot))
