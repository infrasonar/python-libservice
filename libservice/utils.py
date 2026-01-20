import asyncio
import warnings
import ssl
from urllib.parse import urlparse
from typing import TYPE_CHECKING
from .addr import addr_check
from .exceptions import TooManyRedirects, RedirectsNotAllowed
if TYPE_CHECKING:
    import aiohttp
try:
    import aiohttp as _aiohttp
except ImportError:
    _aiohttp = None


def _item_name(item: dict) -> str:
    return item['name']


def order(result: dict):
    """Order result items by item name."""
    for items in result.values():
        items.sort(key=_item_name)


warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message="ssl.TLSVersion.TLSv1 is deprecated"
)

# Allow unsafe legacy renegotiation when verify SSL is disabled
SSL_OP_NO_UNSAFE_LEGACY_RENEGOTIATION = 0x00040000
SSL_CONTEXT_UNSAFE_NO_CHECK = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
SSL_CONTEXT_UNSAFE_NO_CHECK.options &= \
    ~SSL_OP_NO_UNSAFE_LEGACY_RENEGOTIATION
SSL_CONTEXT_UNSAFE_NO_CHECK.check_hostname = False
SSL_CONTEXT_UNSAFE_NO_CHECK.verify_mode = ssl.CERT_NONE
SSL_CONTEXT_UNSAFE_NO_CHECK.minimum_version = ssl.TLSVersion.TLSv1
SSL_CONTEXT_UNSAFE_NO_CHECK.set_ciphers('DEFAULT@SECLEVEL=0')
MAX_REDIRECTS = 5


def get_connector(verify_ssl: bool,
                  loop: asyncio.AbstractEventLoop | None = None
                  ) -> 'aiohttp.TCPConnector':
    if _aiohttp is None:
        raise ImportError("aiohttp is not installed")

    if loop is None:
        loop = asyncio.get_running_loop()

    ssl_context: bool | ssl.SSLContext = True
    if verify_ssl is False:
        ssl_context = SSL_CONTEXT_UNSAFE_NO_CHECK

    return _aiohttp.TCPConnector(
        limit=100,  # 100 is default
        use_dns_cache=False,
        enable_cleanup_closed=True,
        force_close=True,
        ssl=ssl_context,
        loop=loop,
    )


async def safe_get(uri: str,
                   user_agent: str = 'InfraSonar-Service',
                   timeout: float | None = None,
                   verify_ssl: bool = False,
                   allow_redirects: bool | int = False,
                   loop: asyncio.AbstractEventLoop | None = None
                   ) -> 'aiohttp.ClientResponse':
    """
    Performs a GET request while validating redirects to prevent SSRF.
    """
    if _aiohttp is None:
        raise ImportError("aiohttp is not installed")
    current_uri = uri
    aiohttp_timeout = _aiohttp.ClientTimeout(total=timeout)
    connector = get_connector(verify_ssl, loop=loop)
    max_redirects = MAX_REDIRECTS \
        if allow_redirects is True else \
        1 if allow_redirects is False else max(1, allow_redirects)

    async with _aiohttp.ClientSession(timeout=aiohttp_timeout,
                                      connector=connector,
                                      headers={'User-Agent': user_agent}
                                      ) as session:
        for _ in range(max_redirects):
            await addr_check(current_uri)
            async with session.get(current_uri,
                                   allow_redirects=False) as resp:
                if allow_redirects is False or \
                        resp.status not in (301, 302, 303, 307, 308):
                    return resp
                next_url = resp.headers.get('Location')
                if not next_url:
                    break
                if not next_url.startswith('http'):
                    base = urlparse(current_uri)
                    current_uri = \
                        f"{base.scheme}://{base.netloc}{next_url}"
                else:
                    current_uri = next_url
                continue

    raise TooManyRedirects('Too many redirects')
