"""Validation helpers for externally supplied Web Push endpoints."""

import ipaddress
import re
from urllib.parse import urlsplit


_LOCAL_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".lan",
    ".home.arpa",
    ".localdomain",
)


def is_safe_push_endpoint(endpoint: str) -> bool:
    """Accept HTTPS endpoints with public IP literals or syntactically valid DNS names.

    This is a conservative URL validation check, not a complete DNS-rebinding
    defense. It deliberately performs no DNS lookups or network requests.
    """
    if not isinstance(endpoint, str) or not endpoint:
        return False

    if any(character.isspace() or ord(character) < 32 for character in endpoint):
        return False

    try:
        parsed = urlsplit(endpoint)
        hostname = parsed.hostname
        port = parsed.port
    except (ValueError, UnicodeError):
        return False

    if parsed.scheme.lower() != "https":
        return False

    if not parsed.netloc or not hostname:
        return False

    if parsed.username is not None or parsed.password is not None:
        return False

    if parsed.fragment:
        return False

    if port not in (None, 443):
        return False

    host = hostname.rstrip(".").lower()

    if not host or host == "localhost":
        return False

    if any(host.endswith(suffix) for suffix in _LOCAL_SUFFIXES):
        return False

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None

    if address is not None:
        return address.is_global

    if "." not in host or len(host) > 253:
        return False

    labels = host.split(".")
    if any(
        not label
        or len(label) > 63
        or re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label) is None
        for label in labels
    ):
        return False

    return True
