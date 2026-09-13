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
    "balance": {
        "description_mn": "Үлдэгдэл мөнгө болон банкны дүнг харуулна.",
        "description_en": "Check your balance",
        "category": "Эдийн засаг",
        "usage": "A!balance <member>",
        "examples": []
    },
    "bankprotect": {
        "description_mn": "Мөнгөө шилжүүлэг/дээрэмд өртөхөөс хамгаална.",
        "description_en": "Protect your balance",
        "category": "Эдийн засаг",
        "usage": "A!bankprotect",
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
    "daily": {
        "description_mn": "Өдрийн урамшууллаа авах (цатгалан/сэтгэл санаагаар).",
        "description_en": "Claim your daily reward",
        "category": "Эдийн засаг",
        "usage": "A!daily",
        "examples": []
    },
    "deposit": {
        "description_mn": "Банк руу мөнгө байршуулна.",
        "description_en": "Deposit money to bank",
        "category": "Эдийн засаг",
        "usage": "A!deposit <amount_str>",
        "examples": []
    },
    "eat": {
        "description_mn": "Инвентариас хоол идэж цатгалан болон сэтгэл санаагаа сэргээнэ.",
        "description_en": "Eat food from inventory",
        "category": "Эдийн засаг",
        "usage": "A!eat",
        "examples": []
    },
    "jobs": {
        "description_mn": "Ажлын систем харах/ажиллах.",
        "description_en": "View and work jobs",
        "category": "Эдийн засаг",
        "usage": "A!jobs",
        "examples": []
    },
    "relax": {
        "description_mn": "Амарч цатгалан/сэтгэл санаагаа сэргээнэ.",
        "description_en": "Relax to recover stats",
        "category": "Эдийн засаг",
        "usage": "A!relax",
        "examples": []
    },
    "taxinfo": {
        "description_mn": "Татвар болон шимтгэлийн мэдээлэл.",
        "description_en": "Tax information",
        "category": "Эдийн засаг",
        "usage": "A!taxinfo",
        "examples": []
    },
    "transfer": {
        "description_mn": "Өөр хэрэглэгчид мөнгө шилжүүлнэ.",
        "description_en": "Send money to a user",
        "category": "Эдийн засаг",
        "usage": "A!transfer <member> <amount_str>",
        "examples": []
    },
    "withdraw": {
        "description_mn": "Банкнаас мөнгө гаргаж авна.",
        "description_en": "Withdraw money from bank",
        "category": "Эдийн засаг",
        "usage": "A!withdraw <amount_str>",
        "examples": []
    },
    "work": {
        "description_mn": "Ажиллаж мөнгө олох (нэмэлт текст зааж болно).",
        "description_en": "Work to earn money",
        "category": "Эдийн засаг",
        "usage": "A!work <custom_text>",
        "examples": []
    },
    "workphrase": {
        "description_mn": "Ажлын өгүүлбэрийн тохиргоо (embed+button+modal).",
        "description_en": "Work phrase settings",
        "category": "Эдийн засаг",
        "usage": "A!workphrase",
        "examples": []
    },
    "coinflipgame": {
        "description_mn": "Зоо шидэлтийн мөрийтэй тоглоом — тал тавиад бооцоо тавина.",
        "description_en": "Coinflip gambling game",
        "category": "Тоглоом",
        "usage": "A!coinflipgame <amount_str>",
        "examples": []
    },
    "crash": {
        "description_mn": "Crash тоглоом — өсөлт зогсохоос өмнө гарч ав.",
        "description_en": "Crash betting game",
        "category": "Тоглоом",
        "usage": "A!crash <amount_str>",
        "examples": []
    },
    "dice": {
        "description_mn": "Шоо шидэлтийн мөрийтэй тоглоом.",
        "description_en": "Dice gambling game",
        "category": "Тоглоом",
        "usage": "A!dice <amount_str>",
        "examples": []
    },
    "gamble": {
        "description_mn": "Мөрийтэй тоглоом — бооцоо тавин үржүүлэх боломж.",
        "description_en": "Gambling game",
        "category": "Тоглоом",
        "usage": "A!gamble <amount_str>",
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
        "description_mn": "Өндөр карт тоглоом — эсрэгтэйгээ өрсөлдөж карт зүүнэ.",
        "description_en": "High-card duel game",
        "category": "Тоглоом",
        "usage": "A!highcard <amount_str>",
        "examples": []
    },
    "numberguess": {
        "description_mn": "Тоо таах мөрийтэй тоглоом.",
        "description_en": "Number guessing game",
        "category": "Тоглоом",
        "usage": "A!numberguess <amount_str>",
        "examples": []
    },
    "roulettegame": {
        "description_mn": "Рулет тоглоом — өнгө/тоо тавина.",
        "description_en": "Roulette game",
        "category": "Тоглоом",
        "usage": "A!roulettegame <amount_str>",
        "examples": []
    },
    "rps": {
        "description_mn": "Чулуу-цаас-хайч мөрийтэй тоглоом.",
        "description_en": "Rock-paper-scissors game",
        "category": "Тоглоом",
        "usage": "A!rps <amount_str>",
        "examples": []
    },
    "trivia": {
        "description_mn": "Асуулт хариултын мөрийтэй тоглоом.",
        "description_en": "Trivia quiz game",
        "category": "Тоглоом",
        "usage": "A!trivia",
        "examples": []
    },
    "mines": {
        "description_mn": "Mines тоглоом — найдваргүй талбай нээж урамшуулал цуглуул.",
        "description_en": "Mines mining game",
        "category": "Тоглоом",
        "usage": "A!mines <bet>",
        "examples": []
    },
    "pvp": {
        "description_mn": "Хэрэглэгчтэй тулаан хийх (бооцоотой).",
        "description_en": "PvP duel with a user",
        "category": "Тоглоом",
        "usage": "A!pvp <opponent> <amount>",
        "examples": []
    },
    "mafia_setup": {
        "description_mn": "Мафи тоглоомын суваг/дүрэм тохируулах.",
        "description_en": "Setup mafia game",
        "category": "Тоглоом",
        "usage": "/mafia_setup",
        "examples": []
    },
    "mafiacreate": {
        "description_mn": "Шинэ мафи тоглоом үүсгэнэ.",
        "description_en": "Create a mafia session",
        "category": "Тоглоом",
        "usage": "A!mafiacreate",
        "examples": []
    },
    "mafiastart": {
        "description_mn": "Мафи тоглоомыг эхлүүлж тоглогчдыг хуваарилна.",
        "description_en": "Start mafia session",
        "category": "Тоглоом",
        "usage": "A!mafiastart",
        "examples": []
    },
    "mafiaend": {
        "description_mn": "Идэвхтэй мафи тоглоомыг дуусгана.",
        "description_en": "End mafia session",
        "category": "Тоглоом",
        "usage": "A!mafiaend",
        "examples": []
    },
    "blackjack": {
        "description_mn": "Blackjack картын мөрийтэй тоглоом — дилерийг ял.",
        "description_en": "Blackjack card game",
        "category": "Казино",
        "usage": "A!blackjack <amount_str>",
        "examples": []
    },
    "rob": {
        "description_mn": "Өөр хэрэглэгчийг дээрэмдэж мөнгө авах (эрсдэлтэй).",
        "description_en": "Rob another user",
        "category": "Казино",
        "usage": "A!rob <target>",
        "examples": []
    },
    "hack": {
        "description_mn": "Хэрэглэгчийн данс руу хакдах (маш эрсдэлтэй).",
        "description_en": "Hack a user account",
        "category": "Казино",
        "usage": "A!hack <target>",
        "examples": []
    },
    "cgive": {
        "description_mn": "Казино мөнгөө өөр хэрэглэгчид шилжүүлнэ.",
        "description_en": "Transfer casino chips",
        "category": "Казино",
        "usage": "A!cgive <target> <amount>",
        "examples": []
    },
    "highlow": {
        "description_mn": "Өндөр/бага мөрийтэй тоглоом — дараагийн тоог таа.",
        "description_en": "High-low betting game",
        "category": "Казино",
        "usage": "A!highlow <amount_str> <choice>",
        "examples": []
    },
    "slot": {
        "description_mn": "Оромын машины мөрийтэй тоглоом.",
        "description_en": "Slot machine game",
        "category": "Казино",
        "usage": "A!slot <amount_str>",
        "examples": []
    },
    "8ball": {
        "description_mn": "Магик 8-бөмбөг санамсаргүй хариулт өгнө.",
        "description_en": "Magic 8-ball answer",
        "category": "Хөгжилтэй",
        "usage": "A!8ball <question>",
        "examples": []
    },
    "angry": {
        "description_mn": "Уурласан гиф илгээнэ.",
        "description_en": "Angry reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!angry",
        "examples": []
    },
    "avatar": {
        "description_mn": "Хэрэглэгчийн аватарыг харуулна.",
        "description_en": "Show a user avatar",
        "category": "Хөгжилтэй",
        "usage": "A!avatar <member>",
        "examples": []
    },
    "bite": {
        "description_mn": "Хазах гиф илгээнэ.",
        "description_en": "Bite reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!bite <target>",
        "examples": []
    },
    "boop": {
        "description_mn": "Boop хийх гиф илгээнэ.",
        "description_en": "Boop reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!boop <target>",
        "examples": []
    },
    "bully": {
        "description_mn": "Дээрэлхэх гиф илгээнэ.",
        "description_en": "Bully reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!bully <target>",
        "examples": []
    },
    "cat": {
        "description_mn": "Санамсаргүй муурын зураг илгээнэ.",
        "description_en": "Random cat image",
        "category": "Хөгжилтэй",
        "usage": "A!cat",
        "examples": []
    },
    "coin": {
        "description_mn": "Зоо шидэж үр дүнг харуулна.",
        "description_en": "Flip a coin",
        "category": "Хөгжилтэй",
        "usage": "A!coin",
        "examples": []
    },
    "cry": {
        "description_mn": "Уйлах гиф илгээнэ.",
        "description_en": "Cry reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!cry",
        "examples": []
    },
    "cuddle": {
        "description_mn": "Тэврэх гиф илгээнэ.",
        "description_en": "Cuddle reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!cuddle <target>",
        "examples": []
    },
    "dance": {
        "description_mn": "Бүжиглэх гиф илгээнэ.",
        "description_en": "Dance reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!dance",
        "examples": []
    },
    "dog": {
        "description_mn": "Санамсаргүй нохойны зураг илгээнэ.",
        "description_en": "Random dog image",
        "category": "Хөгжилтэй",
        "usage": "A!dog",
        "examples": []
    },
    "fox": {
        "description_mn": "Санамсаргүй үнэгний зураг илгээнэ.",
        "description_en": "Random fox image",
        "category": "Хөгжилтэй",
        "usage": "A!fox",
        "examples": []
    },
    "gif": {
        "description_mn": "Хайлтанд тохирох гиф илгээнэ.",
        "description_en": "Search and send a gif",
        "category": "Хөгжилтэй",
        "usage": "A!gif <query>",
        "examples": []
    },
    "happy": {
        "description_mn": "Баярлах гиф илгээнэ.",
        "description_en": "Happy reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!happy",
        "examples": []
    },
    "handhold": {
        "description_mn": "Гар барьсан гиф илгээнэ.",
        "description_en": "Handhold reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!handhold <target>",
        "examples": []
    },
    "highfive": {
        "description_mn": "Гар алгадсан гиф илгээнэ.",
        "description_en": "High-five reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!highfive <target>",
        "examples": []
    },
    "hug": {
        "description_mn": "Тэврэх гиф илгээнэ.",
        "description_en": "Hug reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!hug <target>",
        "examples": []
    },
    "kiss": {
        "description_mn": "Үнсэх гиф илгээнэ.",
        "description_en": "Kiss reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!kiss <target>",
        "examples": []
    },
    "laugh": {
        "description_mn": "Инээх гиф илгээнэ.",
        "description_en": "Laugh reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!laugh",
        "examples": []
    },
    "meme": {
        "description_mn": "Санамсаргүй meme илгээнэ.",
        "description_en": "Random meme",
        "category": "Хөгжилтэй",
        "usage": "A!meme",
        "examples": []
    },
    "pat": {
        "description_mn": "Толгой илэх гиф илгээнэ.",
        "description_en": "Pat reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!pat <target>",
        "examples": []
    },
    "poke": {
        "description_mn": "Цохих гиф илгээнэ.",
        "description_en": "Poke reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!poke <target>",
        "examples": []
    },
    "punch": {
        "description_mn": "Нүдэх гиф илгээнэ.",
        "description_en": "Punch reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!punch <target>",
        "examples": []
    },
    "roll": {
        "description_mn": "1-ээс өгөгдсөн тоо хүртэл санамсаргүй тоо шиднэ.",
        "description_en": "Roll a random number",
        "category": "Хөгжилтэй",
        "usage": "A!roll <maximum>",
        "examples": []
    },
    "slap": {
        "description_mn": "Алгадах гиф илгээнэ.",
        "description_en": "Slap reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!slap <target>",
        "examples": []
    },
    "sleep": {
        "description_mn": "Унтах гиф илгээнэ.",
        "description_en": "Sleep reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!sleep",
        "examples": []
    },
    "snuggle": {
        "description_mn": "Тусалдсан гиф илгээнэ.",
        "description_en": "Snuggle reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!snuggle <target>",
        "examples": []
    },
    "stare": {
        "description_mn": "Харж зогсох гиф илгээнэ.",
        "description_en": "Stare reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!stare <target>",
        "examples": []
    },
    "think": {
        "description_mn": "Бодож байгаа гиф илгээнэ.",
        "description_en": "Think reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!think",
        "examples": []
    },
    "wave": {
        "description_mn": "Дав хийн вий.",
        "description_en": "Wave reaction gif",
        "category": "Хөгжилтэй",
        "usage": "A!wave <target>",
        "examples": []
    },
    "count_save": {
        "description_mn": "Тооллогын оноо хадгална.",
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
        "description_mn": "Тооллого тоглоомын тохиргооны самбар.",
        "description_en": "Counting setup panel",
        "category": "Хөгжилтэй",
        "usage": "/counting_setup",
        "examples": []
    },
    "lock": {
        "description_mn": "Сувгийг түгжинэ (гишүүд мессеж бичих боломжгүй).",
        "description_en": "Lock a channel",
        "category": "Модераци",
        "usage": "/lock <channel> <reason>",
        "examples": []
    },
    "unlock": {
        "description_mn": "Сувгийн түгжээг тайлна.",
        "description_en": "Unlock a channel",
        "category": "Модераци",
        "usage": "/unlock <channel> <reason>",
        "examples": []
    },
    "kick": {
        "description_mn": "Хэрэглэгчийг серверээс хөөнө.",
        "description_en": "Kick a member",
        "category": "Модераци",
        "usage": "/kick <member> <reason>",
        "examples": []
    },
    "ban": {
        "description_mn": "Хэрэглэгчийг бан хийнэ.",
        "description_en": "Ban a member",
        "category": "Модераци",
        "usage": "/ban <member> <reason>",
        "examples": []
    },
    "unban": {
        "description_mn": "Хэрэглэгчийн баныг цуцлана.",
        "description_en": "Unban a user",
        "category": "Модераци",
        "usage": "/unban <user_id> <reason>",
        "examples": []
    },
    "banlist": {
        "description_mn": "Хориглогдсон хэрэглэгчдийн жагсаалт.",
        "description_en": "List banned users",
        "category": "Модераци",
        "usage": "/banlist",
        "examples": []
    },
    "clear": {
        "description_mn": "Сувгийн мессежүүдийг устгана.",
        "description_en": "Delete messages",
        "category": "Модераци",
        "usage": "/clear <amount>",
        "examples": []
    },
    "timeout": {
        "description_mn": "Хэрэглэгчийг түр хаана (timeout).",
        "description_en": "Timeout a member",
        "category": "Модераци",
        "usage": "/timeout <member> <duration> <reason>",
        "examples": []
    },
    "untimeout": {
        "description_mn": "Түр хаалтыг цуцална.",
        "description_en": "Remove a timeout",
        "category": "Модераци",
        "usage": "/untimeout <member>",
        "examples": []
    },
    "warn": {
        "description_mn": "Хэрэглэгчид анхааруулга өгнө.",
        "description_en": "Warn a member",
        "category": "Модераци",
        "usage": "/warn <member> <reason>",
        "examples": []
    },
    "unwarn": {
        "description_mn": "Хэрэглэгчийн анхааруулгыг хасана.",
        "description_en": "Remove a warning",
        "category": "Модераци",
        "usage": "/unwarn <member> <amount>",
        "examples": []
    },
    "unwarnid": {
        "description_mn": "Анхааруулгыг ID-гаар нь цуцална.",
        "description_en": "Remove warning by ID",
        "category": "Модераци",
        "usage": "/unwarnid <warning_id>",
        "examples": []
    },
    "warned": {
        "description_mn": "Танд өгсөн анхааруулгуудыг харна.",
        "description_en": "View your warnings",
        "category": "Модераци",
        "usage": "/warned",
        "examples": []
    },
    "warnings": {
        "description_mn": "Хэрэглэгчийн анхааруулгыг харна.",
        "description_en": "View user warnings",
        "category": "Модераци",
        "usage": "/warnings <member>",
        "examples": []
    },
    "warnedusers": {
        "description_mn": "Анхааруулга авсан хэрэглэгчдийн жагсаалт.",
        "description_en": "List warned users",
        "category": "Модераци",
        "usage": "/warnedusers",
        "examples": []
    },
    "staff_setup": {
        "description_mn": "Staff (ажилчин) систем тохируулах.",
        "description_en": "Setup staff system",
        "category": "Модераци",
        "usage": "/staff_setup",
        "examples": []
    },
    "staff_counts": {
        "description_mn": "Долоо хоногийн staff онооны эрэмбэ.",
        "description_en": "Weekly staff ranking",
        "category": "Модераци",
        "usage": "/staff_counts",
        "examples": []
    },
    "staff_status": {
        "description_mn": "Тухайн staff-ийн дэлгэрэнгүй үзүүлэлт.",
        "description_en": "Staff member status",
        "category": "Модераци",
        "usage": "/staff_status <member>",
        "examples": []
    },
    "temprole_config": {
        "description_mn": "Түр үүргийн системийн тохиргооны самбар.",
        "description_en": "Temp role config",
        "category": "Модераци",
        "usage": "/temprole_config",
        "examples": []
    },
    "avatar_config": {
        "description_mn": "Avatar шалгалт/лог системийн тохиргоо.",
        "description_en": "Avatar check config",
        "category": "Модераци",
        "usage": "A!avatar_config",
        "examples": []
    },
    "automod": {
        "description_mn": "Auto-moderation тохиргоо (холбоос/спам/үг).",
        "description_en": "Auto-moderation settings",
        "category": "Модераци",
        "usage": "/automod <action> <feature>",
        "examples": []
    },
    "rr": {
        "description_mn": "Reaction role тохиргооны самбар.",
        "description_en": "Reaction role setup",
        "category": "Модераци",
        "usage": "/rr <action> <emoji>",
        "examples": []
    },
    "rrlist": {
        "description_mn": "Reaction-role холболтуудыг харуулна.",
        "description_en": "List reaction roles",
        "category": "Модераци",
        "usage": "A!rrlist",
        "examples": []
    },
    "role give": {
        "description_mn": "Хэрэглэгчид байнгын үүрэг өгнө.",
        "description_en": "Give a permanent role",
        "category": "Модераци",
        "usage": "A!role give <user> <role>",
        "examples": []
    },
    "role remove": {
        "description_mn": "Хэрэглэгчээс байнгын үүрэг хасна.",
        "description_en": "Remove a permanent role",
        "category": "Модераци",
        "usage": "A!role remove <user> <role>",
        "examples": []
    },
    "role info": {
        "description_mn": "Үүргийн дэлгэрэнгүй мэдээлэл.",
        "description_en": "Role details",
        "category": "Модераци",
        "usage": "A!role info <role>",
        "examples": []
    },
    "role members": {
        "description_mn": "Тухайн үүрэгтэй гишүүдийн жагсаалт.",
        "description_en": "Members with a role",
        "category": "Модераци",
        "usage": "A!role members <role>",
        "examples": []
    },
    "temprole give": {
        "description_mn": "Хугацаатай түр үүрэг өгнө.",
        "description_en": "Give a temporary role",
        "category": "Модераци",
        "usage": "A!temprole give <user> <role> <duration>",
        "examples": []
    },
    "temprole remove": {
        "description_mn": "Түр үүргийг хугацаанаас өмнө хасна.",
        "description_en": "Remove a temp role",
        "category": "Модераци",
        "usage": "A!temprole remove <user> <role>",
        "examples": []
    },
    "temprole list": {
        "description_mn": "Идэвхтэй түр үүргүүдийн жагсаалт.",
        "description_en": "List active temp roles",
        "category": "Модераци",
        "usage": "A!temprole list <user>",
        "examples": []
    },
    "temprole clear": {
        "description_mn": "Хэрэглэгчийн бүх түр үүргийг цуцална.",
        "description_en": "Clear temp roles",
        "category": "Модераци",
        "usage": "A!temprole clear <user>",
        "examples": []
    },
    "rank": {
        "description_mn": "Хэрэглэгчийн түвшин, XP болон эрэмбэ.",
        "description_en": "Rank, XP and position",
        "category": "Түвшин",
        "usage": "A!rank <user>",
        "examples": []
    },
    "serveractivity": {
        "description_mn": "Серверийн идэвхтэй байдлын статистик.",
        "description_en": "Server activity ranking",
        "category": "Түвшин",
        "usage": "A!serveractivity",
        "examples": []
    },
    "leaderboard": {
        "description_mn": "Серверийн эрэмбийн самбар.",
        "description_en": "Server leaderboard",
        "category": "Түвшин",
        "usage": "A!leaderboard",
        "examples": []
    },
    "addxp": {
        "description_mn": "Хэрэглэгчид XP нэмэх (эзэмшигч/co-owner).",
        "description_en": "Add XP to a user",
        "category": "Түвшин",
        "usage": "A!addxp <user> <amount>",
        "examples": []
    },
    "removexp": {
        "description_mn": "Хэрэглэгчээс XP хасах (эзэмшигч/co-owner).",
        "description_en": "Remove XP from a user",
        "category": "Түвшин",
        "usage": "A!removexp <user> <amount>",
        "examples": []
    },
    "leveling_setup": {
        "description_mn": "Түвшний системийн бүрэн тохиргоо (роль, XP, цаг).",
        "description_en": "Leveling setup",
        "category": "Түвшин",
        "usage": "A!leveling_setup",
        "examples": []
    },
    "marriage marry": {
        "description_mn": "Гэрлэх санал тавих (хуримын карттай).",
        "description_en": "Propose marriage",
        "category": "Гэр бүл",
        "usage": "/marriage marry <user>",
        "examples": []
    },
    "marriage divorce": {
        "description_mn": "Гэрлэлтийг цуцлах.",
        "description_en": "Divorce your partner",
        "category": "Гэр бүл",
        "usage": "/marriage divorce <user?>",
        "examples": []
    },
    "marriage adopt": {
        "description_mn": "Хүүхэд үрчлэх санал тавих.",
        "description_en": "Adopt a child",
        "category": "Гэр бүл",
        "usage": "/marriage adopt <child>",
        "examples": []
    },
    "marriage makeparent": {
        "description_mn": "Эцэг эх болох санал тавих.",
        "description_en": "Offer to become a parent",
        "category": "Гэр бүл",
        "usage": "/marriage makeparent <parent>",
        "examples": []
    },
    "marriage runaway": {
        "description_mn": "Эцэг эхээсээ зугтах.",
        "description_en": "Run away from parents",
        "category": "Гэр бүл",
        "usage": "/marriage runaway",
        "examples": []
    },
    "marriage partners": {
        "description_mn": "Хамтрагч(ид)-аа харах.",
        "description_en": "View your partners",
        "category": "Гэр бүл",
        "usage": "/marriage partners",
        "examples": []
    },
    "marriage parent": {
        "description_mn": "Эцэг эхээ харах.",
        "description_en": "View your parents",
        "category": "Гэр бүл",
        "usage": "/marriage parent",
        "examples": []
    },
    "marriage children": {
        "description_mn": "Хүүхдүүдээ харах.",
        "description_en": "View your children",
        "category": "Гэр бүл",
        "usage": "/marriage children",
        "examples": []
    },
    "marriage tree": {
        "description_mn": "Гэр бүлийн мод (зураг).",
        "description_en": "Family tree image",
        "category": "Гэр бүл",
        "usage": "/marriage tree <member>",
        "examples": []
    },
    "marriage fulltree": {
        "description_mn": "Бүрэн гэр бүлийн мод (хамтрагчийн гэр бүл орно).",
        "description_en": "Full family tree",
        "category": "Гэр бүл",
        "usage": "/marriage fulltree <member>",
        "examples": []
    },
    "marriage relationship": {
        "description_mn": "Хоёр хэрэглэгчийн хоорондын харилцаа.",
        "description_en": "Relationship between two users",
        "category": "Гэр бүл",
        "usage": "/marriage relationship <user1> <user2>",
        "examples": []
    },
    "marriage familysize": {
        "description_mn": "Гэр бүлийн гишүүдийн тоо.",
        "description_en": "Family size",
        "category": "Гэр бүл",
        "usage": "/marriage familysize",
        "examples": []
    },
    "marriage disown": {
        "description_mn": "Үрчлэсэн хүүхдээсээ татгалзах.",
        "description_en": "Disown a child",
        "category": "Гэр бүл",
        "usage": "/marriage disown <child>",
        "examples": []
    },
    "marriage love": {
        "description_mn": "Хэрэглэгчид өдөр тутмын love оноо өгөх.",
        "description_en": "Give daily love points",
        "category": "Гэр бүл",
        "usage": "/marriage love <target>",
        "examples": []
    },
    "marriage gift": {
        "description_mn": "Хамтрагчдаа бэлэг өгөх.",
        "description_en": "Gift your partner",
        "category": "Гэр бүл",
        "usage": "/marriage gift <gift_type>",
        "examples": []
    },
    "marriage profile": {
        "description_mn": "Гэрлэлтийн зурагт карт үүсгэх.",
        "description_en": "Create a marriage profile card",
        "category": "Гэр бүл",
        "usage": "/marriage profile <member?>",
        "examples": []
    },
    "marriage autoaccept": {
        "description_mn": "Гэрлэх саналыг автоматаар хүлээн авах эсэх.",
        "description_en": "Toggle automatic proposal acceptance",
        "category": "Гэр бүл",
        "usage": "/marriage autoaccept <enabled>",
        "examples": []
    },
    "marriage setup": {
        "description_mn": "Гэр бүлийн системийн админ тохиргооны самбар.",
        "description_en": "Configure the marriage system",
        "category": "Гэр бүл",
        "usage": "/marriage setup",
        "examples": []
    },
    "status": {
        "description_mn": "Ботын төлөв болон эрүүл мэндийг шалгах.",
        "description_en": "Bot status and health",
        "category": "Админ",
        "usage": "/status",
        "examples": []
    },
    "info": {
        "description_mn": "Бот/серверийн ерөнхий мэдээлэл.",
        "description_en": "Bot and server info",
        "category": "Админ",
        "usage": "/info",
        "examples": []
    },
    "rolelist": {
        "description_mn": "Хэрэглэгчийн ролийн жагсаалт.",
        "description_en": "List user roles",
        "category": "Админ",
        "usage": "/rolelist <member>",
        "examples": []
    },
    "addmoney": {
        "description_mn": "Хэрэглэгчид мөнгө нэмэх.",
        "description_en": "Add money to a user",
        "category": "Админ",
        "usage": "/addmoney <member> <amount>",
        "examples": []
    },
    "removemoney": {
        "description_mn": "Хэрэглэгчээс мөнгө хасах.",
        "description_en": "Remove money from a user",
        "category": "Админ",
        "usage": "/removemoney <member> <amount>",
        "examples": []
    },
    "stock set": {
        "description_mn": "Барааны нөөцийг тогтоох (админ).",
        "description_en": "Set item stock",
        "category": "Админ",
        "usage": "A!stock set <item_id> <amount>",
        "examples": []
    },
    "stock add": {
        "description_mn": "Барааны нөөц нэмэх (админ).",
        "description_en": "Add item stock",
        "category": "Админ",
        "usage": "A!stock add <item_id> <amount>",
        "examples": []
    },
    "stock remove": {
        "description_mn": "Барааны нөөц хасах (админ).",
        "description_en": "Remove item stock",
        "category": "Админ",
        "usage": "A!stock remove <item_id> <amount>",
        "examples": []
    },
    "stock reset": {
        "description_mn": "Бүх нөөцийг даруй санамсаргүй болгох (админ).",
        "description_en": "Reset all stock",
        "category": "Админ",
        "usage": "A!stock reset",
        "examples": []
    },
    "stock refresh": {
        "description_mn": "Бүх серверийн нөөцийг дахин дүүргэх.",
        "description_en": "Refresh shop stock",
        "category": "Админ",
        "usage": "A!stock refresh",
        "examples": []
    },
    "help": {
        "description_mn": "Тусламж — ангилал эсвэл тушаалын дэлгэрэнгүй.",
        "description_en": "Help command",
        "category": "Хэрэгсэл",
        "usage": "A!help <command>",
        "examples": []
    },
    "ping": {
        "description_mn": "Ботын ping/удаашралыг харуулна.",
        "description_en": "Bot latency",
        "category": "Хэрэгсэл",
        "usage": "A!ping",
        "examples": []
    },
    "announce": {
        "description_mn": "Зарлал үүсгэх самбар нээх.",
        "description_en": "Create an announcement",
        "category": "Хэрэгсэл",
        "usage": "/announce",
        "examples": []
    },
    "lang": {
        "description_mn": "Ботын хэл солих (mn/en).",
        "description_en": "Change server language",
        "category": "Хэрэгсэл",
        "usage": "A!lang <new_lang>",
        "examples": []
    },
    "menu": {
        "description_mn": "Интерактив цэс нээх.",
        "description_en": "Open interactive menu",
        "category": "Хэрэгсэл",
        "usage": "A!menu",
        "examples": []
    },
    "stick": {
        "description_mn": "Sticky мессеж тохируулах.",
        "description_en": "Set a sticky message",
        "category": "Хэрэгсэл",
        "usage": "A!stick <content>",
        "examples": []
    },
    "unstick": {
        "description_mn": "Sticky мессежийг цуцлах.",
        "description_en": "Remove a sticky message",
        "category": "Хэрэгсэл",
        "usage": "A!unstick",
        "examples": []
    },
    "voicesetup": {
        "description_mn": "Түр дуут сувгийн тохиргооны самбар нээх.",
        "description_en": "Temp voice setup",
        "category": "Хэрэгсэл",
        "usage": "/voicesetup",
        "examples": []
    },
    "voicesettings": {
        "description_mn": "Одоогийн түр сувгийн тохиргоог харах.",
        "description_en": "Temp voice settings",
        "category": "Хэрэгсэл",
        "usage": "/voicesettings",
        "examples": []
    },
    "greeting_set": {
        "description_mn": "Welcome/Goodbye/Boost сувгийг тохируулах.",
        "description_en": "Set a greeting channel",
        "category": "Хэрэгсэл",
        "usage": "/greeting_set <event> <channel> <template_id> <dm>",
        "examples": []
    },
    "greeting_toggle": {
        "description_mn": "Мэдэгдлийг идэвхжүүлэх/унтраах.",
        "description_en": "Toggle greetings",
        "category": "Хэрэгсэл",
        "usage": "/greeting_toggle <event>",
        "examples": []
    },
    "greeting_status": {
        "description_mn": "Одоогийн тохиргоог харах.",
        "description_en": "Greeting status",
        "category": "Хэрэгсэл",
        "usage": "/greeting_status",
        "examples": []
    },
    "greeting_reset": {
        "description_mn": "Бүх мэндчилгээний тохиргоог устгах (болгоомжтой!).",
        "description_en": "Reset all greetings",
        "category": "Хэрэгсэл",
        "usage": "/greeting_reset",
        "examples": []
    },
    "template_create": {
        "description_mn": "Шинэ embed загвар үүсгэх.",
        "description_en": "Create a template",
        "category": "Хэрэгсэл",
        "usage": "/template_create",
        "examples": []
    },
    "template_edit": {
        "description_mn": "Загварыг засварлах.",
        "description_en": "Edit a template",
        "category": "Хэрэгсэл",
        "usage": "/template_edit <template_id>",
        "examples": []
    },
    "template_delete": {
        "description_mn": "Загвар устгах.",
        "description_en": "Delete a template",
        "category": "Хэрэгсэл",
        "usage": "/template_delete <template_id>",
        "examples": []
    },
    "template_list": {
        "description_mn": "Бүх загваруудыг харах.",
        "description_en": "List templates",
        "category": "Хэрэгсэл",
        "usage": "/template_list",
        "examples": []
    },
    "template_preview": {
        "description_mn": "Загварыг урьдчилан харах.",
        "description_en": "Preview a template",
        "category": "Хэрэгсэл",
        "usage": "/template_preview <template_id> <member>",
        "examples": []
    },
    "placeholders": {
        "description_mn": "Мэндчилгээний бүх хувьсагчдыг харах.",
        "description_en": "Greeting placeholders",
        "category": "Хэрэгсэл",
        "usage": "/placeholders",
        "examples": []
    },
    "set_log_channel": {
        "description_mn": "Алдааны лог сувгийг тохируулах.",
        "description_en": "Set log channel",
        "category": "Хэрэгсэл",
        "usage": "/set_log_channel <channel>",
        "examples": []
    },
    "marketplace panel": {
        "description_mn": "Зах зээлийн самбар нээх (слаш).",
        "description_en": "Marketplace panel",
        "category": "Дэлгүүр",
        "usage": "/marketplace panel",
        "examples": []
    },
    "cafe": {
        "description_mn": "Кафе цэс харж, хоол захиалах.",
        "description_en": "Order food at the cafe",
        "category": "Хоол",
        "usage": "A!cafe",
        "examples": []
    },
    "dine": {
        "description_mn": "Инвентариас хоол идэж buff авах.",
        "description_en": "Eat food for buffs",
        "category": "Хоол",
        "usage": "A!dine <number>",
        "examples": []
    },
    "shop": {
        "description_mn": "Дэлгүүр нээж зүйл худалдаж авах.",
        "description_en": "Open the shop",
        "category": "Дэлгүүр",
        "usage": "A!shop",
        "examples": []
    },
    "buy": {
        "description_mn": "Дэлгүүрээс зүйл худалдаж авна.",
        "description_en": "Buy an item",
        "category": "Дэлгүүр",
        "usage": "A!buy <item_input> <quantity>",
        "examples": []
    },
    "vape": {
        "description_mn": "Вейп ашиглан согтуурлыг арилгах.",
        "description_en": "Use a vape",
        "category": "Дэлгүүр",
        "usage": "A!vape",
        "examples": []
    },
    "iteminfo": {
        "description_mn": "Зүйлний дэлгэрэнгүй мэдээлэл (ID-тай).",
        "description_en": "Item details",
        "category": "Дэлгүүр",
        "usage": "A!iteminfo <item_id>",
        "examples": []
    },
    "drink": {
        "description_mn": "Уух зүйл ашиглаж согтуурна.",
        "description_en": "Drink an item",
        "category": "Дэлгүүр",
        "usage": "A!drink <item_id>",
        "examples": []
    },
    "use": {
        "description_mn": "Зүйлээ ашиглана.",
        "description_en": "Use an item",
        "category": "Дэлгүүр",
        "usage": "A!use <item_input>",
        "examples": []
    },
    "equip": {
        "description_mn": "Зүйлээ зүүж авна.",
        "description_en": "Equip an item",
        "category": "Дэлгүүр",
        "usage": "A!equip <item_input>",
        "examples": []
    },
    "unequip": {
        "description_mn": "Зүүсэн зүйлээ тайлж хасна.",
        "description_en": "Unequip an item",
        "category": "Дэлгүүр",
        "usage": "A!unequip <slot_input>",
        "examples": []
    },
    "equipped": {
        "description_mn": "Хэрэглэгчийн зүүсэн зүйлс.",
        "description_en": "View equipped items",
        "category": "Дэлгүүр",
        "usage": "A!equipped <member>",
        "examples": []
    },
    "accessories": {
        "description_mn": "Гоёл чимэглэлийн зүйлс харах.",
        "description_en": "View accessories",
        "category": "Дэлгүүр",
        "usage": "A!accessories",
        "examples": []
    },
    "sogtol": {
        "description_mn": "Согтуу/мансууралын төлөв харах.",
        "description_en": "Drunk status",
        "category": "Дэлгүүр",
        "usage": "A!sogtol",
        "examples": []
    },
    "trade": {
        "description_mn": "Найздаа зүйл бэлэглэх — бараа, тоог цэснээс сонгоно.",
        "description_en": "Trade/give items to a user",
        "category": "Дэлгүүр",
        "usage": "A!trade <найз>",
        "examples": [
            "A!trade @friend   → бараа, тоогоо товч/жагсаалтаар сонгоно"
        ]
    },
    "market": {
        "description_mn": "Зах зээлийн интерактив самбар нээх.",
        "description_en": "Open the marketplace",
        "category": "Дэлгүүр",
        "usage": "A!market",
        "examples": []
    },
    "mp": {
        "description_mn": "Зах зээлийн тусламж.",
        "description_en": "Marketplace help",
        "category": "Дэлгүүр",
        "usage": "A!mp",
        "examples": []
    },
    "profile": {
        "description_mn": "Профайл картаа харах.",
        "description_en": "View your profile card",
        "category": "Дэлгүүр",
        "usage": "A!profile <member>",
        "examples": []
    },
    "inventory": {
        "description_mn": "Инвентар картаа харах.",
        "description_en": "View inventory card",
        "category": "Дэлгүүр",
        "usage": "A!inventory <member>",
        "examples": []
    },
    "confess": {
        "description_mn": "Нууц захиа илгээх (модал).",
        "description_en": "Send a confession",
        "category": "Нууц",
        "usage": "/confess",
        "examples": []
    },
    "confess_setup": {
        "description_mn": "Нууц захианы тохиргооны самбар нээх.",
        "description_en": "Confession setup",
        "category": "Нууц",
        "usage": "/confess_setup",
        "examples": []
    },
    "confess_blacklist": {
        "description_mn": "Хориотой үгийн жагсаалт удирдах.",
        "description_en": "Confession blacklist",
        "category": "Нууц",
        "usage": "/confess_blacklist <action> <word>",
        "examples": []
    },
    "confess_delete": {
        "description_mn": "Нууц захиаг ID-гаар устгах (админ).",
        "description_en": "Delete a confession",
        "category": "Нууц",
        "usage": "/confess_delete <confession_id>",
        "examples": []
    },
    "confess_stats": {
        "description_mn": "Нууц захианы системийн статистик.",
        "description_en": "Confession stats",
        "category": "Нууц",
        "usage": "/confess_stats",
        "examples": []
    },
    "quest": {
        "description_mn": "Даалгаврын систем — тусламж/төлөв харах.",
        "description_en": "Quest system help",
        "category": "Даалгавар",
        "usage": "A!quest",
        "examples": []
    },
    "quest new": {
        "description_mn": "Шинэ даалгавар авах (хамгийн ихдээ 5).",
        "description_en": "Get a new quest",
        "category": "Даалгавар",
        "usage": "A!quest new",
        "examples": []
    },
    "quest status": {
        "description_mn": "Одоогийн идэвхтэй даалгаварууд.",
        "description_en": "Current quests",
        "category": "Даалгавар",
        "usage": "A!quest status",
        "examples": []
    },
    "quest claim": {
        "description_mn": "Даалгавраа биелүүлж, шагнал авах.",
        "description_en": "Claim quest reward",
        "category": "Даалгавар",
        "usage": "A!quest claim <quest_id>",
        "examples": []
    },
    "quest refresh": {
        "description_mn": "Даалгаврыг сольж, шинэчлэх.",
        "description_en": "Refresh a quest",
        "category": "Даалгавар",
        "usage": "A!quest refresh <quest_id>",
        "examples": []
    },
    "quest history": {
        "description_mn": "Сүүлд биелүүлсэн даалгаврын түүх.",
        "description_en": "Completed quest history",
        "category": "Даалгавар",
        "usage": "A!quest history",
        "examples": []
    },
    "invites setup": {
        "description_mn": "Урилгын систем тохируулах.",
        "description_en": "Invite tracking setup",
        "category": "Урилга",
        "usage": "/invites setup",
        "examples": []
    },
    "invites stats": {
        "description_mn": "Урилгын статистик.",
        "description_en": "Invite statistics",
        "category": "Урилга",
        "usage": "/invites stats <member>",
        "examples": []
    },
    "invites codes": {
        "description_mn": "Идэвхтэй урилгын кодууд.",
        "description_en": "Active invite codes",
        "category": "Урилга",
        "usage": "/invites codes <member>",
        "examples": []
    },
    "invites list": {
        "description_mn": "Урьсан хэрэглэгчдийн жагсаалт.",
        "description_en": "List invited users",
        "category": "Урилга",
        "usage": "/invites list <user>",
        "examples": []
    },
    "invites inviter": {
        "description_mn": "Хэрэглэгчийг хэн урьсныг харах.",
        "description_en": "Who invited a user",
        "category": "Урилга",
        "usage": "/invites inviter <member>",
        "examples": []
    },
    "invites addlabel": {
        "description_mn": "Урилгын шошго нэмэх.",
        "description_en": "Add an invite label",
        "category": "Урилга",
        "usage": "/invites addlabel <invite_code> <label> <role>",
        "examples": []
    },
    "invites removelabel": {
        "description_mn": "Урилгын шошго устгах.",
        "description_en": "Remove an invite label",
        "category": "Урилга",
        "usage": "/invites removelabel <invite_code>",
        "examples": []
    },
    "invites graph": {
        "description_mn": "Урилгын статистик график.",
        "description_en": "Invite statistics graph",
        "category": "Урилга",
        "usage": "/invites graph <days>",
        "examples": []
    },
    "giveaway setup": {
        "description_mn": "Giveaway тохиргооны самбар нээх.",
        "description_en": "Giveaway setup",
        "category": "Giveaway",
        "usage": "/giveaway setup",
        "examples": []
    },
    "giveaway end": {
        "description_mn": "Giveaway дуусгах.",
        "description_en": "End a giveaway",
        "category": "Giveaway",
        "usage": "/giveaway end <message_id>",
        "examples": []
    },
    "giveaway reroll": {
        "description_mn": "Giveaway-гийн ялагчийг дахин сонгох.",
        "description_en": "Reroll giveaway winner",
        "category": "Giveaway",
        "usage": "/giveaway reroll <message_id>",
        "examples": []
    },
    "giveaway cancel": {
        "description_mn": "Giveaway цуцлах.",
        "description_en": "Cancel a giveaway",
        "category": "Giveaway",
        "usage": "/giveaway cancel <message_id>",
        "examples": []
    },
    "giveaway entries": {
        "description_mn": "Giveaway-гийн оролцогчдын тоо.",
        "description_en": "Giveaway entries",
        "category": "Giveaway",
        "usage": "/giveaway entries <message_id>",
        "examples": []
    },
    "giveaway list": {
        "description_mn": "Идэвхтэй giveaway-үүдийн жагсаалт.",
        "description_en": "List active giveaways",
        "category": "Giveaway",
        "usage": "/giveaway list",
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
    "Урилга": "🧲",
    "Giveaway": "🎁",
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
    "Урилга": "💌",
    "Giveaway": "🎁",
}

CATEGORY_COLORS = {
    "Эдийн засаг": "16429959",
    "Тоглоом": "16376495",
    "Казино": "13346551",
    "Хөгжилтэй": "16738740",
    "Модераци": "15961000",
    "Түвшин": "10937249",
    "Гэр бүл": "16716016",
    "Админ": "9024762",
    "Хэрэгсэл": "7106694",
    "Хоол": "16753920",
    "Дэлгүүр": "65484",
    "Нууц": "10181046",
    "Даалгавар": "16429959",
    "Урилга": "7653356",
    "Giveaway": "16376495",
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
