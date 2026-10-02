"""Bounded public-image downloads for administrator-supplied card URLs.

The resolver checks the exact addresses used by the connector (not a separate
preflight DNS lookup). Redirects are revalidated and internal/local addresses,
credentials, custom ports and oversized responses fail closed.
"""

import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import aiohttp
from aiohttp.abc import AbstractResolver
from aiohttp.resolver import ThreadedResolver

MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _public_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    if isinstance(address, ipaddress.IPv6Address):
        # Transition/scoped addresses can embed an otherwise blocked IPv4
        # target; public native IPv6 only is allowed.
        if address.ipv4_mapped or address.sixtofour or address.teredo or "%" in value:
            return False
        if address in ipaddress.ip_network("64:ff9b::/96"):
            return False
    return address.is_global and not address.is_multicast


def validate_image_url(url: str) -> str:
    """Validate URL syntax/literal hosts without resolving or fetching it."""
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Image must use a public HTTP(S) URL")
    if parts.username is not None or parts.password is not None:
        raise ValueError("Image URL credentials are not allowed")
    if parts.port not in {None, 443 if parts.scheme == "https" else 80}:
        raise ValueError("Image URL must use a standard HTTP(S) port")
    host = parts.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local image hosts are not allowed")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        # Names are checked against their actual connection addresses below.
        return url
    if not _public_address(host):
        raise ValueError("Private or reserved image addresses are not allowed")
    return url


class _PublicResolver(AbstractResolver):
    def __init__(self):
        self._resolver = ThreadedResolver()

    async def resolve(self, host, port=0, family=socket.AF_INET):
        addresses = await self._resolver.resolve(host, port, family)
        if not addresses or any(not _public_address(item["host"]) for item in addresses):
            raise OSError("Image host does not resolve exclusively to public addresses")
        return addresses

    async def close(self):
        await self._resolver.close()


async def download_public_image(url: str) -> bytes:
    """Fetch at most 5 MiB, allowing only public targets on every redirect.

    Disables automatic decompression (auto_decompress=False) and requests
    identity encoding to prevent decompression bombs before byte-limit checks.
    """
    current = validate_image_url(url)
    resolver = _PublicResolver()
    connector = aiohttp.TCPConnector(resolver=resolver)
    try:
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=10),
            trust_env=False,
            auto_decompress=False,
            headers={"Accept-Encoding": "identity"},
        ) as session:
            for _ in range(6):
                async with session.get(current, allow_redirects=False) as response:
                    # Reject non-identity content encoding (gzip, deflate, etc.)
                    content_encoding = response.headers.get("Content-Encoding", "").lower()
                    if content_encoding and content_encoding != "identity":
                        raise ValueError(f"Content-Encoding '{content_encoding}' not allowed; only identity supported")
                    if response.status in {301, 302, 303, 307, 308}:
                        location = response.headers.get("Location")
                        if not location:
                            raise ValueError("Image redirect has no destination")
                        current = validate_image_url(urljoin(current, location))
                        continue
                    response.raise_for_status()
                    if response.content_length is not None and response.content_length > MAX_IMAGE_BYTES:
                        raise ValueError("Image exceeds the size limit")
                    chunks = []
                    length = 0
                    async for chunk in response.content.iter_chunked(64 * 1024):
                        length += len(chunk)
                        if length > MAX_IMAGE_BYTES:
                            raise ValueError("Image exceeds the size limit")
                        chunks.append(chunk)
                    return b"".join(chunks)
            raise ValueError("Image has too many redirects")
    finally:
        await resolver.close()
