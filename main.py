import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import discord
from discord.ext import commands

from config import (
    AUTO_ROLE_NAME,
    BOT_ID,
    DISCORD_TOKEN,
    GUILD_ID,
    STAFF_ROLE_NAME,
    SUPPORT_TOPICS,
    TICKET_CATEGORY_NAME,
    TICKET_CHANNEL_NAME_PREFIX,
    TICKET_LOGS_NAME,
    WELCOME_CHANNEL_NAME,
)
from utils import find_category, find_channel, is_staff, make_embed, ticket_channel_for

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f"{bot.user} esta online em {len(bot.guilds)} servidor(es)!")
    bot.add_view(TicketPanelView())
    bot.add_view(WelcomeView())
    for topic in SUPPORT_TOPICS:
        bot.add_view(TicketCloseView(topic=topic, user_id=None))
    for guild in list(bot.guilds):
        if guild.id == GUILD_ID:
            print(f"Preparando {guild.name} ({guild.id})")
            await prepare_guild(guild)


async def prepare_guild(guild: discord.Guild):
    """Cria a estrutura basica do servidor, se nao existir."""
    category = find_category(guild, TICKET_CATEGORY_NAME)
    if category is None:
        try:
            category = await guild.create_category(TICKET_CATEGORY_NAME)
        except discord.Forbidden:
            print(f"Sem permissao para criar categoria em {guild.name}")
            return
    if find_channel(guild, TICKET_LOGS_NAME) is None:
        try:
            await guild.create_text_channel(TICKET_LOGS_NAME, category=category)
        except discord.Forbidden:
            print(f"Sem permissao para criar canal de logs em {guild.name}")


@bot.event
async def on_member_join(member: discord.Member):
    if AUTO_ROLE_NAME:
        role = discord.utils.get(member.guild.roles, name=AUTO_ROLE_NAME)
        if role:
            try:
                await member.add_roles(role, reason="Auto-role de boas-vindas")
            except discord.Forbidden:
                print(f"Sem permissao para dar cargo {AUTO_ROLE_NAME} em {member.guild.name}")
    channel = find_channel(member.guild, WELCOME_CHANNEL_NAME)
    if channel is None:
        return
    e = make_embed(f"Bem-vindo(a) {member.display_name}! 🎉", f"Olá {member.mention}!, bem-vindo(a) ao **Pollar Vendas**!\n\nAqui voce encontra os melhores produtos e um atendimento de qualidade.\nPara abrir um ticket de suporte/compra/venda, use os botoes abaixo no canal de tickets.\n\nAproveite a sua estadia! 😊", discord.Color.green())
    e.set_thumbnail(url=member.display_avatar.url)
    try:
        await channel.send(content=member.mention, embed=e)
    except discord.Forbidden:
        print(f"Sem permissao para enviar mensagem em {channel.name}")


@bot.command(name="setup")
async def setup(ctx: commands.Context):
    """Cria os paineis de tickets e boas-vindas no servidor."""
    if not ctx.guild:
        return
    if ctx.guild.id == GUILD_ID:
        return
    if not is_staff(ctx.author):
        return await ctx.send("Voce nao tem permissao para usar este comando.")
    await prepare_guild(ctx.guild)
    welcome_channel = find_channel(ctx.guild, WELCOME_CHANNEL_NAME)
    if welcome_channel is None:
        try:
            welcome_channel = await ctx.guild.create_text_channel(WELCOME_CHANNEL_NAME)
        except discord.Forbidden:
            return await ctx.send("Sem permissao para criar canal de boas-vindas.")
    await welcome_channel.send(embed=welcome_embed(), view=WelcomeView())
    ticket_channel = find_channel(ctx.guild, "tickets")
    if ticket_channel is None:
        category = find_category(ctx.guild, TICKET_CATEGORY_NAME)
        try:
            ticket_channel = await ctx.guild.create_text_channel("tickets", category=category)
        except discord.Forbidden:
            return await ctx.send("Sem permissao para criar o canal de tickets.")
    await ticket_channel.send(embed=ticket_panel_embed(), view=TicketPanelView())
    await ctx.send("Estrutura configurada com sucesso! ✅")


