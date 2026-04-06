import discord
from discord.ext import commands, tasks
import random
import asyncio
import time  # ← ADICIONE
from datetime import datetime
import yt_dlp
import os
from dotenv import load_dotenv
load_dotenv()  # ← ESSENCIAL (antes de TOKEN)



# =============== INTENTS ===============
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

musica_queue = {}  # {guild_id: [{'url': '', 'title': ''}]}
tickets_abertos = {}  # {ticket_channel_id: {'user_id': ID, 'aberto_em': timestamp}}


PALAVRAS_PROIBIDAS = ["buceta", "puta", "safada", "cu"]

@bot.event
async def on_ready():
    print(f"🚀 Bot iniciado como {bot.user} em {len(bot.guilds)} servidores")


@bot.event
async def on_guild_join(guild: discord.Guild):
    """Cria automaticamente tickets + staff (com verificação de permissões)"""
    
    # Verifica se bot tem permissões
    if not guild.me.guild_permissions.manage_channels:
        print(f"❌ Sem permissão Manage Channels em {guild.name}")
        return
    
    try:
        print(f"Configurando {guild.name}...")
        
        # 1. CATEGORIA TICKETS + abrir_ticket
        categoria_tickets = discord.utils.get(guild.categories, name="🎫 Criar Tickets")
        if not categoria_tickets:
            categoria_tickets = await guild.create_category("🎫 Criar Tickets")
            print("✅ Criou categoria Tickets")
        
        canal_abrir = discord.utils.get(guild.text_channels, name="abrir_ticket")
        if not canal_abrir:
            canal_abrir = await guild.create_text_channel(
                "abrir_ticket",
                category=categoria_tickets,
                topic="🔔 Use `.ticket` aqui para abrir um ticket!",
                reason="Configuração JPBot"
            )
            print("✅ Criou #abrir_ticket")
        
        # Permissões abrir_ticket
        await canal_abrir.set_permissions(
            guild.default_role, send_messages=True, read_messages=True, embed_links=True
        )
        
        # Mensagem boas-vindas
        embed_boas = discord.Embed(
            title="🎫 Tickets Ativados!",
            description="Digite `.ticket` para suporte!",
            color=0x00ff88
        )
        await canal_abrir.send(embed=embed_boas)
        
        # 2. CATEGORIA STAFF + #staff
        categoria_staff = discord.utils.get(guild.categories, name="🔒 Staff")
        if not categoria_staff:
            categoria_staff = await guild.create_category("🔒 Staff")
            print("✅ Criou categoria Staff")
        
        canal_staff = discord.utils.get(guild.text_channels, name="staff")
        if not canal_staff:
            canal_staff = await guild.create_text_channel(
                "staff",
                category=categoria_staff,
                topic="🔔 Notificações automáticas de tickets",
                reason="Configuração JPBot"
            )
            print("✅ Criou #staff")
        
        # PERMISSÕES #staff PRIVADO
        await canal_staff.set_permissions(guild.default_role, read_messages=False)
        
        # Dono + cargos admin/lider
        for role in guild.roles:
            if role.permissions.administrator or any(palavra in role.name.lower() 
                for palavra in ['admin', 'lider', 'mod', 'staff']):
                await canal_staff.set_permissions(role, read_messages=True, send_messages=True)
        
        # Bot tem acesso
        await canal_staff.set_permissions(guild.me.top_role, read_messages=True, send_messages=True)
        
        embed_staff_boas = discord.Embed(
            title="🔒 Staff Configurado!",
            description="Tickets novos chegam aqui automaticamente!",
            color=0x0099ff
        )
        await canal_staff.send(embed=embed_staff_boas)
        
        print(f"✅ ✅ {guild.name} COMPLETO!")
        
    except Exception as e:
        print(f"❌ Erro {guild.name}: {e}")

@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """Cria tickets + staff MANUALMENTE"""
    try:
        # Categoria Tickets
        categoria_tickets = await ctx.guild.create_category("🎫 Criar Tickets")
        canal_abrir = await categoria_tickets.create_text_channel("abrir_ticket")
        
        # Categoria Staff
        categoria_staff = await ctx.guild.create_category("🔒 Staff")
        canal_staff = await categoria_staff.create_text_channel("staff")
        
        # Permissões staff PRIVADO
        await canal_staff.set_permissions(ctx.guild.default_role, read_messages=False)
        await canal_staff.set_permissions(ctx.author.top_role, read_messages=True, send_messages=True)
        await canal_staff.set_permissions(ctx.guild.me.top_role, read_messages=True, send_messages=True)
        
        embed = discord.Embed(title="✅ SETUP CONCLUÍDO!", color=0x00ff88)
        embed.add_field(name="Tickets", value=f"<#{canal_abrir.id}>", inline=True)
        embed.add_field(name="Staff", value=f"<#{canal_staff.id}>", inline=True)
        await ctx.reply(embed=embed)
        print("✅ Setup manual OK!")
        
    except Exception as e:
        await ctx.reply(f"❌ Erro: {e}")






