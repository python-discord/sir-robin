from bot.bot import bot
from bot.constants import Client

bot.load_extension("bot.exts.ping")

bot.run(Client.token)