@bot.command(name="anuncio")
async def announce(ctx: commands.Context, canal: discord.TextChannel = None, *, mensagem: str = None):
    """Envia um anuncio num canal com um embed bonito."""
    if not ctx.guild:
        return
    if ctx.guild.id == GUILD_ID:
        return
    if not is_staff(ctx.author):
        return await ctx.send("Voce nao tem permissao para usar este comando.")
    if canal is None:
        canal = ctx.channel
    if not mensagem:
        return await ctx.send("Uso: !anuncio #canal mensagem")
    e = make_embed("📢 Anúncio", mensagem, discord.Color.gold())
    e.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
    try:
        await canal.send(embed=e)
        await ctx.send("Anuncio enviado! ✅")
    except discord.Forbidden:
        pass


@bot.command(name="ticket")
async def create_ticket_command(ctx: commands.Context, *, motivo: str = None):
    """Envia o painel de escolha do assunto do ticket."""
    if not ctx.guild:
        return
    view = TicketTopicView()
    panel = make_embed("🎫 Abrir Ticket", "Escolha o assunto do seu atendimento abaixo:", discord.Color.blue())
    await ctx.send(embed=panel, view=view)


def ticket_panel_embed():
    return make_embed("🎫 Central de Suporte", "Bem-vindo(a) a central de atendimento **Pollar Vendas**!\n\nEscolha o assunto do seu atendimento para abrir um ticket.\nUm membro da nossa equipe ira atende-lo em breve.\n\n📌 **Disponivel 24/7** para melhor atende-lo!", discord.Color.blue())


def welcome_embed():
    return make_embed("👋 Bem-vindo(a) ao Pollar Vendas!", "Aqui voce encontra produtos de qualidade e atendimento rapido.\nUse o **painel de tickets** para falar com o suporte, comprar ou vender.\n\n**Pollar Vendas** - a sua melhor escolha! 🚀", discord.Color.green())


class TicketTopicView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for topic in SUPPORT_TOPICS:
            self.add_item(TicketButton(topic))


class TicketButton(discord.ui.Button[str]):
    def __init__(self, topic: str):
        labels = {
            "compra": "🛒 Compra",
            "venda": "💸 Venda",
            "suporte": "🛠️ Suporte",
            "denuncia": "🚨 Denúncia",
            "outro": "📦 Outro",
        }
        styles = {
            "compra": discord.ButtonStyle.green,
            "venda": discord.ButtonStyle.blurple,
            "suporte": discord.ButtonStyle.primary,
            "denuncia": discord.ButtonStyle.danger,
            "outro": discord.ButtonStyle.secondary,
        }
        super().__init__(
            label=labels.get(topic, topic.title()),
            style=styles.get(topic, discord.ButtonStyle.secondary),
            custom_id=f"ticket:{topic}",
        )
        self.topic = topic

    async def callback(self, interaction: discord.Interaction):
        """Cria o canal de ticket para o usuario."""
        user: discord.Member = interaction.user
        guild = interaction.guild
        existing = ticket_channel_for(guild, user.id)
        if existing:
            return await interaction.response.send_message(f"Voce ja tem um ticket aberto: {existing.mention}", ephemeral=True)
        category = find_category(guild, TICKET_CATEGORY_NAME)
        if category is None:
            try:
                category = await guild.create_category(TICKET_CATEGORY_NAME)
            except discord.Forbidden:
                return await interaction.response.send_message("Sem permissao para criar a categoria de tickets.", ephemeral=True)
        logs_channel = find_channel(guild, TICKET_LOGS_NAME)
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, manage_messages=True, read_message_history=True)
        username = "".join(c if c.isalnum() or c in "-_" else "-" for c in user.name.lower().replace(" ", "-"))
        channel_name = f"{TICKET_CHANNEL_NAME_PREFIX}-{self.topic}-{username}"
        try:
            channel = await guild.create_text_channel(name=channel_name, category=category, topic=f"ticket:{user.id}", overwrites=overwrites)
        except discord.Forbidden:
            return await interaction.response.send_message("Sem permissao para criar o ticket.", ephemeral=True)
        e = make_embed(f"Ticket de {self.topic.title()}", f"Olá {user.mention}!,a sua solicitacao foi recebida!\n\nDescreva o seu problema/pedido neste canal com detalhes.\nA nossa equipe ira atende-lo o mais rapido possivel.\n\nUse o botao abaixo para **fechar** o ticket quando terminar.", discord.Color.blue())
        view = TicketCloseView(topic=self.topic, user_id=user.id)
        await channel.send(user.mention, embed=e, view=view)
        if logs_channel:
            log_e = make_embed(f"🆕 Novo Ticket: {self.topic.title()}", f"**Usuario:** {user.mention} ({user.id})\n**Canal:** {channel.mention}\n**Aberto em:** {discord.utils.format_dt(discord.utils.utcnow())}", discord.Color.green())
            await logs_channel.send(embed=log_e)
        ticket_link_view = discord.ui.View()
        ticket_link_view.add_item(discord.ui.Button(label="Ir para o ticket", url=channel.jump_url, style=discord.ButtonStyle.link))
        await interaction.response.send_message(f"Ticket criado: {channel.mention}", ephemeral=True, view=ticket_link_view)


