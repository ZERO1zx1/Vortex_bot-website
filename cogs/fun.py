import discord
from discord.ext import commands
import random
import os
import aiohttp
from typing import Optional

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # gifs хавтас assets/gifs/ замд байх ёстой
        self.gifs_base = os.path.abspath("./assets/gifs")

    def _get_random_gif(self, action: str):
        """Тухайн үйлдлийн хавтсаас санамсаргүй .gif файл буцаана"""
        folder = os.path.join(self.gifs_base, action)
        if not os.path.isdir(folder):
            return None
        try:
            files = [f for f in os.listdir(folder) if f.endswith(".gif")]
        except OSError:
            return None
        if not files:
            return None
        filepath = os.path.join(folder, random.choice(files))
        return discord.File(filepath, filename=f"{action}.gif")

    async def _send_action(self, ctx, action: str, texts: list, title: str, color, target: discord.Member = None):
        """Текст болон (боломжтой бол) гифтэй embed илгээх"""
        gif = self._get_random_gif(action)
        embed = discord.Embed(
            title=title,
            description=random.choice(texts),
            color=color
        )
        embed.set_footer(text=str(ctx.author), icon_url=ctx.author.display_avatar.url)

        # Даалгаврын системд мэдэгдэх
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "fun_command", 1)

        if gif:
            embed.set_image(url=f"attachment://{action}.gif")
            await ctx.send(embed=embed, file=gif)
        else:
            await ctx.send(embed=embed)

    # ==================== ҮНДСЭН ====================
    @commands.command(name='ping')
    async def ping(self, ctx):
        embed = discord.Embed(title="🏓 Pong!", description=f"Пинг: {round(self.bot.latency * 1000)} ms", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(name='avatar', aliases=['av'])
    async def avatar(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        embed = discord.Embed(title=f"🖼️ {target.display_name} - ИЙН АВАТААР", color=discord.Color.blue())
        embed.set_image(url=target.display_avatar.url)
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ==================== ЛОКАЛ ГИФ ХАЙЛТ ====================
    @commands.command(name='gif')
    async def gif_local(self, ctx, *, query: str = None):
        """assets/gifs/ доторх .gif файлуудаас хайлт хийх"""
        gifs_folder = self.gifs_base

        if not os.path.isdir(gifs_folder):
            return await ctx.send("❌ `assets/gifs/` хавтас олдсонгүй. Та эхлээд хавтас үүсгэж, .gif файлууд хийх хэрэгтэй.")

        if query is None:
            # Санамсаргүй .gif
            all_gifs = []
            for root, dirs, files in os.walk(gifs_folder):
                for f in files:
                    if f.endswith(".gif"):
                        all_gifs.append(os.path.join(root, f))
            if not all_gifs:
                return await ctx.send("❌ Ямар ч гиф олдсонгүй. `assets/gifs/` хавтас хоосон байна.")
            gif_path = random.choice(all_gifs)
        else:
            # Хайлт
            query_lower = query.lower()
            matched = []
            for root, dirs, files in os.walk(gifs_folder):
                for f in files:
                    if f.endswith(".gif") and query_lower in f.lower():
                        matched.append(os.path.join(root, f))
            # Хэрэв олдохгүй бол хавтасны нэрээр хайх
            if not matched:
                for folder in os.listdir(gifs_folder):
                    if query_lower in folder.lower():
                        folder_path = os.path.join(gifs_folder, folder)
                        if os.path.isdir(folder_path):
                            for f in os.listdir(folder_path):
                                if f.endswith(".gif"):
                                    matched.append(os.path.join(folder_path, f))
            if not matched:
                return await ctx.send(f"❌ `{query}` гэсэн гиф олдсонгүй.")
            gif_path = random.choice(matched)

        file = discord.File(gif_path, filename=os.path.basename(gif_path))
        embed = discord.Embed(title=f"🔍 Гиф: {query or 'Санамсаргүй'}", color=0x00ffff)
        embed.set_image(url=f"attachment://{os.path.basename(gif_path)}")
        await ctx.send(embed=embed, file=file)

    # ==================== БУСАД ХӨГЖИЛТЭЙ ====================
    @commands.command(name='meme')
    async def meme(self, ctx):
        subreddits = ['memes', 'dankmemes', 'meirl', 'ProgrammerHumor']
        sub = random.choice(subreddits)
        async with aiohttp.ClientSession() as sess:
            try:
                url = f"https://meme-api.com/gimme/{sub}"
                async with sess.get(url) as resp:
                    if resp.status != 200:
                        return await ctx.send("❌ Мийм татаж чадсангүй.")
                    data = await resp.json()
                    embed = discord.Embed(title=data['title'], url=data['postLink'], color=0x00ff00)
                    embed.set_image(url=data['url'])
                    embed.set_footer(text=f"👍 {data['ups']} | r/{data['subreddit']}")
                    await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send("❌ Мийм татахад алдаа гарлаа.")

    @commands.command(name='coin')
    async def coin(self, ctx):
        result = random.choice(["🧴", "🦁"])
        await ctx.send(f"🪙 {ctx.author.mention} зоос шидэв... **{result}**!")

    @commands.command(name='roll')
    async def roll(self, ctx, maximum: Optional[int] = 6):
        if maximum < 1:
            maximum = 6
        result = random.randint(1, maximum)
        await ctx.send(f"🎲 {ctx.author.mention} шоо хаяв: **{result}** (1-{maximum})")

    @commands.command(name='8ball')
    async def eightball(self, ctx, *, question: str):
        answers = [
            "Тийм.", "Үгүй.", "Магадгүй.", "Эргэлзээтэй.",
            "Мэдээж.", "Тодорхойгүй.", "Тийм байх.", "Үгүй байх."
        ]
        await ctx.send(f"🎱 {ctx.author.mention} асуув: *{question}*\n**Хариулт:** {random.choice(answers)}")

    @commands.command(name='dog')
    async def dog(self, ctx):
        async with aiohttp.ClientSession() as sess:
            try:
                async with sess.get("https://dog.ceo/api/breeds/image/random") as resp:
                    data = await resp.json()
                    embed = discord.Embed(title="🐶 Сайн уу нохой!", color=0xffcc00)
                    embed.set_image(url=data['message'])
                    await ctx.send(embed=embed)
            except:
                await ctx.send("❌ Нохойн зураг авахад алдаа гарлаа.")

    @commands.command(name='cat')
    async def cat(self, ctx):
        async with aiohttp.ClientSession() as sess:
            try:
                async with sess.get("https://api.thecatapi.com/v1/images/search") as resp:
                    data = await resp.json()
                    if data:
                        embed = discord.Embed(title="🐱 Мяав!", color=0xff69b4)
                        embed.set_image(url=data[0]['url'])
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("❌ Муур олдсонгүй.")
            except:
                await ctx.send("❌ Муурны зураг авахад алдаа гарлаа.")

    @commands.command(name='fox')
    async def fox(self, ctx):
        async with aiohttp.ClientSession() as sess:
            try:
                async with sess.get("https://randomfox.ca/floof/") as resp:
                    data = await resp.json()
                    embed = discord.Embed(title="🦊 Үнэг ирлээ!", color=0xff6600)
                    embed.set_image(url=data['image'])
                    await ctx.send(embed=embed)
            except:
                await ctx.send("❌ Үнэгний зураг авахад алдаа гарлаа.")

    # ==================== ACTION COMMANDS ====================
    @commands.command(name='hug')
    async def hug(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} өөрийгөө тэврээд ганцаардалтайгаа зуурав..."]
            return await self._send_action(ctx, "hug", msgs, "🫂 ГАНЦААРДАЛ", discord.Color.orange())
        if target == ctx.author:
            msgs = [f"{ctx.author.mention} өөрийгөө тэврэв. Өөртөө хайртай байх нь чухал!"]
            return await self._send_action(ctx, "hug", msgs, "🫂 ӨӨРТЭЭ ТЭВРЭЛТ", discord.Color.green())
        texts = [f"{ctx.author.mention} {target.mention} -г чанга тэврэв! 🥰",
                 f"{ctx.author.mention} {target.mention} -г бүслэн тэврээд, дулаан мэдрэмж түгээв."]
        await self._send_action(ctx, "hug", texts, "🫂 **ТЭВРЭЛТ** 🤗", discord.Color.green(), target)

    @commands.command(name='kiss')
    async def kiss(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} агаар үнсэж, хэн нэгнийг хайрлахыг хүсэв..."]
            return await self._send_action(ctx, "kiss", msgs, "💋 ХҮСЭЛ", discord.Color.purple())
        if target == ctx.author:
            embed = discord.Embed(title="💋 ӨӨРТЭЭ ҮНСЭЛТ", description=f"{ctx.author.mention} өөрийгөө үнсэхийг оролдсон ч бие нь үгүйсгэв. 😅", color=discord.Color.purple())
            return await ctx.send(embed=embed)
        texts = [f"{ctx.author.mention} {target.mention} -г хацар дээр нь үнсэв! 😳💖"]
        await self._send_action(ctx, "kiss", texts, "💋 **ҮНСЭЛТ** 💏", discord.Color.magenta(), target)

    @commands.command(name='slap')
    async def slap(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} агаарыг цохив. Чи хүчтэй байна!"]
            return await self._send_action(ctx, "slap", msgs, "👋 АГААР ЦОХИХ", discord.Color.orange())
        if target == ctx.author:
            embed = discord.Embed(title="👋 ӨӨРИЙГӨӨ ЦОХИХ", description=f"{ctx.author.mention} өөрийгөө цохиод, 'Анхаар!' гэж хашгирав.", color=discord.Color.red())
            return await ctx.send(embed=embed)
        texts = [f"{ctx.author.mention} {target.mention} -г чанга цохив! 😖"]
        await self._send_action(ctx, "slap", texts, "👋 **АЛГАДАЛТ** 😖", discord.Color.red(), target)

    @commands.command(name='pat')
    async def pat(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} агаарыг илбэв. Хэн нэгэн ирээсэй гэж бодож байна."]
            return await self._send_action(ctx, "pat", msgs, "🫳 АГААР ИЛЭХ", discord.Color.blue())
        if target == ctx.author:
            embed = discord.Embed(title="🫳 ӨӨРТЭЭ ХҮРЭХ", description=f"{ctx.author.mention} өөрийн толгойг илбэв.", color=discord.Color.blue())
            return await ctx.send(embed=embed)
        texts = [f"{ctx.author.mention} {target.mention} -н толгойд энхрийлэн хүрэв! 'Сайн байна уу?'"]
        await self._send_action(ctx, "pat", texts, "🫳 **ТОЛГОЙД ХҮРЭХ** 🌟", discord.Color.gold(), target)

    @commands.command(name='cuddle')
    async def cuddle(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} дэрэнгүйгээр зуурав. Ганцаардал их байна уу?"]
            return await self._send_action(ctx, "cuddle", msgs, "🤗 ГАНЦААРДАЛ", discord.Color.orange())
        if target == ctx.author:
            embed = discord.Embed(title="🤗 ӨӨРИЙГӨӨ БҮСЛЭХ", description=f"{ctx.author.mention} өөрийн биеийг бүслэн зуурав.", color=discord.Color.green())
            return await ctx.send(embed=embed)
        texts = [f"{ctx.author.mention} {target.mention} -г бүслэн зуурав! Тайвшруулах сайхан мэдрэмж."]
        await self._send_action(ctx, "cuddle", texts, "🤗 **ЗУУРАЛТ** 🛋️", discord.Color.teal(), target)

    @commands.command(name='bite')
    async def bite(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} агаарыг хазав... Амт нь юу ч биш."]
            return await self._send_action(ctx, "bite", msgs, "🦷 АГААР ХАЗАХ", discord.Color.orange())
        if target == ctx.author:
            embed = discord.Embed(title="🦷 ӨӨРИЙГӨӨ ХАЗАХ", description=f"{ctx.author.mention} өөрийн гараа хазаад, 'Ай!' гэв.", color=discord.Color.red())
            return await ctx.send(embed=embed)
        texts = [f"{ctx.author.mention} {target.mention} -г зөөлөн хазав! 'Тоглоом шүү'"]
        await self._send_action(ctx, "bite", texts, "🦷 **ХАЗАЛТ** 🐺", discord.Color.orange(), target)

    @commands.command(name='poke')
    async def poke(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} агаарыг хатгав. Хэнийг хатгахаа мэдэхгүй байна."]
            return await self._send_action(ctx, "poke", msgs, "👉 АГААР ХАТГАХ", discord.Color.blue())
        if target == ctx.author:
            embed = discord.Embed(title="👉 ӨӨРИЙГӨӨ ХАТГАХ", description=f"{ctx.author.mention} өөрийгөө хатгаад, 'Өө!' гэж хашгирав.", color=discord.Color.blue())
            return await ctx.send(embed=embed)
        texts = [f"{ctx.author.mention} {target.mention} -г хатгав! 'Хөөе, анхаар!'"]
        await self._send_action(ctx, "poke", texts, "👉 **ХАТГАЛТ** 🖕(биш)", discord.Color.green(), target)

    @commands.command(name='wave')
    async def wave(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} чиглэлгүй далавчлав. Хариу ирэхгүй нь харамсалтай."]
            return await self._send_action(ctx, "wave", msgs, "👋 ГАНЦААР ДАЛАВЧЛАХ", discord.Color.blue())
        texts = [f"{ctx.author.mention} {target.mention} -д далавчлав! {target.mention} бас далавчлав."]
        await self._send_action(ctx, "wave", texts, "👋 **ДАЛАВЧЛАЛТ** 🙋", discord.Color.green(), target)

    @commands.command(name='punch')
    async def punch(self, ctx, target: discord.Member = None):
        if not target:
            msgs = [f"{ctx.author.mention} агаарт нударгаа савлаж, хүчээ харуулав."]
            return await self._send_action(ctx, "punch", msgs, "👊 АГААР ЦОХИХ", discord.Color.orange())
        if target == ctx.author:
            embed = discord.Embed(title="👊 ӨӨРИЙГӨӨ ЦОХИХ", description=f"{ctx.author.mention} өөрийн цээжийг цохиод, 'Би хүчтэй!' гэв.", color=discord.Color.red())
            return await ctx.send(embed=embed)
        texts = [f"{ctx.author.mention} {target.mention} -г нударгаар цохив! 'Болгоомжтой бай!'"]
        await self._send_action(ctx, "punch", texts, "👊 **НУДАРГЫН ЦОХИЛТ** 💢", discord.Color.red(), target)

    @commands.command(name='boop')
    async def boop(self, ctx, target: discord.Member = None):
        if not target:
            embed = discord.Embed(title="👆 АГААР БУП", description=f"{ctx.author.mention} агаарыг буп хийв. Хариу үйлдэл гараагүй.", color=discord.Color.blue())
            return await ctx.send(embed=embed)
        texts = [f"{ctx.author.mention} {target.mention} -н хамарыг буп хийв! 'Буп!'"]
        await self._send_action(ctx, "boop", texts, "👆 **БУП** 🐶", discord.Color.green(), target)

    @commands.command(name='bully')
    async def bully(self, ctx, target: discord.Member = None):
        if not target:
            embed = discord.Embed(title="😈 БУЛИМДАХГҮЙ", description=f"{ctx.author.mention} хэнийг ч булимдахгүй байхаар шийдлээ. Сайн сонголт!", color=discord.Color.green())
            return await ctx.send(embed=embed)
        if target == ctx.author:
            embed = discord.Embed(title="😈 ӨӨРТЭЭ БУЛИМДАХ", description=f"{ctx.author.mention} өөрийгөө булимдахад, 'Би хангалттай сайн' гэж хэлэв.", color=discord.Color.orange())
            return await ctx.send(embed=embed)
        texts = [f"{ctx.author.mention} {target.mention} -г 'Чи чадахгүй ээ!' гэж булимдав."]
        await self._send_action(ctx, "bully", texts, "😈 **БУЛИМДАЛТ** 😠", discord.Color.red(), target)

    @commands.command(name='handhold')
    async def handhold(self, ctx, target: discord.Member = None):
        if not target:
            embed = discord.Embed(title="🤝 ӨӨРТЭЙГЭЭ ГАР БАРИХ", description=f"{ctx.author.mention} өөрийн гараа атгаад, 'Би өөртөө итгэдэг' гэв.", color=discord.Color.blue())
            return await ctx.send(embed=embed)
        if target == ctx.author:
            embed = discord.Embed(title="🤝 ХОЁР ГАР БАРИХ", description=f"{ctx.author.mention} хоёр гараа нийлүүлэн барьж, өөртэйгөө эвлэрэв.", color=discord.Color.green())
            return await ctx.send(embed=embed)
        texts = [f"{ctx.author.mention} {target.mention} -тай гар барьж, найз боллоо! 🤝"]
        await self._send_action(ctx, "handhold", texts, "🤝 **ГАР БАРИЛТ** 👫", discord.Color.teal(), target)

    @commands.command(name='stare')
    async def stare(self, ctx, target: discord.Member = None):
        if not target:
            embed = discord.Embed(title="👀 АГААР ХАРАХ", description=f"{ctx.author.mention} цонхоор харж, сэтгэл бодолд автлаа.", color=discord.Color.blue())
            return await ctx.send(embed=embed)
        texts = [f"{ctx.author.mention} {target.mention} -г ширтэн харж, нүдээ анихгүй байв."]
        await self._send_action(ctx, "stare", texts, "👀 **ХАРАЛТ** 🔍", discord.Color.purple(), target)

    @commands.command(name='highfive')
    async def highfive(self, ctx, target: discord.Member = None):
        if not target:
            embed = discord.Embed(title="🙌 ГАНЦААР ӨНДӨР ТАВИХ", description=f"{ctx.author.mention} агаарт алга ташив.", color=discord.Color.blue())
            return await ctx.send(embed=embed)
        if target == ctx.author:
            embed = discord.Embed(title="🙌 ӨӨРТЭЭ ӨНДӨР ТАВИХ", description=f"{ctx.author.mention} өөрийн гараараа өндөр тавив.", color=discord.Color.green())
            return await ctx.send(embed=embed)
        texts = [f"{ctx.author.mention} {target.mention} -тай алга харилцан өндөр тавив! 'Ерөөл!'"]
        await self._send_action(ctx, "highfive", texts, "🙌 **ӨНДӨР ТАВИЛТ** 🖐️", discord.Color.green(), target)

    @commands.command(name='snuggle')
    async def snuggle(self, ctx, target: discord.Member = None):
        if not target:
            embed = discord.Embed(title="🛋️ ГАНЦААР ЗУУРАХ", description=f"{ctx.author.mention} хөнжилд орж, ганцаараа зуурав.", color=discord.Color.orange())
            return await ctx.send(embed=embed)
        if target == ctx.author:
            embed = discord.Embed(title="🛋️ ӨӨРИЙГӨӨ ЗУУРАХ", description=f"{ctx.author.mention} хөнжилөө боож, бяцхан бөмбөг шиг зуурав.", color=discord.Color.green())
            return await ctx.send(embed=embed)
        texts = [f"{ctx.author.mention} {target.mention} -н хажууд орж, хамтдаа зуурав! Дулаахан 💤"]
        await self._send_action(ctx, "snuggle", texts, "🛋️ **ЗУУРАЛТ** 🛌", discord.Color.teal(), target)

    # ==================== EMOTE COMMANDS ====================
    @commands.command(name='cry')
    async def cry(self, ctx):
        texts = [f"{ctx.author.mention} уйлж байна... Түүнд тайтрал хэрэгтэй байна."]
        await self._send_action(ctx, "cry", texts, "😢 **УЙЛАЛТ** 💧", discord.Color.blue())

    @commands.command(name='dance')
    async def dance(self, ctx):
        texts = [f"{ctx.author.mention} хөгжимд автан, гайхалтай бүжиглэж байна!"]
        await self._send_action(ctx, "dance", texts, "💃 **БҮЖИГ** 🕺", discord.Color.gold())

    @commands.command(name='laugh')
    async def laugh(self, ctx):
        texts = [f"{ctx.author.mention} чангаар инээв! Бүх өрөө инээдэнд автлаа."]
        await self._send_action(ctx, "laugh", texts, "😂 **ИНЭЭЛТ** 🤣", discord.Color.green())

    @commands.command(name='sleep')
    async def sleep(self, ctx):
        texts = [f"{ctx.author.mention} нойрны оронд хэвтээд, амттай зүүд зүүдлэв."]
        await self._send_action(ctx, "sleep", texts, "😴 **УНТАХ** 💤", discord.Color.dark_blue())

    @commands.command(name='think')
    async def think(self, ctx):
        texts = [f"{ctx.author.mention} эрүүгээ түшин, гүн бодолд автлаа."]
        await self._send_action(ctx, "think", texts, "🤔 **БОДОЛТ** 💭", discord.Color.purple())

    @commands.command(name='angry')
    async def angry(self, ctx):
        texts = [f"{ctx.author.mention} нүд нь гал цацарч, уур хилэн дүүрэн харагдана."]
        await self._send_action(ctx, "angry", texts, "😠 **УУРЛАХ** 😤", discord.Color.dark_red())

    @commands.command(name='happy')
    async def happy(self, ctx):
        texts = [f"{ctx.author.mention} аз жаргалтайгаар үсэрч, дээшээ харайлаа!"]
        await self._send_action(ctx, "happy", texts, "😊 **ЖАРГАЛТАЙ** 🥳", discord.Color.green())

async def setup(bot):
    await bot.add_cog(Fun(bot))
