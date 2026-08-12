from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
import asyncio, io, json, logging, os, time, random
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import aiohttp, discord
from discord.ext import commands, tasks
from discord import ui
from utils.supabase_cog import SupabaseCog
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Resampling

# ---------- Logger ----------
log = logging.getLogger(__name__)

# ---------- Asset paths ----------
ASSETS_DIR = os.path.abspath(os.path.abspath("./assets"))
DEFAULT_ASSET_FONT = os.path.join(ASSETS_DIR, "levelfont.otf")
os.makedirs(ASSETS_DIR, exist_ok=True)

# ---------- Font helper (kept for legacy) ----------
try:
    from utils.font_utils import load_font as _load_font
except ImportError:
    def _load_font(size=40, bold=True):
        paths = [
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ] if bold else [
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        for p in paths:
            if os.path.exists(p):
                try: return ImageFont.truetype(p, size)
                except: pass
        return ImageFont.load_default(size)

# ---------- Color constants ----------
EMBED_COLOR   = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
GOLD_COLOR    = 0xfab387
WARNING_COLOR = 0xf9e2af
ERROR_COLOR   = 0xf38ba8
INFO_COLOR    = 0x89b4fa

# ---------- Defaults ----------
DEFAULT_XP_TIERS = [{"max_words":10,"xp":5},{"max_words":30,"xp":10},{"max_words":999,"xp":20}]
DEFAULT_XP_MEDIA = 15
DEFAULT_XP_REACTION = 1
DEFAULT_XP_VOICE_SILENT = 5
DEFAULT_XP_VOICE_TALKING = 15
DEFAULT_MSG_COOLDOWN = 60
DEFAULT_REACT_COOLDOWN = 10
DEFAULT_PROG_TYPE = "arithmetic"
DEFAULT_PROG_BASE = 100
DEFAULT_PROG_STEP = 150
VOICE_INTERVAL_SECS = 180

# ---------- Safe converters ----------
def _safe_int(value, default=0):
    try: return int(value)
    except: return default

def _safe_float(value, default=0.0):
    try: return float(value)
    except: return default

def _safe_bool(value, default=False):
    if isinstance(value, bool): return value
    if isinstance(value, int): return bool(value)
    if isinstance(value, str): return value.lower() in ('1','true','yes','on')
    return default

# ---------- XP progression math ----------
def xp_for_level(level: int, cfg: Dict[str, Any]) -> int:
    if cfg.get("prog_type") == "geometric":
        mult = float(cfg.get("prog_step", 1.5))
        return max(1, int(cfg.get("prog_base", 100) * (mult ** level)))
    return max(1, cfg.get("prog_base", 100) + level * int(cfg.get("prog_step", 150)))

def xp_for_message(content: str, cfg: Dict[str, Any]) -> int:
    words = len(content.split()) if content else 0
    tiers = cfg.get("xp_tiers", DEFAULT_XP_TIERS)
    if isinstance(tiers, str):
        try: tiers = json.loads(tiers)
        except: tiers = DEFAULT_XP_TIERS
    for tier in sorted(tiers, key=lambda t: int(t["max_words"])):
        if words <= int(tier["max_words"]): return int(tier["xp"])
    return int(tiers[-1]["xp"]) if tiers else 5

# ---------- Avatar helper (unused in DLC, kept for other purposes) ----------
async def fetch_avatar(url, size=128):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                data = await resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGBA").resize((size,size), resample=Resampling.LANCZOS)
    except:
        img = Image.new("RGBA",(size,size),(88,101,242,255))
    mask = Image.new("L",(size,size),0)
    ImageDraw.Draw(mask).ellipse((0,0,size,size),fill=255)
    img.putalpha(mask)
    return img

async def _load_background_image(url: Optional[str]):
    if not url:
        return None

    if isinstance(url, str) and url.startswith(("http://", "https://")):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        return Image.open(io.BytesIO(data)).convert("RGBA")
        except:
            return None

    if isinstance(url, str):
        candidate_paths = []
        if os.path.isabs(url):
            candidate_paths.append(url)
        else:
            candidate_paths.extend([
                os.path.join(ASSETS_DIR, url),
                os.path.join(os.path.dirname(__file__), url),
                os.path.join(os.getcwd(), url),
            ])
        for path in candidate_paths:
            if path and os.path.exists(path):
                try:
                    return Image.open(path).convert("RGBA")
                except:
                    pass
    return None

async def _load_overlay(overlay_name: str, width: int, height: int):
    if not overlay_name:
        return None
    candidates = [
        os.path.join(ASSETS_DIR, overlay_name),
        os.path.join(os.path.dirname(__file__), "assets", overlay_name),
        os.path.join(os.getcwd(), "assets", overlay_name),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            try:
                overlay = Image.open(path).convert("RGBA")
                return overlay.resize((width, height), resample=Resampling.LANCZOS)
            except:
                pass
    return None


def _load_asset_font(size: int, bold: bool = True):
    try:
        if os.path.exists(DEFAULT_ASSET_FONT):
            return ImageFont.truetype(DEFAULT_ASSET_FONT, size)
    except:
        pass
    try:
        return _load_font(size, bold)
    except:
        return ImageFont.load_default()

# ---------- Config load/save ----------
async def get_config(db_manager, guild_id: int) -> Dict[str, Any]:
    row = await db_manager.fetchone("leveling_config", {"guild_id": str(guild_id)})
    if not row:
        return {
            "enabled": True, "announce_channel": None, "voice_xp_enabled": True,
            "prog_type": "arithmetic", "prog_base": 100, "prog_step": 150,
            "xp_tiers": DEFAULT_XP_TIERS, "xp_media": 15, "xp_reaction": 1,
            "xp_voice_silent": 5, "xp_voice_talking": 15, "msg_cooldown": 60,
            "react_cooldown": 10, "background_url": None, "xp_drop_enabled": False,
            "xp_drop_channel": None, "xp_drop_min": 100, "xp_drop_max": 500,
            "xp_drop_interval": 3600, "cafe_buff_enabled": True, "invite_xp": 0,
            "marriage_bonus": 0.1,
        }
    cols = ["guild_id","enabled","announce_channel","voice_xp_enabled","prog_type","prog_base","prog_step","xp_tiers","xp_media","xp_reaction","xp_voice_silent","xp_voice_talking","msg_cooldown","react_cooldown","background_url","xp_drop_enabled","xp_drop_channel","xp_drop_min","xp_drop_max","xp_drop_interval","cafe_buff_enabled","invite_xp","marriage_bonus"]
    data = {}
    for i, key in enumerate(cols):
        data[key] = row[i] if i < len(row) else None
    return {
        "enabled": _safe_bool(data.get("enabled"), True),
        "announce_channel": data.get("announce_channel"),
        "voice_xp_enabled": _safe_bool(data.get("voice_xp_enabled"), True),
        "prog_type": data.get("prog_type") or "arithmetic",
        "prog_base": _safe_int(data.get("prog_base"), 100),
        "prog_step": _safe_float(data.get("prog_step"), 150.0),
        "xp_tiers": json.loads(data["xp_tiers"]) if data.get("xp_tiers") and data["xp_tiers"].startswith('[') else DEFAULT_XP_TIERS,
        "xp_media": _safe_int(data.get("xp_media"), 15),
        "xp_reaction": _safe_int(data.get("xp_reaction"), 1),
        "xp_voice_silent": _safe_int(data.get("xp_voice_silent"), 5),
        "xp_voice_talking": _safe_int(data.get("xp_voice_talking"), 15),
        "msg_cooldown": _safe_int(data.get("msg_cooldown"), 60),
        "react_cooldown": _safe_int(data.get("react_cooldown"), 10),
        "background_url": data.get("background_url"),
        "xp_drop_enabled": _safe_bool(data.get("xp_drop_enabled"), False),
        "xp_drop_channel": data.get("xp_drop_channel"),
        "xp_drop_min": _safe_int(data.get("xp_drop_min"), 100),
        "xp_drop_max": _safe_int(data.get("xp_drop_max"), 500),
        "xp_drop_interval": _safe_int(data.get("xp_drop_interval"), 3600),
        "cafe_buff_enabled": _safe_bool(data.get("cafe_buff_enabled"), True),
        "invite_xp": _safe_int(data.get("invite_xp"), 0),
        "marriage_bonus": _safe_float(data.get("marriage_bonus"), 0.1),
    }

async def set_config(db_manager, guild_id: int, cfg: Dict[str, Any]):
    data = {
        "guild_id": str(guild_id),
        "enabled": bool(cfg.get("enabled", True)),
        "announce_channel": cfg.get("announce_channel"),
        "voice_xp_enabled": bool(cfg.get("voice_xp_enabled", True)),
        "prog_type": cfg.get("prog_type", "arithmetic"),
        "prog_base": int(cfg.get("prog_base", 100)),
        "prog_step": float(cfg.get("prog_step", 150)),
        "xp_tiers": json.dumps(cfg.get("xp_tiers", DEFAULT_XP_TIERS)),
        "xp_media": int(cfg.get("xp_media", 15)),
        "xp_reaction": int(cfg.get("xp_reaction", 1)),
        "xp_voice_silent": int(cfg.get("xp_voice_silent", 5)),
        "xp_voice_talking": int(cfg.get("xp_voice_talking", 15)),
        "msg_cooldown": int(cfg.get("msg_cooldown", 60)),
        "react_cooldown": int(cfg.get("react_cooldown", 10)),
        "background_url": cfg.get("background_url"),
        "xp_drop_enabled": bool(cfg.get("xp_drop_enabled", False)),
        "xp_drop_channel": cfg.get("xp_drop_channel"),
        "xp_drop_min": int(cfg.get("xp_drop_min", 100)),
        "xp_drop_max": int(cfg.get("xp_drop_max", 500)),
        "xp_drop_interval": int(cfg.get("xp_drop_interval", 3600)),
        "cafe_buff_enabled": bool(cfg.get("cafe_buff_enabled", True)),
        "invite_xp": int(cfg.get("invite_xp", 0)),
        "marriage_bonus": float(cfg.get("marriage_bonus", 0.1))
    }
    await db_manager.execute("leveling_config", data)

# ---------- Rank card renderer (DiscordLevelingCard) ----------
async def render_dlc_card(member, level, current_xp, needed_xp, rank_pos, background_url=None):
    try:
        width, height = 900, 360
        base = Image.new("RGBA", (width, height), (20, 25, 35, 255))

        background = await _load_background_image(background_url)
        if background:
            try:
                background = background.resize((width, height), resample=Resampling.LANCZOS)
                base.alpha_composite(background)
            except:
                pass

        for overlay_name in ["overlay1.png", "curveborder.png"]:
            overlay = await _load_overlay(overlay_name, width, height)
            if overlay:
                try:
                    base.alpha_composite(overlay)
                except:
                    pass

        draw = ImageDraw.Draw(base)

        avatar_url = None
        try:
            avatar_url = getattr(member.display_avatar, "url", None)
            if avatar_url and hasattr(member.display_avatar, "replace"):
                avatar_url = member.display_avatar.replace(size=256, format="png").url
        except:
            avatar_url = None

        avatar = None
        if avatar_url:
            avatar = await fetch_avatar(avatar_url, 160)
        if avatar is None:
            avatar = Image.new("RGBA", (160, 160), (88, 101, 242, 255))

        avatar = avatar.convert("RGBA").resize((160, 160), resample=Resampling.LANCZOS)
        mask = Image.new("L", (160, 160), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 159, 159), fill=255)
        avatar.putalpha(mask)
        base.alpha_composite(avatar, dest=(50, 100))

        font_main = _load_asset_font(46, bold=True)
        font_sub = _load_asset_font(28, bold=False)
        font_small = _load_asset_font(18, bold=False)

        title = member.display_name[:24]
        draw.text((240, 80), title, font=font_main, fill=(255, 255, 255, 255))
        draw.text((240, 150), f"Түвшин {level}", font=font_sub, fill=(234, 179, 8, 255))
        draw.text((240, 190), f"Байр #{rank_pos}", font=font_sub, fill=(200, 200, 200, 255))

        bar_x, bar_y, bar_w, bar_h = 240, 250, 580, 32
        draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=14, fill=(60, 67, 82, 255))
        fill_w = int(bar_w * min(1.0, current_xp / max(1, needed_xp)))
        if fill_w > 0:
            draw.rounded_rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), radius=14, fill=(114, 137, 218, 255))

        xp_text = f"{current_xp:,}/{needed_xp:,} XP"
        try:
            bbox = draw.textbbox((0, 0), xp_text, font=font_small)
            tx_w = bbox[2] - bbox[0]
            tx_h = bbox[3] - bbox[1]
        except AttributeError:
            tx_w, tx_h = draw.textsize(xp_text, font=font_small)
        draw.text((bar_x + (bar_w - tx_w) // 2, bar_y + (bar_h - tx_h) // 2), xp_text, font=font_small, fill=(255, 255, 255, 255))

        footer_text = f"{member.name} • Gurten LGC-ээр бүтээгдсэн"
        draw.text((240, 310), footer_text, font=font_small, fill=(170, 170, 170, 255))

        buffer = io.BytesIO()
        base.save(buffer, "PNG")
        buffer.seek(0)
        return buffer
    except Exception as e:
        log.error(f"Rank card render failed: {e}")
        return None

# ---------- UI Views (same as before) ----------
class XPDropView(ui.View):
    def __init__(self, xp_amount, cog):
        super().__init__(timeout=300)
        self.xp_amount = xp_amount; self.cog = cog; self.claimed = set()
    @ui.button(label="🎉 XP авах", style=discord.ButtonStyle.success)
    async def claim(self, interaction, button):
        if interaction.user.id in self.claimed:
            return await interaction.response.send_message("❌ Та аль хэдийн авсан.", ephemeral=True)
        self.claimed.add(interaction.user.id)
        await self.cog.add_xp(interaction.user.id, interaction.guild.id, self.xp_amount,
                             member=interaction.guild.get_member(interaction.user.id))
        await interaction.response.send_message(f"✅ +{self.xp_amount} XP авлаа!", ephemeral=True)

class LevelRewardManagerView(ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=600)
        self.cog = cog; self.ctx = ctx; self.selected_level = None
    async def build_embed(self):
        entries = await self.cog.get_level_rewards(self.ctx.guild.id)
        embed = discord.Embed(title="🎁 Түвшний мөнгөн шагнал", color=GOLD_COLOR)
        if not entries: embed.description = "Одоогоор ямар ч шагнал тохируулаагүй байна."
        else:
            lines = []
            for e in entries: lines.append(f"**Level {e['level']}** → {e['money']:,} ₮")
            embed.description = "\n".join(lines)
        embed.set_footer(text="Доорх цэсээр түвшин сонгоод 'Шагнал тохируулах' эсвэл 'Устгах' дарна уу.")
        return embed
    async def refresh_message(self, interaction):
        embed = await self.build_embed()
        await interaction.edit_original_response(embed=embed, view=self)
    @ui.select(placeholder="Түвшин сонгох", row=0, min_values=1, max_values=1)
    async def level_select(self, interaction, select):
        self.selected_level = int(select.values[0])
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"Түвшин {self.selected_level} сонгогдлоо.", ephemeral=True)
    @ui.button(label="💰 Шагнал тохируулах", style=discord.ButtonStyle.green, row=1)
    async def set_reward_btn(self, interaction, button):
        if self.selected_level is None: return await interaction.response.send_message("❌ Эхлээд түвшин сонгоно уу.", ephemeral=True)
        modal = ui.Modal(title="Шагнал тохируулах")
        money_input = ui.TextInput(label="Мөнгөн дүн (₮)", placeholder="5000", required=True)
        modal.add_item(money_input)
        async def on_submit(inter):
            try:
                money = int(money_input.value)
                if money <= 0: raise ValueError
            except: return await inter.response.send_message("❌ Эерэг бүхэл тоо оруулна уу.", ephemeral=True)
            await self.cog.set_level_reward(self.ctx.guild.id, self.selected_level, money)
            await inter.response.send_message(f"✅ Level {self.selected_level} → {money:,} ₮ тохируулагдлаа.", ephemeral=True)
            await self.refresh_message(inter)
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)
    @ui.button(label="🗑️ Устгах", style=discord.ButtonStyle.red, row=1)
    async def remove_reward_btn(self, interaction, button):
        if self.selected_level is None: return await interaction.response.send_message("❌ Эхлээд түвшин сонгоно уу.", ephemeral=True)
        await self.cog.delete_level_reward(self.ctx.guild.id, self.selected_level)
        await interaction.response.send_message(f"🗑️ Level {self.selected_level} шагнал устгагдлаа.", ephemeral=True)
        await self.refresh_message(interaction)

