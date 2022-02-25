from bot.bot import bot
from bot.constants import Client

bot.load_extension("bot.exts.ping")

if not Client.in_ci:
    bot.run(Client.token)
