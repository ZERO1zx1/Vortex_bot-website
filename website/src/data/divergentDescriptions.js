/* ============================================================
   REVIEW REQUIRED — divergent command descriptions

   The retired js/app.js i18n dictionary carried a `cmd.<name>.desc` copy of
   every command description alongside the generated catalog. The two had
   drifted: for the commands listed below the old hand-maintained string
   contradicts the catalog's `desc` / `descEN`.

   The site renders the catalog text (generated from src/cogs/help.py, the real
   source of truth). The previous wording is preserved here verbatim so nothing
   is lost — review each row and delete this file once resolved.

   Run: python website/tools/sync_cmd_i18n.py --review
   ============================================================ */

/** Old hand-written EN text that disagrees with the generated catalog. */
export const DIVERGENT_EN = {
  addmoney: {
    old: 'Add coins to a user (admin)',
    catalog: 'Add money to a user'
  },
  adopt: {
    old: 'Adopt a child',
    catalog: 'Offer to adopt a child'
  },
  avatar: {
    old: 'View a user',
    catalog: 'Show a user avatar'
  },
  balance: {
    old: 'View your coin balance',
    catalog: 'Check your balance'
  },
  ban: {
    old: 'Ban a user from the server',
    catalog: 'Ban a member'
  },
  buy: {
    old: 'Buy stocks',
    catalog: 'Buy an item'
  },
  cafe: {
    old: 'View cafe menu and info',
    catalog: 'Order food at the cafe'
  },
  clear: {
    old: 'Bulk-delete messages',
    catalog: 'Delete messages'
  },
  confess: {
    old: 'Anonymous confession in the channel',
    catalog: 'Send a confession'
  },
  count_stats_server: {
    old: 'Server counting stats',
    catalog: 'Server counting stats'
  },
  daily: {
    old: 'Claim your daily coin reward',
    catalog: 'Claim your daily reward'
  },
  dice: {
    old: 'Roll dice against the bot',
    catalog: 'Dice gambling game'
  },
  dine: {
    old: 'Eat a meal at the cafe (spend coins)',
    catalog: 'Eat food for buffs'
  },
  disown: {
    old: 'Disown a child',
    catalog: 'Disown an adopted child'
  },
  divorce: {
    old: 'End your marriage',
    catalog: 'Divorce your partner'
  },
  familytree: {
    old: 'View your family tree',
    catalog: 'Show a family tree'
  },
  gamble: {
    old: 'Gambling with buttons (high/low)',
    catalog: 'Gambling game'
  },
  gift: {
    old: 'Send a gift to your spouse',
    catalog: 'Gift your partner'
  },
  help: {
    old: 'List all commands by category',
    catalog: 'Help command'
  },
  kick: {
    old: 'Kick a user from the server',
    catalog: 'Kick a member'
  },
  leaderboard: {
    old: 'Show the top users by rank',
    catalog: 'XP leaderboard'
  },
  lock: {
    old: 'Lock a channel (admin)',
    catalog: 'Lock a channel'
  },
  love: {
    old: 'Check your love level',
    catalog: 'Give daily love points'
  },
  market: {
    old: 'Browse the cafe shop items',
    catalog: 'Open the marketplace'
  },
  marriagepro: {
    old: 'Your marriage profile',
    catalog: 'Create a marriage profile card'
  },
  mp: {
    old: 'Marketplace shortcut',
    catalog: 'Marketplace help'
  },
  placeholders: {
    old: 'Placeholder info',
    catalog: 'Greeting placeholders'
  },
  propose: {
    old: 'Propose marriage to someone',
    catalog: 'Propose marriage to a user'
  },
  pvp: {
    old: 'Duel another player',
    catalog: 'PvP duel with a user'
  },
  rank: {
    old: 'View your rank and XP',
    catalog: 'Rank, XP and position'
  },
  removemoney: {
    old: 'Remove coins from a user (admin)',
    catalog: 'Remove money from a user'
  },
  rob: {
    old: 'Attempt to rob another user (risky!)',
    catalog: 'Rob another user'
  },
  rps: {
    old: 'Rock-paper-scissors vs the bot',
    catalog: 'Rock-paper-scissors game'
  },
  serveractivity: {
    old: 'View server activity stats',
    catalog: 'Server activity ranking'
  },
  spouse: {
    old: 'View your spouse info',
    catalog: 'Show your spouse'
  },
  template_create: {
    old: 'Create an embed template (admin)',
    catalog: 'Create a template'
  },
  template_delete: {
    old: 'Delete a template (admin)',
    catalog: 'Delete a template'
  },
  template_edit: {
    old: 'Edit a template (admin)',
    catalog: 'Edit a template'
  },
  template_list: {
    old: 'List saved templates',
    catalog: 'List templates'
  },
  template_preview: {
    old: 'Preview a template (admin)',
    catalog: 'Preview a template'
  },
  texas: {
    old: 'Multiplayer Texas Hold’em poker',
    catalog: "Multiplayer Texas Hold'em for 2–6 players"
  },
  timeout: {
    old: 'Timeout a user temporarily',
    catalog: 'Timeout a member'
  },
  trade: {
    old: 'Trade items with another user',
    catalog: 'Trade/give items to a user'
  },
  unban: {
    old: 'Unban a user',
    catalog: 'Unban a user'
  },
  unlock: {
    old: 'Unlock a channel (admin)',
    catalog: 'Unlock a channel'
  },
  warn: {
    old: 'Issue a warning (admin)',
    catalog: 'Warn a member'
  },
  warnings: {
    old: 'View a user',
    catalog: 'View user warnings'
  },
  work: {
    old: 'Work to earn coins',
    catalog: 'Work to earn money'
  },
  workphrase: {
    old: 'Customize your work phrases',
    catalog: 'Work phrase settings'
  }
}