class LevelRoleManagerView(ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=600)
        self.cog = cog; self.ctx = ctx
        self.selected_level = None; self.selected_role = None
    async def build_embed(self):
        entries = await self.cog.get_level_roles(self.ctx.guild.id)
        embed = discord.Embed(title="🛠️ Түвшний ролиудыг тохируулах", color=INFO_COLOR)
        if not entries: embed.description = "Одоогоор ямар ч түвшний роль тохируулаагүй байна."
        else:
            lines = []
            for e in entries:
                role = self.ctx.guild.get_role(e["role_id"])
                role_text = role.mention if role else f"<@&{e['role_id']}>"
                lines.append(f"**Level {e['level']}** → {role_text}")
            embed.description = "\n".join(lines)
        embed.set_footer(text="Доорх цэсээр түвшин/роль сонгоод 'Тохируулах' эсвэл 'Устгах' дарна уу.")
        return embed
    async def refresh_message(self, interaction):
        embed = await self.build_embed()
        await interaction.edit_original_response(embed=embed, view=self)
    @ui.select(placeholder="1️⃣ Түвшин сонгох", row=0, min_values=1, max_values=1)
    async def level_select(self, interaction, select):
        self.selected_level = int(select.values[0])
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"Түвшин {self.selected_level} сонгогдлоо.", ephemeral=True)
    @ui.select(cls=ui.RoleSelect, placeholder="2️⃣ Роль сонгох", row=1, min_values=1, max_values=1)
    async def role_select(self, interaction, select):
        self.selected_role = select.values[0]
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"Роль {self.selected_role.mention} сонгогдлоо.", ephemeral=True)
    @ui.button(label="✅ Тохируулах", style=discord.ButtonStyle.green, row=2)
    async def set_btn(self, interaction, button):
        if self.selected_level is None or self.selected_role is None:
            return await interaction.response.send_message("❌ Түвшин болон роль сонгоно уу.", ephemeral=True)
        await self.cog.set_level_role(self.ctx.guild.id, self.selected_level, self.selected_role.id)
        await interaction.response.send_message(f"✅ Level {self.selected_level} → {self.selected_role.mention}", ephemeral=True)
        await self.refresh_message(interaction)
    @ui.button(label="🗑️ Устгах", style=discord.ButtonStyle.red, row=2)
    async def remove_btn(self, interaction, button):
        if self.selected_level is None: return await interaction.response.send_message("❌ Түвшин сонгоно уу.", ephemeral=True)
        await self.cog.delete_level_role(self.ctx.guild.id, self.selected_level)
        await interaction.response.send_message(f"🗑️ Level {self.selected_level} устгагдлаа.", ephemeral=True)
        await self.refresh_message(interaction)
    @ui.button(label="🎁 Шагнал", style=discord.ButtonStyle.blurple, row=3)
    async def reward_btn(self, interaction, button):
        view = LevelRewardManagerView(self.cog, self.ctx)
        embed = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

