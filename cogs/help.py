import discord
from discord.ext import commands
from discord import app_commands, ui
from utils.branding import BOT_NAME

# ═══════════════════════════════════════════════════════════════════════════════
# БҮХ КОМАНДЫН ДЭЛГЭРЭНГҮЙ ТОДОРХОЙЛОЛТ (шинэчлэгдсэн, алдаагүй)
# ═══════════════════════════════════════════════════════════════════════════════
COMMAND_INFO = {
    # ── Эдийн засаг ──
    "balance": {
        "category": "Эдийн засаг",
        "description_en": "Check your wallet and bank balance.",
        "description_mn": "Таны гар дээрх мөнгө болон банкны үлдэгдлийг харна.",
        "usage": "gbalance [@хэрэглэгч]",
        "examples": ["gbalance", "gbalance @Bold"],
    },
    "work": {
        "category": "Эдийн засаг",
        "description_en": "Work to earn money. Higher level = better job.",
        "description_mn": "Ажил хийж мөнгө олох. Түвшин өндөр байх тусмаа сайн ажил.",
        "usage": "gwork [өөрийн текст]",
        "examples": ["gwork", "gwork кофе чанаж байна"],
    },
    "daily": {
        "category": "Эдийн засаг",
        "description_en": "Claim your daily reward once every 24 hours.",
        "description_mn": "24 цаг тутамд нэг удаа өдрийн урамшуулал авах.",
        "usage": "gdaily",
        "examples": ["gdaily"],
    },
    "deposit": {
        "category": "Эдийн засаг",
        "description_en": "Deposit money into your bank account.",
        "description_mn": "Гар дээрх мөнгөө банкинд хийх.",
        "usage": "gdeposit <дүн/all>",
        "examples": ["gdeposit 5000", "gdeposit all"],
    },
    "withdraw": {
        "category": "Эдийн засаг",
        "description_en": "Withdraw money from your bank account.",
        "description_mn": "Банкнаас мөнгө гаргах.",
        "usage": "gwithdraw <дүн/all>",
        "examples": ["gwithdraw 5000", "gwithdraw all"],
    },
    "transfer": {
        "category": "Эдийн засаг",
        "description_en": "Send money to another user.",
        "description_mn": "Бусад хэрэглэгчид мөнгө илгээх.",
        "usage": "gtransfer @хэрэглэгч <дүн/all>",
        "examples": ["gtransfer @Bold 5000", "gtransfer @Bold all"],
    },
    "bankprotect": {
        "category": "Эдийн засаг",
        "description_en": "Protect your bank from robbers for 2 hours.",
        "description_mn": "Банкаа 2 цагийн турш дээрэмчдээс хамгаална.",
        "usage": "gbankprotect",
        "examples": ["gbankprotect"],
    },
    "eat": {
        "category": "Эдийн засаг",
        "description_en": "Eat food to reduce hunger.",
        "description_mn": "Өлсгөлөнгөө багасгахын тулд хоол идэх.",
        "usage": "geat",
        "examples": ["geat"],
    },
    "relax": {
        "category": "Эдийн засаг",
        "description_en": "Relax to reduce mood/stress.",
        "description_mn": "Амарч, уур бухимдлаа багасгах.",
        "usage": "grelax",
        "examples": ["grelax"],
    },

    # ── Тоглоом ──
    "gamble": {
        "category": "Тоглоом",
        "description_en": "Gamble your money with a 30% chance to win.",
        "description_mn": "30% хожих магадлалтай мөрийтэй тоглоом.",
        "usage": "ggamble <дүн/all>",
        "examples": ["ggamble 1000", "ggamble all"],
    },
    "coinflip": {
        "category": "Тоглоом",
        "description_en": "Flip a coin and bet on heads or tails.",
        "description_mn": "Зоос шидэж, heads эсвэл tails гэж таах.",
        "usage": "gcoinflip <heads/tails> <дүн>",
        "examples": ["gcoinflip heads 500", "gcoinflip tails all"],
    },
    "slot": {
        "category": "Тоглоом",
        "description_en": "Play the slot machine. 3 same symbols = JACKPOT!",
        "description_mn": "Слот машин тоглох. 3 ижил тэмдэгт = JACKPOT!",
        "usage": "gslot <дүн>",
        "examples": ["gslot 1000", "gslot 5000"],
    },
    "roulette": {
        "category": "Тоглоом",
        "description_en": "Play roulette. Bet on red, black, or green.",
        "description_mn": "Рулет тоглох. Улаан, хар, ногоон дээр бооцоо тавих.",
        "usage": "groulette <red/black/green> <дүн>",
        "examples": ["groulette red 1000", "groulette green 500"],
    },
    "dice": {
        "category": "Тоглоом",
        "description_en": "Guess the dice roll (1-6) to win 6x your bet.",
        "description_mn": "Шооны тоог тааж (1-6) бооцооны 6 дахин хожих.",
        "usage": "gdice <1-6> <дүн>",
        "examples": ["gdice 3 500", "gdice 6 1000"],
    },
    "rps": {
        "category": "Тоглоом",
        "description_en": "Play Rock Paper Scissors against the bot.",
        "description_mn": "Боттой чулуу, даавуу, хайч тоглох.",
        "usage": "grps <rock/paper/scissors> <дүн>",
        "examples": ["grps rock 500", "grps scissors 1000"],
    },
    "numberguess": {
        "category": "Тоглоом",
        "description_en": "Guess a number (1-10) within 10 seconds.",
        "description_mn": "Ботны бодсон тоог (1-10) 10 секундэд таах.",
        "usage": "gnumberguess <дүн>",
        "examples": ["gnumberguess 500"],
    },
    "trivia": {
        "category": "Тоглоом",
        "description_en": "Answer a trivia question to earn XP.",
        "description_mn": "Асуултанд зөв хариулж XP авах.",
        "usage": "gtrivia",
        "examples": ["gtrivia"],
    },

    # ── Казино ──
    "blackjack": {
        "category": "Казино",
        "description_en": "Play Blackjack against the dealer. Get close to 21.",
        "description_mn": "Дилертэй блэкжэк тоглох. 21-д ойртох.",
        "usage": "gblackjack <дүн>",
        "examples": ["gblackjack 500", "gblackjack all"],
    },
    "highlow": {
        "category": "Казино",
        "description_en": "Guess if the next number is higher or lower.",
        "description_mn": "Дараагийн тоо өмнөхөөсөө их эсвэл бага эсэхийг таах.",
        "usage": "ghighlow <дүн> [higher/lower]",
        "examples": ["ghighlow 500", "ghighlow 1000 higher"],
    },
    "rob": {
        "category": "Казино",
        "description_en": "Attempt to rob another user. 30% success rate.",
        "description_mn": "Хэрэглэгчийг дээрэмдэх оролдлого. 30% амжилттай.",
        "usage": "grob @хэрэглэгч",
        "examples": ["grob @Bold"],
    },
    "hack": {
        "category": "Казино",
        "description_en": "Hack a user's bank account. Low success rate.",
        "description_mn": "Банкны данс хакердах. Амжилт багатай.",
        "usage": "ghack @хэрэглэгч",
        "examples": ["ghack @Bold"],
    },

    # ── Хөгжилтэй ──
    "hug": {"category": "Хөгжилтэй", "description_en": "Hug someone!", "description_mn": "Хэн нэгнийг тэврэх!", "usage": "ghug [@хэрэглэгч]", "examples": ["ghug", "ghug @Bold"]},
    "kiss": {"category": "Хөгжилтэй", "description_en": "Kiss someone!", "description_mn": "Хэн нэгнийг үнсэх!", "usage": "gkiss [@хэрэглэгч]", "examples": ["gkiss", "gkiss @Bold"]},
    "slap": {"category": "Хөгжилтэй", "description_en": "Slap someone!", "description_mn": "Хэн нэгнийг алгадах!", "usage": "gslap [@хэрэглэгч]", "examples": ["gslap", "gslap @Bold"]},
    "pat": {"category": "Хөгжилтэй", "description_en": "Pat someone's head.", "description_mn": "Хэн нэгний толгойг илэх.", "usage": "gpat [@хэрэглэгч]", "examples": ["gpat", "gpat @Bold"]},
    "cuddle": {"category": "Хөгжилтэй", "description_en": "Cuddle with someone!", "description_mn": "Хэн нэгэнтэй зууралдах!", "usage": "gcuddle [@хэрэглэгч]", "examples": ["gcuddle", "gcuddle @Bold"]},
    "bite": {"category": "Хөгжилтэй", "description_en": "Bite someone playfully.", "description_mn": "Хэн нэгнийг зөөлөн хазах.", "usage": "gbite [@хэрэглэгч]", "examples": ["gbite", "gbite @Bold"]},
    "poke": {"category": "Хөгжилтэй", "description_en": "Poke someone to get their attention.", "description_mn": "Хэн нэгнийг хатгаж анхаарлыг нь татах.", "usage": "gpoke [@хэрэглэгч]", "examples": ["gpoke", "gpoke @Bold"]},
    "wave": {"category": "Хөгжилтэй", "description_en": "Wave at someone.", "description_mn": "Хэн нэгэнд даллах.", "usage": "gwave [@хэрэглэгч]", "examples": ["gwave", "gwave @Bold"]},
    "punch": {"category": "Хөгжилтэй", "description_en": "Punch someone!", "description_mn": "Хэн нэгнийг цохих!", "usage": "gpunch [@хэрэглэгч]", "examples": ["gpunch", "gpunch @Bold"]},
    "boop": {"category": "Хөгжилтэй", "description_en": "Boop someone's nose.", "description_mn": "Хэн нэгний хамарт буп хийх.", "usage": "gboop [@хэрэглэгч]", "examples": ["gboop", "gboop @Bold"]},
    "bully": {"category": "Хөгжилтэй", "description_en": "Bully someone (just for fun).", "description_mn": "Хэн нэгнийг хошигнон булимдах.", "usage": "gbully [@хэрэглэгч]", "examples": ["gbully", "gbully @Bold"]},
    "handhold": {"category": "Хөгжилтэй", "description_en": "Hold hands with someone.", "description_mn": "Хэн нэгэнтэй гар барих.", "usage": "ghandhold [@хэрэглэгч]", "examples": ["ghandhold", "ghandhold @Bold"]},
    "stare": {"category": "Хөгжилтэй", "description_en": "Stare intently at someone.", "description_mn": "Хэн нэгнийг ширтэх.", "usage": "gstare [@хэрэглэгч]", "examples": ["gstare", "gstare @Bold"]},
    "highfive": {"category": "Хөгжилтэй", "description_en": "Give someone a high-five.", "description_mn": "Хэн нэгэнд өндөр тавих.", "usage": "ghighfive [@хэрэглэгч]", "examples": ["ghighfive", "ghighfive @Bold"]},
    "snuggle": {"category": "Хөгжилтэй", "description_en": "Snuggle up with someone.", "description_mn": "Хэн нэгэнтэй зууран дулаацах.", "usage": "gsnuggle [@хэрэглэгч]", "examples": ["gsnuggle", "gsnuggle @Bold"]},
    "cry": {"category": "Хөгжилтэй", "description_en": "Cry...", "description_mn": "Уйлах...", "usage": "gcry", "examples": ["gcry"]},
    "dance": {"category": "Хөгжилтэй", "description_en": "Show off your dance moves.", "description_mn": "Бүжиглэх чадвараа харуулах.", "usage": "gdance", "examples": ["gdance"]},
    "laugh": {"category": "Хөгжилтэй", "description_en": "Laugh out loud!", "description_mn": "Чангаар инээх!", "usage": "glaugh", "examples": ["glaugh"]},
    "sleep": {"category": "Хөгжилтэй", "description_en": "Go to sleep.", "description_mn": "Унтах.", "usage": "gsleep", "examples": ["gsleep"]},
    "think": {"category": "Хөгжилтэй", "description_en": "Ponder something deeply.", "description_mn": "Гүн бодолд автах.", "usage": "gthink", "examples": ["gthink"]},
    "angry": {"category": "Хөгжилтэй", "description_en": "Express anger.", "description_mn": "Уурлах сэтгэлээ илэрхийлэх.", "usage": "gangry", "examples": ["gangry"]},
    "happy": {"category": "Хөгжилтэй", "description_en": "Show how happy you are!", "description_mn": "Аз жаргалтай байгаагаа харуулах!", "usage": "ghappy", "examples": ["ghappy"]},
    "gif": {"category": "Хөгжилтэй", "description_en": "Search and post a random GIF.", "description_mn": "Санамсаргүй GIF хайж оруулах.", "usage": "ggif <хайлт>", "examples": ["ggif cat", "ggif hello"]},
    "meme": {"category": "Хөгжилтэй", "description_en": "Get a random meme from Reddit.", "description_mn": "Reddit-ээс санамсаргүй мийм авах.", "usage": "gmeme", "examples": ["gmeme"]},
    "8ball": {"category": "Хөгжилтэй", "description_en": "Ask the magic 8-ball a question.", "description_mn": "Шидэт бөмбөлөгөөс асуулт асуух.", "usage": "g8ball <асуулт>", "examples": ["g8ball би өнөөдөр азтай юу?"]},
    "dog": {"category": "Хөгжилтэй", "description_en": "Get a random dog picture.", "description_mn": "Санамсаргүй нохойн зураг авах.", "usage": "gdog", "examples": ["gdog"]},
    "cat": {"category": "Хөгжилтэй", "description_en": "Get a random cat picture.", "description_mn": "Санамсаргүй муурны зураг авах.", "usage": "gcat", "examples": ["gcat"]},
    "fox": {"category": "Хөгжилтэй", "description_en": "Get a random fox picture.", "description_mn": "Санамсаргүй үнэгний зураг авах.", "usage": "gfox", "examples": ["gfox"]},

    # ── Түвшин / XP ──
    "rank": {
        "category": "Түвшин",
        "description_en": "Check your or someone's level rank card.",
        "description_mn": "Өөрийн эсвэл бусдын түвшний картыг харах.",
        "usage": "grank [@хэрэглэгч]",
        "examples": ["grank", "grank @Bold"],
    },
    "leaderboard": {
        "category": "Түвшин",
        "description_en": "Show the server level leaderboard.",
        "description_mn": "Серверийн түвшний самбарыг харуулах.",
        "usage": "gleaderboard",
        "examples": ["gleaderboard"],
    },
    "levelsetup": {
        "category": "Түвшин",
        "description_en": "Open the interactive leveling settings panel (admin only).",
        "description_mn": "Интерактив түвшний тохиргооны самбар нээх (зөвхөн админ).",
        "usage": "glevelsetup",
        "examples": ["glevelsetup"],
    },
    "addxp": {
        "category": "Түвшин",
        "description_en": "Add XP to a user (owner/co-owner only).",
        "description_mn": "Хэрэглэгчид XP нэмэх (зөвхөн эзэмшигч/co-owner).",
        "usage": "gaddxp @хэрэглэгч <тоо>",
        "examples": ["gaddxp @Bold 500"],
    },
    "removexp": {
        "category": "Түвшин",
        "description_en": "Remove XP from a user (owner/co-owner only).",
        "description_mn": "Хэрэглэгчээс XP хасах (зөвхөн эзэмшигч/co-owner).",
        "usage": "gremovexp @хэрэглэгч <тоо>",
        "examples": ["gremovexp @Bold 200"],
    },
    "setxp": {
        "category": "Түвшин",
        "description_en": "Set a user's exact XP (owner/co-owner only).",
        "description_mn": "Хэрэглэгчийн XP-г яг тодорхой тохируулах (эзэмшигч/co-owner).",
        "usage": "gsetxp @хэрэглэгч <тоо>",
        "examples": ["gsetxp @Bold 5000"],
    },
    "resetxp": {
        "category": "Түвшин",
        "description_en": "Reset a user's XP to zero (owner/co-owner only).",
        "description_mn": "Хэрэглэгчийн XP-г тэглэх (эзэмшигч/co-owner).",
        "usage": "gresetxp @хэрэглэгч",
        "examples": ["gresetxp @Bold"],
    },
    "imagelink": {
        "category": "Түвшин",
        "description_en": "Set the rank card background image (URL or attachment).",
        "description_mn": "Түвшний картын дэвсгэр зургийг тохируулах (URL эсвэл хавсралт).",
        "usage": "gimagelink <URL> / гэрэл зургийг хавсаргах",
        "examples": ["gimagelink https://...", "gimagelink (зураг хавсаргах)"],
    },
    "toggleleveling": {
        "category": "Түвшин",
        "description_en": "Enable/disable the entire leveling system.",
        "description_mn": "Түвшний системийг бүрэн асаах/унтраах.",
        "usage": "gtoggleleveling",
        "examples": ["gtoggleleveling"],
    },
    "exception": {
        "category": "Түвшин",
        "description_en": "Manage XP exceptions (channels/users that don't earn XP).",
        "description_mn": "XP олгохгүй байх онцгой тохиргоог удирдах (суваг/хэрэглэгч).",
        "usage": "gexception add/remove <channel/user> @обьект",
        "examples": ["gexception add channel #general", "gexception remove user @Bold"],
    },
    "exceptions": {
        "category": "Түвшин",
        "description_en": "List all current XP exceptions.",
        "description_mn": "Одоогийн бүх XP онцгой тохиргоог харах.",
        "usage": "gexceptions",
        "examples": ["gexceptions"],
    },

    # ── Даалгавар (Quests) ──
    "quest": {
        "category": "Даалгавар",
        "description_en": "Quest system: new, status, claim, refresh, history.",
        "description_mn": "Даалгаврын систем: шинэ, статус, авах, сэргээх, түүх.",
        "usage": "gquest <new/status/claim/refresh/history>",
        "examples": ["gquest new", "gquest status", "gquest claim q123456"],
    },

    # ── Модераци ──
    "warn": {
        "category": "Модераци",
        "description_en": "Warn a member.",
        "description_mn": "Гишүүнд анхааруулга өгөх.",
        "usage": "gwarn @хэрэглэгч <шалтгаан>",
        "examples": ["gwarn @Bold спам"],
    },
    "warnings": {
        "category": "Модераци",
        "description_en": "Check a member's warnings.",
        "description_mn": "Гишүүний анхааруулгуудыг шалгах.",
        "usage": "gwarnings @хэрэглэгч",
        "examples": ["gwarnings @Bold"],
    },
    "kick": {
        "category": "Модераци",
        "description_en": "Kick a member from the server.",
        "description_mn": "Гишүүнийг серверээс хөөх.",
        "usage": "gkick @хэрэглэгч [шалтгаан]",
        "examples": ["gkick @Bold", "gkick @Bold дүрэм зөрчсөн"],
    },
    "ban": {
        "category": "Модераци",
        "description_en": "Ban a member from the server.",
        "description_mn": "Гишүүнийг серверээс бан хийх.",
        "usage": "gban @хэрэглэгч [шалтгаан]",
        "examples": ["gban @Bold", "gban @Bold дүрэм зөрчсөн"],
    },
    "unban": {
        "category": "Модераци",
        "description_en": "Unban a user by ID.",
        "description_mn": "ID-аар хэрэглэгчийн банг цуцлах.",
        "usage": "gunban <хэрэглэгчийн ID>",
        "examples": ["gunban 123456789"],
    },
    "timeout": {
        "category": "Модераци",
        "description_en": "Timeout (mute) a member for a duration.",
        "description_mn": "Гишүүнийг тодорхой хугацаагаар түр хаах.",
        "usage": "gtimeout @хэрэглэгч <хугацаа> [шалтгаан]",
        "examples": ["gtimeout @Bold 10m спам"],
    },
    "untimeout": {
        "category": "Модераци",
        "description_en": "Remove a timeout early.",
        "description_mn": "Түр хаалтыг хугацаанаас өмнө цуцлах.",
        "usage": "gunmute @хэрэглэгч",
        "examples": ["gunmute @Bold"],
    },
    "lock": {
        "category": "Модераци",
        "description_en": "Lock a text channel.",
        "description_mn": "Текст сувгийг түгжих.",
        "usage": "glock [суваг]",
        "examples": ["glock", "glock #general"],
    },
    "unlock": {
        "category": "Модераци",
        "description_en": "Unlock a text channel.",
        "description_mn": "Түгжигдсэн сувгийг онгойлгох.",
        "usage": "gunlock [суваг]",
        "examples": ["gunlock", "gunlock #general"],
    },
    "clear": {
        "category": "Модераци",
        "description_en": "Bulk delete recent messages (1-100).",
        "description_mn": "Сүүлийн мессежүүдийг олноор устгах (1-100).",
        "usage": "gclear <тоо>",
        "examples": ["gclear 10"],
    },

    # ── Гэр бүл ──
    "propose": {
        "category": "Гэр бүл",
        "description_en": "Propose marriage to someone.",
        "description_mn": "Хэн нэгэнд гэрлэх санал тавих.",
        "usage": "gpropose @хэрэглэгч",
        "examples": ["gpropose @Bold"],
    },
    "divorce": {
        "category": "Гэр бүл",
        "description_en": "Divorce your current spouse(s).",
        "description_mn": "Одоогийн хань(иуд)-аас салах.",
        "usage": "gdivorce [@хэрэглэгч]",
        "examples": ["gdivorce", "gdivorce @Bold"],
    },
    "spouse": {
        "category": "Гэр бүл",
        "description_en": "See your current spouse(s).",
        "description_mn": "Одоогийн хань(иуд)-аа харах.",
        "usage": "gspouse",
        "examples": ["gspouse"],
    },
    "love": {
        "category": "Гэр бүл",
        "description_en": "Send love points to your partner.",
        "description_mn": "Ханьдаа хайрын оноо илгээх.",
        "usage": "glove @хэрэглэгч",
        "examples": ["glove @Bold"],
    },
    "gift": {
        "category": "Гэр бүл",
        "description_en": "Send a gift to your partner.",
        "description_mn": "Ханьдаа бэлэг өгөх.",
        "usage": "ggift <flower/chocolate/ring/necklace/teddy>",
        "examples": ["ggift flower", "ggift ring"],
    },
    "adopt": {
        "category": "Гэр бүл",
        "description_en": "Adopt a user as your child.",
        "description_mn": "Хэрэглэгчийг хүүхдээ болгон өргөмжлөх.",
        "usage": "gadopt @хэрэглэгч",
        "examples": ["gadopt @Bold"],
    },
    "disown": {
        "category": "Гэр бүл",
        "description_en": "Disown a child.",
        "description_mn": "Хүүхдээсээ татгалзах.",
        "usage": "gdisown @хэрэглэгч",
        "examples": ["gdisown @Bold"],
    },
    "familytree": {
        "category": "Гэр бүл",
        "description_en": "Show your family tree as an image.",
        "description_mn": "Гэр бүлийн модыг зураг хэлбэрээр харах.",
        "usage": "gfamilytree [@хэрэглэгч]",
        "examples": ["gfamilytree", "gfamilytree @Bold"],
    },
    "marriagepro": {
        "category": "Гэр бүл",
        "description_en": "View marriage card with love level.",
        "description_mn": "Хайр сэтгэлийн түвшинтэй гэрлэлтийн карт үзэх.",
        "usage": "gmarriagepro [@хэрэглэгч]",
        "examples": ["gmarriagepro", "gmarriagepro @Bold"],
    },

    # ── Админ / Удирдлага ──
    "admin-panel": {
        "category": "Админ",
        "description_en": "Open the economy admin settings panel.",
        "description_mn": "Эдийн засгийн админ тохиргооны самбар нээх.",
        "usage": "gadmin-panel",
        "examples": ["gadmin-panel"],
    },
    "role": {
        "category": "Админ",
        "description_en": "Manage permanent roles. Sub: give, remove.",
        "description_mn": "Байнгын үүрэг удирдах. Дэд: give, remove.",
        "usage": "grole give @хэрэглэгч @үүрэг",
        "examples": ["grole give @Bold @Member"],
    },
    "temprole": {
        "category": "Админ",
        "description_en": "Manage temporary roles. Sub: give, remove.",
        "description_mn": "Түр үүрэг удирдах. Дэд: give, remove.",
        "usage": "gtemprole give @хэрэглэгч @үүрэг 1h",
        "examples": ["gtemprole give @Bold @VIP 30m"],
    },
    "giveaway": {
        "category": "Админ",
        "description_en": "Create/manage giveaways. Sub: start, end, reroll.",
        "description_mn": "Гивэвэй үүсгэх/удирдах.",
        "usage": "ggiveaway start",
        "examples": ["ggiveaway start"],
    },
    "invites": {
        "category": "Админ",
        "description_en": "Invite tracking and leaderboard.",
        "description_mn": "Урилгын бүртгэл, самбар.",
        "usage": "ginvites leaderboard",
        "examples": ["ginvites leaderboard"],
    },

    # ── Хэрэгсэл ──
    "avatar": {
        "category": "Хэрэгсэл",
        "description_en": "Display user's avatar.",
        "description_mn": "Хэрэглэгчийн профайл зургийг харуулах.",
        "usage": "gavatar [@хэрэглэгч]",
        "examples": ["gavatar", "gavatar @Bold"],
    },
    "profile": {
        "category": "Хэрэгсэл",
        "description_en": "Display user's full profile card (money, level, job, etc.).",
        "description_mn": "Хэрэглэгчийн бүрэн профайл картыг харуулах (мөнгө, түвшин, ажил г.м).",
        "usage": "gprofile [@хэрэглэгч]",
        "examples": ["gprofile", "gprofile @Bold"],
    },
    "inventory": {
        "category": "Хэрэгсэл",
        "description_en": "Display user's inventory card.",
        "description_mn": "Хэрэглэгчийн инвентар картыг харуулах.",
        "usage": "ginventory",
        "examples": ["ginventory"],
    },
    "ping": {
        "category": "Хэрэгсэл",
        "description_en": "Check bot latency.",
        "description_mn": "Ботын хариу хүлээх хугацааг шалгах.",
        "usage": "gping",
        "examples": ["gping"],
    },
    "serverinfo": {
        "category": "Хэрэгсэл",
        "description_en": "Show server information.",
        "description_mn": "Серверийн мэдээлэл харуулах.",
        "usage": "gserverinfo",
        "examples": ["gserverinfo"],
    },

    # ── Тусгай / Бусад ──
    "mines": {
        "category": "Тоглоом",
        "description_en": "Play Minesweeper-style game for money.",
        "description_mn": "Уурхайн тоглоом (Mines) мөнгөтэй тоглох.",
        "usage": "gmines <дүн>",
        "examples": ["gmines 500"],
    },
    "pvp": {
        "category": "Тоглоом",
        "description_en": "Duel another player (Rock-Paper-Scissors style).",
        "description_mn": "Өөр тоглогчтой тулаан хийх (довтолгоо/хамгаалалт).",
        "usage": "gpvp @хэрэглэгч <дүн>",
        "examples": ["gpvp @Bold 500"],
    },
    "cafe": {
        "category": "Хоол",
        "description_en": "Open the cafe to buy food and drinks.",
        "description_mn": "Хоол унд захиалах кафе нээх.",
        "usage": "gcafe",
        "examples": ["gcafe"],
    },
    "dine": {
        "category": "Хоол",
        "description_en": "Eat food from your inventory to get buffs.",
        "description_mn": "Инвентариас хоол идэж, түр хүчин чадал авах.",
        "usage": "gdine <дугаар>",
        "examples": ["gdine 1"],
    },
    "shop": {
        "category": "Дэлгүүр",
        "description_en": "Open the shop to buy items.",
        "description_mn": "Бараа худалдан авах дэлгүүр нээх.",
        "usage": "gshop",
        "examples": ["gshop"],
    },
    "marketplace": {
        "category": "Дэлгүүр",
        "description_en": "Buy/sell items from other players.",
        "description_mn": "Бусад тоглогчдоос бараа худалдах/худалдан авах зах зээл.",
        "usage": "gmarketplace panel",
        "examples": ["gmarketplace panel"],
    },
    "stock": {
        "category": "Дэлгүүр",
        "description_en": "View and manage shop stock (admin).",
        "description_mn": "Дэлгүүрийн нөөцийг харж удирдах (админ).",
        "usage": "gstock status",
        "examples": ["gstock status"],
    },
    "confess": {
        "category": "Нууц",
        "description_en": "Send an anonymous confession.",
        "description_mn": "Нэрээ нууцлан захиа илгээх.",
        "usage": "gconfess",
        "examples": ["gconfess"],
    },
    "counting": {
        "category": "Тоглоом",
        "description_en": "Counting game (set channel, etc.)",
        "description_mn": "Тоолох тоглоом (суваг тохируулах гэх мэт).",
        "usage": "gcounting_setup",
        "examples": ["gcounting_setup"],
    },
    "voicesetup": {
        "category": "Админ",
        "description_en": "Setup temporary voice channels.",
        "description_mn": "Түр дуут суваг тохируулах.",
        "usage": "gvoicesetup",
        "examples": ["gvoicesetup"],
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

        embed = discord.Embed(
            title=f"{emoji} {category.upper()} тушаалууд",
            description="",
            color=color
        )
        commands = [(cmd, info) for cmd, info in COMMAND_INFO.items() if info["category"] == category]
        if not commands:
            embed.description = "Энэ ангилалд тушаал байхгүй."
            return embed

        for cmd, info in commands:
            embed.add_field(
                name=f"`{cmd}`",
                value=f"🇬🇧 {info['description_en']}\n🇲🇳 {info['description_mn']}",
                inline=False
            )
        embed.set_footer(text=f"{self.ctx.author.name} | {BOT_NAME} | LGC",
                         icon_url=self.ctx.author.display_avatar.url)
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

            embed = discord.Embed(
                title=f"📖 {cmd_key.upper()} тушаалын тусламж",
                color=0xfab387
            )
            embed.add_field(name="📂 Ангилал", value=info["category"], inline=True)
            embed.add_field(name="🇬🇧 Англи", value=info["description_en"], inline=False)
            embed.add_field(name="🇲🇳 Монгол", value=info["description_mn"], inline=False)
            embed.add_field(name="⚙️ Хэрэглэх хэлбэр", value=f"`{info['usage']}`", inline=False)
            if info.get("examples"):
                examples = "\n".join(f"• `{ex}`" for ex in info["examples"])
                embed.add_field(name="📝 Жишээ", value=examples, inline=False)
            embed.set_footer(text=f"{BOT_NAME} | Help System")
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Help(bot))