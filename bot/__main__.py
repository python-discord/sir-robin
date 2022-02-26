from botcore.utils.extensions import walk_extensions

from bot import exts
from bot.bot import bot
from bot.constants import Client

for extension in walk_extensions(exts):
    bot.load_extension(extension)


if not Client.in_ci:
    bot.run(Client.token)