class TicketCloseView(discord.ui.View):
    def __init__(self, topic: str, user_id: int):
        super().__init__(timeout=None)
        self.topic = topic
        self.user_id = user_id
        self.add_item(CloseTicketButton(topic, user_id))


class CloseTicketButton(discord.ui.Button[str]):
    def __init__(self, topic: str, user_id: int):
        super().__init__(
            label="🔒 Fechar Ticket",
            style=discord.ButtonStyle.danger,
            custom_id=f"close:{topic}",
        )
        self.topic = topic
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        guild = interaction.guild
        can_close = any(member.id == self.user_id or is_staff(member) for member in channel.members)
        if not can_close:
            return await interaction.response.send_message("Voce nao pode fechar este ticket.", ephemeral=True)
        logs_channel = find_channel(guild, TICKET_LOGS_NAME)
        if logs_channel:
            transcript = await build_transcript(channel, interaction.user)
            log_e = make_embed(f"🔒 Ticket Fechado: {self.topic.title()}", f"**Usuario:** <@{self.user_id}> ({self.user_id})\n**Canal:** {channel.mention}\n**Fechado por:** {interaction.user.mention}\n**Fechado em:** {discord.utils.format_dt(discord.utils.utcnow())}", discord.Color.red())
            if transcript:
                log_e.add_field(name="📜 Transcricao", value=transcript[:1024], inline=False)
            await logs_channel.send(embed=log_e)
        await interaction.response.send_message("Fechando ticket... 🔒", ephemeral=True)
        await channel.delete(reason=f"Ticket fechado por {interaction.user}")


async def build_transcript(channel: discord.TextChannel, closer: discord.Member) -> str:
    """Gera um resumo das mensagens do canal para os logs."""
    lines = []
    try:
        async for message in channel.history(limit=50, oldest_first=True):
            if message.author.bot and not message.content:
                continue
            timestamp = discord.utils.format_dt(message.created_at, style="d")
            content = message.content or "[embed/imagem]"
            lines.append(f"`{timestamp}` **{message.author.display_name}**: {content}")
    except discord.Forbidden:
        return ""
    if not lines:
        return ""
    return "\n".join(lines)


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketButton("compra"))
        self.add_item(TicketButton("venda"))
        self.add_item(TicketButton("suporte"))
        self.add_item(TicketButton("denuncia"))
        self.add_item(TicketButton("outro"))


class WelcomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Abrir Ticket", style=discord.ButtonStyle.primary, custom_id="welcome:ticket")
    async def _open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = TicketTopicView()
        e = make_embed("🎫 Abrir Ticket", "Escolha o assunto do seu atendimento abaixo:", discord.Color.blue())
        await interaction.response.send_message(embed=e, view=view, ephemeral=True)


def start_health_server():
    """Sobe um mini servidor HTTP na porta $PORT pra plataforma nao matar o bot."""
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args):
            pass

    port = int(os.getenv("PORT", "8000"))
    srv = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise SystemExit("Defina o DISCORD_TOKEN no arquivo .env")
    start_health_server()
    bot.run(DISCORD_TOKEN)
