TABLES = [
    # Economy
    '''CREATE TABLE IF NOT EXISTS economy (
        user_id VARCHAR(255), guild_id VARCHAR(255),
        balance BIGINT DEFAULT 1000,
        bank_balance BIGINT DEFAULT 0,
        last_daily BIGINT, last_work BIGINT,
        bank_protect_until BIGINT DEFAULT 0,
        prison_until BIGINT DEFAULT 0,
        hunger INT DEFAULT 0, mood INT DEFAULT 0,
        PRIMARY KEY (user_id, guild_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    # Levels
    '''CREATE TABLE IF NOT EXISTS levels (
        user_id VARCHAR(255), guild_id VARCHAR(255),
        xp BIGINT DEFAULT 0, level INT DEFAULT 1,
        message_count INT DEFAULT 0,
        voice_seconds BIGINT DEFAULT 0,
        reaction_count INT DEFAULT 0,
        PRIMARY KEY (user_id, guild_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    # Leveling Config
    '''CREATE TABLE IF NOT EXISTS leveling_config (
        guild_id VARCHAR(255) PRIMARY KEY, enabled TINYINT DEFAULT 1,
        announce_channel BIGINT, voice_xp_enabled TINYINT DEFAULT 1,
        prog_type VARCHAR(20) DEFAULT 'arithmetic', prog_base INT DEFAULT 100,
        prog_step FLOAT DEFAULT 150, xp_tiers TEXT, xp_media INT DEFAULT 15,
        xp_reaction INT DEFAULT 1, xp_voice_silent INT DEFAULT 5,
        xp_voice_talking INT DEFAULT 15, msg_cooldown INT DEFAULT 60,
        react_cooldown INT DEFAULT 10, background_url TEXT, font_name TEXT,
        xp_drop_enabled TINYINT DEFAULT 0, xp_drop_channel BIGINT,
        xp_drop_min INT DEFAULT 100, xp_drop_max INT DEFAULT 500,
        xp_drop_interval INT DEFAULT 3600, cafe_buff_enabled TINYINT DEFAULT 1,
        invite_xp INT DEFAULT 0, marriage_bonus FLOAT DEFAULT 0.1
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    # Level Roles & Rewards
    '''CREATE TABLE IF NOT EXISTS level_roles (
        guild_id VARCHAR(255), level INT, role_id BIGINT,
        PRIMARY KEY (guild_id, level)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',
    '''CREATE TABLE IF NOT EXISTS level_rewards (
        guild_id VARCHAR(255), level INT, money INT DEFAULT 0,
        PRIMARY KEY (guild_id, level)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    # Warnings
    '''CREATE TABLE IF NOT EXISTS warnings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(255), guild_id VARCHAR(255),
        moderator_id VARCHAR(255), reason TEXT,
        timestamp BIGINT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    # Marriages
    '''CREATE TABLE IF NOT EXISTS marriages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(255), partner_id VARCHAR(255),
        guild_id VARCHAR(255), marriage_date VARCHAR(50),
        ring_name VARCHAR(100), ring_emoji VARCHAR(100),
        love_points INT DEFAULT 0,
        UNIQUE KEY unique_marriage (user_id, partner_id, guild_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    # Temp Channels
    '''CREATE TABLE IF NOT EXISTS temp_channels (
        id INT AUTO_INCREMENT PRIMARY KEY,
        guild_id VARCHAR(255) NOT NULL,
        channel_id BIGINT NOT NULL UNIQUE,
        owner_id BIGINT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',
    
    # Guild Config
    '''CREATE TABLE IF NOT EXISTS guild_config (
        guild_id VARCHAR(255) PRIMARY KEY,
        create_channel_id BIGINT,
        max_channels_per_user INT DEFAULT 3,
        category_id BIGINT,
        control_channel_id BIGINT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',
    
    # Lottery
    '''CREATE TABLE IF NOT EXISTS lottery (
        id INT PRIMARY KEY, pool BIGINT DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',
    '''CREATE TABLE IF NOT EXISTS lottery_entries (
        user_id VARCHAR(255), guild_id VARCHAR(255),
        tickets INT DEFAULT 0,
        PRIMARY KEY (user_id, guild_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',
]

ALTER_QUERIES = [
    "ALTER TABLE economy ADD COLUMN IF NOT EXISTS hunger INT DEFAULT 0",
    "ALTER TABLE economy ADD COLUMN IF NOT EXISTS mood INT DEFAULT 0",
    "ALTER TABLE economy ADD COLUMN IF NOT EXISTS prison_until BIGINT DEFAULT 0",
    "ALTER TABLE levels ADD COLUMN IF NOT EXISTS message_count INT DEFAULT 0",
    "ALTER TABLE levels ADD COLUMN IF NOT EXISTS voice_seconds BIGINT DEFAULT 0",
    "ALTER TABLE levels ADD COLUMN IF NOT EXISTS reaction_count INT DEFAULT 0",
    "ALTER TABLE leveling_config ADD COLUMN IF NOT EXISTS cafe_buff_enabled TINYINT DEFAULT 1",
    "ALTER TABLE leveling_config ADD COLUMN IF NOT EXISTS invite_xp INT DEFAULT 0",
    "ALTER TABLE leveling_config ADD COLUMN IF NOT EXISTS marriage_bonus FLOAT DEFAULT 0.1",
    "ALTER TABLE leveling_config ADD COLUMN IF NOT EXISTS font_name TEXT",
]

INDEXES = [
    "ALTER TABLE economy ADD INDEX IF NOT EXISTS idx_economy_balance (balance)",
    "ALTER TABLE economy ADD INDEX IF NOT EXISTS idx_economy_guild (guild_id, balance)",
    "ALTER TABLE levels ADD INDEX IF NOT EXISTS idx_levels_guild (guild_id, level DESC, xp DESC)",
]
