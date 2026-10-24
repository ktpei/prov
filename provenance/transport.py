"""Bounded JSON requests to fixed API endpoints; no automatic retries."""

import http.client
import json
import urllib.error
import urllib.request


class ProviderError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderError("API redirects are disabled")


def post_json(url, payload, headers, timeout):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, allow_nan=False).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=timeout) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ProviderError("API response exceeds 2 MB limit")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ProviderError("API response must be an object")
        return result
    except urllib.error.HTTPError as exc:
        # Never include provider response bodies, headers, or credentials in logs.
        raise ProviderError(f"API HTTP {exc.code}; no automatic retry") from None
    except (OSError, http.client.HTTPException, json.JSONDecodeError, UnicodeError):
        raise ProviderError("API network, timeout, or JSON error; no automatic retry") from None
