import re
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
    DEAL_CATEGORY_NAME,
    DEAL_CHANNEL_NAME_PREFIX,
    DEAL_LOGS_NAME,
    DEAL_TOPICS,
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
    bot.add_view(StaffPanelView())
    bot.add_view(DealPanelView())
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
    deal_cat = find_category(guild, DEAL_CATEGORY_NAME)
    if deal_cat is None:
        try:
            deal_cat = await guild.create_category(DEAL_CATEGORY_NAME)
        except discord.Forbidden:
            print(f"Sem permissao para criar categoria {DEAL_CATEGORY_NAME} em {guild.name}")
    if deal_cat is not None:
        vchannel = find_channel(guild, "vendas")
        if vchannel is None:
            try:
                vchannel = await guild.create_text_channel("vendas", category=deal_cat)
                await vchannel.edit(sync_permissions=False, overwrites={
                    guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False),
                    bot.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, embed_links=True, attach_files=True),
                })
            except discord.Forbidden:
                print(f"Sem permissao para criar canal de vendas em {guild.name}")
        if vchannel is not None:
            try:
                msgs_ok = vchannel.last_message_id is not None
                if not msgs_ok:
                    vview = DealPanelView()
                    vembed = make_embed("🛒 Vender ou Trocar", "Aqui voce pode **vender** ou **trocar** algo com a gente!\n\n**💰 Vender** — voce oferece um produto/servico e a gente paga por ele.\n**🔄 Trocar** — voce oferece algo e a gente oferece um produto nosso em troca.\n\nClique no botao abaixo para abrir a negociacao.\nNossa equipe analisa a sua proposta e responde aqui mesmo.\n\n📌 Regras: apenas negociacoes serias; sem spam; sem golpe.", discord.Color.gold())
                    await vchannel.send(embed=vembed, view=vview)
                    print("Painel de vendas publicado")
            except Exception as e:
                print(f"Falha ao publicar painel de vendas: {e}")
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
    e = make_embed(f"Bem-vindo(a) {member.display_name}! 🎉", f"Olá {member.mention}!, bem-vindo(a) ao **Pollar Vendas**!\n\nAqui voce encontra os melhores produtos e um atendimento de qualidade.\nPara abrir um ticket de suporte, denuncia ou outro, use os botoes abaixo no canal de tickets.\n\nAproveite a sua estadia! 😊", discord.Color.green())
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

@bot.command(name="painel")
async def staff_panel_command(ctx: commands.Context):
    if not ctx.guild or not is_staff(ctx.author):
        return await ctx.send("Voce nao tem permissao para usar este comando.")
    topic = "suporte"
    if ctx.channel and ctx.channel.name:
        parts = ctx.channel.name.split("-")
        if len(parts) > 1 and parts[1] in SUPPORT_TOPICS:
            topic = parts[1]
    user_id = None
    if ctx.channel.topic and ctx.channel.topic.startswith("ticket:"):
        try:
            user_id = int(ctx.channel.topic.split(":", 1)[1])
        except ValueError:
            user_id = None
    painel_staff = make_embed("🛡️ Painel da Equipe", "Use as ações abaixo para gerenciar este ticket.\n\n**🔒 Fechar** — encerra e salva o transcript.\n**👤 Usuário** — mostra quem abriu.\n**✏️ Renomear** — muda o nome do canal.\n**➕ Adicionar** — libera acesso a outro usuário.\n**➖ Remover** — tira o acesso de um usuário.\n**🔄 Passar** — transfere o ticket para outro staff.\n**✅ Finalizar** — conclui o atendimento e bloqueia o canal.", discord.Color.dark_teal())
    await ctx.send(embed=painel_staff, view=StaffPanelView(topic=topic, user_id=user_id))


