"""Shared HTTP helper for external APIs.

Every outside call goes through here so timeouts, retries and error
messages behave the same everywhere.
"""

import time

import requests

DEFAULT_TIMEOUT = 10
MAX_ATTEMPTS = 2  # one try + one retry
USER_AGENT = "SmartHealthAssistant/1.0 (university project)"


class ExternalAPIError(Exception):
    """Raised when an external API cannot give a usable answer."""

    def __init__(self, service, message):
        self.service = service
        self.message = message
        super().__init__(f"{service}: {message}")


def get_json(service, url, params=None, timeout=DEFAULT_TIMEOUT):
    """GET a URL and return parsed JSON. Retries once on network errors and 5xx."""
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=timeout,
                headers={"User-Agent": USER_AGENT},
            )

            if response.status_code >= 500 and attempt < MAX_ATTEMPTS:
                time.sleep(1)
                continue

            if response.status_code == 404:
                raise ExternalAPIError(service, "not found")

            if response.status_code >= 400:
                raise ExternalAPIError(
                    service, f"HTTP {response.status_code} from service"
                )

            try:
                return response.json()
            except ValueError:
                raise ExternalAPIError(service, "response was not valid JSON")

        except requests.Timeout:
            last_error = f"timed out after {timeout}s"
        except requests.ConnectionError:
            last_error = "could not connect (check your internet)"
        except requests.RequestException as exc:
            last_error = f"request failed: {exc.__class__.__name__}"

        if attempt < MAX_ATTEMPTS:
            time.sleep(1)

    raise ExternalAPIError(service, last_error or "unknown error")