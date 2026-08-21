from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional, Dict, Any, Union
import ast
import operator

# ===== ӨНГӨНҮҮД =====
EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa

# ==================== АЮУЛГҮЙ МАТЕМАТИК БОДОЛТ ====================
ALLOWED_NODES = {
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Load, ast.Expr,
    ast.Name,
}
SAFE_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}

def evaluate_expression(expr: str) -> Union[int, float, None]:
    try:
        tree = ast.parse(expr.strip(), mode='eval')
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if type(node) not in ALLOWED_NODES:
            return None
    if any(isinstance(n, ast.Name) for n in ast.walk(tree)):
        return None
    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            if isinstance(node.op, ast.USub): return -operand
            if isinstance(node.op, ast.UAdd): return +operand
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op_type = type(node.op)
            if op_type in SAFE_OPERATORS:
                return SAFE_OPERATORS[op_type](left, right)
        raise ValueError("Дэмжигдэхгүй үйлдэл")
    try:
        result = _eval(tree.body)
        if isinstance(result, (int, float)):
            return result
        return None
    except (ValueError, ZeroDivisionError):
        return None

# ==================== МОДАЛ: РОЛЬ ID ОРУУЛАХ ====================
class RoleIDModal(ui.Modal, title="Роль ID оруулах"):
    role_id_input = ui.TextInput(
        label="Ролийн Discord ID",
        placeholder="123456789012345678",
        required=True
    )
    def __init__(self, view, role_type: str):
        super().__init__()
        self.view = view
        self.role_type = role_type  # 'failed', 'reliable', 'save'

    async def on_submit(self, interaction: discord.Interaction):
        role_id_str = self.role_id_input.value.strip()
        try:
            role_id = int(role_id_str)
        except ValueError:
            return await interaction.response.send_message("❌ Буруу ID формат.", ephemeral=True)
        role = interaction.guild.get_role(role_id)
        if not role:
            return await interaction.response.send_message("❌ Роль олдсонгүй.", ephemeral=True)

        column_map = {
            "failed": "failed_role_id",
            "reliable": "reliable_role_id",
            "save": "save_role_id"
        }
        column = column_map[self.role_type]
        await self.view.cog.bot.db_manager.update(
            "counting_config",
            {"guild_id": str(interaction.guild.id)},
            {column: role.id},
        )
        await interaction.response.send_message(f"✅ {role.mention} роль тохируулагдлаа.", ephemeral=True)
        await self.view.refresh(interaction)