@bot.command(name="vendas")
async def vendas_command(ctx: commands.Context):
    """Publica o painel de Vender/Trocar no canal atual."""
    if not ctx.guild or not is_staff(ctx.author):
        return await ctx.send("Voce nao tem permissao para usar este comando.")
    painel = make_embed("🛒 Vender ou Trocar", "Aqui voce pode **vender** ou **trocar** algo com a gente!\n\n**💰 Vender** — voce oferece um produto/servico e a gente paga por ele.\n**🔄 Trocar** — voce oferece algo e a gente oferece um produto nosso em troca.\n\nClique no botao abaixo para abrir a negociacao.\nNossa equipe analisa a sua proposta e responde aqui mesmo.\n\n📌 Regras: apenas negociacoes serias; sem spam; sem golpe.", discord.Color.gold())
    await ctx.send(embed=painel, view=DealPanelView())


def ticket_panel_embed():
    return make_embed("🎫 Central de Suporte", "Bem-vindo(a) a central de atendimento **Pollar Vendas**!\n\nEscolha o assunto do seu atendimento para abrir um ticket.\nUm membro da nossa equipe ira atende-lo em breve.\n\n📌 **Disponivel 24/7** para melhor atende-lo!", discord.Color.blue())


def welcome_embed():
    return make_embed("👋 Bem-vindo(a) ao Pollar Vendas!", "Aqui voce encontra produtos de qualidade e atendimento rapido.\nUse o **painel de tickets** para falar com o suporte, denunciar ou outro.\n\n**Pollar Vendas** - a sua melhor escolha! 🚀", discord.Color.green())



class DealTopicView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for topic in DEAL_TOPICS:
            self.add_item(DealButton(topic))

class DealButton(discord.ui.Button[str]):
    def __init__(self, topic: str):
        labels = {"vender": "💰 Vender", "trocar": "🔄 Trocar"}
        styles = {"vender": discord.ButtonStyle.success, "trocar": discord.ButtonStyle.primary}
        super().__init__(
            label=labels.get(topic, topic.title()),
            style=styles.get(topic, discord.ButtonStyle.secondary),
            custom_id="deal:".format(topic),
        )
        self.topic = topic

    async def callback(self, interaction: discord.Interaction):
        user: discord.Member = interaction.user
        guild = interaction.guild
        existing = ticket_channel_for(guild, user.id)
        if existing:
            return await interaction.response.send_message("Voce ja tem um ticket aberto: {}".format(existing.mention), ephemeral=True)
        category = find_category(guild, DEAL_CATEGORY_NAME)
        if category is None:
            try:
                category = await guild.create_category(DEAL_CATEGORY_NAME)
            except discord.Forbidden:
                return await interaction.response.send_message("Sem permissao para criar a categoria.", ephemeral=True)
        logs_channel = find_channel(guild, DEAL_LOGS_NAME)
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, manage_messages=True, read_message_history=True)
        username = "".join(c if c.isalnum() or c in "-_" else "-" for c in user.name.lower().replace(" ", "-"))
        channel_name = "{}-{}-{}".format(DEAL_CHANNEL_NAME_PREFIX, self.topic, username)
        try:
            channel = await guild.create_text_channel(name=channel_name, category=category, topic="deal:{}:{}".format(user.id, self.topic), overwrites=overwrites)
        except discord.Forbidden:
            return await interaction.response.send_message("Sem permissao para criar a negociacao.", ephemeral=True)
        if self.topic == "vender":
            e = make_embed("💰 Vender", "Ola {0}!, conte para a gente o que voce quer **vender** e o **valor** desejado.".format(user.mention, discord.Color.gold()))
        else:
            e = make_embed("🔄 Trocar", "Ola {0}!, conte o que voce quer **trocar** e o que voce deseja em troca.".format(user.mention, discord.Color.blue()))
        view = TicketCloseView(topic=self.topic, user_id=user.id)
        await channel.send(user.mention, embed=e, view=view)
        link_view = discord.ui.View()
        link_view.add_item(discord.ui.Button(label="📍 Ir para a negociacao", style=discord.ButtonStyle.link, url=channel.jump_url))
        if logs_channel:
            log_e = make_embed("🆕 Nova Negociacao: {}".format(self.topic.title()), "**Usuario:** {0} ({1})".format(user.mention, user.id), discord.Color.gold())
            await logs_channel.send(embed=log_e, view=link_view)
        await interaction.response.send_message("Negociacao criada: {}".format(channel.mention), ephemeral=True, view=link_view)

class DealPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DealButton("vender"))
        self.add_item(DealButton("trocar"))
        self.add_item(DealPanelStaffButton())

class DealPanelStaffButton(discord.ui.Button[str]):
    def __init__(self):
        super().__init__(label="🛡️ Painel da Equipe", style=discord.ButtonStyle.secondary, custom_id="deal:staff")

    async def callback(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Voce nao tem permissao para acessar o painel.", ephemeral=True)
        painel_staff = make_embed("🛡️ Painel da Equipe", "Use as acoes abaixo para gerenciar esta negociacao.\n\n**🔒 Fechar** — encerra e salva o transcript.\n**👤 Usuario** — mostra quem abriu.\n**✏️ Renomear** — muda o nome do canal.\n**➕ Adicionar** — libera acesso a outro usuario.\n**➖ Remover** — tira o acesso de um usuario.\n**🔄 Passar** — transfere para outro staff.\n**✅ Finalizar** — conclui e bloqueia o canal.", discord.Color.dark_teal())
        await interaction.response.send_message(embed=painel_staff, view=StaffPanelView(topic=self.topic, user_id=interaction.user.id), ephemeral=True)

class TicketTopicView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for topic in SUPPORT_TOPICS:
            self.add_item(TicketButton(topic))


class TicketButton(discord.ui.Button[str]):
    def __init__(self, topic: str):
        labels = {
            "suporte": "🛠️ Suporte",
            "denuncia": "🚨 Denúncia",
            "outro": "📦 Outro",
        }
        styles = {
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
        link_view = discord.ui.View()
        link_view.add_item(discord.ui.Button(label="📍 Ir para o ticket", style=discord.ButtonStyle.link, url=channel.jump_url))
        if logs_channel:
            log_e = make_embed(f"🆕 Novo Ticket: {self.topic.title()}", f"**Usuario:** {user.mention} ({user.id})\n**Canal:** {channel.mention}\n**Aberto em:** {discord.utils.format_dt(discord.utils.utcnow())}", discord.Color.green())
            await logs_channel.send(embed=log_e, view=link_view)
        await interaction.response.send_message(f"Ticket criado: {channel.mention}", ephemeral=True, view=link_view)





def ticket_link_view(channel: discord.TextChannel) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="📍 Ir para o ticket", style=discord.ButtonStyle.link, url=channel.jump_url))
    return view

class StaffUserButton(discord.ui.Button[str]):
    def __init__(self, user_id: int):
        super().__init__(label="👤 Usuário", style=discord.ButtonStyle.primary, custom_id="staff:user")
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Sem permissao para usar o painel.", ephemeral=True)
        user = interaction.guild.get_member(self.user_id)
        if user is None:
            return await interaction.response.send_message(f"👤 Usuário do ticket: ID `{self.user_id}` (nao esta mais no servidor.)", ephemeral=True)
        await interaction.response.send_message(f"👤 **Usuário do ticket:** {user.mention} (`{user.id}`)", ephemeral=True)