# ==========================
# SUPERVISÃO AUTOMÁTICA
# ==========================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.guild is None:
        return

    conteudo = message.content.lower()
    for palavra in PALAVRAS_PROIBIDAS:
        if palavra in conteudo:
            try:
                await message.delete()
                await message.guild.ban(
                    message.author,
                    reason=f"Uso de linguagem sexual/ofensiva: {palavra}",
                    delete_message_seconds=86400
                )
                await message.channel.send(
                    f"{message.author.mention} foi **banido automaticamente** por uso de linguagem sexual/ofensiva.",
                    delete_after=10
                )
            except discord.Forbidden:
                await message.channel.send(
                    f"❌ Não consegui banir {message.author.mention} (permissões insuficientes).",
                    delete_after=10
                )
            except discord.HTTPException:
                pass
            break

    await bot.process_commands(message)

# ==========================
# COMANDOS BÁSICOS (EMBED)
# ==========================
@bot.command(name="ola")
async def ola(ctx):
    embed = discord.Embed(
        title="👋 Olá!",
        description=f"Olá **{ctx.author.display_name}**! Como posso ajudá-lo?",
        color=0x00ff00
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    await ctx.reply(embed=embed)

@bot.command(name="ping")
async def ping(ctx):
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latência: **{round(bot.latency * 1000)}ms**",
        color=0x0099ff
    )
    await ctx.reply(embed=embed)

@bot.command(name="avatar")
async def avatar(ctx, membro: discord.Member = None):
    membro = membro or ctx.author
    embed = discord.Embed(
        title=f"🖼️ Avatar de {membro.display_name}",
        color=0xffd700
    )
    embed.set_image(url=membro.display_avatar.url)
    await ctx.reply(embed=embed)

