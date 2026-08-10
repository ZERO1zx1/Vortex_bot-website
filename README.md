# 🛡️ Gurten Discord Bot (Modernized)

A feature-rich Discord bot modernized with Python and Supabase for high-performance data persistence and scalability.

## ✨ Features
- **Economy System**: Comprehensive economy with jobs, crimes, banking, and global stats.
- **Leveling & XP**: Advanced leveling system with customizable rank cards and XP drops.
- **Moderation**: Robust moderation tools with staff activity tracking and warning systems.
- **Social & Fun**: Marriage, adoptions, casino games (Blackjack), counting, and confessions.
- **Customizable**: Guild-specific configurations for almost every module.

## 🚀 Modernization Highlights
- **Supabase Integration**: Replaced legacy MySQL/SQLite with Supabase (PostgreSQL) for better reliability and ease of management.
- **Refactored Architecture**: Introduced `SupabaseCog` base class and `SupabaseManager` for clean database interactions.
- **Feature Restoration**: Restored high-quality legacy features like `casino`, `register`, and `greetings`.
- **Interaction Safety**: Improved UI components with better acknowledgement checks and error handling.

## 🛠️ Installation

### 1. Prerequisites
- Python 3.10+
- Supabase Project (URL and Service Role Key)
- Discord Bot Token

### 2. Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/ZERO1zx1/gurtendev.git
   cd gurtendev
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables:
   - Copy `.env.example` to `.env`.
   - Fill in your `DISCORD_TOKEN`, `SUPABASE_URL`, and `SUPABASE_KEY`.

### 3. Database Setup
- Apply the schema provided in `database/supabase_schema.sql` to your Supabase project via the SQL Editor in the Supabase Dashboard.

### 4. Run the Bot
```bash
python main.py
```

## 📜 Documentation
- Detailed documentation for each module can be found in the `docs/` directory (coming soon).
- Use `ghelp` in Discord to see all available commands.

## 🤝 Contributing
Contributions are welcome! Please open an issue or submit a pull request for any improvements.

## 📄 License
This project is licensed under the MIT License.