# ==================== МОДАЛ: АЛБАДМАЛ ТОО ====================
class ForceCountModal(ui.Modal, title="Тооллын утга тогтоох"):
    number_input = ui.TextInput(
        label="Тоо оруулна уу",
        placeholder="Жишээ: 500",
        required=True
    )
    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            num = int(self.number_input.value)
            if num < 0:
                return await interaction.response.send_message("❌ Эерэг тоо оруулна уу.", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("❌ Зөвхөн тоо оруулна уу.", ephemeral=True)

        await self.view.cog.update_progress(interaction.guild.id, num, None, 0)
        await interaction.response.send_message(f"✅ Тоолол **{num}** болж тогтоогдлоо.", ephemeral=True)
        await self.view.refresh(interaction)

# ==================== ТОХИРГООНЫ САМБАР (VIEW) ====================
class CountingSetupView(ui.View):
    def __init__(self, cog, guild_id, author_id):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Энэ самбар таных биш.", ephemeral=True)
            return False
        return True

    async def refresh(self, interaction: discord.Interaction):
        cfg = await self.cog.get_config(self.guild_id)
        embed = self.build_embed(cfg, interaction.guild)
        await interaction.edit_original_response(embed=embed, view=self)

    def build_embed(self, cfg, guild):
        if cfg is None:
            desc = "⚠️ **Тохиргоо хийгдээгүй.**\nДоорх сонголтоор сувгаа тохируулна уу."
            channel_text = "❌ Сонгогдоогүй"
            enabled = False
            math_mode = False
            delete_msg = False
            failed_role_text = "❌ Тохируулаагүй"
            reliable_role_text = "❌ Тохируулаагүй"
            save_role_text = "❌ Тохируулаагүй"
            high_score = 0
            best_streak = 0
        else:
            channel = guild.get_channel(cfg['channel_id'])
            channel_text = channel.mention if channel else "❌ Устгагдсан"
            enabled = cfg['enabled']
            math_mode = cfg['math_mode']
            delete_msg = cfg['delete_messages']
            failed_role = guild.get_role(cfg['failed_role_id']) if cfg['failed_role_id'] else None
            reliable_role = guild.get_role(cfg['reliable_role_id']) if cfg['reliable_role_id'] else None
            save_role = guild.get_role(cfg['save_role_id']) if cfg['save_role_id'] else None
            failed_role_text = failed_role.mention if failed_role else "❌ Тохируулаагүй"
            reliable_role_text = reliable_role.mention if reliable_role else "❌ Тохируулаагүй"
            save_role_text = save_role.mention if save_role else "❌ Тохируулаагүй"
            high_score = cfg['high_score']
            best_streak = cfg['best_streak']
            desc = None

        embed = discord.Embed(
            title="🔧 Тооллогын тохиргоо",
            description=desc,
            color=INFO_COLOR
        )
        embed.add_field(name="📢 Тоолох суваг", value=channel_text, inline=False)
        embed.add_field(name="🔘 Идэвхтэй", value="✅" if enabled else "❌", inline=True)
        embed.add_field(name="🧮 Математик илэрхийлэл", value="✅" if math_mode else "❌", inline=True)
        embed.add_field(name="🗑️ Буруу мессеж устгах", value="✅" if delete_msg else "❌", inline=True)
        embed.add_field(name="⚠️ Алдааны роль", value=failed_role_text, inline=True)
        embed.add_field(name="🌟 Найдвартай роль", value=reliable_role_text, inline=True)
        embed.add_field(name="🛟 Аврах роль", value=save_role_text, inline=True)
        embed.add_field(name="🏆 Дээд амжилт", value=f"```{high_score}```", inline=True)
        embed.add_field(name="🔥 Хамгийн урт цуврал", value=f"```{best_streak}```", inline=True)
        embed.set_footer(text="Дээрх товчлууруудаар тохиргоог өөрчлөөрэй.")
        return embed

    # ---------- СУВАГ СОНГОХ ----------
    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📢 Тоолох сувгаа сонго...", min_values=1, max_values=1, row=0)
    async def select_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        channel = select.values[0]
        await self.cog.bot.db_manager.upsert(
            "counting_config",
            {"guild_id": str(interaction.guild.id), "channel_id": channel.id, "enabled": 1},
            on_conflict="guild_id",
        )
        await interaction.response.defer()
        await self.refresh(interaction)

    # ---------- ТӨЛӨВ ТОВЧНУУД ----------
    @ui.button(label="🔘 Тооллого асаах/унтраах", style=discord.ButtonStyle.primary, row=1)
    async def toggle_enabled(self, interaction: discord.Interaction, button: ui.Button):
        cfg = await self.cog.get_config(self.guild_id)
        if not cfg:
            await interaction.response.send_message("❌ Эхлээд сувгаа сонгоно уу.", ephemeral=True)
            return
        new_state = not cfg['enabled']
        await self.cog.bot.db_manager.update(
            "counting_config",
            {"guild_id": str(interaction.guild.id)},
            {"enabled": int(new_state)},
        )
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="🧮 Math Mode", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_math(self, interaction: discord.Interaction, button: ui.Button):
        cfg = await self.cog.get_config(self.guild_id)
        if not cfg:
            await interaction.response.send_message("❌ Эхлээд сувгаа сонгоно уу.", ephemeral=True)
            return
        new_state = not cfg['math_mode']
        await self.cog.bot.db_manager.update(
            "counting_config",
            {"guild_id": str(interaction.guild.id)},
            {"math_mode": int(new_state)},
        )
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="🗑️ Мессеж устгах", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_delete(self, interaction: discord.Interaction, button: ui.Button):
        cfg = await self.cog.get_config(self.guild_id)
        if not cfg:
            await interaction.response.send_message("❌ Эхлээд сувгаа сонгоно уу.", ephemeral=True)
            return
        new_state = not cfg['delete_messages']
        await self.cog.bot.db_manager.update(
            "counting_config",
            {"guild_id": str(interaction.guild.id)},
            {"delete_messages": int(new_state)},
        )
        await interaction.response.defer()
        await self.refresh(interaction)

    # ---------- РОЛЬ ТОХИРГОО ----------
    @ui.button(label="⚠️ Алдааны роль", style=discord.ButtonStyle.danger, row=2)
    async def set_failed_role(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RoleIDModal(self, "failed"))

    @ui.button(label="🌟 Найдвартай роль", style=discord.ButtonStyle.success, row=2)
    async def set_reliable_role(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RoleIDModal(self, "reliable"))

    @ui.button(label="🛟 Аврах роль", style=discord.ButtonStyle.success, row=2)
    async def set_save_role(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RoleIDModal(self, "save"))

    # ---------- БУСАД ҮЙЛДЭЛ ----------
    @ui.button(label="🔢 Тоо тогтоох", style=discord.ButtonStyle.primary, row=3)
    async def force_number(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ForceCountModal(self))

    @ui.button(label="🔄 Шинэчлэх", style=discord.ButtonStyle.gray, row=3)
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="🧹 Бүх тохиргоог устгах", style=discord.ButtonStyle.danger, row=3)
    async def reset_config(self, interaction: discord.Interaction, button: ui.Button):
        await self.cog.bot.db_manager.delete("counting_config", {"guild_id": str(interaction.guild.id)})
        await self.cog.bot.db_manager.delete("counting_progress", {"guild_id": str(interaction.guild.id)})
        await interaction.response.send_message("✅ Бүх тохиргоо устлаа.", ephemeral=True)
        await self.refresh(interaction)

    async def on_timeout(self):
        if self.message:
            try:
                for child in self.children:
                    child.disabled = True
                await self.message.edit(view=self)
            except:
                pass