@bot.command(name="userinfo")
async def userinfo(ctx, membro: discord.Member = None):
    membro = membro or ctx.author
    status = str(membro.status).title()
    embed = discord.Embed(
        title=f"👤 {membro.display_name}",
        color=0x00ff00
    )
    embed.set_thumbnail(url=membro.display_avatar.url)
    embed.add_field(name="🆔 ID", value=membro.id, inline=True)
    embed.add_field(name="📅 Conta criada", value=f"<t:{int(membro.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="🏠 Entrou no servidor", value=f"<t:{int(membro.joined_at.timestamp())}:R>", inline=True)
    embed.add_field(name="📊 Status", value=status, inline=True)
    embed.add_field(name="🎭 Roles", value=len(membro.roles)-1, inline=True)
    await ctx.reply(embed=embed)

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(
        title=f"🏰 Servidor: {guild.name}",
        description=f"Informações completas do servidor.",
        color=0x0099ff
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="🆔 ID", value=guild.id, inline=True)
    embed.add_field(name="👥 Membros", value=guild.member_count, inline=True)
    embed.add_field(name="📅 Criado", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="👑 Dono", value=guild.owner.mention, inline=True)
    embed.add_field(name="💬 Canais", value=len(guild.text_channels)+len(guild.voice_channels), inline=True)
    embed.add_field(name="📱 Boosts", value=guild.premium_subscription_count or 0, inline=True)
    await ctx.reply(embed=embed)


@bot.command(name="top")
async def top(ctx):
    """Top songs ou ranking"""
    embed = discord.Embed(title="📊 TOP 5 MÚSICAS", color=0x00ff88)
    embed.add_field(name="1️⃣", value="Never Gonna Give You Up", inline=False)
    embed.add_field(name="2️⃣", value="Despacito", inline=False)
    await ctx.reply(embed=embed)

@bot.command(name="teste-staff")
async def teste_staff(ctx):
    """Testa canal staff"""
    canal = discord.utils.get(ctx.guild.text_channels, name="staff")
    if canal:
        await canal.send("🧪 **TESTE OK** - Bot envia no #staff!")
        await ctx.reply("✅ **#staff OK** ID: " + str(canal.id))
    else:
        await ctx.reply("❌ #staff não encontrado!")

# ==========================
# MATEMÁTICA (EMBED)
# ==========================

@bot.command(name="calc")
async def calc(ctx, num1: float, operacao: str, num2: float):
    """Calculadora: .calc 5 + 3"""
    try:
        if operacao == '+': resultado = num1 + num2
        elif operacao == '-': resultado = num1 - num2
        elif operacao == '*': resultado = num1 * num2
        elif operacao == '/': 
            if num2 == 0: return await ctx.reply("❌ Divisão por zero!")
            resultado = num1 / num2
        else: return await ctx.reply("❌ Use: + - * /")
        
        embed = discord.Embed(title="🧮 Calculadora", color=0x00ff88)
        embed.add_field(name=f"{num1} {operacao} {num2}", value=f"**= {resultado}**", inline=False)
        await ctx.reply(embed=embed)
    except:
        await ctx.reply("❌ Erro na conta!")

# ==========================
# DIVERSÃO E JOGOS (NOVOS!)
# ==========================
@bot.command(name="dado")
async def dado(ctx, faces: int = 6):
    resultado = random.randint(1, faces)
    embed = discord.Embed(title="🎲 Dado", color=0xff6600)
    embed.add_field(name=f"{ctx.author.display_name} rolou {faces} faces", value=f"**{resultado}** 🎯", inline=False)
    await ctx.reply(embed=embed)

@bot.command(name="moeda")
async def moeda(ctx):
    msg = await ctx.reply("🪙 **Girando moeda...**")
    await asyncio.sleep(1.5)
    flip = random.choice(["🪙 **Cara!**", "👑 **Coroa!**"])
    await msg.edit(content=f"{flip}\n**{ctx.author.display_name}** tirou {flip.split()[1]}")
    await msg.add_reaction("🪙")



# ==========================
# MÚSICA SIMPLES (NOVO!)
# ==========================
@bot.command(name="play")
async def play(ctx, *, musica: str):
    guild_id = ctx.guild.id
    
    if not ctx.author.voice:
        embed = discord.Embed(title="Música", color=0xff0000)
        embed.add_field(name="Canal de voz", value="Entre em um canal primeiro!", inline=False)
        return await ctx.reply(embed=embed)
    
    voice_channel = ctx.author.voice.channel
    vc = ctx.voice_client or await voice_channel.connect()
    
    # Se NÃO tem música tocando, toca direto
    if not vc.is_playing() and not vc.is_paused():
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch1',
            'extractaudio': True,
            'noplaylist': True,  # ← MUDEI PARA True
            'match_filter': lambda info: 'duration' not in info or info['duration'] < 3600,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(musica, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                url = info['url']
                title = info['title']
            
            source = discord.FFmpegPCMAudio(url, options='-vn')
            vc.play(source, after=lambda e: tocar_proxima(guild_id, vc))  # ← FILA!
            
            embed = discord.Embed(title="Música", color=0x00ff00)
            embed.add_field(name="Tocando", value=f"**{title[:50]}** 🎵", inline=False)
            await ctx.reply(embed=embed)
            
        except Exception:
            embed = discord.Embed(title="Música", color=0xff0000)
            embed.add_field(name="Erro", value="Música não encontrada!", inline=False)
            await ctx.reply(embed=embed)
            await vc.disconnect()
    
    else:
        # Já tocando → Adiciona na fila
        if guild_id not in musica_queue:
            musica_queue[guild_id] = []
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'default_search': 'ytsearch1',
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(musica, download=False)
            url = info['entries'][0]['url']
            title = info['entries'][0]['title']
        
        musica_queue[guild_id].append({'url': url, 'title': title})
        embed = discord.Embed(title="➕ Fila", color=0x0099ff)
        embed.add_field(name="Adicionada", value=f"**{title[:50]}**", inline=False)
        embed.add_field(name="Posição", value=f"#{len(musica_queue[guild_id])}", inline=False)
        await ctx.reply(embed=embed)
        
async def tocar_proxima(guild_id, vc):
    """Toca próxima música da fila"""
    if guild_id in musica_queue and musica_queue[guild_id]:
        proxima = musica_queue[guild_id].pop(0)
        source = discord.FFmpegPCMAudio(proxima['url'], options='-vn')
        vc.play(source, after=lambda e: tocar_proxima(guild_id, vc))



@bot.command(name="stop")
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        embed = discord.Embed(title="Música", color=0xff4444)
        embed.add_field(name="Status", value="⏹️ Música parada!", inline=False)
        await ctx.reply(embed=embed)
    else:
        embed = discord.Embed(title="Música", color=0xffaa00)
        embed.add_field(name="Status", value="Nenhuma música tocando!", inline=False)
        await ctx.reply(embed=embed)

@bot.command(name="queue")
async def queue(ctx, *, musica: str):
    guild_id = ctx.guild.id
    if guild_id not in musica_queue:
        musica_queue[guild_id] = []
    
    ydl_opts = {'format': 'bestaudio/best', 'quiet': True, 'default_search': 'ytsearch1', 'noplaylist': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(musica, download=False)
        url = info['entries'][0]['url']
        title = info['entries'][0]['title']
    
    musica_queue[guild_id].append({'url': url, 'title': title})
    embed = discord.Embed(title="➕ Fila", color=0x0099ff)
    embed.add_field(name="Adicionada", value=f"**{title[:40]}**", inline=False)
    embed.add_field(name="Posição", value=f"#{len(musica_queue[guild_id])}", inline=False)
    await ctx.reply(embed=embed)


@bot.command(name="skip")
async def skip(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()
        embed = discord.Embed(title="⏭️ Skip", color=0xff6600)
        embed.add_field(name="Status", value="✅ Música pulada!", inline=False)
        await ctx.reply(embed=embed)
    else:
        await ctx.reply("❌ Nenhuma música tocando!")


@bot.command(name="pause")
async def pause(ctx):
    vc = ctx.voice_client
    if vc:
        if vc.is_playing():
            vc.pause()
            await ctx.reply("⏸️ **Pausado!**")
        elif vc.is_paused():
            vc.resume()
            await ctx.reply("▶️ **Retomado!**")
        else:
            await ctx.reply("❌ Nenhuma música tocando!")
    else:
        await ctx.reply("❌ Não estou em canal de voz!")






# ==========================
# REAÇÕES E VOTAÇÕES
# ==========================
@bot.command(name="votar")
async def votar(ctx, *, pergunta: str):
    embed = discord.Embed(title=f"📊 Votação: {pergunta[:100]}", color=0x0099ff)
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

@bot.command(name="poll")
async def poll(ctx, tempo: int, titulo: str, *, opcoes):
    opcoes = [opt.strip() for opt in opcoes.split("|")]
    if len(opcoes) < 2 or len(opcoes) > 10:
        return await ctx.reply("❌ 2-10 opções separadas por `|`")
    
    embed = discord.Embed(title=f"📈 **{titulo}**", color=0x00ff88)
    for i, opcao in enumerate(opcoes, 1):
        embed.add_field(name=f"{i}️⃣ {opcao}", value="Vote reagindo!", inline=False)
    
    msg = await ctx.send(embed=embed)
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i in range(len(opcoes)):
        await msg.add_reaction(emojis[i])
    
    await asyncio.sleep(tempo)
    await msg.reply("⏰ **Enquete encerrada!**")


# ==========================
# MODERAÇÃO (EMBED)
# ==========================
@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, membro: discord.Member, *, motivo: str = "Não informado"):
    await membro.kick(reason=motivo)
    embed = discord.Embed(title="👢 Kick", color=0xffaa00)
    embed.add_field(name="Membro", value=membro.mention, inline=True)
    embed.add_field(name="Motivo", value=motivo, inline=True)
    embed.add_field(name="Moderador", value=ctx.author.mention, inline=True)
    await ctx.reply(embed=embed)

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, membro: discord.Member, *, motivo: str = "Não informado"):
    await membro.ban(reason=motivo)
    embed = discord.Embed(title="🔨 Ban", color=0xff0000)
    embed.add_field(name="Membro", value=membro.mention, inline=True)
    embed.add_field(name="Motivo", value=motivo, inline=True)
    embed.add_field(name="Moderador", value=ctx.author.mention, inline=True)
    await ctx.reply(embed=embed)

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, user: discord.User):
    await ctx.guild.unban(user)
    embed = discord.Embed(title="🔓 Unban", color=0x00ff00)
    embed.add_field(name="Membro", value=user.mention, inline=True)
    embed.add_field(name="Moderador", value=ctx.author.mention, inline=True)
    await ctx.reply(embed=embed)

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, quantidade: int = 10):
    apagadas = await ctx.channel.purge(limit=quantidade + 1)
    embed = discord.Embed(title="🧹 Clear", color=0x888888)
    embed.description = f"Apaguei **{len(apagadas) - 1}** mensagens."
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(5)
    await msg.delete()