class LevelingSetupView(ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=600)
        self.cog = cog; self.ctx = ctx; self.message = None
    async def interaction_check(self, interaction):
        if interaction.user.id == interaction.guild.owner_id or interaction.user.id in self.cog.bot.config.get("co_owners",[]): return True
        await interaction.response.send_message("⛔ Сервер эзэмшигч эсвэл ботын co-owner эрх шаардлагатай.", ephemeral=True)
        return False
    async def refresh(self):
        cfg = await get_config(self.cog.bot.db, self.ctx.guild.id)
        embed = discord.Embed(title="🔧 Түвшний систем тохиргоо", color=INFO_COLOR)
        ch = self.ctx.guild.get_channel(cfg["announce_channel"]) if cfg["announce_channel"] else None
        embed.add_field(name="📢 Мэдэгдэл суваг", value=ch.mention if ch else "Тохируулаагүй", inline=False)
        embed.add_field(name="Систем идэвхтэй", value="✅" if cfg["enabled"] else "❌", inline=True)
        embed.add_field(name="Дуут XP", value="✅" if cfg["voice_xp_enabled"] else "❌", inline=True)
        embed.add_field(name="Cooldown (msg/react)", value=f"{cfg['msg_cooldown']}с / {cfg['react_cooldown']}с", inline=True)
        embed.add_field(name="Прогресс", value=f"{cfg['prog_type']} (base={cfg['prog_base']}, step={cfg['prog_step']})", inline=True)
        embed.add_field(name="Урилгын XP", value=str(cfg.get("invite_xp",0)), inline=True)
        embed.add_field(name="Гэрлэлтийн урамшуулал", value=f"{cfg.get('marriage_bonus',0.1)*100}%", inline=True)
        await self.message.edit(embed=embed, view=self)
    @ui.button(label="📢 Суваг сонгох", style=discord.ButtonStyle.secondary, row=0)
    async def channel_btn(self, interaction, button):
        opts = []
        for ch in interaction.guild.text_channels[:25]:
            opts.append(discord.SelectOption(label=f"#{ch.name}", value=str(ch.id)))
        if not opts: return await interaction.response.send_message("Сонгох суваг байхгүй.", ephemeral=True)
        class ChannelSelect(ui.Select):
            def __init__(self): super().__init__(placeholder="Мэдэгдэл сувгаа сонго...", options=opts)
            async def callback(self, inter):
                cfg = await get_config(self.view.cog.bot.db, self.view.ctx.guild.id)
                cfg["announce_channel"] = int(self.values[0])
                await set_config(self.view.cog.bot.db, self.view.ctx.guild.id, cfg)
                await inter.response.send_message("✅ Суваг тохируулагдлаа.", ephemeral=True)
                await self.view.refresh()
        view = ui.View(timeout=60); view.add_item(ChannelSelect())
        await interaction.response.send_message("Сувгаа сонгоно уу:", view=view, ephemeral=True)
    @ui.button(label="🔄 Систем унтраах/асаах", style=discord.ButtonStyle.primary, row=0)
    async def toggle_btn(self, interaction, button):
        cfg = await get_config(self.cog.bot.db, self.ctx.guild.id)
        cfg["enabled"] = not cfg["enabled"]
        await set_config(self.cog.bot.db, self.ctx.guild.id, cfg)
        await interaction.response.send_message(f"Систем {'ассан' if cfg['enabled'] else 'унтарсан'}.", ephemeral=True)
        await self.refresh()
    @ui.button(label="⏱ Cooldown тохируулах", style=discord.ButtonStyle.secondary, row=1)
    async def cd_btn(self, interaction, button):
        modal = ui.Modal(title="Cooldown (секунд)")
        msg_inp = ui.TextInput(label="Мессеж", placeholder="60", required=True)
        react_inp = ui.TextInput(label="Реакц", placeholder="10", required=True)
        modal.add_item(msg_inp); modal.add_item(react_inp)
        async def on_submit(inter):
            try:
                m = int(msg_inp.value); r = int(react_inp.value)
                if m<=0 or r<=0: raise ValueError
            except: return await inter.response.send_message("❌ Эерэг бүхэл тоо оруулна уу.", ephemeral=True)
            cfg = await get_config(self.cog.bot.db, self.ctx.guild.id)
            cfg["msg_cooldown"] = m; cfg["react_cooldown"] = r
            await set_config(self.cog.bot.db, self.ctx.guild.id, cfg)
            await inter.response.send_message("✅ Cooldown шинэчлэгдлээ.", ephemeral=True)
            await self.refresh()
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)
    @ui.button(label="🎨 Арын зураг URL", style=discord.ButtonStyle.secondary, row=1)
    async def bg_btn(self, interaction, button):
        modal = ui.Modal(title="Арын зураг")
        url_inp = ui.TextInput(label="Зургийн URL", placeholder="https://...", required=True)
        modal.add_item(url_inp)
        async def on_submit(inter):
            cfg = await get_config(self.cog.bot.db, self.ctx.guild.id)
            cfg["background_url"] = url_inp.value.strip()
            await set_config(self.cog.bot.db, self.ctx.guild.id, cfg)
            await inter.response.send_message("✅ Арын зураг тохируулагдлаа.", ephemeral=True)
            await self.refresh()
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)
    @ui.button(label="🎖️ Түвшний роль тохиргоо", style=discord.ButtonStyle.success, row=2)
    async def role_manager_btn(self, interaction, button):
        view = LevelRoleManagerView(self.cog, self.ctx)
        embed = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