class StaffRenameButton(discord.ui.Button[str]):
    def __init__(self):
        super().__init__(label="✏️ Renomear", style=discord.ButtonStyle.secondary, custom_id="staff:rename")

    async def callback(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Sem permissao para usar o painel.", ephemeral=True)
        await interaction.response.send_modal(RenameTicketModal())

class RenameTicketModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Renomear canal do ticket")
        self.novo_nome = discord.ui.TextInput(label="Novo nome do canal", placeholder="ex: ticket-suporte-fulano", max_length=80, required=True, custom_id="rename_name")
        self.add_item(self.novo_nome)

    async def on_submit(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Sem permissao.", ephemeral=True)
        canal = interaction.channel
        nome = self.novo_nome.value.strip().lower().replace(" ", "-")
        nome = "".join(c for c in nome if c.isalnum() or c in "-_")
        if len(nome) < 2:
            return await interaction.response.send_message("Nome invalido para o canal.", ephemeral=True)
        try:
            await canal.edit(name=nome)
            logs = find_channel(interaction.guild, TICKET_LOGS_NAME)
            if logs:
                await logs.send(embed=make_embed("✏️ Canal renomeado", f"**Canal:** {canal.mention}\n**Novo nome:** `{nome}`\n**Por:** {interaction.user.mention}", discord.Color.blue()))
            await interaction.response.send_message(f"Canal renomeado para **{nome}**! ✅", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Sem permissao para renomear o canal.", ephemeral=True)

class StaffAddButton(discord.ui.Button[str]):
    def __init__(self):
        super().__init__(label="➕ Adicionar", style=discord.ButtonStyle.success, custom_id="staff:add")

    async def callback(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Sem permissao para usar o painel.", ephemeral=True)
        await interaction.response.send_modal(AddUserTicketModal())

class AddUserTicketModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Adicionar usuário ao ticket")
        self.user_input = discord.ui.TextInput(label="ID ou menção do usuário", placeholder="ex: 123456789012345678 ou @fulano", required=True, custom_id="add_user")
        self.add_item(self.user_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Sem permissao.", ephemeral=True)
        target = await _resolve_user(interaction, self.user_input.value)
        if target is None:
            return await interaction.response.send_message("Usuário não encontrado. Envie o ID ou a menção.", ephemeral=True)
        await interaction.channel.set_permissions(target, view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
        logs = find_channel(interaction.guild, TICKET_LOGS_NAME)
        if logs:
            await logs.send(embed=make_embed("➕ Usuário adicionado", f"**Ticket:** {interaction.channel.mention}\n**Usuário:** {target.mention} (`{target.id}`)\n**Por:** {interaction.user.mention}", discord.Color.green()))
        await interaction.response.send_message(f"✅ {target.mention} adicionado ao ticket!", ephemeral=True)

class StaffRemoveButton(discord.ui.Button[str]):
    def __init__(self, user_id: int):
        super().__init__(label="➖ Remover", style=discord.ButtonStyle.danger, custom_id="staff:remove")
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Sem permissao para usar o painel.", ephemeral=True)
        await interaction.response.send_modal(RemoveUserTicketModal(self.user_id))

class RemoveUserTicketModal(discord.ui.Modal):
    def __init__(self, owner_id: int):
        super().__init__(title="Remover usuário do ticket")
        self.user_input = discord.ui.TextInput(label="ID ou menção do usuário", placeholder="ex: 123456789012345678 ou @fulano", required=True, custom_id="remove_user")
        self.add_item(self.user_input)
        self.owner_id = owner_id

    async def on_submit(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Sem permissao.", ephemeral=True)
        target = await _resolve_user(interaction, self.user_input.value)
        if target is None:
            return await interaction.response.send_message("Usuário não encontrado. Envie o ID ou a menção.", ephemeral=True)
        if target.id == self.owner_id:
            return await interaction.response.send_message("❌ Não é possível remover o dono do ticket.", ephemeral=True)
        await interaction.channel.set_permissions(target, overwrite=None)
        logs = find_channel(interaction.guild, TICKET_LOGS_NAME)
        if logs:
            await logs.send(embed=make_embed("➖ Usuário removido", f"**Ticket:** {interaction.channel.mention}\n**Usuário:** {target.mention} (`{target.id}`)\n**Por:** {interaction.user.mention}", discord.Color.red()))
        await interaction.response.send_message(f"➖ {target.mention} removido do ticket.", ephemeral=True)

async def _resolve_user(interaction: discord.Interaction, raw: str) -> discord.Member:
    raw = raw.strip()
    m = re.search(r"<@!?(\d+)>", raw)
    if m:
        user_id = int(m.group(1))
    else:
        try:
            user_id = int(raw)
        except ValueError:
            return None
    member = interaction.guild.get_member(user_id)
    if member is None:
        try:
            member = await interaction.guild.fetch_member(user_id)
        except discord.NotFound:
            return None
    return member

class StaffPanelView(discord.ui.View):
    def __init__(self, topic: str = "suporte", user_id: int = None):
        super().__init__(timeout=None)
        self.add_item(StaffUserButton(user_id))
        self.add_item(StaffRenameButton())
        self.add_item(StaffAddButton())
        self.add_item(StaffRemoveButton(user_id))
        self.add_item(PassTicketButton())
        self.add_item(FinishTicketButton(topic, user_id))
        self.add_item(CloseTicketButton(topic, user_id))

class TicketCloseView(discord.ui.View):
    def __init__(self, topic: str, user_id: int):
        super().__init__(timeout=None)
        self.topic = topic
        self.user_id = user_id
        self.add_item(CloseTicketButton(topic, user_id))



class PassTicketButton(discord.ui.Button[str]):
    def __init__(self):
        super().__init__(label="🔄 Passar Ticket", style=discord.ButtonStyle.primary, custom_id="staff:pass")

    async def callback(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Sem permissao para usar o painel.", ephemeral=True)
        await interaction.response.send_modal(PassTicketModal())

class PassTicketModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Passar ticket para outro staff")
        self.target = discord.ui.TextInput(label="ID ou menção do staff", placeholder="ex: 123456789012345678 ou @staff", required=True, custom_id="pass_target")
        self.add_item(self.target)

    async def on_submit(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Sem permissao.", ephemeral=True)
        target = await _resolve_user(interaction, self.target.value)
        if target is None:
            return await interaction.response.send_message("Usuário não encontrado. Envie o ID ou a menção.", ephemeral=True)
        if not is_staff(target):
            return await interaction.response.send_message("❌ O usuário informado não é da equipe (staff).", ephemeral=True)
        await interaction.channel.set_permissions(target, view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
        logs = find_channel(interaction.guild, TICKET_LOGS_NAME)
        if logs:
            await logs.send(embed=make_embed("🔄 Ticket passado", f"**Ticket:** {interaction.channel.mention}\n**De:** {interaction.user.mention}\n**Para:** {target.mention} (`{target.id}`)", discord.Color.blue()))
        await interaction.channel.send(f"🔔 {target.mention}, você foi designado para assumir este ticket!")
        await interaction.response.send_message(f"🔄 Ticket passado para {target.mention}!", ephemeral=True)

class FinishTicketButton(discord.ui.Button[str]):
    def __init__(self, topic: str, user_id: int):
        super().__init__(label="✅ Finalizar Ticket", style=discord.ButtonStyle.success, custom_id=f"finish:{topic}")
        self.topic = topic
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Sem permissao para usar o painel.", ephemeral=True)
        channel = interaction.channel
        if "finalizado" in channel.name:
            return await interaction.response.send_message("Este ticket ja foi finalizado.", ephemeral=True)
        user = interaction.guild.get_member(self.user_id)
        try:
            await channel.edit(name=channel.name.replace("ticket", "finalizado", 1))
            if user:
                await channel.set_permissions(user, view_channel=True, send_messages=False, read_message_history=True, attach_files=False)
        except discord.Forbidden:
            await interaction.response.send_message("Sem permissao para finalizar o ticket.", ephemeral=True)
            return
        await channel.send(embed=make_embed("✅ Ticket finalizado", "O atendimento foi concluído. O canal ficou disponível apenas para leitura. Obrigado pelo contato!", discord.Color.green()))
        logs = find_channel(interaction.guild, TICKET_LOGS_NAME)
        if logs:
            transcript = await build_transcript(channel, interaction.user)
            log_e = make_embed(f"✅ Ticket Finalizado: {self.topic.title()}", f"**Usuario:** <@{self.user_id}> ({self.user_id})\n**Canal:** {channel.mention}\n**Finalizado por:** {interaction.user.mention}\n**Em:** {discord.utils.format_dt(discord.utils.utcnow())}", discord.Color.green())
            if transcript:
                log_e.add_field(name="📜 Transcricao", value=transcript[:1024], inline=False)
            await logs.send(embed=log_e)
        await interaction.response.send_message("Ticket finalizado! ✅ (use 🔒 Fechar para apagar o canal)", ephemeral=True)

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
