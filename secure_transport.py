"""Credential-bearing HTTPS requests: fixed hosts, no redirects, bounded JSON."""

import json
import ssl
import urllib.parse
import urllib.request

HOSTS = frozenset({"api.binance.com", "api.openai.com"})


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def secure_json(request, timeout=15, max_bytes=1_048_576, allowed_hosts=HOSTS):
    url = urllib.parse.urlsplit(request.full_url)
    if (
        url.scheme != "https"
        or url.hostname not in allowed_hosts
        or url.username
        or url.password
        or url.port not in (None, 443)
        or url.fragment
    ):
        raise ValueError("Credential destination is not permitted")
    opener = urllib.request.build_opener(
        NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context())
    )
    with opener.open(request, timeout=timeout) as response:
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("Response exceeded the accepted size")
    value = json.loads(raw)
    if not isinstance(value, (dict, list)):
        raise ValueError("Unexpected JSON document type")
    return value
