from typing import Optional

from aiohttp import ClientConnectorError
from botcore.utils.logging import get_logger

from bot.bot import bot

log = get_logger(__name__)

FAILED_REQUEST_ATTEMPTS = 3
PASTE_SERVICE = "https://paste.pythondiscord.com/{key}"


async def send_to_paste_service(contents: str, *, extension: str = "") -> Optional[str]:
    """
    Upload `contents` to the paste service.

    `extension` is added to the output URL before being returned. When an error occurs,
    `None` is returned, otherwise the generated URL with the suffix.
    """
    extension = extension and f".{extension}"
    log.debug(f"Sending contents of size {len(contents.encode())} bytes to paste service.")
    paste_url = PASTE_SERVICE.format(key="documents")
    for attempt in range(1, FAILED_REQUEST_ATTEMPTS + 1):
        try:
            async with bot.http_session.post(paste_url, data=contents) as response:
                response_json = await response.json()
        except ClientConnectorError:
            log.warning(
                f"Failed to connect to paste service at url {paste_url}, "
                f"trying again ({attempt}/{FAILED_REQUEST_ATTEMPTS})."
            )
            continue
        except Exception:
            log.exception(
                f"An unexpected error has occurred during handling of the request, "
                f"trying again ({attempt}/{FAILED_REQUEST_ATTEMPTS})."
            )
            continue

        if "message" in response_json:
            log.warning(
                f"Paste service returned error {response_json['message']} with status code {response.status}, "
                f"trying again ({attempt}/{FAILED_REQUEST_ATTEMPTS})."
            )
            continue
        elif "key" in response_json:
            log.info(f"Successfully uploaded contents to paste service behind key {response_json['key']}.")

            paste_link = PASTE_SERVICE.format(key=response_json['key']) + extension

            if extension == '.py':
                return paste_link

            return paste_link + "?noredirect"

        log.warning(
            f"Got unexpected JSON response from paste service: {response_json}\n"
            f"trying again ({attempt}/{FAILED_REQUEST_ATTEMPTS})."
        )