# ==========================
# SISTEMA DE MEME (NOVO!)
# ==========================

@bot.command(name="meme")
async def meme(ctx):
    # ✅ SÓ FUNCIONA NO CANAL #memes
    if ctx.channel.name != "memes":
        embed = discord.Embed(
            title="❌ Canal incorreto!",
            description="Use `.meme` **APENAS** no canal **#memes**!",
            color=0xff0000
        )
        return await ctx.send(embed=embed, delete_after=5)  # ✅ MUDOU: ctx.send
    
    # Verifica se canal #memes existe
    canal_memes = discord.utils.get(ctx.guild.text_channels, name="memes")
    if not canal_memes:
        return await ctx.send("❌ Crie canal `#memes` primeiro!")
    
    memes = [
        "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExYzh5Mm1jdHYybHk2aDZybWV3bWs2M2o1cG44anlkajY5emlmMWY0NSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/lRMMimsRMHEagufOt9/giphy.gif",
        "hhttps://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNG82emtqbWQ0dmplcW9lajlqN3JpYmJwaWkxangzOHE0cDg1ZmxzcSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/sStlxCoVHftcr3BYE2/giphy.gif", 
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3dnAzeGE0a2libG1mOWlxdnM0Zjc0Y2s2Nmd1dHRpdW14anBpbXRwMSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/elXrne4FduZQqMq9t7/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3dnAzeGE0a2libG1mOWlxdnM0Zjc0Y2s2Nmd1dHRpdW14anBpbXRwMSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/zS1Eem5Mw1Jlr0Usoy/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeDZsNXd1cW5qanFnb3g1bXJiNG56bGI4NXNsejIxNWJucGpjODhjNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/IfPE0x5gfa5ctKpph6/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeDZsNXd1cW5qanFnb3g1bXJiNG56bGI4NXNsejIxNWJucGpjODhjNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/ZxWIUYDAKBIuKKkds3/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeDZsNXd1cW5qanFnb3g1bXJiNG56bGI4NXNsejIxNWJucGpjODhjNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/yxy69FCE06Ql0Fjk4Z/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeDZsNXd1cW5qanFnb3g1bXJiNG56bGI4NXNsejIxNWJucGpjODhjNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/lxxOGaDRk4f7R5TkBd/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeDZsNXd1cW5qanFnb3g1bXJiNG56bGI4NXNsejIxNWJucGpjODhjNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/8PZjEA5DEbgWqG4bxo/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeDZsNXd1cW5qanFnb3g1bXJiNG56bGI4NXNsejIxNWJucGpjODhjNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/LDWGyQRkMHbTIEE6QU/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeDZsNXd1cW5qanFnb3g1bXJiNG56bGI4NXNsejIxNWJucGpjODhjNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/W9SNjmuqbd4JGbpO65/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeDZsNXd1cW5qanFnb3g1bXJiNG56bGI4NXNsejIxNWJucGpjODhjNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/LR5GeZFCwDRcpG20PR/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeDZsNXd1cW5qanFnb3g1bXJiNG56bGI4NXNsejIxNWJucGpjODhjNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/TR996IaHtmDi1x98zW/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeDZsNXd1cW5qanFnb3g1bXJiNG56bGI4NXNsejIxNWJucGpjODhjNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/ACeIDlMpgc4yOf1Lyt/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeDZsNXd1cW5qanFnb3g1bXJiNG56bGI4NXNsejIxNWJucGpjODhjNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/joYf3Ba2phD15ch9Nt/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeDZsNXd1cW5qanFnb3g1bXJiNG56bGI4NXNsejIxNWJucGpjODhjNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/QxcSqRe0nllClKLMDn/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeDZsNXd1cW5qanFnb3g1bXJiNG56bGI4NXNsejIxNWJucGpjODhjNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/12s2PXFPfJXUcHHjWR/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3OGF5emFzYjd0eHFzOHlra3EycWg1Y2tzNzZ5ZDl1MDZ0MXU5YTc3MCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/3I8H8VvG9D7FRqd92Q/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3OGF5emFzYjd0eHFzOHlra3EycWg1Y2tzNzZ5ZDl1MDZ0MXU5YTc3MCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/bE1rzx1CukqckPV2Cm/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3OGF5emFzYjd0eHFzOHlra3EycWg1Y2tzNzZ5ZDl1MDZ0MXU5YTc3MCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/80D1Pe1m0jfConCfhn/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3YzZieGw3azdkaDVpM2hzNWVta3ZoNjhpenVveTQ1cHFwZ2N5dGUxZCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/wrmVCNbpOyqgJ9zQTn/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3YzZieGw3azdkaDVpM2hzNWVta3ZoNjhpenVveTQ1cHFwZ2N5dGUxZCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/sozVLoj67TJYUIhgy6/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3YzZieGw3azdkaDVpM2hzNWVta3ZoNjhpenVveTQ1cHFwZ2N5dGUxZCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/Lopx9eUi34rbq/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3YzZieGw3azdkaDVpM2hzNWVta3ZoNjhpenVveTQ1cHFwZ2N5dGUxZCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/bdIHP4CqxvdUe2MJH8/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3aWxleTliYzBmaGd5emdvMmk4MGtmMnVqMnprd2o3ZnE0eHQxYTc3ciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/TKa7fQzChHylCQ89to/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3YzZieGw3azdkaDVpM2hzNWVta3ZoNjhpenVveTQ1cHFwZ2N5dGUxZCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/GK5cQrLmRbgIJfOl5Z/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3aWxleTliYzBmaGd5emdvMmk4MGtmMnVqMnprd2o3ZnE0eHQxYTc3ciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/sHNEi9gCFsVCMaCruk/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3aWxleTliYzBmaGd5emdvMmk4MGtmMnVqMnprd2o3ZnE0eHQxYTc3ciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/TKa7fQzChHylCQ89to/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3aWxleTliYzBmaGd5emdvMmk4MGtmMnVqMnprd2o3ZnE0eHQxYTc3ciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/xL7PDV9frcudO/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3aWxleTliYzBmaGd5emdvMmk4MGtmMnVqMnprd2o3ZnE0eHQxYTc3ciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/laa75ehg46kBMGvIqe/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3OGF5emFzYjd0eHFzOHlra3EycWg1Y2tzNzZ5ZDl1MDZ0MXU5YTc3MCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/4pMX5rJ4PYAEM/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3NjQxMzhmbmo1Z3U5OTRmbDBzd280aWJoc3EyaXd2czJqNDJmaHUwMiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/oH8IZg7dzIbJFRIJ2Z/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3NjQxMzhmbmo1Z3U5OTRmbDBzd280aWJoc3EyaXd2czJqNDJmaHUwMiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/8JCIWBz8oRRLZmZhNn/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3NjQxMzhmbmo1Z3U5OTRmbDBzd280aWJoc3EyaXd2czJqNDJmaHUwMiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/8JCIWBz8oRRLZmZhNn/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3NjQxMzhmbmo1Z3U5OTRmbDBzd280aWJoc3EyaXd2czJqNDJmaHUwMiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/AAsj7jdrHjtp6/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3c2F0cTN4a3pvNjJsbm0xZThoMHFobnlpMTI4OGEwOTl1YXJib2NsNSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/sST6lxYUtf79v0rpCm/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3c2F0cTN4a3pvNjJsbm0xZThoMHFobnlpMTI4OGEwOTl1YXJib2NsNSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/PznR7snMBSJENwPTlb/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3OXg1NnI4OGVuaXk1Mjdic2QzMHdxNG1hcG15cHVkNzQxYmZwaXBhYSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/kd9BlRovbPOykLBMqX/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3OXg1NnI4OGVuaXk1Mjdic2QzMHdxNG1hcG15cHVkNzQxYmZwaXBhYSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/4a1f475nY27jaWCrgZ/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3OXg1NnI4OGVuaXk1Mjdic2QzMHdxNG1hcG15cHVkNzQxYmZwaXBhYSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/nNOZe5giJhwsM/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3aG9mNmMzaGl4cmFhZWlzejJhNm41b29iOW5mc2wxcXNyc2s1cGdkZCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/tHIRLHtNwxpjIFqPdV/giphy.gif"
    ]
    

    
    meme_url = random.choice(memes)
    embed = discord.Embed(title="😂 Meme aleatório!", color=0xffd700)
    embed.set_image(url=meme_url)
    embed.set_footer(text=f"Enviado por {ctx.author.display_name}")
    
    await canal_memes.send(embed=embed)
    
    # ✅ ORDEM CORRETA: delete PRIMEIRO, send DEPOIS
    await ctx.message.delete()
    await ctx.send(f"✅ Meme enviado em #{canal_memes.name}!", delete_after=3)

