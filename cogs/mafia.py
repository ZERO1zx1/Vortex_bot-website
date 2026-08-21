from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
import discord
from discord.ext import commands
from discord import app_commands, ui
import asyncio
import random
import time
from typing import Dict, List, Optional
from datetime import datetime, timezone

# ══════════════ Өнгөний палитр ══════════════
EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
PURPLE_COLOR = 0xcba6f7
INFO_COLOR = 0x89b4fa
MAFIA_RED = 0xdd7878

# ══════════════ Хугацаа тохируулах модал ══════════════
class TimeModal(ui.Modal, title="Тоглоомын хугацаа тохируулах"):
    night = ui.TextInput(label="Шөнийн хугацаа (сек)", placeholder="120", required=True)
    day = ui.TextInput(label="Өдрийн хугацаа (сек)", placeholder="120", required=True)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            night = int(self.night.value)
            day = int(self.day.value)
            if night < 30 or day < 30:
                return await interaction.response.send_message("Хугацаа хамгийн багадаа 30 секунд байх ёстой.", ephemeral=True)
            self.view.cog.night_timeout = night
            self.view.cog.day_vote_timeout = day
            await interaction.response.send_message(f"✅ Шөнө: {night}с, Өдөр: {day}с болж тохируулагдлаа.", ephemeral=True)
            await self.view.refresh(interaction)
        except ValueError:
            await interaction.response.send_message("❌ Зөвхөн тоо оруулна уу.", ephemeral=True)

# ══════════════ Тохиргооны самбар ══════════════
class MafiaSetupView(ui.View):
    def __init__(self, cog, guild_id, author_id):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id
        self.message = None
        self.selected_channel: Optional[discord.TextChannel] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Энэ самбар таных биш.", ephemeral=True)
            return False
        return True

    async def refresh(self, interaction: discord.Interaction):
        embed = self.build_embed(interaction.guild)
        await interaction.edit_original_response(embed=embed, view=self)

    def build_embed(self, guild):
        embed = discord.Embed(title="🎭 **МАФИ ТОХИРГОО**", color=PURPLE_COLOR)
        embed.add_field(name="📢 Тоглоомын суваг", value=self.selected_channel.mention if self.selected_channel else "❌ Сонгогдоогүй", inline=False)
        embed.add_field(name="🌙 Шөнийн хугацаа", value=f"{self.cog.night_timeout}с", inline=True)
        embed.add_field(name="☀️ Өдрийн хугацаа", value=f"{self.cog.day_vote_timeout}с", inline=True)
        embed.set_footer(text="Дээрх сонголтуудыг ашиглан тохиргоог өөрчилнө үү.")
        return embed

    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📢 Тоглоомын суваг сонго...", min_values=1, max_values=1, row=0)
    async def select_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        self.selected_channel = select.values[0]
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="⏱ Хугацаа", style=discord.ButtonStyle.secondary, row=1)
    async def time_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TimeModal(self))

    @ui.button(label="🔄 Шинэчлэх", style=discord.ButtonStyle.gray, row=1)
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await self.refresh(interaction)

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            try: await self.message.edit(view=self)
            except: pass

# ══════════════ Лобби самбар ══════════════
class MafiaLobbyView(ui.View):
    def __init__(self, cog, game):
        super().__init__(timeout=None)
        self.cog = cog
        self.game = game
        self.message = None

    @ui.button(label="🎭 Нэгдэх", style=discord.ButtonStyle.success)
    async def join_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.game.phase != "waiting":
            return await interaction.response.send_message("❌ Тоглоом аль хэдийн эхэлсэн.", ephemeral=True)
        if any(p.member.id == interaction.user.id for p in self.game.players):
            return await interaction.response.send_message("❌ Та аль хэдийн нэгдсэн байна.", ephemeral=True)
        if len(self.game.players) >= 20:
            return await interaction.response.send_message("❌ Дээд хязгаар 20 тоглогч.", ephemeral=True)
        num = len(self.game.players) + 1
        self.game.players.append(MafiaPlayer(interaction.user, num))
        embed = self._build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @ui.button(label="🔄 Шинэчлэх", style=discord.ButtonStyle.gray)
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        embed = self._build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    def _build_embed(self):
        embed = discord.Embed(title="🎭 **МАФИ ТОГЛООМ**", color=PURPLE_COLOR)
        if self.game.players:
            desc = f"Нэгдсэн: **{len(self.game.players)}/20**\n\n" + "\n".join([f"**{p.number}.** {p.member.mention}" for p in self.game.players])
        else:
            desc = "Одоогоор тоглогч байхгүй."
        embed.description = desc
        embed.set_footer(text="Хамгийн багадаа 12 тоглогч шаардлагатай. 'Нэгдэх' товч дээр дарна уу.")
        return embed

