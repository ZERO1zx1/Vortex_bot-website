# Vortex Bot Website

Discord bot services and web tooling backed by Supabase, with configurable economy settings and deployment support.

## Features

- Discord bot configuration through environment variables.
- Supabase-backed server integration.
- Configurable economy values, balance limits, bonuses, and transfer tax.
- Docker-based deployment support.
- Separate bot and documentation directories for project organization.

## Tech Stack

- Python
- Discord bot services
- Supabase
- Docker

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/ZERO1zx1/Vortex_bot-website.git
cd Vortex_bot-website
```

### 2. Configure environment variables

Copy the example file and fill in the required server-side values:

```bash
cp .env.example .env
```

Required values include:

- `DISCORD_TOKEN`
- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`

Optional configuration includes `OWNER_ID`, `CO_OWNERS`, `GUILD_ID`, `BONUS_PERCENT`, `MAX_BALANCE`, and `TRANSFER_TAX_PERCENT`.

Never commit real tokens, Supabase secrets, or service-role keys.

### 3. Run the project

Use the repository's existing Python entry point or deployment configuration under `aether_bot/`. The repository includes a `Dockerfile` for containerized deployment.

## Project Structure

```
.
├── aether_bot/       # Bot application code
├── docs/              # Project documentation
├── .env.example       # Environment variable template
├── Dockerfile         # Container configuration
└── README.md
```

## License

No license file is currently visible in the repository. Add a license before distributing the project publicly.

## Contributing

Keep secrets out of commits, document configuration changes, and use focused Conventional Commit messages for documentation updates.