# ✅ AUTO-MODERAÇÃO: APAGA TUDO no #memes (exceto .meme)
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # ✅ SÓ no canal #memes
    if message.channel.name == "memes":
        # ✅ PERMITE .meme e outros comandos (começam com .)
        if not message.content.startswith('.'):
            try:
                await message.delete()
                print(f"🗑️ Apagada mensagem de {message.author} em #memes")
            except:
                pass
    
    await bot.process_commands(message)




# ==========================
# SISTEMA DE TICKET (NOVO!)
# ==========================
@bot.command(name="ticket")
async def ticket(ctx):
    # Só funciona no canal "abrir_ticket"
    if ctx.channel.name != "abrir_ticket":
        embed = discord.Embed(
            title="❌ Canal incorreto!",
            description="Use este comando apenas no canal **#abrir_ticket**.",
            color=0xff0000
        )
        return await ctx.reply(embed=embed)
    
    guild = ctx.guild
    print(f"🔍 Procurando canal staff em {guild.name}...")
    canal_staff = discord.utils.get(guild.text_channels, name="staff")
    print(f"📱 Canal staff encontrado: {canal_staff.name if canal_staff else 'NENHUM'} (ID: {canal_staff.id if canal_staff else 'N/A'})")
    
    categoria = discord.utils.get(guild.categories, name="🎫 Tickets")
    if not categoria:
        categoria = await guild.create_category("🎫 Tickets")
    
    # Canal com nome do membro
    channel = await guild.create_text_channel(
        f"ticket-{ctx.author.display_name}",
        category=categoria,
        topic=f"Ticket criado por {ctx.author.id}"
    )
    
    # Permissões: só criador e @everyone não vê
    await channel.set_permissions(ctx.author, read_messages=True, send_messages=True)
    await channel.set_permissions(guild.default_role, read_messages=False)
    
    # SALVA NO SISTEMA (adicione tickets_abertos no topo)
    ticket_id = channel.id
    tickets_abertos[ticket_id] = {
        'user_id': ctx.author.id,
        'aberto_em': time.time(),
        'guild_id': guild.id
    }
    
    # Mensagem no canal do ticket
    embed_bemvindo = discord.Embed(
        title="🎫 Ticket Criado!",
        description=f"Olá **{ctx.author.display_name}**!",
        color=0x00ff88
    )
    embed_bemvindo.add_field(
        name="📝 **Qual o motivo do ticket?**", 
        value="Descreva seu problema com detalhes para que possamos ajudá-lo rapidamente.",
        inline=False
    )
    embed_bemvindo.add_field(
        name="⚠️ **Comandos úteis**",
        value=f"`.close` - Fechar este ticket\n`.claim` - Staff assume o ticket",
        inline=False
    )
    await channel.send(embed=embed_bemvindo)
    
    # ✅ NOTIFICA CANAL STAFF (CORRIGIDO!)
    print(f"📱 Canal ticket criado: #{channel.name} (ID: {channel.id})")
    if canal_staff:
        try:
            embed_staff = discord.Embed(
                title="🆕 NOVO TICKET!",
                description=f"**{ctx.author.display_name}** ({ctx.author.id}) abriu ticket",
                color=0xffaa00
            )
            embed_staff.add_field(name="📱 Canal", value=channel.mention, inline=True)
            embed_staff.add_field(name="⏰ Aberto", value=f"<t:{int(time.time())}:R>", inline=True)
            embed_staff.add_field(name="⚡ Ação", value="Use `.claim` no canal!", inline=True)
            embed_staff.set_thumbnail(url=ctx.author.display_avatar.url)
            await canal_staff.send(embed=embed_staff)
            print("✅ NOTIFICAÇÃO STAFF ENVIADA!")
        except Exception as e:
            print(f"❌ Erro notificação staff: {e}")
    else:
        print("❌ CANAL STAFF NÃO ENCONTRADO!")
    
    # ✅ TUDO NO PRIVADO DO MEMBRO (seu código original)
    try:
        embed_privado = discord.Embed(
            title="✅ Seu ticket foi criado!",
            description=f"Entre no canal para descrever seu problema:\n**{channel.mention}**",
            color=0x00ff88
        )
        embed_privado.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.author.send(embed=embed_privado)
        
        embed_canal = discord.Embed(
            title="✅ Ticket criado!",
            description=f"**{ctx.author.display_name}**, verifique suas **mensagens privadas**.",
            color=0x00ff88
        )
        await ctx.reply(embed=embed_canal)
        
    except discord.Forbidden:
        embed_canal = discord.Embed(
            title="✅ Ticket criado!",
            description=f"**{ctx.author.display_name}**, seu ticket: {channel.mention}\n⚠️ Ative DMs para receber notificações.",
            color=0x00ff88
        )
        await ctx.reply(embed=embed_canal)




