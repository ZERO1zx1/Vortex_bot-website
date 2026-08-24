import discord
from discord.ext import commands
from discord import app_commands, ui
from utils.branding import BOT_NAME, BOT_FOOTER
from datetime import datetime, timezone

# ═══════════════════════════════════════════════════════════════════════════════
# БҮХ КОМАНДЫН ДЭЛГЭРЭНГҮЙ ТОДОРХОЙЛОЛТ (шинэчлэгдсэн, алдаагүй)
# ═══════════════════════════════════════════════════════════════════════════════
COMMAND_INFO = {
    "admin-panel": {
        "description_mn": "Эдийн засаг админы самбар (тест/тохиргоо).",
        "description_en": "Economy admin panel",
        "category": "Эдийн засаг",
        "usage": "A!admin-panel",
        "examples": []
    },
    "bail": {
        "description_mn": "Баривчлагдаас мөнгөөр гарч чөлөөлөгдөнө.",
        "description_en": "Pay bail to be released",
        "category": "Эдийн засаг",
        "usage": "A!bail",
        "examples": []
    },
    "crime": {
        "description_mn": "Зөрүүд ажил — амжилттай бол урамшуулал, бусад тохиолдолд торгууль.",
        "description_en": "Commit a crime for cash",
        "category": "Эдийн засаг",
        "usage": "A!crime",
        "examples": []
    },
    "jobs": {
        "description_mn": "Ажлын систем харах/ажиллах.",
        "description_en": "Job system",
        "category": "Эдийн засаг",
        "usage": "A!jobs",
        "examples": []
    },
    "taxinfo": {
        "description_mn": "Татвар болон шимтгэлийн мэдээлэл.",
        "description_en": "Tax information",
        "category": "Эдийн засаг",
        "usage": "A!taxinfo",
        "examples": []
    },
    "workphrase": {
        "description_mn": "Ажлын хэллэгийн систем.",
        "description_en": "Work phrase system",
        "category": "Эдийн засаг",
        "usage": "A!workphrase",
        "examples": []
    },
    "coinflipgame": {
        "description_mn": "Талбайн тоглоом — зоогийн мөнгөнээр тал руу чихэгдэнэ.",
        "description_en": "Coinflip gambling game",
        "category": "Тоглоом",
        "usage": "A!coinflipgame <amount_str>",
        "examples": []
    },
    "crash": {
        "description_mn": "Crash тоглоом — өсөлт зогсоохоос өмнө гарч ав.",
        "description_en": "Crash betting game",
        "category": "Тоглоом",
        "usage": "A!crash <amount_str>",
        "examples": []
    },
    "gamestats": {
        "description_mn": "Өөрийн тоглоомын нийт статистик харуулна.",
        "description_en": "Your game statistics",
        "category": "Тоглоом",
        "usage": "A!gamestats",
        "examples": []
    },
    "highcard": {
        "description_mn": "Өндөр карт тоглоом — эсрэгтэйгээ өрсөлд.",
        "description_en": "High-card duel game",
        "category": "Тоглоом",
        "usage": "A!highcard <amount_str>",
        "examples": []
    },
    "mafia_setup": {
        "description_mn": "Mafia тоглоомын суваг/дүрэм тохируулах.",
        "description_en": "Setup mafia game",
        "category": "Тоглоом",
        "usage": "/mafia_setup",
        "examples": []
    },
    "mafiacreate": {
        "description_mn": "Шинэ Mafia наалт үүсгэнэ.",
        "description_en": "Create a mafia session",
        "category": "Тоглоом",
        "usage": "A!mafiacreate",
        "examples": []
    },
    "mafiaend": {
        "description_mn": "Идэвхтэй Mafia наалтыг дуусгана.",
        "description_en": "End mafia session",
        "category": "Тоглоом",
        "usage": "A!mafiaend",
        "examples": []
    },
    "mafiastart": {
        "description_mn": "Mafia наалт эхлүүлж тоглогчдыг хуваарилна.",
        "description_en": "Start mafia session",
        "category": "Тоглоом",
        "usage": "A!mafiastart",
        "examples": []
    },
    "roulettegame": {
        "description_mn": "Рулетт тоглоом — өнгө/тойрог тавина.",
        "description_en": "Roulette game",
        "category": "Тоглоом",
        "usage": "A!roulettegame <amount_str>",
        "examples": []
    },
    "cgive": {
        "description_mn": "Казино мөнгөө өөр хэрэглэгчид шилжүүлнэ.",
        "description_en": "Transfer casino chips",
        "category": "Казино",
        "usage": "A!cgive <target> <amount>",
        "examples": []
    },
    "8ball": {
        "description_mn": "Магадлалтай 8 тост хариулт өгнө.",
        "description_en": "Magic 8-ball answer",
        "category": "Хөгжилтэй",
        "usage": "A!8ball <question>",
        "examples": []
    },
    "coin": {
        "description_mn": "Зоогийн мөнгө хаяж үр дүнг харуулна.",
        "description_en": "Flip a coin",
        "category": "Хөгжилтэй",
        "usage": "A!coin",
        "examples": []
    },
    "count_save": {
        "description_mn": "Тооллогын оноо хадгалах.",
        "description_en": "Save counting score",
        "category": "Хөгжилтэй",
        "usage": "/count_save",
        "examples": []
    },
    "count_stats_server": {
        "description_mn": "Серверийн тооллогын статистик.",
        "description_en": "Server counting stats",
        "category": "Хөгжилтэй",
        "usage": "/count_stats_server",
        "examples": []
    },
    "count_stats_user": {
        "description_mn": "Хэрэглэгчийн тооллогын статистик.",
        "description_en": "User counting stats",
        "category": "Хөгжилтэй",
        "usage": "/count_stats_user <member>",
        "examples": []
    },
    "counting_setup": {
        "description_mn": "Тооллого тоглоомын тохиргоо.",
        "description_en": "Counting setup",
        "category": "Хөгжилтэй",
        "usage": "/counting_setup",
        "examples": []
    },
    "roll": {
        "description_mn": "1-ээс өгөгдсөн хүртэлх тоо шиднэ.",
        "description_en": "Roll a random number",
        "category": "Хөгжилтэй",
        "usage": "A!roll <maximum>",
        "examples": []
    },
    "avatar_config": {
        "description_mn": "Avatar шалгалт/лог системийн тохиргоо.",
        "description_en": "Avatar check config",
        "category": "Модераци",
        "usage": "A!avatar_config",
        "examples": []
    },
    "banlist": {
        "description_mn": "Хориглогдсон хэрэглэгчдийн жагсаалт.",
        "description_en": "List banned users",
        "category": "Модераци",
        "usage": "/banlist",
        "examples": []
    },
    "rrlist": {
        "description_mn": "Reaction-role холболтууд харах.",
        "description_en": "List reaction roles",
        "category": "Модераци",
        "usage": "A!rrlist",
        "examples": []
    },
    "staff_counts": {
        "description_mn": "Ажилчдын үйл ажиллагааны тооллого.",
        "description_en": "Staff activity counts",
        "category": "Модераци",
        "usage": "/staff_counts",
        "examples": []
    },
    "staff_setup": {
        "description_mn": "Стaff (ажилчин) систем тохируулах.",
        "description_en": "Setup staff system",
        "category": "Модераци",
        "usage": "/staff_setup",
        "examples": []
    },
    "staff_status": {
        "description_mn": "Ажилчны төлөв/статистик.",
        "description_en": "Staff status",
        "category": "Модераци",
        "usage": "/staff_status <member>",
        "examples": []
    },
    "temprole_config": {
        "description_mn": "Түр роль системийн тохиргоо.",
        "description_en": "Temp role config",
        "category": "Модераци",
        "usage": "/temprole_config",
        "examples": []
    },
    "unwarnid": {
        "description_mn": "Анхааруулгыг ID-гаар нь цуцлана.",
        "description_en": "Remove warning by ID",
        "category": "Модераци",
        "usage": "/unwarnid <warning_id>",
        "examples": []
    },
    "warned": {
        "description_mn": "Өөрт огдсон анхааруулгууд.",
        "description_en": "Your warnings",
        "category": "Модераци",
        "usage": "/warned",
        "examples": []
    },
    "warnedusers": {
        "description_mn": "Анхааруулга авсан хэрэглэгчид.",
        "description_en": "List warned users",
        "category": "Модераци",
        "usage": "/warnedusers",
        "examples": []
    },
    "leveling_setup": {
        "description_mn": "Түвшний системийн бүрэн тохиргоо (роль, XP, цаг).",
        "description_en": "Leveling setup",
        "category": "Түвшин",
        "usage": "A!leveling_setup",
        "examples": []
    },
    "serveractivity": {
        "description_mn": "Серверийн хамгийн идэвхтэй гишүүдийн жагсаалт.",
        "description_en": "Server activity ranking",
        "category": "Түвшин",
        "usage": "A!serveractivity",
        "examples": []
    },
    "autoaccept": {
        "description_mn": "Гэрлэх саналыг автоматаар зөвшөөрөх эсэх.",
        "description_en": "Auto-accept marriage",
        "category": "Гэр бүл",
        "usage": "/autoaccept <enabled>",
        "examples": []
    },
    "marriage_setup": {
        "description_mn": "Гэр бүлийн системийн тохиргоо.",
        "description_en": "Marriage setup",
        "category": "Гэр бүл",
        "usage": "/marriage_setup",
        "examples": []
    },
    "addmoney": {
        "description_mn": "Хэрэглэгчид мөнгө нэмнэ.",
        "description_en": "Add money to a user",
        "category": "Админ",
        "usage": "/addmoney <member> <amount>",
        "examples": []
    },
    "info": {
        "description_mn": "Бот/серверийн ерөнхий мэдээлэл.",
        "description_en": "Bot/server info",
        "category": "Админ",
        "usage": "/info",
        "examples": []
    },
    "removemoney": {
        "description_mn": "Хэрэглэгчээс мөнгө хасна.",
        "description_en": "Remove money from a user",
        "category": "Админ",
        "usage": "/removemoney <member> <amount>",
        "examples": []
    },
    "rolelist": {
        "description_mn": "Хэрэглэгчийн ролийн жагсаалт.",
        "description_en": "List user roles",
        "category": "Админ",
        "usage": "/rolelist <member>",
        "examples": []
    },
    "status": {
        "description_mn": "Ботын ажиллагааны төлөв.",
        "description_en": "Bot status",
        "category": "Админ",
        "usage": "/status",
        "examples": []
    },
    "addxp": {
        "description_mn": "addxp команд",
        "description_en": "addxp",
        "category": "Хэрэгсэл",
        "usage": "A!addxp <user> <amount>",
        "examples": []
    },
    "adopt": {
        "description_mn": "adopt команд",
        "description_en": "adopt",
        "category": "Хэрэгсэл",
        "usage": "A!adopt <child>",
        "examples": []
    },
    "angry": {
        "description_mn": "angry команд",
        "description_en": "angry",
        "category": "Хэрэгсэл",
        "usage": "A!angry",
        "examples": []
    },
    "announce": {
        "description_mn": "Серверт зар мэдээ тараах.",
        "description_en": "Send announcement",
        "category": "Хэрэгсэл",
        "usage": "/announce",
        "examples": []
    },
    "avatar": {
        "description_mn": "avatar команд",
        "description_en": "avatar",
        "category": "Хэрэгсэл",
        "usage": "A!avatar <member>",
        "examples": []
    },
    "balance": {
        "description_mn": "balance команд",
        "description_en": "balance",
        "category": "Хэрэгсэл",
        "usage": "A!balance <member>",
        "examples": []
    },
    "ban": {
        "description_mn": "ban команд",
        "description_en": "ban",
        "category": "Хэрэгсэл",
        "usage": "/ban <member> <reason>",
        "examples": []
    },
    "bankprotect": {
        "description_mn": "bankprotect команд",
        "description_en": "bankprotect",
        "category": "Хэрэгсэл",
        "usage": "A!bankprotect",
        "examples": []
    },
    "bite": {
        "description_mn": "bite команд",
        "description_en": "bite",
        "category": "Хэрэгсэл",
        "usage": "A!bite <target>",
        "examples": []
    },
    "blackjack": {
        "description_mn": "blackjack команд",
        "description_en": "blackjack",
        "category": "Хэрэгсэл",
        "usage": "A!blackjack <amount_str>",
        "examples": []
    },
    "boop": {
        "description_mn": "boop команд",
        "description_en": "boop",
        "category": "Хэрэгсэл",
        "usage": "A!boop <target>",
        "examples": []
    },
    "bully": {
        "description_mn": "bully команд",
        "description_en": "bully",
        "category": "Хэрэгсэл",
        "usage": "A!bully <target>",
        "examples": []
    },
    "cafe": {
        "description_mn": "cafe команд",
        "description_en": "cafe",
        "category": "Хэрэгсэл",
        "usage": "A!cafe",
        "examples": []
    },
    "cat": {
        "description_mn": "cat команд",
        "description_en": "cat",
        "category": "Хэрэгсэл",
        "usage": "A!cat",
        "examples": []
    },
    "clear": {
        "description_mn": "clear команд",
        "description_en": "clear",
        "category": "Хэрэгсэл",
        "usage": "/clear <amount>",
        "examples": []
    },
    "confess": {
        "description_mn": "confess команд",
        "description_en": "confess",
        "category": "Хэрэгсэл",
        "usage": "/confess",
        "examples": []
    },
    "cry": {
        "description_mn": "cry команд",
        "description_en": "cry",
        "category": "Хэрэгсэл",
        "usage": "A!cry",
        "examples": []
    },
    "cuddle": {
        "description_mn": "cuddle команд",
        "description_en": "cuddle",
        "category": "Хэрэгсэл",
        "usage": "A!cuddle <target>",
        "examples": []
    },
    "daily": {
        "description_mn": "daily команд",
        "description_en": "daily",
        "category": "Хэрэгсэл",
        "usage": "A!daily",
        "examples": []
    },
    "dance": {
        "description_mn": "dance команд",
        "description_en": "dance",
        "category": "Хэрэгсэл",
        "usage": "A!dance",
        "examples": []
    },
    "deposit": {
        "description_mn": "deposit команд",
        "description_en": "deposit",
        "category": "Хэрэгсэл",
        "usage": "A!deposit <amount_str>",
        "examples": []
    },
    "dice": {
        "description_mn": "dice команд",
        "description_en": "dice",
        "category": "Хэрэгсэл",
        "usage": "A!dice <amount_str>",
        "examples": []
    },
    "dine": {
        "description_mn": "dine команд",
        "description_en": "dine",
        "category": "Хэрэгсэл",
        "usage": "A!dine <number>",
        "examples": []
    },
    "disown": {
        "description_mn": "disown команд",
        "description_en": "disown",
        "category": "Хэрэгсэл",
        "usage": "A!disown <child>",
        "examples": []
    },
    "divorce": {
        "description_mn": "divorce команд",
        "description_en": "divorce",
        "category": "Хэрэгсэл",
        "usage": "A!divorce <user>",
        "examples": []
    },
    "dog": {
        "description_mn": "dog команд",
        "description_en": "dog",
        "category": "Хэрэгсэл",
        "usage": "A!dog",
        "examples": []
    },
    "eat": {
        "description_mn": "eat команд",
        "description_en": "eat",
        "category": "Хэрэгсэл",
        "usage": "A!eat",
        "examples": []
    },
    "familytree": {
        "description_mn": "familytree команд",
        "description_en": "familytree",
        "category": "Хэрэгсэл",
        "usage": "A!familytree <member>",
        "examples": []
    },
    "fox": {
        "description_mn": "fox команд",
        "description_en": "fox",
        "category": "Хэрэгсэл",
        "usage": "A!fox",
        "examples": []
    },
    "gamble": {
        "description_mn": "gamble команд",
        "description_en": "gamble",
        "category": "Хэрэгсэл",
        "usage": "A!gamble <amount_str>",
        "examples": []
    },
    "gif": {
        "description_mn": "gif команд",
        "description_en": "gif",
        "category": "Хэрэгсэл",
        "usage": "A!gif <query>",
        "examples": []
    },
    "gift": {
        "description_mn": "gift команд",
        "description_en": "gift",
        "category": "Хэрэгсэл",
        "usage": "A!gift <gift_type>",
        "examples": []
    },
    "greeting_reset": {
        "description_mn": "Мэндчилгээний тохиргоо цэвэрлэх.",
        "description_en": "Reset greetings",
        "category": "Хэрэгсэл",
        "usage": "/greeting_reset",
        "examples": []
    },
    "greeting_status": {
        "description_mn": "Мэндчилгээний төлөв харах.",
        "description_en": "Greeting status",
        "category": "Хэрэгсэл",
        "usage": "/greeting_status",
        "examples": []
    },
    "hack": {
        "description_mn": "hack команд",
        "description_en": "hack",
        "category": "Хэрэгсэл",
        "usage": "A!hack <target>",
        "examples": []
    },
    "handhold": {
        "description_mn": "handhold команд",
        "description_en": "handhold",
        "category": "Хэрэгсэл",
        "usage": "A!handhold <target>",
        "examples": []
    },
    "happy": {
        "description_mn": "happy команд",
        "description_en": "happy",
        "category": "Хэрэгсэл",
        "usage": "A!happy",
        "examples": []
    },
    "help": {
        "description_mn": "Тусламж — ангилал эсвэл тушаалын дэлгэрэнгүй.",
        "description_en": "Help command",
        "category": "Хэрэгсэл",
        "usage": "A!help <command>",
        "examples": []
    },
    "highfive": {
        "description_mn": "highfive команд",
        "description_en": "highfive",
        "category": "Хэрэгсэл",
        "usage": "A!highfive <target>",
        "examples": []
    },
    "highlow": {
        "description_mn": "highlow команд",
        "description_en": "highlow",
        "category": "Хэрэгсэл",
        "usage": "A!highlow <amount_str> <choice>",
        "examples": []
    },
    "hug": {
        "description_mn": "hug команд",
        "description_en": "hug",
        "category": "Хэрэгсэл",
        "usage": "A!hug <target>",
        "examples": []
    },
    "inventory": {
        "description_mn": "inventory команд",
        "description_en": "inventory",
        "category": "Хэрэгсэл",
        "usage": "A!inventory <member>",
        "examples": []
    },
    "kick": {
        "description_mn": "kick команд",
        "description_en": "kick",
        "category": "Хэрэгсэл",
        "usage": "/kick <member> <reason>",
        "examples": []
    },
    "kiss": {
        "description_mn": "kiss команд",
        "description_en": "kiss",
        "category": "Хэрэгсэл",
        "usage": "A!kiss <target>",
        "examples": []
    },
    "lang": {
        "description_mn": "Ботын хэл солих.",
        "description_en": "Change language",
        "category": "Хэрэгсэл",
        "usage": "A!lang <new_lang>",
        "examples": []
    },
    "laugh": {
        "description_mn": "laugh команд",
        "description_en": "laugh",
        "category": "Хэрэгсэл",
        "usage": "A!laugh",
        "examples": []
    },
    "leaderboard": {
        "description_mn": "leaderboard команд",
        "description_en": "leaderboard",
        "category": "Хэрэгсэл",
        "usage": "A!leaderboard",
        "examples": []
    },
    "lock": {
        "description_mn": "lock команд",
        "description_en": "lock",
        "category": "Хэрэгсэл",
        "usage": "/lock <channel> <reason>",
        "examples": []
    },
    "love": {
        "description_mn": "love команд",
        "description_en": "love",
        "category": "Хэрэгсэл",
        "usage": "A!love <target>",
        "examples": []
    },
    "marriagepro": {
        "description_mn": "marriagepro команд",
        "description_en": "marriagepro",
        "category": "Хэрэгсэл",
        "usage": "A!marriagepro <member>",
        "examples": []
    },
    "meme": {
        "description_mn": "meme команд",
        "description_en": "meme",
        "category": "Хэрэгсэл",
        "usage": "A!meme",
        "examples": []
    },
    "mines": {
        "description_mn": "mines команд",
        "description_en": "mines",
        "category": "Хэрэгсэл",
        "usage": "A!mines <bet>",
        "examples": []
    },
    "numberguess": {
        "description_mn": "numberguess команд",
        "description_en": "numberguess",
        "category": "Хэрэгсэл",
        "usage": "A!numberguess <amount_str>",
        "examples": []
    },
    "pat": {
        "description_mn": "pat команд",
        "description_en": "pat",
        "category": "Хэрэгсэл",
        "usage": "A!pat <target>",
        "examples": []
    },
    "ping": {
        "description_mn": "ping команд",
        "description_en": "ping",
        "category": "Хэрэгсэл",
        "usage": "A!ping",
        "examples": []
    },
    "placeholders": {
        "description_mn": "Мэндчилгээний боломжит тэмдэгтүүд.",
        "description_en": "Greeting placeholders",
        "category": "Хэрэгсэл",
        "usage": "/placeholders",
        "examples": []
    },
    "poke": {
        "description_mn": "poke команд",
        "description_en": "poke",
        "category": "Хэрэгсэл",
        "usage": "A!poke <target>",
        "examples": []
    },
    "profile": {
        "description_mn": "profile команд",
        "description_en": "profile",
        "category": "Хэрэгсэл",
        "usage": "A!profile <member>",
        "examples": []
    },
    "propose": {
        "description_mn": "propose команд",
        "description_en": "propose",
        "category": "Хэрэгсэл",
        "usage": "A!propose <user>",
        "examples": []
    },
    "punch": {
        "description_mn": "punch команд",
        "description_en": "punch",
        "category": "Хэрэгсэл",
        "usage": "A!punch <target>",
        "examples": []
    },
    "quest": {
        "description_mn": "quest команд",
        "description_en": "quest",
        "category": "Хэрэгсэл",
        "usage": "A!quest",
        "examples": []
    },
    "rank": {
        "description_mn": "rank команд",
        "description_en": "rank",
        "category": "Хэрэгсэл",
        "usage": "A!rank <user>",
        "examples": []
    },
    "relax": {
        "description_mn": "relax команд",
        "description_en": "relax",
        "category": "Хэрэгсэл",
        "usage": "A!relax",
        "examples": []
    },
    "removexp": {
        "description_mn": "removexp команд",
        "description_en": "removexp",
        "category": "Хэрэгсэл",
        "usage": "A!removexp <user> <amount>",
        "examples": []
    },
    "rob": {
        "description_mn": "rob команд",
        "description_en": "rob",
        "category": "Хэрэгсэл",
        "usage": "A!rob <target>",
        "examples": []
    },
    "rps": {
        "description_mn": "rps команд",
        "description_en": "rps",
        "category": "Хэрэгсэл",
        "usage": "A!rps <amount_str>",
        "examples": []
    },
    "set_log_channel": {
        "description_mn": "Лог бичих суваг тохируулах.",
        "description_en": "Set log channel",
        "category": "Хэрэгсэл",
        "usage": "/set_log_channel <channel>",
        "examples": []
    },
    "shop": {
        "description_mn": "shop команд",
        "description_en": "shop",
        "category": "Хэрэгсэл",
        "usage": "A!shop",
        "examples": []
    },
    "slap": {
        "description_mn": "slap команд",
        "description_en": "slap",
        "category": "Хэрэгсэл",
        "usage": "A!slap <target>",
        "examples": []
    },
    "sleep": {
        "description_mn": "sleep команд",
        "description_en": "sleep",
        "category": "Хэрэгсэл",
        "usage": "A!sleep",
        "examples": []
    },
    "slot": {
        "description_mn": "slot команд",
        "description_en": "slot",
        "category": "Хэрэгсэл",
        "usage": "A!slot <amount_str>",
        "examples": []
    },
    "snuggle": {
        "description_mn": "snuggle команд",
        "description_en": "snuggle",
        "category": "Хэрэгсэл",
        "usage": "A!snuggle <target>",
        "examples": []
    },
    "spouse": {
        "description_mn": "spouse команд",
        "description_en": "spouse",
        "category": "Хэрэгсэл",
        "usage": "A!spouse",
        "examples": []
    },
    "stare": {
        "description_mn": "stare команд",
        "description_en": "stare",
        "category": "Хэрэгсэл",
        "usage": "A!stare <target>",
        "examples": []
    },
    "stick": {
        "description_mn": "Статик мессеж бэхлэх.",
        "description_en": "Pin a sticky message",
        "category": "Хэрэгсэл",
        "usage": "/stick <content>",
        "examples": []
    },
    "template_create": {
        "description_mn": "Мэндчилгээний загвар үүсгэх.",
        "description_en": "Create template",
        "category": "Хэрэгсэл",
        "usage": "/template_create",
        "examples": []
    },
    "template_delete": {
        "description_mn": "Загвар устгах.",
        "description_en": "Delete template",
        "category": "Хэрэгсэл",
        "usage": "/template_delete <template_id>",
        "examples": []
    },
    "template_edit": {
        "description_mn": "Загвар засварлах.",
        "description_en": "Edit template",
        "category": "Хэрэгсэл",
        "usage": "/template_edit <template_id>",
        "examples": []
    },
    "template_list": {
        "description_mn": "Загваруудын жагсаалт.",
        "description_en": "List templates",
        "category": "Хэрэгсэл",
        "usage": "/template_list",
        "examples": []
    },
    "template_preview": {
        "description_mn": "Загварыг урьдчилж харах.",
        "description_en": "Preview template",
        "category": "Хэрэгсэл",
        "usage": "/template_preview <template_id> <member>",
        "examples": []
    },
    "think": {
        "description_mn": "think команд",
        "description_en": "think",
        "category": "Хэрэгсэл",
        "usage": "A!think",
        "examples": []
    },
    "transfer": {
        "description_mn": "transfer команд",
        "description_en": "transfer",
        "category": "Хэрэгсэл",
        "usage": "A!transfer <member> <amount_str>",
        "examples": []
    },
    "trivia": {
        "description_mn": "trivia команд",
        "description_en": "trivia",
        "category": "Хэрэгсэл",
        "usage": "A!trivia",
        "examples": []
    },
    "unban": {
        "description_mn": "unban команд",
        "description_en": "unban",
        "category": "Хэрэгсэл",
        "usage": "/unban <user_id> <reason>",
        "examples": []
    },
    "unlock": {
        "description_mn": "unlock команд",
        "description_en": "unlock",
        "category": "Хэрэгсэл",
        "usage": "/unlock <channel> <reason>",
        "examples": []
    },
    "unstick": {
        "description_mn": "Бэхэлсэн мессеж цуцлах.",
        "description_en": "Unpin sticky message",
        "category": "Хэрэгсэл",
        "usage": "A!unstick",
        "examples": []
    },
    "untimeout": {
        "description_mn": "untimeout команд",
        "description_en": "untimeout",
        "category": "Хэрэгсэл",
        "usage": "/untimeout <member>",
        "examples": []
    },
    "voicesettings": {
        "description_mn": "Түр дуут сувагны тохиргоо.",
        "description_en": "Temp voice settings",
        "category": "Хэрэгсэл",
        "usage": "/voicesettings",
        "examples": []
    },
    "voicesetup": {
        "description_mn": "voicesetup команд",
        "description_en": "voicesetup",
        "category": "Хэрэгсэл",
        "usage": "/voicesetup",
        "examples": []
    },
    "warn": {
        "description_mn": "warn команд",
        "description_en": "warn",
        "category": "Хэрэгсэл",
        "usage": "/warn <member> <reason>",
        "examples": []
    },
    "warnings": {
        "description_mn": "warnings команд",
        "description_en": "warnings",
        "category": "Хэрэгсэл",
        "usage": "/warnings <member>",
        "examples": []
    },
    "wave": {
        "description_mn": "wave команд",
        "description_en": "wave",
        "category": "Хэрэгсэл",
        "usage": "A!wave <target>",
        "examples": []
    },
    "withdraw": {
        "description_mn": "withdraw команд",
        "description_en": "withdraw",
        "category": "Хэрэгсэл",
        "usage": "A!withdraw <amount_str>",
        "examples": []
    },
    "work": {
        "description_mn": "work команд",
        "description_en": "work",
        "category": "Хэрэгсэл",
        "usage": "A!work <custom_text>",
        "examples": []
    },
    "accessories": {
        "description_mn": "Гоёл чимэглэлийн зүйлс харах.",
        "description_en": "View accessories",
        "category": "Дэлгүүр",
        "usage": "A!accessories",
        "examples": []
    },
    "buy": {
        "description_mn": "Дэлгүүрээс зүйл худалдаж авна.",
        "description_en": "Buy an item",
        "category": "Дэлгүүр",
        "usage": "A!buy <item_input> <quantity>",
        "examples": []
    },
    "drink": {
        "description_mn": "Уух зүйл ашиглаж согтуур болно.",
        "description_en": "Drink an item",
        "category": "Дэлгүүр",
        "usage": "A!drink <item_id>",
        "examples": []
    },
    "equip": {
        "description_mn": "Зүйлээ зүүж авна.",
        "description_en": "Equip an item",
        "category": "Дэлгүүр",
        "usage": "A!equip <item_input>",
        "examples": []
    },
    "equipped": {
        "description_mn": "Хэрэглэгчийн зүүсэн зүйлс харах.",
        "description_en": "View equipped items",
        "category": "Дэлгүүр",
        "usage": "A!equipped <member>",
        "examples": []
    },
    "iteminfo": {
        "description_mn": "Зүйлний дэлгэрэнгүй мэдээлэл (ID-тай).",
        "description_en": "Item details",
        "category": "Дэлгүүр",
        "usage": "A!iteminfo <item_id>",
        "examples": []
    },
    "market": {
        "description_mn": "Зах зээлийн зарыг харах.",
        "description_en": "View marketplace",
        "category": "Дэлгүүр",
        "usage": "A!market",
        "examples": []
    },
    "mp": {
        "description_mn": "Зах зээл командын товчлол.",
        "description_en": "Marketplace shortcut",
        "category": "Дэлгүүр",
        "usage": "A!mp",
        "examples": []
    },
    "sogtol": {
        "description_mn": "Согтуу байдлын төлөв харах.",
        "description_en": "Drunk status",
        "category": "Дэлгүүр",
        "usage": "A!sogtol",
        "examples": []
    },
    "trade": {
        "description_mn": "Нөхөртэйгөө зүйл солилцох.",
        "description_en": "Trade items with a user",
        "category": "Дэлгүүр",
        "usage": "A!trade <user> <item> <amount> <target>",
        "examples": []
    },
    "unequip": {
        "description_mn": "Зүүсэн зүйлээ тайрч хасна.",
        "description_en": "Unequip an item",
        "category": "Дэлгүүр",
        "usage": "A!unequip <slot_input>",
        "examples": []
    },
    "use": {
        "description_mn": "Зүйлээ ашиглана.",
        "description_en": "Use an item",
        "category": "Дэлгүүр",
        "usage": "A!use <item_input>",
        "examples": []
    },
    "vape": {
        "description_mn": "Вейп ашиглан согтуурээ арилгана.",
        "description_en": "Use a vape",
        "category": "Дэлгүүр",
        "usage": "A!vape",
        "examples": []
    },
    "confess_blacklist": {
        "description_mn": "Нууц мессежид хориглосон үг жагсаах.",
        "description_en": "Confession blacklist",
        "category": "Нууц",
        "usage": "/confess_blacklist <action> <word>",
        "examples": []
    },
    "confess_delete": {
        "description_mn": "Нууц мессежийг ID-гаар устгах.",
        "description_en": "Delete a confession",
        "category": "Нууц",
        "usage": "/confess_delete <confession_id>",
        "examples": []
    },
    "confess_setup": {
        "description_mn": "Нууц мессежийн суваг тохируулах.",
        "description_en": "Confession setup",
        "category": "Нууц",
        "usage": "/confess_setup",
        "examples": []
    },
    "confess_stats": {
        "description_mn": "Нууц мессежийн статистик.",
        "description_en": "Confession stats",
        "category": "Нууц",
        "usage": "/confess_stats",
        "examples": []
    },
}
class HelpView(ui.View):
    def __init__(self, ctx, default_category: str = "Эдийн засаг"):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.current_category = default_category

        options = []
        for cat in CATEGORY_EMOJIS:
            options.append(discord.SelectOption(
                label=cat,
                value=cat,
                emoji=CATEGORY_EMOJIS.get(cat, "📁"),
                description=f"{CATEGORY_ICONS.get(cat,'📌')} {sum(1 for v in COMMAND_INFO.values() if v['category']==cat)} тушаал",
            ))
        self.select = ui.Select(placeholder="📂 Ангилал сонгох...", options=options, row=0)
        self.select.callback = self.on_select
        self.add_item(self.select)

        home = ui.Button(label="🏠 Нүүр", emoji="🏠", style=discord.ButtonStyle.primary, row=1)
        home.callback = self.on_home
        self.add_item(home)

    async def on_select(self, interaction: discord.Interaction):
        self.current_category = self.select.values[0]
        await self._render(interaction)

    async def on_home(self, interaction: discord.Interaction):
        self.current_category = None
        await self._render(interaction)

    async def send_initial(self):
        embed = self.build_home_embed()
        return await self.ctx.send(embed=embed, view=self)

    async def _render(self, interaction: discord.Interaction):
        if self.current_category is None:
            embed = self.build_home_embed()
        else:
            embed = self.build_category_embed(self.current_category)
        await interaction.response.edit_message(embed=embed, view=self)

    # ── Нүүр хуудас ──
    def build_home_embed(self):
        total = len(COMMAND_INFO)
        embed = discord.Embed(
            title=f"📚 {BOT_NAME} — Тусламжийн төв",
            description=(
                f"> **{total}** тушаал · **{len(CATEGORY_EMOJIS)}** ангилал\n"
                f"> Префикс: **`A!`**  •  Slash команд (`/`) мөн дэмжигдэнэ"
            ),
            color=0x1e1e2f,
            timestamp=datetime.now(timezone.utc),
        )
        cats = list(CATEGORY_EMOJIS.keys())
        half = (len(cats) + 1) // 2
        left, right = cats[:half], cats[half:]
        lines_l = [f"{CATEGORY_EMOJIS[c]} {c} · `{sum(1 for v in COMMAND_INFO.values() if v['category']==c)}`" for c in left]
        lines_r = [f"{CATEGORY_EMOJIS[c]} {c} · `{sum(1 for v in COMMAND_INFO.values() if v['category']==c)}`" for c in right]
        embed.add_field(name="🗂️ Ангилалууд", value="\n".join(lines_l) or "—", inline=True)
        embed.add_field(name="\u200b", value="\n".join(lines_r) or "—", inline=True)
        embed.add_field(
            name="💡 Хэрэглээ",
            value=(
                "> Дэлгэрэнгүй тушаал: `A!help rank`\n"
                "> Slash хувилбар: `/help rank`\n"
                "> Дээрх цэснээс ангилал сонгоод товчоор үзнэ үү."
            ),
            inline=False,
        )
        embed.set_author(name=str(self.ctx.author), icon_url=self.ctx.author.display_avatar.url)
        if self.ctx.guild and self.ctx.guild.icon:
            embed.set_thumbnail(url=self.ctx.guild.icon.url)
        elif self.ctx.bot.user:
            embed.set_thumbnail(url=self.ctx.bot.user.display_avatar.url)
        embed.set_footer(text=f"{BOT_NAME} • Тусламжийн самбар • 180с дараа дуусна")
        return embed

    # ── Ангилалын хуудас ──
    def build_category_embed(self, category: str):
        emoji = CATEGORY_EMOJIS.get(category, "📁")
        icon = CATEGORY_ICONS.get(category, "📌")
        color = CATEGORY_COLORS.get(category, 0x1e1e2f)

        commands = [(cmd, info) for cmd, info in COMMAND_INFO.items() if info["category"] == category]

        embed = discord.Embed(
            title=f"{emoji}  {category}  {icon}",
            description=f"**{len(commands)} тушаал** — {BOT_NAME}",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        if not commands:
            embed.add_field(name="📭 Хоосон", value="> Энэ ангилалд тушаал байхгүй байна.", inline=False)
            return embed

        MAX = 950
        chunks, current, size = [], [], 0
        for cmd, info in commands:
            line = (
                f"**`{cmd}`** — {info['description_mn']}\n"
                f"　↳ `{info['usage']}`\n"
            )
            if size + len(line) > MAX and current:
                chunks.append("".join(current)); current, size = [], 0
            current.append(line); size += len(line)
        if current:
            chunks.append("".join(current))

        for i, chunk in enumerate(chunks, start=1):
            name = f"{icon} Тушаалууд {i}/{len(chunks)}" if len(chunks) > 1 else f"{icon} Тушаалууд"
            embed.add_field(name=name, value=chunk.strip(), inline=False)

        embed.set_author(name=str(self.ctx.author), icon_url=self.ctx.author.display_avatar.url)
        if self.ctx.guild and self.ctx.guild.icon:
            embed.set_thumbnail(url=self.ctx.guild.icon.url)
        embed.set_footer(text=f"{BOT_NAME} • {category} • Нүүр рүү буцах: 🏠")
        return embed


# Категорийн тохиргоо
CATEGORY_EMOJIS = {
    "Эдийн засаг": "💰",
    "Тоглоом": "🎮",
    "Казино": "🎰",
    "Хөгжилтэй": "🎉",
    "Модераци": "🛡️",
    "Түвшин": "✨",
    "Гэр бүл": "💒",
    "Админ": "⚙️",
    "Хэрэгсэл": "🔧",
    "Хоол": "🍜",
    "Дэлгүүр": "🛍️",
    "Нууц": "🤫",
    "Даалгавар": "📜",
}

CATEGORY_ICONS = {
    "Эдийн засаг": "💵",
    "Тоглоом": "🕹️",
    "Казино": "🃏",
    "Хөгжилтэй": "💖",
    "Модераци": "⚖️",
    "Түвшин": "📈",
    "Гэр бүл": "💍",
    "Админ": "🔐",
    "Хэрэгсэл": "📋",
    "Хоол": "🍱",
    "Дэлгүүр": "🏪",
    "Нууц": "📝",
    "Даалгавар": "🗒️",
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

CATEGORY_COUNT_INFO = f"{len(CATEGORY_EMOJIS)} ангилал · нийт {len(COMMAND_INFO)} тушаал"


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='help', description="Командын тусламж (ангилал эсвэл дэлгэрэнгүй)")
    @app_commands.describe(command="Тусламж авах тушаалын нэр (хоосон орхивол ангиллын самбар)")
    async def help_command(self, ctx, *, command: str = None):
        if command is None:
            view = HelpView(ctx, default_category="Эдийн засаг")
            await view.send_initial()
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
            embed.add_field(
                name="⌨️ Slash хувилбар",
                value=f"`/{cmd_key}`",
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
