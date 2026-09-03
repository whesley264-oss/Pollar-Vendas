import discord

from config import STAFF_ROLE_NAME, TICKET_CATEGORY_NAME


def is_staff(member: discord.Member) -> bool:
    """Return True if the member has the staff role."""
    return any(r.name == STAFF_ROLE_NAME or r.permissions.administrator for r in member.roles)


def make_embed(title: str, description: str = "", color: discord.Color = discord.Color.blue()) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color)
    e.set_footer(text="Pollar Vendas")
    return e


def find_category(guild: discord.Guild, name: str) -> discord.CategoryChannel:
    return discord.utils.get(guild.categories, name=name)


def find_channel(guild: discord.Guild, name: str) -> discord.TextChannel:
    return discord.utils.get(guild.text_channels, name=name)


def find_role(guild: discord.Guild, name: str) -> discord.Role:
    return discord.utils.get(guild.roles, name=name)


def ticket_channel_for(guild: discord.Guild, user_id: int) -> discord.TextChannel:
    category = find_category(guild, TICKET_CATEGORY_NAME)
    if not category:
        return None
    for channel in category.channels:
        if isinstance(channel, discord.TextChannel) and channel.topic == f"ticket:{user_id}":
            return channel
    return None