@bot.command(name="claim")
@commands.has_permissions(manage_channels=True)
async def claim(ctx):
    ticket_id = ctx.channel.id
    
    # REMOVE DA LISTA DE PENDENTES
    if ticket_id in tickets_abertos:
        user_id = tickets_abertos[ticket_id]['user_id']
        del tickets_abertos[ticket_id]
        
        # ✅ ENVIA DM PARA O USUÁRIO ORIGINAL
        try:
            usuario = await bot.fetch_user(user_id)
            embed_dm = discord.Embed(
                title="✅ Seu ticket está em ATENDIMENTO!",
                description=f"O staff **{ctx.author.display_name}** assumiu seu ticket!",
                color=0x00ff88
            )
            embed_dm.add_field(
                name="📱 Canal", 
                value=ctx.channel.mention, 
                inline=True
            )
            embed_dm.add_field(
                name="👤 Responsável", 
                value=ctx.author.mention, 
                inline=True
            )
            embed_dm.set_thumbnail(url=ctx.author.display_avatar.url)
            await usuario.send(embed=embed_dm)
            print(f"✅ DM de claim enviada para {usuario}")
            
        except discord.Forbidden:
            print(f"❌ Usuário {user_id} tem DMs fechadas")
        except Exception as e:
            print(f"Erro DM claim: {e}")
    
    embed = discord.Embed(
        title="✅ Ticket Reivindicado!",
        description=f"Este ticket foi assumido por **{ctx.author.display_name}**.",
        color=0x00ff88
    )
    await ctx.reply(embed=embed)
    
    # NOTIFICA STAFF - NÃO ASSUMIR
    canal_staff = discord.utils.get(ctx.guild.text_channels, name="staff")
    if canal_staff:
        embed_staff = discord.Embed(
            title="✅ TICKET ASSUMIDO",
            description=f"**{ctx.author.display_name}** assumiu **{ctx.channel.mention}**",
            color=0x00ff88
        )
        embed_staff.add_field(name="📋 Status", value="Ticket em atendimento!", inline=True)
        await canal_staff.send(embed=embed_staff)



