from bot.log import log

try:
    from dotenv import load_dotenv
    log.debug("Found .env file, loading environment variables from it.")
    load_dotenv(override=True)
except ModuleNotFoundError:
    pass