# ══════════════ Тоглогч болон тоглоомын классууд ══════════════
class MafiaPlayer:
    def __init__(self, member: discord.Member, number: int):
        self.member = member
        self.number = number
        self.role: Optional[str] = None
        self.alive = True
        self.night_action: Optional[int] = None
        self.night_action_extra: Optional[int] = None
        self.copied_role = False
        self.vote_target: Optional[int] = None

class MafiaGame:
    def __init__(self, channel: discord.TextChannel, host: discord.Member):
        self.channel = channel
        self.host = host
        self.players: List[MafiaPlayer] = []
        self.phase = "waiting"
        self.day_count = 1
        self.night_task: Optional[asyncio.Task] = None
        self.vote_task: Optional[asyncio.Task] = None
        self.event_used = False
        self.interrogation_used = False
        self.joker_win = False
        self.double_kill_night = False
        self.blackout_night = False
        self.role_swap_pending = False
        self.mafia_channel: Optional[discord.TextChannel] = None
        self.detective_channel: Optional[discord.TextChannel] = None
        self.game_category: Optional[discord.CategoryChannel] = None

# ══════════════ Үндсэн ког ══════════════
class Mafia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games: Dict[int, MafiaGame] = {}
        self.night_timeout = 120
        self.day_vote_timeout = 120

    def get_game(self, channel_id: int) -> Optional[MafiaGame]:
        return self.games.get(channel_id)

    async def send_embed(self, channel, title, desc, color=EMBED_COLOR, fields=None, thumbnail=None):
        embed = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.now(timezone.utc))
        if thumbnail: embed.set_thumbnail(url=thumbnail)
        if fields:
            for name, val in fields: embed.add_field(name=name, value=val, inline=False)
        await channel.send(embed=embed)

    async def send_dm(self, member, title, desc, color=EMBED_COLOR, thumbnail=None):
        try:
            embed = discord.Embed(title=title, description=desc, color=color)
            if thumbnail: embed.set_thumbnail(url=thumbnail)
            await member.send(embed=embed)
        except: pass

    def role_name(self, role: str) -> str:
        return {
            "civilian": "👨‍🌾 Энгийн иргэн",
            "mafia": "🔪 Мафи",
            "detective": "👮 Цагдаа",
            "doctor": "💊 Эмч",
            "turncoat": "🔄 Яашка (Урвуулагч)",
            "don": "👑 Дон (Мафийн ахлагч)",
            "godmother": "👸 Godmother (Мафийн эх)",
            "joker": "🃏 Joker"
        }.get(role, "❓ Тодорхойгүй")

    # ────── Админ тохиргоо ──────
    @app_commands.command(name="mafia_setup", description="Мафи тоглоомын тохиргооны самбар")
    @app_commands.default_permissions(administrator=True)
    async def mafia_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = MafiaSetupView(self, interaction.guild_id, interaction.user.id)
        embed = view.build_embed(interaction.guild)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ────── Тоглоом үүсгэх ──────
    @commands.hybrid_command(name="mafiacreate")
    @commands.has_permissions(administrator=True)
    async def mafia_create(self, ctx):
        if ctx.channel.id in self.games:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Энэ сувагт аль хэдийн тоглоом явж байна.", ERROR_COLOR)
        game = MafiaGame(ctx.channel, ctx.author)
        self.games[ctx.channel.id] = game
        view = MafiaLobbyView(self, game)
        msg = await ctx.send(embed=view._build_embed(), view=view)
        view.message = msg

    # ────── Тоглоом эхлүүлэх ──────
    @commands.hybrid_command(name="mafiastart")
    @commands.has_permissions(administrator=True)
    async def mafia_start(self, ctx):
        game = self.get_game(ctx.channel.id)
        if not game:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Тоглоом байхгүй.", ERROR_COLOR)
        if game.phase != "waiting":
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Тоглоом аль хэдийн эхэлсэн.", ERROR_COLOR)
        if len(game.players) < 12:
            return await self.send_embed(ctx.channel, "❌ **АЛДАА**", "Хамгийн багадаа 12 тоглогч шаардлагатай.", ERROR_COLOR)

        # Дүр тараах
        roles = self.generate_roles(len(game.players))
        for i, p in enumerate(game.players):
            p.role = roles[i]
            p.alive = True
            p.night_action = None
            p.night_action_extra = None
            p.vote_target = None

        # Фракцийн суваг үүсгэх
        await self.create_faction_channels(game)

        game.phase = "night"
        game.day_count = 1

        # Тоглогчдод дүр мэдээлэх
        for p in game.players:
            embed_desc = f"**{self.role_name(p.role)}**\n\n{self.role_description(p.role, p.number)}"
            await self.send_dm(p.member, "🔮 ТАНЫ ДҮР", embed_desc, PURPLE_COLOR)

        # Фракцийн мэдээлэл
        if game.mafia_channel:
            mafia_players = [p for p in game.players if p.role in ("mafia", "don", "godmother")]
            if len(mafia_players) > 1:
                names = [f"№{p.number} - {p.member.mention}" for p in mafia_players]
                await game.mafia_channel.send(embed=discord.Embed(title="🔪 МАФИ ХАМТРАГЧИД", description="\n".join(names), color=MAFIA_RED))
        if game.detective_channel:
            detective_players = [p for p in game.players if p.role == "detective"]
            if len(detective_players) > 1:
                names = [f"№{p.number} - {p.member.mention}" for p in detective_players]
                await game.detective_channel.send(embed=discord.Embed(title="👮 ЦАГДАА ХАМТРАГЧИД", description="\n".join(names), color=INFO_COLOR))

        # Joker мэдэгдэх
        joker = next((p for p in game.players if p.role == "joker"), None)
        if joker:
            await self.send_dm(joker.member, "🃏 JOKER", "Хэрэв та өдөр vote-р шидэгдвэл ганцаараа ялна.", GOLD_COLOR)

        # Эхлэлийн мэдэгдэл
        faction_info = ""
        if game.mafia_channel: faction_info += f"🔪 Мафийн суваг: {game.mafia_channel.mention}\n"
        if game.detective_channel: faction_info += f"👮 Цагдаагийн суваг: {game.detective_channel.mention}\n"
        await ctx.send(embed=discord.Embed(
            title="🌙 **ШӨНӨ БОЛЛО**",
            description=f"Нийт **{len(game.players)}** тоглогчтой тоглоом эхэллээ!\n\n"
                        f"{faction_info}"
                        f"• 🔪 Мафи: `kill <дугаар>`\n"
                        f"• 💊 Эмч: `save <дугаар>`\n"
                        f"• 👮 Цагдаа: `investigate <дугаар>`\n"
                        f"• 🔄 Яашка: `sleep <үхсэн дугаар>`\n\n"
                        f"⏱️ **Хугацаа: {self.night_timeout} секунд**",
            color=PURPLE_COLOR
        ))

        game.night_task = self.bot.loop.create_task(self.night_phase_timer(game))

    # ────── Тоглоом зогсоох ──────
    @commands.hybrid_command(name="mafiaend")
    @commands.has_permissions(administrator=True)
    async def mafia_end(self, ctx):
        game = self.get_game(ctx.channel.id)
        if game:
            await self.end_game(game)

    async def end_game(self, game: MafiaGame, reason: str = "Тоглоом дуусгав"):
        if game.night_task: game.night_task.cancel()
        if game.vote_task: game.vote_task.cancel()
        await self.delete_faction_channels(game)
        if game.channel.id in self.games:
            del self.games[game.channel.id]
        try:
            await self.send_embed(game.channel, "⏹️ **ТОГЛООМ ЗОГСЛОО**", reason, WARNING_COLOR)
        except: pass

    # ────── Дүр тараалт ──────
    def generate_roles(self, count: int) -> List[str]:
        roles = []
        mafia_cnt = max(1, round(count / 4))
        for _ in range(mafia_cnt):
            roles.append("mafia")
        remaining = count - mafia_cnt
        if remaining >= 4:
            roles.append("detective")
            roles.append("doctor")
            remaining -= 2
        elif remaining >= 3:
            roles.append("doctor")
            remaining -= 1
        if count >= 6 and remaining >= 1:
            roles.append("turncoat")
            remaining -= 1
        if count >= 12 and remaining >= 1:
            roles.append("joker")
            remaining -= 1
        if count >= 20:
            don_role = random.choice(["don", "godmother"])
            for i, r in enumerate(roles):
                if r == "mafia":
                    roles[i] = don_role
                    break
        for _ in range(remaining):
            roles.append("civilian")
        random.shuffle(roles)
        return roles

    def role_description(self, role: str, num: int) -> str:
        base = f"🔢 **Таны дугаар:** `{num}`\n\n"
        if role == "mafia":
            return base + "**🌙 Шөнийн үйлдэл:** `kill <дугаар>`\n⚠️ Хамтрагчаа (мафи, яашка) алж болохгүй."
        elif role == "detective":
            return base + "**🌙 Шөнийн үйлдэл:** `investigate <дугаар>`\n🔍 Хариуг би танд DM-ээр илгээнэ."
        elif role == "doctor":
            return base + "**🌙 Шөнийн үйлдэл:** `save <дугаар>`\n💊 Хэрэв мафийн алсан хүн эмчлэгдвэл амьд үлдэнэ."
        elif role == "turncoat":
            return base + "**🌙 Шөнийн үйлдэл:** `sleep <үхсэн дугаар>`\n🔄 Тэдний дүрийг хуулж, тэр болно."
        elif role in ("don", "godmother"):
            return base + "**🌙 Шөнийн үйлдэл:** `kill <дугаар>`\n👑 Та мафийн удирдагч. Өөрийн хамтрагчаа мэднэ."
        elif role == "joker":
            return base + "**☀️ Өдрийн үйлдэл:** `vote <дугаар>`\n🃏 Хэрэв та өөртөө санал өгүүлж, vote-р шидэгдвэл ганцаараа ялна."
        else:
            return base + "**☀️ Өдрийн үйлдэл:** `vote <дугаар>`\n🗳️ Мафийг олоход тусал."

    # ────── Фракцийн суваг үүсгэх/устгах ──────
    async def create_faction_channels(self, game: MafiaGame):
        guild = game.channel.guild
        cat = discord.utils.get(guild.categories, name="🕵️ Mafia Game")
        if not cat:
            try:
                cat = await guild.create_category("🕵️ Mafia Game")
            except discord.Forbidden:
                return
        game.game_category = cat

        # Мафийн суваг
        mafia_players = [p for p in game.players if p.role in ("mafia", "don", "godmother")]
        if len(mafia_players) >= 2:
            overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False)}
            for p in mafia_players: overwrites[p.member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            overwrites[guild.me] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            try:
                channel = await guild.create_text_channel("mafia-chat", category=cat, overwrites=overwrites)
                game.mafia_channel = channel
                await channel.send(embed=discord.Embed(title="🔪 МАФИ ЧАТ", description="Энд хэлэлцэж, `kill <дугаар>` командаар алах хүнээ шийднэ.", color=MAFIA_RED))
            except: pass

        # Цагдаагийн суваг
        detective_players = [p for p in game.players if p.role == "detective"]
        if len(detective_players) >= 2:
            overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False)}
            for p in detective_players: overwrites[p.member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            overwrites[guild.me] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            try:
                channel = await guild.create_text_channel("detective-chat", category=cat, overwrites=overwrites)
                game.detective_channel = channel
                await channel.send(embed=discord.Embed(title="👮 ЦАГДАА ЧАТ", description="Энд мэдээллээ хуваалцаж, `investigate <дугаар>` командаар хэнийг шалгахаа шийднэ.", color=INFO_COLOR))
            except: pass

    async def delete_faction_channels(self, game: MafiaGame):
        for ch in [game.mafia_channel, game.detective_channel]:
            if ch:
                try: await ch.delete()
                except: pass
        if game.game_category:
            try:
                if not game.game_category.channels:
                    await game.game_category.delete()
            except: pass

    # ────── Шөнийн фаза ──────
    async def night_phase_timer(self, game: MafiaGame):
        await asyncio.sleep(self.night_timeout)
        game = self.get_game(game.channel.id)
        if not game or game.phase != "night":
            return
        await self.resolve_night_actions(game)

    async def resolve_night_actions(self, game: MafiaGame):
        mafia_players = [p for p in game.players if p.role in ("mafia", "don", "godmother") and p.alive]
        doctor = next((p for p in game.players if p.role == "doctor" and p.alive), None)
        detective = next((p for p in game.players if p.role == "detective" and p.alive), None)
        turncoat = next((p for p in game.players if p.role == "turncoat" and p.alive), None)

        blackout = game.blackout_night
        game.blackout_night = False

        # Алах санал цуглуулах
        kill_votes = {}
        for p in mafia_players:
            if p.night_action and isinstance(p.night_action, int):
                kill_votes[p.night_action] = kill_votes.get(p.night_action, 0) + 1

        kill_targets = []
        if kill_votes:
            max_v = max(kill_votes.values())
            candidates = [num for num, cnt in kill_votes.items() if cnt == max_v]
            kill_targets.append(random.choice(candidates))

        # Double kill
        if game.double_kill_night:
            extra_kills = []
            for p in mafia_players:
                if p.night_action_extra and isinstance(p.night_action_extra, int):
                    extra_kills.append(p.night_action_extra)
            if extra_kills:
                counts = {}
                for t in extra_kills:
                    counts[t] = counts.get(t, 0) + 1
                max_e = max(counts.values())
                candidates2 = [num for num, cnt in counts.items() if cnt == max_e]
                kill_targets.append(random.choice(candidates2))
            if len(kill_targets) < 2:
                alive_nums = [p.number for p in game.players if p.alive and p.number not in kill_targets]
                if alive_nums:
                    kill_targets.append(random.choice(alive_nums))
            game.double_kill_night = False

        doctor_target = doctor.night_action if doctor and isinstance(doctor.night_action, int) else None
        detective_target = detective.night_action if detective and isinstance(detective.night_action, int) else None

        # Яашка
        if turncoat:
            if turncoat.night_action is None:
                dead_nums = [p.number for p in game.players if not p.alive and p.number != turncoat.number]
                if dead_nums:
                    turncoat.night_action = random.choice(dead_nums)
                    await self.send_dm(turncoat.member, "🔄 АВТОМАТ УНТЛАА", f"Та **{turncoat.night_action}** дугаартай тоглогчийн сүнстэй унтлаа.", WARNING_COLOR)
            if turncoat.night_action:
                target = next((p for p in game.players if p.number == turncoat.night_action), None)
                if target and not target.alive and target.role in ("mafia", "detective", "doctor"):
                    turncoat.role = target.role
                    turncoat.copied_role = True
                    await self.send_dm(turncoat.member, "🔄 ДҮР ХУУЛАВ", f"Та одоо **{self.role_name(target.role)}** боллоо!", SUCCESS_COLOR)

        # Детектив шалгалт
        if detective_target and not blackout:
            target = next((p for p in game.players if p.number == detective_target), None)
            if target and target.alive:
                is_mafia = target.role in ("mafia", "don", "godmother") or (target.role == "turncoat" and not target.copied_role)
                result = "**ХУЛГАЙЧ**" if is_mafia else "**ХУЛГАЙЧ БИШ**"
                await self.send_dm(detective.member, "🔍 МӨРДӨЛТИЙН ҮР ДҮН", f"{detective_target} дугаартай тоглогч → {result}", GOLD_COLOR)

        # Алах
        killed_players = []
        for kt in kill_targets:
            target = next((p for p in game.players if p.number == kt), None)
            if target and target.alive:
                if doctor_target == kt and not blackout:
                    await self.send_embed(game.channel, "💊 **АМЬД ҮЛДЭВ**", f"🔹 **{kt}** дугаартай тоглогч эмчийн авралаар амьд үлдлээ.", SUCCESS_COLOR)
                else:
                    target.alive = False
                    killed_players.append(kt)

        if killed_players:
            await self.send_embed(game.channel, "💀 **АЛАГДЛАА**", f"🔸 **{', '.join(map(str, killed_players))}** дугаартай тоглогч(д) шөнө алагдлаа!\n" +
                                  "\n".join([f"📜 Тэр **{self.role_name(next(p for p in game.players if p.number == kp).role)}** байсан." for kp in killed_players]), ERROR_COLOR)

        # Цэвэрлэх
        for p in game.players:
            p.night_action = None
            p.night_action_extra = None

        if await self.check_win(game):
            return

        game.phase = "day"
        game.day_count += 1
        await game.channel.send(embed=discord.Embed(
            title="☀️ **ӨДӨР БОЛЛО**",
            description=f"**{game.day_count}** -р өдөр эхэллээ.\nАмьд тоглогчид `vote <дугаар>` гэж нийтийн сувагт санал өгнө үү.\n⏱️ **Хугацаа: {self.day_vote_timeout} секунд**",
            color=GOLD_COLOR
        ))
        game.vote_task = self.bot.loop.create_task(self.voting_phase_timer(game))

    # ────── Санал хураалт ──────
    async def voting_phase_timer(self, game: MafiaGame):
        await asyncio.sleep(self.day_vote_timeout)
        game = self.get_game(game.channel.id)
        if not game or game.phase != "day":
            return

        votes = {}
        for p in game.players:
            if p.alive and p.vote_target:
                votes[p.vote_target] = votes.get(p.vote_target, 0) + 1

        result_embed = discord.Embed(title="🗳️ **САНАЛ ХУРААЛТЫН ДҮН**", color=INFO_COLOR)
        eliminated_num = None
        if not votes:
            result_embed.description = "Хэн ч санал өгөөгүй тул хэн ч үхээгүй."
            result_embed.color = WARNING_COLOR
        else:
            max_v = max(votes.values())
            eliminated = [num for num, cnt in votes.items() if cnt == max_v]
            if len(eliminated) > 1:
                result_embed.description = f"**{', '.join(map(str, eliminated))}** нар адил санал авсан тул хэн ч үхээгүй."
                result_embed.color = WARNING_COLOR
            else:
                eliminated_num = eliminated[0]
                elim_player = next((p for p in game.players if p.number == eliminated_num), None)
                if elim_player:
                    elim_player.alive = False
                    result_embed.description = f"⚖️ **{eliminated_num}** дугаартай тоглогч хөөгдөн үхэв!\n📜 Тэр **{self.role_name(elim_player.role)}** байсан."
                    result_embed.color = ERROR_COLOR

        await game.channel.send(embed=result_embed)

        # Joker шалгах
        if eliminated_num is not None:
            joker = next((p for p in game.players if p.role == "joker" and p.number == eliminated_num), None)
            if joker:
                game.joker_win = True
                await game.channel.send(embed=discord.Embed(title="🃏 **JOKER SOLO WIN!** 🃏",
                                                            description=f"**{joker.member.mention}** өөрийгөө vote-р гаргуулж, ганцаараа ялалт байгууллаа!",
                                                            color=GOLD_COLOR))
                game.phase = "ended"
                await self.delete_faction_channels(game)
                del self.games[game.channel.id]
                return

        for p in game.players:
            p.vote_target = None

        if await self.check_win(game):
            return

        game.phase = "night"
        await game.channel.send(embed=discord.Embed(
            title="🌙 **ШӨНӨ БУУВ**",
            description="Мафи, эмч, цагдаа, яашка үйлдлээ өөрийн фракцийн сувагт (эсвэл DM) хийгээрэй.\n"
                        f"⏱️ **Хугацаа: {self.night_timeout} секунд**",
            color=PURPLE_COLOR
        ))
        game.night_task = self.bot.loop.create_task(self.night_phase_timer(game))

    # ────── Ялалт шалгах ──────
    async def check_win(self, game: MafiaGame) -> bool:
        alive = [p for p in game.players if p.alive]
        mafia_side = [p for p in alive if p.role in ("mafia", "don", "godmother") or (p.role == "turncoat" and not p.copied_role)]
        town_side = [p for p in alive if p not in mafia_side and p.role != "joker"]

        if len(mafia_side) == 0:
            await game.channel.send(embed=discord.Embed(title="🎉 **ИРГЭД ЯЛАЛТ БАЙГУУЛЛАА!**", description="Бүх мафи болон урвуулагч үхсэн.", color=SUCCESS_COLOR))
            game.phase = "ended"
            await self.delete_faction_channels(game)
            del self.games[game.channel.id]
            return True
        if len(mafia_side) >= len(town_side):
            await game.channel.send(embed=discord.Embed(title="💀 **МАФИ ЯЛАЛТ БАЙГУУЛЛАА!**", description="Мафи тоогоор илүү болов.", color=MAFIA_RED))
            game.phase = "ended"
            await self.delete_faction_channels(game)
            del self.games[game.channel.id]
            return True
        return False

    # ────── Мессеж сонсогч ──────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Өдрийн санал өгөлт (нийтийн суваг)
        if message.guild is not None:
            game = self.get_game(message.channel.id)
            if game and game.phase == "day":
                content = message.content.strip().lower()
                if content.startswith("vote "):
                    try:
                        parts = content.split()
                        if len(parts) != 2: return
                        target_num = int(parts[1])
                    except: return
                    voter = next((p for p in game.players if p.member.id == message.author.id), None)
                    if not voter or not voter.alive:
                        await message.delete()
                        return
                    target = next((p for p in game.players if p.number == target_num and p.alive), None)
                    if not target:
                        await message.channel.send(f"{message.author.mention} **{target_num}** дугаартай амьд тоглогч байхгүй.", delete_after=5)
                        await message.delete()
                        return
                    if voter.vote_target is not None:
                        await message.channel.send(f"{message.author.mention} Та аль хэдийн санал өгсөн байна.", delete_after=5)
                        await message.delete()
                        return
                    voter.vote_target = target.number
                    await message.channel.send(f"✅ {message.author.mention} → **{target_num}** дугаарт санал өглөө.", delete_after=5)
                    await message.delete()
                return

            # Шөнийн командууд фракцийн сувагт
            for g in self.games.values():
                if g.phase == "night" and message.channel.id in [c.id for c in (g.mafia_channel, g.detective_channel) if c]:
                    game = g
                    break
            else:
                return

            player = next((p for p in game.players if p.member.id == message.author.id), None)
            if not player or not player.alive:
                return

            content = message.content.strip().lower()
            parts = content.split()
            if len(parts) != 2:
                await message.channel.send(f"{message.author.mention} ❌ **Буруу формат!** Жишээ: `kill 3`")
                return
            action, target_str = parts[0], parts[1]
            try: target_num = int(target_str)
            except:
                await message.channel.send(f"{message.author.mention} ❌ **Зөвхөн тоо оруулна уу.**")
                return

            target_player = next((p for p in game.players if p.number == target_num), None)
            if not target_player:
                await message.channel.send(f"{message.author.mention} ❌ **{target_num}** дугаартай тоглогч байхгүй.")
                return

            role = player.role
            channel = message.channel

            if action == "kill":
                if role not in ("mafia", "don", "godmother"):
                    await channel.send(f"{message.author.mention} ❌ **Та мафи биш.**")
                    return
                if target_num == player.number:
                    await channel.send(f"{message.author.mention} ❌ **Өөртөө алах боломжгүй.**")
                    return
                if target_player.role in ("mafia", "don", "godmother", "turncoat"):
                    await channel.send(f"{message.author.mention} ❌ **Хамтрагчаа алж болохгүй.**")
                    return
                if game.double_kill_night and player.night_action is not None:
                    player.night_action_extra = target_num
                    await channel.send(f"✅ {message.author.mention} **{target_num}** -г хоёр дахь байгаагаар алахаар шийдлээ.")
                else:
                    player.night_action = target_num
                    await channel.send(f"✅ {message.author.mention} **{target_num}** -г алахаар шийдлээ.")

            elif action == "save":
                if role != "doctor":
                    await channel.send(f"{message.author.mention} ❌ **Зөвхөн эмч эмчилнэ.**")
                    return
                player.night_action = target_num
                await channel.send(f"✅ {message.author.mention} **{target_num}** -г эмчлэнэ.")

            elif action == "investigate":
                if role != "detective":
                    await channel.send(f"{message.author.mention} ❌ **Зөвхөн цагдаа мөрдөнө.**")
                    return
                player.night_action = target_num
                await channel.send(f"✅ {message.author.mention} **{target_num}** -г мөрдөнө.")

            elif action == "sleep":
                if role != "turncoat":
                    await channel.send(f"{message.author.mention} ❌ **Зөвхөн яашка унтаж болно.**")
                    return
                if target_player.alive:
                    await channel.send(f"{message.author.mention} ❌ **Зөвхөн үхсэн тоглогчтой унтана.**")
                    return
                player.night_action = target_num
                await channel.send(f"✅ {message.author.mention} **{target_num}** -тэй унтана.")
            else:
                await channel.send(f"{message.author.mention} ❌ **Буруу үйлдэл.** Зөвшөөрөгдсөн: `kill`, `save`, `investigate`, `sleep`")

        # DM командууд (фракцийн суваггүй үед)
        if message.guild is None:
            for game in self.games.values():
                if game.phase != "night": continue
                player = next((p for p in game.players if p.member.id == message.author.id and p.alive), None)
                if not player: continue

                content = message.content.strip().lower()
                parts = content.split()
                if len(parts) != 2:
                    await message.channel.send("❌ **Буруу формат!** Жишээ: `kill 3`")
                    return
                action, target_str = parts[0], parts[1]
                try: target_num = int(target_str)
                except:
                    await message.channel.send("❌ **Зөвхөн тоо оруулна уу.**")
                    return

                target_player = next((p for p in game.players if p.number == target_num), None)
                if not target_player:
                    await message.channel.send(f"❌ **{target_num}** дугаартай тоглогч байхгүй.")
                    return

                role = player.role

                if action == "kill":
                    if role not in ("mafia", "don", "godmother"):
                        await message.channel.send("❌ **Та мафи биш.**")
                        return
                    if target_num == player.number:
                        await message.channel.send("❌ **Өөртөө алах боломжгүй.**")
                        return
                    if target_player.role in ("mafia", "don", "godmother", "turncoat"):
                        await message.channel.send("❌ **Хамтрагчаа алж болохгүй.**")
                        return
                    if game.double_kill_night and player.night_action is not None:
                        player.night_action_extra = target_num
                        await message.channel.send(f"✅ Та **{target_num}** -г хоёр дахь байгаагаар алахаар шийдлээ.")
                    else:
                        player.night_action = target_num
                        await message.channel.send(f"✅ Та **{target_num}** -г алахаар шийдлээ.")

                elif action == "save":
                    if role != "doctor":
                        await message.channel.send("❌ **Зөвхөн эмч эмчилнэ.**")
                        return
                    player.night_action = target_num
                    await message.channel.send(f"✅ Та **{target_num}** -г эмчлэнэ.")

                elif action == "investigate":
                    if role != "detective":
                        await message.channel.send("❌ **Зөвхөн цагдаа мөрдөнө.**")
                        return
                    player.night_action = target_num
                    await message.channel.send(f"✅ Та **{target_num}** -г мөрдөнө.")

                elif action == "sleep":
                    if role != "turncoat":
                        await message.channel.send("❌ **Зөвхөн яашка унтаж болно.**")
                        return
                    if target_player.alive:
                        await message.channel.send("❌ **Зөвхөн үхсэн тоглогчтой унтана.**")
                        return
                    player.night_action = target_num
                    await message.channel.send(f"✅ Та **{target_num}** -тэй унтана.")
                else:
                    await message.channel.send("❌ **Буруу үйлдэл.** Зөвшөөрөгдсөн: `kill`, `save`, `investigate`, `sleep`")
                break

async def setup(bot):
    await bot.add_cog(Mafia(bot))