/** Old hand-written MN text that disagrees with the generated catalog. */
export const DIVERGENT_MN = {
  addmoney: {
    old: 'Хэрэглэгчид мөнгө нэмэх (админ)',
    catalog: 'Хэрэглэгчид мөнгө нэмэх.'
  },
  adopt: {
    old: 'Хүүхэд үрчлэх',
    catalog: 'Хүүхэд үрчлэх санал тавина.'
  },
  avatar: {
    old: 'Хүний аватар харах',
    catalog: 'Хэрэглэгчийн аватарыг харуулна.'
  },
  balance: {
    old: 'Таны мөнгөн дүн',
    catalog: 'Үлдэгдэл мөнгө болон банкны дүнг харуулна.'
  },
  ban: {
    old: 'Серверээс банлах',
    catalog: 'Хэрэглэгчийг бан хийнэ.'
  },
  buy: {
    old: 'Хувьцаа худалдаж авах',
    catalog: 'Дэлгүүрээс зүйл худалдаж авна.'
  },
  cafe: {
    old: 'Кафегийн цэс ба мэдээлэл',
    catalog: 'Кафе цэс харж, хоол захиалах.'
  },
  clear: {
    old: 'Мессеж цэвэрлэх (purge)',
    catalog: 'Сувгийн мессежүүдийг устгана.'
  },
  confess: {
    old: 'Аноним илчлэл',
    catalog: 'Нууц захиа илгээх (модал).'
  },
  count_stats_server: {
    old: 'Тооллын статистик',
    catalog: 'Серверийн тооллогын статистик.'
  },
  daily: {
    old: 'Өдөр бүрийн мөнгөний урамшуулал',
    catalog: 'Өдрийн урамшууллаа авах (цатгалан/сэтгэл санаагаар).'
  },
  dice: {
    old: 'Шоо шидэх',
    catalog: 'Шоо шидэлтийн мөрийтэй тоглоом.'
  },
  dine: {
    old: 'Кафед хоол идэх',
    catalog: 'Инвентариас хоол идэж buff авах.'
  },
  disown: {
    old: 'Хүүхдээсээ татгалзах',
    catalog: 'Үрчилсэн хүүхдээсээ татгалзана.'
  },
  divorce: {
    old: 'Салалт',
    catalog: 'Гэрлэлтийг цуцална.'
  },
  familytree: {
    old: 'Гэр бүлийн мод',
    catalog: 'Гэр бүлийн мод харуулна.'
  },
  gamble: {
    old: 'Шуудайнд мөнгө тавих',
    catalog: 'Мөрийтэй тоглоом — бооцоо тавин үржүүлэх боломж.'
  },
  gift: {
    old: 'Ханиандаа бэлэг өгөх',
    catalog: 'Хамтрагчдаа бэлэг өгнө.'
  },
  help: {
    old: 'Бүх командыг ангиллаар нь',
    catalog: 'Тусламж — ангилал эсвэл тушаалын дэлгэрэнгүй.'
  },
  kick: {
    old: 'Хөөх',
    catalog: 'Хэрэглэгчийг серверээс хөөнө.'
  },
  leaderboard: {
    old: 'Түвшингийн тэргүүнүүд',
    catalog: 'XP-ээр эрэмбэлсэн leaderboard.'
  },
  lock: {
    old: 'Суваг түгжих',
    catalog: 'Сувгийг түгжинэ (гишүүд мессеж бичих боломжгүй).'
  },
  love: {
    old: 'Хайрын хэмжээ харах',
    catalog: 'Өдрийн love оноо өгнө.'
  },
  market: {
    old: 'Кафегийн дэлгүүр, хоол/уух зүйлс',
    catalog: 'Зах зээлийн интерактив самбар нээх.'
  },
  marriagepro: {
    old: 'Гэрлэлийн профиль',
    catalog: 'Гэрлэлтийн зурагт карт үүсгэнэ.'
  },
  mp: {
    old: 'Marketplace-ийн товчлол',
    catalog: 'Зах зээлийн тусламж.'
  },
  placeholders: {
    old: 'Placeholder мэдээлэл',
    catalog: 'Мэндчилгээний бүх хувьсагчдыг харах.'
  },
  propose: {
    old: 'Хайртай хүнээсээ гэрлэлтийн санал тавь',
    catalog: 'Хэрэглэгчид гэрлэх санал тавина.'
  },
  pvp: {
    old: 'Тоглогч хоорондын тулаан',
    catalog: 'Хэрэглэгчтэй тулаан хийх (бооцоотой).'
  },
  rank: {
    old: 'Таны түвшин ба XP',
    catalog: 'Хэрэглэгчийн түвшин, XP болон эрэмбэ.'
  },
  removemoney: {
    old: 'Хэрэглэгчээс мөнгө хасах (админ)',
    catalog: 'Хэрэглэгчээс мөнгө хасах.'
  },
  rob: {
    old: 'Нэгнээсээ хулгайлах (эрсдэлтэй!)',
    catalog: 'Өөр хэрэглэгчийг дээрэмдэж мөнгө авах (эрсдэлтэй).'
  },
  rps: {
    old: 'Чулуу-цаас-хайч',
    catalog: 'Чулуу-цаас-хайч мөрийтэй тоглоом.'
  },
  serveractivity: {
    old: 'Server-ийн идэвхтэй байдал',
    catalog: 'Серверийн идэвхтэй байдлын статистик.'
  },
  spouse: {
    old: 'Таны ханийн мэдээлэл',
    catalog: 'Хамтрагчаа харуулна.'
  },
  template_create: {
    old: 'Загвар үүсгэх',
    catalog: 'Шинэ embed загвар үүсгэх.'
  },
  template_delete: {
    old: 'Загвар устгах',
    catalog: 'Загвар устгах.'
  },
  template_edit: {
    old: 'Загвар засах',
    catalog: 'Загварыг засварлах.'
  },
  template_list: {
    old: 'Загварууд харах',
    catalog: 'Бүх загваруудыг харах.'
  },
  template_preview: {
    old: 'Загвар урьдчилж харах',
    catalog: 'Загварыг урьдчилан харах.'
  },
  texas: {
    old: 'Олон тоглогчтой Texas Hold’em poker',
    catalog: "Texas Hold'em — 2–6 хүнтэй multiplayer poker ширээ."
  },
  timeout: {
    old: 'Түр хугацаагаар хаах',
    catalog: 'Хэрэглэгчийг түр хаана (timeout).'
  },
  trade: {
    old: 'Бараа солилцоо',
    catalog: 'Найздаа зүйл бэлэглэх — бараа, тоог цэснээс сонгоно.'
  },
  unban: {
    old: 'Баныг авах',
    catalog: 'Хэрэглэгчийн баныг цуцлана.'
  },
  unlock: {
    old: 'Суваг тайлах',
    catalog: 'Сувгийн түгжээг тайлна.'
  },
  warn: {
    old: 'Сануулга өгөх',
    catalog: 'Хэрэглэгчид анхааруулга өгнө.'
  },
  warnings: {
    old: 'Таны сануулгууд',
    catalog: 'Хэрэглэгчийн анхааруулгыг харна.'
  },
  work: {
    old: 'Ажиллаж мөнгө ол',
    catalog: 'Ажиллаж мөнгө олох (нэмэлт текст зааж болно).'
  },
  workphrase: {
    old: 'Ажлын үгсийн жагсаалт тохируулах',
    catalog: 'Ажлын өгүүлбэрийн тохиргоо (embed+button+modal).'
  }
}

export const DIVERGENT_COUNT = 49
