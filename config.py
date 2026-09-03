import os

from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

GUILD_ID = 1544808342021480492
BOT_ID = 1544889738996088872
STAFF_ROLE_NAME = os.getenv("STAFF_ROLE_NAME", "Equipe")
TICKET_CATEGORY_NAME = os.getenv("TICKET_CATEGORY_NAME", "Tickets")
TICKET_LOGS_NAME = os.getenv("TICKET_LOGS_NAME", "transcripts")
WELCOME_CHANNEL_NAME = os.getenv("WELCOME_CHANNEL_NAME", "boas-vindas")
AUTO_ROLE_NAME = os.getenv("AUTO_ROLE_NAME", "")

TICKET_CHANNEL_NAME_PREFIX = "ticket"

SUPPORT_TOPICS = [
    "compra",
    "venda",
    "suporte",
    "denuncia",
    "outro",
]