# ==================== ҮНДСЭН COG ====================
class Counting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Tables are pre-configured in Supabase via SQL migrations
        pass

    # ---------- DB туслахууд ----------
    async def get_config(self, guild_id: int) -> Dict[str, Any]:
        row = await self.bot.db_manager.fetch_one("counting_config", {"guild_id": str(guild_id)})
        if not row: return None
        config = {
            "channel_id": row.get("channel_id"),
            "enabled": bool(row.get("enabled", 1)),
            "delete_messages": bool(row.get("delete_messages", 0)),
            "math_mode": bool(row.get("math_mode", 0)),
            "failed_role_id": row.get("failed_role_id"),
            "reliable_role_id": row.get("reliable_role_id"),
            "save_role_id": row.get("save_role_id"),
            "high_score": row.get("high_score") or 0,
            "best_streak": row.get("best_streak") or 0,
        }
        return config

    async def get_progress(self, guild_id: int) -> Dict[str, Any]:
        row = await self.bot.db_manager.fetch_one("counting_progress", {"guild_id": str(guild_id)})
        if not row: return {"current": 0, "last_user": None, "streak": 0}
        return {"current": row.get("current_count", 0), "last_user": row.get("last_user_id"), "streak": row.get("streak", 0)}

    async def update_progress(self, guild_id: int, current: int, last_user: Optional[int], streak: int):
        await self.bot.db_manager.upsert(
            "counting_progress",
            {
                "guild_id": str(guild_id),
                "current_count": current,
                "last_user_id": last_user,
                "streak": streak,
            },
            on_conflict="guild_id",
        )

    async def reset_count(self, guild_id: int):
        await self.update_progress(guild_id, 0, None, 0)

    async def update_high_score(self, guild_id: int, new_score: int):
        await self.bot.db_manager.update(
            "counting_config", {"guild_id": str(guild_id)}, {"high_score": new_score}
        )

    async def update_best_streak(self, guild_id: int, new_streak: int):
        await self.bot.db_manager.update(
            "counting_config", {"guild_id": str(guild_id)}, {"best_streak": new_streak}
        )

    async def add_stats(self, guild_id: int, user_id: int, correct: bool, streak: int = 0):
        col = "correct" if correct else "wrong"
        existing = await self.bot.db_manager.fetch_one(
            "counting_stats", {"guild_id": str(guild_id), "user_id": str(user_id)}
        )
        if existing:
            current = existing.get(col, 0) or 0
            data = {col: current + 1}
            if correct:
                data["best_streak"] = max(existing.get("best_streak", 0) or 0, streak)
            await self.bot.db_manager.update(
                "counting_stats",
                {"guild_id": str(guild_id), "user_id": str(user_id)},
                data,
            )
        else:
            data = {"guild_id": str(guild_id), "user_id": str(user_id), col: 1}
            if correct:
                data["best_streak"] = streak
            await self.bot.db_manager.insert("counting_stats", data)

    async def add_save_stat(self, guild_id: int, user_id: int):
        existing = await self.bot.db_manager.fetch_one(
            "counting_stats", {"guild_id": str(guild_id), "user_id": str(user_id)}
        )
        if existing:
            await self.bot.db_manager.update(
                "counting_stats",
                {"guild_id": str(guild_id), "user_id": str(user_id)},
                {"saves": (existing.get("saves", 0) or 0) + 1},
            )
        else:
            await self.bot.db_manager.insert("counting_stats", {
                "guild_id": str(guild_id), "user_id": str(user_id), "saves": 1,
            })

    # ========== PUBLIC API: LEADERBOARD ХОЛБОЛТ ==========
    async def get_top_counters(self, guild_id: int, limit=10, offset=0):
        """Хамгийн олон зөв тоолсон хэрэглэгчдийг буцаана (Leaderboard ког ашиглах)."""
        rows = await self.bot.db_manager.fetch_all(
            "counting_stats",
            {"guild_id": str(guild_id)},
            order_by="correct",
            desc=True,
            limit=limit,
            offset=offset,
        )
        return [(int(r["user_id"]), r.get("correct", 0)) for r in rows]

    # ==================== ТООЛЛОГО СОНСОГЧ ====================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        cfg = await self.get_config(message.guild.id)
        if not cfg or not cfg["enabled"] or message.channel.id != cfg["channel_id"]: return

        content = message.content.strip()
        num = None
        try: num = int(content)
        except ValueError:
            if cfg["math_mode"]:
                num = evaluate_expression(content)
                if num is not None and not isinstance(num, int): num = None
        if num is None or not isinstance(num, int): return

        prog = await self.get_progress(message.guild.id)
        expected = prog["current"] + 1

        if num != expected or (prog["last_user"] == message.author.id and prog["current"] != 0):
            await self.add_stats(message.guild.id, message.author.id, False)
            await self.reset_count(message.guild.id)
            embed = discord.Embed(title="❌ БУРУУ ТОО!",
                description=f"{message.author.mention} буруу тоо бичлээ.\n**{expected}** байх ёстой байсан.\nТоолол **0** болж шинэчлэгдлээ.",
                color=ERROR_COLOR)
            embed.set_footer(text="Дараагийн тоо: 1")
            await message.channel.send(embed=embed)
            if cfg["delete_messages"]:
                try: await message.delete()
                except: pass
            if cfg["failed_role_id"]:
                role = message.guild.get_role(cfg["failed_role_id"])
                if role:
                    try: await message.author.add_roles(role, reason="Тооллогын алдаа")
                    except: pass
            return

        new_streak = prog["streak"] + 1 if prog["last_user"] == message.author.id else 1
        await self.update_progress(message.guild.id, expected, message.author.id, new_streak)
        await self.add_stats(message.guild.id, message.author.id, True, new_streak)
        
        # Даалгаврын системд мэдэгдэх
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            await quests_cog.trigger_event(message.author.id, message.guild.id, "counting_participate", 1)
        
        try: await message.add_reaction("✅")
        except: pass

        if expected > cfg["high_score"]:
            await self.update_high_score(message.guild.id, expected)
            await message.channel.send(embed=discord.Embed(
                title="🏆 ШИНЭ ДЭЭД АМЖИЛТ!",
                description=f"{message.author.mention} **{expected}**-д хүрч, шинэ амжилт тогтоолоо!",
                color=GOLD_COLOR))

        if new_streak > cfg["best_streak"]:
            await self.update_best_streak(message.guild.id, new_streak)
            await message.channel.send(embed=discord.Embed(
                title="🔥 ХАМГИЙН УРТ ЦУВРАЛ!",
                description=f"{message.author.mention} **{new_streak}** дараалсан зөв тоогоор шинэ рекорд тогтоолоо!",
                color=0xffa500))

        if new_streak == 50 and cfg["reliable_role_id"]:
            role = message.guild.get_role(cfg["reliable_role_id"])
            if role and role not in message.author.roles:
                try:
                    await message.author.add_roles(role, reason="50 дараалсан зөв тоололт")
                    await message.channel.send(f"🌟 {message.author.mention} та найдвартай тоологч боллоо!", delete_after=5)
                except: pass

    # ==================== ХЭРЭГЛЭГЧИЙН КОМАНДУУД ====================
    @app_commands.command(name="count_stats_user", description="Хэрэглэгчийн тооллогын статистик")
    async def count_stats_user(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target = member or interaction.user
        row = await self.bot.db_manager.fetch_one(
            "counting_stats",
            {"guild_id": str(interaction.guild.id), "user_id": str(target.id)},
        )
        if not row:
            embed = discord.Embed(title="📊 Тооллогын статистик",
                description=f"{target.mention} одоогоор тооллогод оролцоогүй байна.", color=INFO_COLOR)
        else:
            correct = row.get("correct", 0) or 0
            wrong = row.get("wrong", 0) or 0
            saves = row.get("saves", 0) or 0
            strikes = row.get("strikes", 0) or 0
            best_streak = row.get("best_streak", 0) or 0
            total = correct + wrong
            accuracy = (correct / total * 100) if total > 0 else 0
            embed = discord.Embed(title=f"📊 {target.display_name} - ТООЛЛОГЫН СТАТИСТИК", color=INFO_COLOR)
            embed.add_field(name="✅ Зөв", value=f"```{correct}```", inline=True)
            embed.add_field(name="❌ Буруу", value=f"```{wrong}```", inline=True)
            embed.add_field(name="🎯 Нарийвчлал", value=f"```{accuracy:.1f}%```", inline=True)
            embed.add_field(name="🛟 Авралт", value=f"```{saves}```", inline=True)
            embed.add_field(name="⚠️ Анхааруулга", value=f"```{strikes}```", inline=True)
            embed.add_field(name="🔥 Хамгийн урт цуврал", value=f"```{best_streak}```", inline=True)
            embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="count_stats_server", description="Серверийн тооллогын статистик")
    async def count_stats_server(self, interaction: discord.Interaction):
        cfg = await self.get_config(interaction.guild.id)
        if not cfg:
            return await interaction.response.send_message("❌ Тохиргоо хийгдээгүй.", ephemeral=True)
        prog = await self.get_progress(interaction.guild.id)
        embed = discord.Embed(title="📈 СЕРВЕРИЙН ТООЛЛОГО", color=INFO_COLOR)
        embed.add_field(name="🔢 Одоогийн тоо", value=f"```{prog['current']}```", inline=True)
        embed.add_field(name="🏆 Дээд амжилт", value=f"```{cfg['high_score']}```", inline=True)
        embed.add_field(name="🔥 Хамгийн урт цуврал", value=f"```{cfg['best_streak']}```", inline=True)
        embed.add_field(name="👤 Одоогийн цуврал", value=f"```{prog['streak']}```", inline=True)
        embed.add_field(name="📢 Суваг", value=f"<#{cfg['channel_id']}>", inline=True)
        embed.add_field(name="🔘 Төлөв", value="Идэвхтэй" if cfg['enabled'] else "Унтарсан", inline=True)
        embed.add_field(name="🧮 Math Mode", value="Идэвхтэй" if cfg['math_mode'] else "Унтарсан", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="count_save", description="Тооллыг аврах (алдаа гарахаас хамгаалах)")
    async def count_save(self, interaction: discord.Interaction):
        cfg = await self.get_config(interaction.guild.id)
        if not cfg or not cfg["enabled"]:
            return await interaction.response.send_message("❌ Тооллого идэвхгүй байна.", ephemeral=True)
        allowed = False
        for rid in [cfg["save_role_id"], cfg["reliable_role_id"]]:
            if rid:
                role = interaction.guild.get_role(rid)
                if role and role in interaction.user.roles:
                    allowed = True
                    break
        if not allowed:
            return await interaction.response.send_message("❌ Танд аврах эрх байхгүй.", ephemeral=True)
        prog = await self.get_progress(interaction.guild.id)
        if prog["current"] == 0:
            return await interaction.response.send_message("❌ Одоогоор тоолол хоосон байна.", ephemeral=True)
        await self.add_save_stat(interaction.guild.id, interaction.user.id)
        embed = discord.Embed(description=f"✅ {interaction.user.mention} тооллыг аварлаа! Одоогийн тоо **{prog['current']}** хэвээр байна.", color=SUCCESS_COLOR)
        await interaction.response.send_message(embed=embed)

    # ==================== АДМИН ТОХИРГОО (ГАНЦ КОМАНД) ====================
    @app_commands.command(name="counting_setup", description="Тооллогын бүх тохиргоог удирдах самбар")
    @app_commands.default_permissions(administrator=True)
    async def counting_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cfg = await self.get_config(interaction.guild.id)
        view = CountingSetupView(self, interaction.guild.id, interaction.user.id)
        embed = view.build_embed(cfg, interaction.guild)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Counting(bot))