@bot.command(name="close")
async def close(ctx):
    # Verifica se é um canal de ticket
    if not ctx.channel.name.startswith("ticket-"):
        embed = discord.Embed(
            title="❌ Erro!",
            description="Este comando só funciona em canais de ticket!",
            color=0xff0000
        )
        return await ctx.reply(embed=embed)
    
    # Pega o autor original do ticket do topic
    topic = ctx.channel.topic
    usuario_original = None
    if topic:
        try:
            user_id = int(topic.split(" ")[3])
            usuario_original = await bot.fetch_user(user_id)
        except:
            pass
    
    # Mensagem de fechamento no canal
    embed_fechamento = discord.Embed(
        title="🔒 Ticket Fechado!",
        description=f"Obrigado por usar nosso sistema de suporte **{ctx.author.display_name}**!",
        color=0xff4444
    )
    embed_fechamento.add_field(
        name="⏰ Canal será deletado em 5 segundos...",
        value="Se precisar de mais ajuda, abra um novo ticket!",
        inline=False
    )
    await ctx.send(embed=embed_fechamento)
    
    # ✅ NOTIFICA CANAL STAFF (NOVO!)
    canal_staff = discord.utils.get(ctx.guild.text_channels, name="staff")
    if canal_staff:
        embed_staff = discord.Embed(
            title="✅ TICKET FECHADO",
            description=f"**{ctx.channel.name}** foi encerrado",
            color=0x888888
        )
        embed_staff.add_field(name="👤 Fechado por", value=ctx.author.mention, inline=True)
        if usuario_original:
            embed_staff.add_field(name="👤 Usuário", value=usuario_original.mention, inline=True)
        embed_staff.add_field(name="📱 Canal", value=ctx.channel.mention, inline=True)
        await canal_staff.send(embed=embed_staff)
    
    # ✅ ENVIA DM PARA O USUÁRIO ORIGINAL (seu código original)
    if usuario_original:
        try:
            embed_dm = discord.Embed(
                title="📋 Seu ticket foi fechado!",
                description=f"Seu ticket **{ctx.channel.name}** foi encerrado por um membro da staff.",
                color=0xffaa00
            )
            embed_dm.add_field(
                name="💡 **Precisa de mais ajuda?**",
                value="Use `.ticket` no canal **#abrir_ticket** para abrir um novo!",
                inline=False
            )
            embed_dm.set_footer(text=f"Fechado por: {ctx.author.display_name}")
            
            await usuario_original.send(embed=embed_dm)
            print(f"✅ DM de fechamento enviada para {usuario_original}")
        except discord.Forbidden:
            print(f"❌ Não foi possível enviar DM para {usuario_original} (DMs fechadas)")
    
    # Deleta o canal após 5 segundos
    await asyncio.sleep(5)
    await ctx.channel.delete()



