# Aether Universal Character & Content Framework

## Purpose

This document turns the original Aether concept into a reusable, platform-neutral framework. It can support Discord interactions, short-form video, GIF collections, polls, captions, and future character packs without hard-coding the system to one anime or game.

The default profile is **Aether from Genshin Impact**. The framework itself is intentionally character-agnostic: replacing the profile data creates a Tanjiro, Luffy, Naruto, Gojo, Anya, or any other character pack.

## Character research axes

Every character pack should cover these ten fields:

1. **Identity** — who the character is and where they come from.
2. **Goal** — the character's central objective.
3. **Personality** — defining traits and behavioral tone.
4. **Skills** — abilities, tools, and signature actions.
5. **Relationships** — family, allies, rivals, and mentors.
6. **Arc** — the character's development path.
7. **Theme** — the emotional ideas the character represents.
8. **Work ethic** — how the character approaches responsibility and effort.
9. **Quotes** — short, safe-to-use lines or original paraphrases.
10. **Fandom hooks** — GIFs, memes, polls, ships, and community prompts.

## Default profile: Aether

| Field | Profile |
|---|---|
| Identity | The male Traveler from Genshin Impact, travelling across Teyvat. |
| Goal | Find Lumine, uncover Teyvat's truth, and understand the world's seven nations. |
| Personality | Calm, thoughtful, compassionate, responsible, and action-oriented. |
| Skills | Sword combat, elemental switching, exploration, problem solving, and helping others. |
| Relationships | Lumine, Paimon, the Archons, and friends across Teyvat. |
| Arc | Mondstadt → Liyue → Inazuma → Sumeru → Fontaine → Natlan → Snezhnaya → Khaenri'ah. |
| Themes | Family, growth through travel, humanity, responsibility, and truth-seeking. |
| Work ethic | Keeps commitments, learns continuously, helps others, stays patient, and remains humble. |
| Tone | Hopeful, adventurous, warm, lightly playful, and never overly dramatic. |
| Community hooks | Element polls, region quizzes, motivation prompts, GIF reactions, and team compatibility. |

## Content voice

Use short, energetic lines with a warm Traveler tone:

- “Ad astra, Traveler! ✨”
- “Аялал үргэлжилж байна.”
- “Тэвчээр + хүндэтгэл + хариуцлага.”
- “Paimon approves 🌸”
- “Let’s go, Traveler!”

Avoid presenting fan-made lines as official quotes. For public content, prefer original paraphrases and clearly label fan content.

## Discord feature pack

| Command | Purpose |
|---|---|
| `/aether` | Send a random Aether-style motivation card or GIF. |
| `/element` | Show a random element theme and caption. |
| `/region` | Show a random Teyvat region vibe. |
| `/quote` | Send a short original Traveler-style line. |
| `/paimon` | Send a light Paimon-style reaction. |
| `/traveler` | Send a daily motivation prompt. |
| `/hug @user` | Send a friendly hug reaction. |
| `/poll` | Start a Genshin-themed community poll. |
| `/team @user1 @user2` | Generate a playful compatibility result. |
| `/daily` | Send a daily character or world fact. |

### Response design

- Use the shared Aether embed style and centralized color constants.
- Keep responses ephemeral when they contain private settings or moderation data.
- Use local assets first, then safe public URLs as fallback.
- Add a caption, not only an image, so the interaction remains useful if media fails.
- Keep GIFs categorized by `aether`, `element`, `region`, `reaction`, and `motivation`.

## GIF storyboard set

The 30-scene storyboard is a production guide, not a promise that every scene already exists as a local GIF. Each scene should have a caption, duration target, and visual effect. The bot can expose only the scenes that have a verified asset.

| Range | Theme | Examples |
|---|---|---|
| 1–5 | Arrival and readiness | waking up, Paimon, sword draw, Anemo, Geo |
| 6–10 | Element showcase | Electro, Dendro, Hydro, Pyro, Cryo |
| 11–17 | Region journey | Statue, Mondstadt, Liyue, Inazuma, Sumeru, Fontaine, Natlan |
| 18–20 | Emotion | Lumine memory, tears, smile |
| 21–24 | Everyday adventure | cooking, fishing, climbing, gliding |
| 25–30 | Resolve and finish | boss fight, victory, bow, comedy, stars, walking forward |

## 30-second short-form script

**0–3s:** Aether яагаад зүгээр нэг аялагч биш гэдгийг мэдэх үү?

**3–8s:** Тэр хариуцлагатай. Lumine-г хайх зорилгоо хэзээ ч орхидоггүй.

**8–13s:** Байнга суралцдаг — шинэ region, шинэ element, шинэ чадвар.

**13–20s:** Бусдад тусалдаг. Тэр хүчээрээ биш, үйлдлээрээ өөрийгөө харуулдаг.

**20–27s:** Тэвчээр, хүндэтгэл, хариуцлага — энэ бол түүний гол зэвсэг.

**27–30s:** Чи Aether-оос ямар чадвар сурах вэ? Комментод бичээрэй.

## Platform adaptation

- **Discord:** interactive commands, embeds, polls, GIF reactions.
- **TikTok/Reels:** 30-second script, hook in the first three seconds, one CTA.
- **YouTube Shorts:** the same script with a stronger title card and subtitle-safe layout.
- **Instagram:** carousel research card, quote card, and region poll story.

## Seven-day starter calendar

| Day | Content |
|---|---|
| Monday | Is Aether good at responsibility? |
| Tuesday | Seven elements, seven skills. |
| Wednesday | Region journey: Mondstadt → Natlan. |
| Thursday | Paimon reaction compilation. |
| Friday | Five original Traveler-style lines. |
| Saturday | Aether GIF compilation. |
| Sunday | Poll: Aether or Lumine? |

## Reusable character-pack contract

To create another character pack, replace only the data fields in `src/data/aether_vibe.json`:

- `identity`
- `goal`
- `personality`
- `skills`
- `relationships`
- `arc`
- `themes`
- `voice`
- `commands`
- `media_categories`

The command names and UI integration can remain unchanged.