# ================== MAIN COG ==================
class Leveling(SupabaseCog):
    def __init__(self, bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self._msg_cooldown = {}
        self._react_cooldown = {}
        self._voice_join = {}
        self._voice_last_xp = {}
        self.voice_task = None
        self.xp_drop_task = None

    async def cog_load(self):
        self.session = aiohttp.ClientSession()
        self.voice_task = asyncio.create_task(self._voice_xp_loop())
        self.xp_drop_task = self.xp_drop_loop.start()

    async def cog_unload(self):
        if self.voice_task: self.voice_task.cancel()
        if self.xp_drop_task: self.xp_drop_task.cancel()
        if self.session: await self.session.close()

    async def init_db(self):
        # Tables are pre-configured in Supabase
        pass

    def _on_cooldown(self, storage, user_id, seconds, guild_id=0):
        now = time.monotonic()
        key = (guild_id, user_id)
        last = storage.get(key, 0)
        if now - last < seconds: return True
        storage[key] = now
        return False

    async def get_active_buff(self, user_id, guild_id):
        mult = 1.0
        try:
            cafe = self.bot.get_cog("Cafe")
            if cafe:
                cfg = await get_config(self.db, guild_id)
                if cfg.get("cafe_buff_enabled", True) and hasattr(cafe, 'get_buff'):
                    buff = cafe.get_buff(user_id, guild_id)
                    if asyncio.iscoroutine(buff): buff = await buff
                    if buff and buff.get('type') == 'xp_boost': mult *= buff.get('xp_mult', 1.0)
        except: pass
        try:
            marriage = self.bot.get_cog("Marriage")
            if marriage and hasattr(marriage, 'get_married_bonus'):
                bonus = marriage.get_married_bonus(user_id, guild_id)
                if asyncio.iscoroutine(bonus): bonus = await bonus
                if bonus: mult *= (1 + bonus)
        except: pass
        return mult

    async def _add_xp(self, user_id, guild_id, amount, member=None, check_mute=True, channel=None):
        if amount == 0: return
        if member and check_mute:
            try:
                if member.timed_out_until and member.timed_out_until > datetime.now(timezone.utc): return
                if hasattr(member,'voice') and member.voice and (member.voice.mute or member.voice.self_mute): return
            except: pass
        if amount > 0:
            try:
                multiplier = await self.get_active_buff(user_id, guild_id)
                amount = int(amount * multiplier)
            except: pass
        row = await self.bot.db_manager.fetch_one(
            "levels", {"user_id": str(user_id), "guild_id": str(guild_id)}
        )
        xp, level = (row.get("xp", 0) or 0, row.get("level", 1) or 1) if row else (0, 1)
        old_level = level
        new_xp = xp + amount
        cfg = await get_config(self.db, guild_id)
        leveled_up = False
        while new_xp < 0 and level > 1:
            level -= 1
            new_xp += xp_for_level(level, cfg)
        if new_xp < 0:
            new_xp = 0
        while True:
            needed = xp_for_level(level, cfg)
            if new_xp >= needed:
                new_xp -= needed; level += 1; leveled_up = True
            else: break
        await self.bot.db_manager.upsert(
            "levels",
            {"user_id": str(user_id), "guild_id": str(guild_id), "xp": new_xp, "level": level},
            on_conflict="user_id,guild_id",
        )
        if leveled_up and member:
            await self._announce_level_up(member, old_level, level, new_xp, channel)
            try:
                quests = self.bot.get_cog("Quests")
                if quests and hasattr(quests,'trigger_event'): await quests.trigger_event(member.id, guild_id, "level_up", 1)
            except: pass

    async def _announce_level_up(self, member, old, new, current_xp, source_channel):
        guild = member.guild
        cfg = await get_config(self.bot.db, guild.id)
        # Level reward
        try:
            reward_row = await self.bot.db_manager.fetch_one(
                "level_rewards", {"guild_id": str(guild.id), "level": new}
            )
            if reward_row and (reward_row.get("money", 0) or 0) > 0:
                economy = self.bot.get_cog("Economy")
                if economy:
                    await economy.update_balance(member.id, guild.id, reward_row["money"])
                    embed = discord.Embed(title="🎁 Түвшний шагнал!", description=f"{member.mention} Lv.{new} хүрсэн тул **{reward_row['money']:,}₮** авлаа!", color=GOLD_COLOR)
                    ch = guild.get_channel(cfg.get("announce_channel")) if cfg.get("announce_channel") else source_channel
                    if ch:
                        try: await ch.send(embed=embed)
                        except: pass
        except: pass
        # Level role
        try:
            role_row = await self.bot.db_manager.fetch_one(
                "level_roles", {"guild_id": str(guild.id), "level": new}
            )
            if role_row:
                role = guild.get_role(role_row.get("role_id"))
                if role and role not in member.roles: await member.add_roles(role, reason=f"Level {new}")
        except: pass
        channel = guild.get_channel(cfg.get("announce_channel")) if cfg.get("announce_channel") else source_channel
        if not channel: return
        needed = xp_for_level(new, cfg)
        rank_pos = await self.get_rank_position(member.id, guild.id)
        try:
            buf = await render_dlc_card(member, new, current_xp, needed, rank_pos, cfg.get("background_url"))
            if buf:
                file = discord.File(buf, filename="levelup.png")
                try: await channel.send(content=member.mention, file=file)
                except: pass
            else:
                embed = discord.Embed(title="🎉 Түвшин ахисан!", description=f"{member.mention} Lv.{new} хүрлээ!", color=GOLD_COLOR)
                try: await channel.send(embed=embed)
                except: pass
        except Exception as e: log.error(f"Level up announcement: {e}")

    # ========== PUBLIC API ==========
    async def add_xp(self, user_id, guild_id, amount, member=None, check_mute=True, channel=None):
        await self._add_xp(user_id, guild_id, amount, member, check_mute, channel)
    async def remove_xp(self, user_id, guild_id, amount, member=None):
        await self._add_xp(user_id, guild_id, -amount, member, check_mute=False)
    async def transfer_xp(self, from_id, to_id, guild_id, amount):
        if await self.get_total_xp(from_id, guild_id) < amount: return False
        await self._add_xp(from_id, guild_id, -amount); await self._add_xp(to_id, guild_id, amount)
        return True
    async def get_total_xp(self, user_id, guild_id):
        row = await self.bot.db_manager.fetch_one(
            "levels", {"user_id": str(user_id), "guild_id": str(guild_id)}
        )
        if not row: return 0
        xp = row.get("xp", 0) or 0
        level = row.get("level", 1) or 1
        cfg = await get_config(self.db, guild_id)
        return sum(xp_for_level(l,cfg) for l in range(level)) + xp
    async def get_level(self, user_id, guild_id):
        row = await self.bot.db_manager.fetch_one(
            "levels", {"user_id": str(user_id), "guild_id": str(guild_id)}
        )
        return row.get("level", 1) if row else 1
    async def get_rank_position(self, user_id, guild_id):
        rows = await self.bot.db_manager.fetch_all(
            "levels", {"guild_id": str(guild_id)},
            order_by="level", desc=True,
        )
        rows.sort(key=lambda r: (r.get("level", 0) or 0, r.get("xp", 0) or 0), reverse=True)
        for i, r in enumerate(rows):
            if int(r.get("user_id")) == int(user_id): return i+1
        return len(rows)+1
    async def set_xp(self, user_id, guild_id, xp):
        cfg = await get_config(self.db, guild_id)
        level = 1; remaining = xp
        while True:
            needed = xp_for_level(level, cfg)
            if remaining >= needed: remaining -= needed; level += 1
            else: break
        await self.bot.db_manager.upsert(
            "levels",
            {"user_id": str(user_id), "guild_id": str(guild_id), "xp": remaining, "level": level},
            on_conflict="user_id,guild_id",
        )
    async def set_level(self, user_id, guild_id, level):
        await self.bot.db_manager.upsert(
            "levels",
            {"user_id": str(user_id), "guild_id": str(guild_id), "xp": 0, "level": level},
            on_conflict="user_id,guild_id",
        )

    async def get_config(self, guild_id):
        return await get_config(self.bot.db, guild_id)
    def xp_for_level(self, level, cfg):
        return xp_for_level(level, cfg)
    def get_rank_info(self, level):
        if level < 10: return "Эхлэгч", "🌱"
        if level < 25: return "Сонирхогч", "⭐"
        if level < 50: return "Мэргэжилтэн", "🌟"
        if level < 100: return "Мастер", "💎"
        return "Домог", "👑"

    async def award_invite_xp(self, inviter_id, guild_id):
        cfg = await get_config(self.db, guild_id)
        xp_reward = cfg.get("invite_xp", 0)
        if xp_reward > 0:
            guild = self.bot.get_guild(guild_id)
            member = guild.get_member(inviter_id) if guild else None
            await self._add_xp(inviter_id, guild_id, xp_reward, member=member)

    async def get_exceptions(self, guild_id):
        rows = await self.bot.db_manager.fetch_all(
            "leveling_exceptions", {"guild_id": str(guild_id)}
        )
        return {"channels":[r["target_id"] for r in rows if r.get("type")=="channel"],
                "users":[r["target_id"] for r in rows if r.get("type")=="user"]}
    async def add_exception(self, guild_id, exc_type, target_id):
        await self.bot.db_manager.upsert(
            "leveling_exceptions",
            {"guild_id": str(guild_id), "type": exc_type, "target_id": target_id},
            on_conflict="guild_id,type,target_id",
        )
    async def remove_exception(self, guild_id, exc_type, target_id):
        await self.bot.db_manager.delete(
            "leveling_exceptions",
            {"guild_id": str(guild_id), "type": exc_type, "target_id": target_id},
        )

    async def get_level_roles(self, guild_id):
        rows = await self.bot.db_manager.fetch_all(
            "level_roles", {"guild_id": str(guild_id)}, order_by="level"
        )
        return [{"level": r["level"], "role_id": r["role_id"]} for r in rows]
    async def set_level_role(self, guild_id, level, role_id):
        await self.bot.db_manager.upsert(
            "level_roles",
            {"guild_id": str(guild_id), "level": level, "role_id": role_id},
            on_conflict="guild_id,level",
        )
    async def delete_level_role(self, guild_id, level):
        await self.bot.db_manager.delete(
            "level_roles", {"guild_id": str(guild_id), "level": level}
        )

    async def get_level_rewards(self, guild_id):
        rows = await self.bot.db_manager.fetch_all(
            "level_rewards", {"guild_id": str(guild_id)}, order_by="level"
        )
        return [{"level": r["level"], "money": r["money"]} for r in rows]
    async def set_level_reward(self, guild_id, level, money):
        await self.bot.db_manager.upsert(
            "level_rewards",
            {"guild_id": str(guild_id), "level": level, "money": money},
            on_conflict="guild_id,level",
        )
    async def delete_level_reward(self, guild_id, level):
        await self.bot.db_manager.delete(
            "level_rewards", {"guild_id": str(guild_id), "level": level}
        )

    # ========== EVENT LISTENERS ==========
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot: return
        cfg = await get_config(self.bot.db, message.guild.id)
        if not cfg["enabled"]: return
        exc = await self.get_exceptions(message.guild.id)
        if message.channel.id in exc["channels"] or message.author.id in exc["users"]: return
        if self._on_cooldown(self._msg_cooldown, message.author.id, cfg["msg_cooldown"], message.guild.id): return
        xp = xp_for_message(message.content, cfg)
        if message.attachments: xp += cfg["xp_media"]
        await self._add_xp(message.author.id, message.guild.id, xp, member=message.author, channel=message.channel)
        try:
            lvl_row = await self.bot.db_manager.fetch_one(
                "levels", {"user_id": str(message.author.id), "guild_id": str(message.guild.id)}
            )
            if lvl_row:
                await self.bot.db_manager.update(
                    "levels",
                    {"user_id": str(message.author.id), "guild_id": str(message.guild.id)},
                    {"message_count": (lvl_row.get("message_count", 0) or 0) + 1},
                )
            else:
                await self.bot.db_manager.insert("levels", {
                    "user_id": str(message.author.id), "guild_id": str(message.guild.id), "message_count": 1,
                })
        except: pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.guild_id or payload.user_id == self.bot.user.id: return
        cfg = await get_config(self.bot.db, payload.guild_id)
        if not cfg["enabled"]: return
        exc = await self.get_exceptions(payload.guild_id)
        if payload.channel_id in exc["channels"] or payload.user_id in exc["users"]: return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        member = guild.get_member(payload.user_id)
        if not member or member.bot: return
        if self._on_cooldown(self._react_cooldown, payload.user_id, cfg["react_cooldown"], payload.guild_id): return
        await self._add_xp(payload.user_id, payload.guild_id, cfg["xp_reaction"], member=member, check_mute=False)
        try:
            lvl_row = await self.bot.db_manager.fetch_one(
                "levels", {"user_id": str(payload.user_id), "guild_id": str(payload.guild_id)}
            )
            if lvl_row:
                await self.bot.db_manager.update(
                    "levels",
                    {"user_id": str(payload.user_id), "guild_id": str(payload.guild_id)},
                    {"reaction_count": (lvl_row.get("reaction_count", 0) or 0) + 1},
                )
            else:
                await self.bot.db_manager.insert("levels", {
                    "user_id": str(payload.user_id), "guild_id": str(payload.guild_id), "reaction_count": 1,
                })
        except: pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel and not after.channel:
            key = (member.guild.id, member.id)
            self._voice_join.pop(key, None); self._voice_last_xp.pop(key, None)

    async def _voice_xp_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                now = time.monotonic()
                for guild in self.bot.guilds:
                    cfg = await get_config(self.bot.db, guild.id)
                    if not cfg["enabled"] or not cfg.get("voice_xp_enabled",True): continue
                    exc = await self.get_exceptions(guild.id)
                    for vc in guild.voice_channels:
                        for member in vc.members:
                            if member.bot or member.id in exc["users"] or member.voice.deaf or member.voice.self_deaf: continue
                            key = (guild.id, member.id)
                            if key not in self._voice_join: self._voice_join[key] = now; self._voice_last_xp[key] = now
                            if now - self._voice_last_xp.get(key,0) >= VOICE_INTERVAL_SECS:
                                talking = not (member.voice.mute or member.voice.self_mute)
                                xp = cfg["xp_voice_talking"] if talking else cfg["xp_voice_silent"]
                                self._voice_last_xp[key] = now
                                await self._add_xp(member.id, guild.id, xp, member=member, check_mute=False)
                                try:
                                    lvl_row = await self.bot.db_manager.fetch_one(
                                        "levels", {"user_id": str(member.id), "guild_id": str(guild.id)}
                                    )
                                    if lvl_row:
                                        await self.bot.db_manager.update(
                                            "levels",
                                            {"user_id": str(member.id), "guild_id": str(guild.id)},
                                            {"voice_seconds": (lvl_row.get("voice_seconds", 0) or 0) + VOICE_INTERVAL_SECS},
                                        )
                                    else:
                                        await self.bot.db_manager.insert("levels", {
                                            "user_id": str(member.id), "guild_id": str(guild.id), "voice_seconds": VOICE_INTERVAL_SECS,
                                        })
                                except: pass
            except Exception as e: log.error(f"Voice XP loop: {e}")
            await asyncio.sleep(30)

    @tasks.loop(minutes=1)
    async def xp_drop_loop(self):
        for guild in self.bot.guilds:
            try:
                cfg = await get_config(self.bot.db, guild.id)
                if not cfg["xp_drop_enabled"]: continue
                channel = guild.get_channel(cfg["xp_drop_channel"])
                if not channel: continue
                if random.random() < 0.1:
                    xp = random.randint(cfg["xp_drop_min"], cfg["xp_drop_max"])
                    embed = discord.Embed(title="🌟 XP DROP!", description=f"Түргэн! Дараагийн товчийг дарж **{xp} XP** аваарай!", color=GOLD_COLOR)
                    view = XPDropView(xp, self)
                    await channel.send(embed=embed, view=view)
            except Exception as e: log.error(f"XP drop: {e}")

    @xp_drop_loop.before_loop
    async def before_xp_drop_loop(self): await self.bot.wait_until_ready()

    # ========== COMMANDS ==========
    @commands.hybrid_command(name="grank", aliases=["rank","lvl"])
    async def grank(self, ctx, user: discord.Member = None):
        target = user or ctx.author
        await ctx.defer()
        total_xp = await self.get_total_xp(target.id, ctx.guild.id)
        level = await self.get_level(target.id, ctx.guild.id)
        cfg = await get_config(self.bot.db, ctx.guild.id)
        xp_in_level = total_xp - sum(xp_for_level(l,cfg) for l in range(level))
        needed = xp_for_level(level, cfg)
        rank = await self.get_rank_position(target.id, ctx.guild.id)
        try:
            buf = await render_dlc_card(target, level, xp_in_level, needed, rank, cfg.get("background_url"))
            if buf:
                file = discord.File(buf, filename="rank.png")
                embed = discord.Embed(color=0x7289da)
                embed.set_image(url="attachment://rank.png")
                embed.set_footer(text=f"Rank #{rank}  •  Total XP: {total_xp:,}")
                await ctx.send(embed=embed, file=file)
            else:
                embed = discord.Embed(title=f"📊 {target.display_name}", description=f"**Level:** {level}\n**XP:** {xp_in_level}/{needed}\n**Rank:** #{rank}", color=0x7289da)
                embed.set_footer(text=f"Total XP: {total_xp:,}")
                await ctx.send(embed=embed)
        except Exception as e: await ctx.send(f"❌ Rank карт үүсгэхэд алдаа гарлаа: {e}", ephemeral=True)

    # ========== NEW: Server Activity Command ==========
    @commands.hybrid_command(name="serveractivity", aliases=["activity"])
    async def server_activity(self, ctx):
        """Серверийн идэвхтэй байдлыг харах"""
        guild = ctx.guild
        online = sum(1 for m in guild.members if m.status != discord.Status.offline)
        offline = guild.member_count - online
        voice_count = sum(1 for vc in guild.voice_channels for m in vc.members)

        # Message count from database (all-time active chatters)
        active_chatters = 0
        try:
            lvl_rows = await self.bot.db_manager.fetch_all(
                "levels", {"guild_id": str(guild.id)}
            )
            active_chatters = sum(1 for r in lvl_rows if (r.get("message_count", 0) or 0) > 0)
        except: pass

        embed = discord.Embed(title=f"📈 {guild.name} - Server Activity", color=SUCCESS_COLOR)
        embed.add_field(name="👥 Members", value=f"Total: {guild.member_count}\nOnline: {online}\nOffline: {offline}")
        embed.add_field(name="🔊 Voice", value=f"Currently in VC: {voice_count}")
        embed.add_field(name="💬 Text Chatters (all-time)", value=active_chatters)
        embed.set_footer(text="Note: Text chatters count is all-time, not 24h. To get 24h stats, add a last_message_time column.")
        await ctx.send(embed=embed)

    async def _is_allowed(self, user):
        try:
            cfg = self.bot.config
            return user.id == cfg.get("owner_id") or user.id in cfg.get("co_owners",[])
        except: return False

    @commands.command(name="addxp")
    async def addxp_cmd(self, ctx, user: discord.Member, amount: int):
        if not await self._is_allowed(ctx.author): return await ctx.send("⛔ Зөвхөн бот эзэмшигч эсвэл co-owner ашиглах боломжтой.", ephemeral=True)
        if amount <= 0: return await ctx.send("❌ Эерэг тоо оруулна уу.", ephemeral=True)
        await self._add_xp(user.id, ctx.guild.id, amount, member=user, check_mute=False)
        await ctx.send(f"✅ {user.display_name}-д {amount} XP нэмлээ.")

    @commands.command(name="removexp")
    async def removexp_cmd(self, ctx, user: discord.Member, amount: int):
        if not await self._is_allowed(ctx.author): return await ctx.send("⛔ Зөвхөн бот эзэмшигч эсвэл co-owner ашиглах боломжтой.", ephemeral=True)
        if amount <= 0: return await ctx.send("❌ Эерэг тоо оруулна уу.", ephemeral=True)
        await self._add_xp(user.id, ctx.guild.id, -amount, member=user, check_mute=False)
        await ctx.send(f"✅ {user.display_name}-ээс {amount} XP хасагдлаа.")

    @commands.command(name="leveling_setup", aliases=["lsetup"])
    async def leveling_setup(self, ctx):
        if not (ctx.author.guild_permissions.administrator or await self._is_allowed(ctx.author)):
            return await ctx.send("⛔ Админ эрх шаардлагатай.", ephemeral=True)
        cfg = await get_config(self.bot.db, ctx.guild.id)
        embed = discord.Embed(title="🔧 Түвшний систем тохиргоо", color=INFO_COLOR)
        ch = ctx.guild.get_channel(cfg["announce_channel"]) if cfg["announce_channel"] else None
        embed.add_field(name="📢 Мэдэгдэл суваг", value=ch.mention if ch else "Тохируулаагүй", inline=False)
        embed.add_field(name="Систем идэвхтэй", value="✅" if cfg["enabled"] else "❌", inline=True)
        embed.add_field(name="Дуут XP", value="✅" if cfg["voice_xp_enabled"] else "❌", inline=True)
        embed.add_field(name="Cooldown (msg/react)", value=f"{cfg['msg_cooldown']}с / {cfg['react_cooldown']}с", inline=True)
        embed.add_field(name="Прогресс", value=f"{cfg['prog_type']} (base={cfg['prog_base']}, step={cfg['prog_step']})", inline=True)
        embed.add_field(name="Урилгын XP", value=str(cfg.get("invite_xp",0)), inline=True)
        embed.add_field(name="Гэрлэлтийн урамшуулал", value=f"{cfg.get('marriage_bonus',0.1)*100}%", inline=True)
        view = LevelingSetupView(self, ctx)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

async def setup(bot):
    await bot.add_cog(Leveling(bot))