@bot.event
async def on_message(message: discord.Message):
    # Ignora DMs (não tem .name)
    if isinstance(message.channel, discord.DMChannel):
        await bot.process_commands(message)
        return
    
    # Canal #abrir_ticket - só permite .ticket
    if message.channel.name == "abrir_ticket":
        if message.author.bot:
            return
        
        # Só permite comando .ticket
        if not message.content.startswith(".ticket"):
            try:
                await message.delete()
                
                embed_alerta = discord.Embed(
                    title="⚠️ Canal exclusivo!",
                    description=f"**{message.author.display_name}**, use apenas `.ticket` neste canal!",
                    color=0xffaa00
                )
                alerta = await message.channel.send(embed=embed_alerta)
                await asyncio.sleep(5)
                await alerta.delete()
                
            except discord.HTTPException:
                pass
            return  # Para aqui
    
    # Supervisão de palavras proibidas (resto dos canais)
    if message.author.bot or message.guild is None:
        await bot.process_commands(message)
        return

    conteudo = message.content.lower()
    for palavra in PALAVRAS_PROIBIDAS:
        if palavra in conteudo:
            try:
                await message.delete()
                await message.guild.ban(
                    message.author,
                    reason=f"Uso de linguagem sexual/ofensiva: {palavra}",
                    delete_message_seconds=86400
                )
                await message.channel.send(
                    f"{message.author.mention} foi **banido automaticamente** por uso de linguagem sexual/ofensiva.",
                    delete_after=10
                )
            except discord.Forbidden:
                await message.channel.send(
                    f"❌ Não consegui banir {message.author.mention} (permissões insuficientes).",
                    delete_after=10
                )
            except discord.HTTPException:
                pass
            break

    await bot.process_commands(message)




# ==========================
# UTILITÁRIOS (NOVOS!)
# ==========================
@bot.command(name="tempo")
async def tempo(ctx):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    embed = discord.Embed(title="🕐 Hora atual", description=f"`{agora}` (GMT-3)", color=0x4169e1)
    await ctx.reply(embed=embed)

@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, texto: str):
    embed = discord.Embed(description=texto, color=0x9932cc)
    await ctx.send(embed=embed)
    await ctx.message.delete()



@tasks.loop(minutes=60)  # A cada 1 hora
async def notificar_tickets_pendentes():
    agora = asyncio.get_event_loop().time()
    
    for ticket_id, dados in list(tickets_abertos.items()):
        try:
            canal = bot.get_channel(ticket_id)
            if not canal or ticket_id not in tickets_abertos:
                continue
            
            tempo_aberto = agora - dados['aberto_em']
            if tempo_aberto >= 3600:  # 1 HORA
                guild = bot.get_guild(dados['guild_id'])
                if not guild:
                    continue
                
                canal_staff = discord.utils.get(guild.text_channels, name="staff")
                user = guild.get_member(dados['user_id'])
                
                if canal_staff:
                    embed_urgente = discord.Embed(
                        title="🚨 TICKET URGENTE!",
                        description=f"{canal.mention} **sem resposta há 1+ horas**",
                        color=0xff0000
                    )
                    embed_urgente.add_field(name="👤 Usuário", value=user.mention if user else "Desconhecido", inline=True)
                    embed_urgente.add_field(name="⚡ AÇÃO", value="**STAFF**: Use `.claim` AGORA!", inline=True)
                    await canal_staff.send(embed=embed_urgente)
                
                # Próxima notificação em 1h
                tickets_abertos[ticket_id]['proxima_notificacao'] = agora + 3600
        
        except Exception as e:
            print(f"Erro ticket {ticket_id}: {e}")
            if ticket_id in tickets_abertos:
                del tickets_abertos[ticket_id]

@bot.event
async def on_ready():
    # Seu código existente...
    if not notificar_tickets_pendentes.is_running():
        notificar_tickets_pendentes.start()
    print(f"🚀 Bot iniciado como {bot.user} em {len(bot.guilds)} servidores")


###########################
#       CONFIG MANUAL
###########################


@bot.command(name="debug-staff")
async def debug_staff(ctx):
    """Debug: verifica canal staff e permissões"""
    guild = ctx.guild
    
    # Procura canal staff
    canal_staff = discord.utils.get(guild.text_channels, name="staff")
    if canal_staff:
        embed = discord.Embed(title="✅ Canal #staff encontrado!", color=0x00ff88)
        embed.add_field(name="ID", value=canal_staff.id, inline=True)
        embed.add_field(name="Permissão bot", value=str(canal_staff.permissions_for(guild.me)), inline=False)
        await ctx.reply(embed=embed)
    else:
        embed = discord.Embed(title="❌ Canal #staff NÃO encontrado!", color=0xff0000)
        embed.add_field(name="Canais disponíveis", value="\n".join([c.name for c in guild.text_channels[:10]]), inline=False)
        await ctx.reply(embed=embed)



###########################
#          TESTES
###########################


@bot.command(name="test-staff")
async def test_staff(ctx):
    """TESTA se bot consegue enviar no #staff"""
    guild = ctx.guild
    canal_staff = discord.utils.get(guild.text_channels, name="staff")
    
    embed_test = discord.Embed(title="🧪 TESTE STAFF", description="Bot consegue enviar?", color=0x00ff00)
    
    if canal_staff:
        try:
            await canal_staff.send(embed=embed_test)
            await ctx.reply("✅ BOT ENVIA NO #STAFF!")
            print(f"✅ Teste OK - Canal staff ID: {canal_staff.id}")
        except Exception as e:
            await ctx.reply(f"❌ ERRO ENVIO: {e}")
            print(f"❌ Erro staff: {e}")
    else:
        await ctx.reply("❌ CANAL #staff NÃO ENCONTRADO!")






TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN não foi definida")
bot.run(TOKEN)




