# Aether font assets

The bot's generated images use `src/utils/fonts.py`, which discovers bundled
TrueType/OpenType files first and then falls back to installed Noto/DejaVu
fonts. This keeps Mongolian, Cyrillic, Latin, CJK, and emoji text readable in
Docker and local development.

The `package.json` and `package-lock.json` files describe the web font sources
used by the website layer:

- Inter — UI/body text
- Roboto — compact labels and numeric metadata

`node_modules/` is intentionally ignored and must not be committed. Discord
embed text does not load local fonts; these assets apply to generated image
cards and the website only.
