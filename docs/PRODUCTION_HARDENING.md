# Production hardening ба хөгжүүлэлтийн төлөвлөгөө

Энэ баримт нь 2026-09-13-ны code hardening өөрчлөлтүүд болон үлдсэн
гададвэр шаардсан ажлыг ялгаж тэмдэглэнэ.

## Хэрэгжсэн

- Бот болон API `SUPABASE_SECRET_KEY`-г зөвхөн server-side ашиглана
  (`SUPABASE_SERVICE_ROLE_KEY`, хуучин `SUPABASE_KEY` нэрийг migration үед дэмжинэ).
- Browser bundle-ээс Supabase URL/key болон direct REST fallback арилсан.
- RLS migration бүх `allow_all` policy, anon/authenticated өргөн grants-ийг
  буцааж, зөвхөн `bot_status(id=1)` SELECT-ийг public үлдээсэн.
- `increment()` RPC-г public/anon/authenticated role-оос хаасан.
- Discord invite Administrator (`permissions=8`) шаардахаа больсон.
- Cog бүртгэлийг `cogs/*.py` automatic discovery болгож тест нэмсэн.
- Python compile, pytest, command catalog validation бүхий CI нэмсэн.
- Backend-д Redis shared cache, JSON request log, request ID, readiness,
  operational metrics нэмсэн.
- README-ийн command/table тоог бодит эх үүсвэртэй тааруулсан.
- Premium plan API contract нэмсэн; provider байхгүй үед checkout disabled.

## Deploy хийхээс өмнө заавал

1. Supabase Dashboard-аас service-role/secret key авч bot болон backend-ийн
   secret environment-д `SUPABASE_SECRET_KEY` нэрээр хадгална.
2. Hardening SQL-г maintenance window-д ажиллуулж bot/API smoke test хийнэ.
3. `website/js/config.js` дахь `API_BASE_URL`-д production backend URL бичнэ.
4. Олон API worker ашиглавал `REDIS_URL` тохируулна.
5. Discord Developer Portal дээр bot role-ийн permissions-ийг ашиглаж буй
   feature-үүдээр нь сонгож олгоно; Administrator бүү олго.
6. Supabase database advisor болон `supabase test db`-г live project дээр
   ажиллуулна.

## Гадаад шийдвэргүйгээр автоматаар дуусгах боломжгүй зүйл

- Premium checkout: Stripe/QPay/SocialPay зэрэг provider, merchant account,
  refund/cancel дүрэм, татварын баримт, webhook secret сонгох шаардлагатай.
- Alert destination: Sentry/Better Stack/Grafana/Discord webhook-ийн аль нэг,
  байгууллагын endpoint болон secret шаардлагатай.
- 1,000+ мөртэй Cog-уудыг задлах: behavior-preserving integration test-үүдийг
  эхлээд нэмээд feature тус бүрээр жижиг PR болгон хийх нь аюулгүй. Нэг дор
  механикаар хуваавал Discord UI state болон background task lifecycle эвдрэх
  эрсдэл өндөр.

## Дараагийн архитектурын дараалал

1. `help.py`-ийн command metadata-г generated JSON руу гаргах.
2. `shop.py`-г catalog, inventory service, UI view гэж салгах.
3. `marriage.py`-г relationship service, family-tree renderer, Discord UI болгох.
4. `moderation.py`-г actions, staff analytics, UI гэж салгах.
5. `economy.py`-г domain service, configuration UI, scheduled jobs болгох.
6. Module бүрт unit test болон fake repository contract нэмсний дараа хуучин
   implementation-ийг устгах.
