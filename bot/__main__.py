import logging

from bot.bot import TOKEN, bot

log = logging.getLogger(__name__)


bot.load_extension("bot.exts.ping")

bot.run(TOKEN)
