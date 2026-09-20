# Aether website

Aether bot-ын Монгол хэл дээрх anime/cyberpunk танилцуулга болон command catalog.

## Бүтэц

- `index.html` — нүүр, 11 үндсэн систем, статус, community, changelog, FAQ
- `js/commands.js` — active bot cogs-оос автоматаар үүссэн command catalog
- `js/app.js` — хайлт, filter, modal, theme, animation, live status
- `tools/sync_website_commands.py` — `ACTIVE_COGS` болон `COMMAND_INFO`-г тулгаж catalog sync хийнэ
- `validate_commands.js` — catalog-ийн бүтэц, duplicate, command type шалгана

## Catalog шинэчлэх

Bot-д command нэмсэн эсвэл active cog өөрчлөгдсөн үед:

```powershell
python website/tools/sync_website_commands.py
node website/validate_commands.js
```

Command-ийн нийт тоо, slash/text задаргаа нь `commands.js`-ээс web дээр автоматаар гардаг. Иймээс HTML дотор гараар тоо солих шаардлагагүй.

## Үндсэн системүүд

Economy, Games & Casino, Level/Ranking/Profile, Shop/Inventory, Giveaway, Ticket,
Moderation & Statistics, Webhook Automation, Marriage, Fun, Confessions.

Firebase Hosting нь `website/` хавтсыг publish хийдэг.
