-- AETHER i18n: серверийн хэлний тохиргоо (MN/EN)
-- ЭНЭ ФАЙЛЫГ Supabase SQL Editor дотор хуулж ажиллуул:
--   https://supabase.com/dashboard/project/onpxpvemmjesobxpilgd/sql
-- RLS-ийн бодлоготой нийцэж байгаа тул анон (бот) key-ээр ч бичиж уншина.

-- 1. guild_config хүснэгтэд lang багана нэмэх (байхгүй бол)
ALTER TABLE IF EXISTS guild_config
ADD COLUMN IF NOT EXISTS lang TEXT DEFAULT 'mn';

-- 2. Анхны утга: хуучин серверүүд Монголоор эхлэнэ
UPDATE guild_config SET lang = 'mn' WHERE lang IS NULL;

-- 3. Багана байхгүй хүснэгтийн хувьд (first-time setup)
-- guild_config үгүй бол хүснэгтийг үүсгэнэ
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id TEXT PRIMARY KEY,
    create_channel_id BIGINT,
    max_channels_per_user INT DEFAULT 3,
    category_id BIGINT,
    control_channel_id BIGINT,
    lang TEXT DEFAULT 'mn'
);
