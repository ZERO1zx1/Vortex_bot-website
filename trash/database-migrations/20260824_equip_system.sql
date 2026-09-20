-- AETHER: Зүүлт/гоёлын хэрэгсэл (equip) систем
-- ЭНЭ ФАЙЛЫГ Supabase SQL Editor дотор хуулж ажиллуулна уу.
--   https://supabase.com/dashboard/project/<project>/sql

-- Хэрэглэгчийн зүүсэн бараа (слот тутамд 1 бараа)
CREATE TABLE IF NOT EXISTS user_equips (
    guild_id TEXT NOT NULL,
    user_id  TEXT NOT NULL,
    slot     TEXT NOT NULL,      -- ring | necklace | bracelet | charm
    item_id  BIGINT NOT NULL,
    updated_at BIGINT DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, slot)
);

-- Ботын service key RLS-ийг тойрч гарна; нийтээр унших/бичих бодлого
ALTER TABLE user_equips ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "bot full access user_equips" ON user_equips;
CREATE POLICY "bot full access user_equips"
    ON user_equips
    FOR ALL
    USING (true)
    WITH CHECK (true);
