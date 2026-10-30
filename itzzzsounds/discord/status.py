"""
Discord Custom Status manager (updates the status bubble next to user avatar via User Token).
"""

import logging
import time
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


class DiscordStatusManager:
    def __init__(
        self,
        auth_token: Optional[str] = None,
        min_update_interval: float = 3.0,
        emoji_name: str = "🎵",
        enabled: bool = False,
    ):
        self.auth_token = auth_token
        self.min_update_interval = min_update_interval
        self.emoji_name = emoji_name
        self.enabled = bool(enabled and auth_token)

        self._session = requests.Session()
        self._last_update_time = 0.0
        self._rate_limited_until = 0.0
        self._last_text: Optional[str] = None
        self._pending_text: Optional[str] = None
        self._original_status: Optional[Dict[str, Any]] = None
        self._has_saved_original = False

        if self.enabled:
            self._fetch_current_status()

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": self.auth_token or "",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
        }

    def _fetch_current_status(self):
        """Fetch and store current status to restore on program exit."""
        if not self.enabled or self._has_saved_original:
            return
        try:
            resp = self._session.get(
                "https://discord.com/api/v9/users/@me/settings",
                headers=self._get_headers(),
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                self._original_status = data.get("custom_status")
                self._has_saved_original = True
                logger.info("Saved original custom status for restoration on exit.")
        except Exception as e:
            logger.debug(f"Could not fetch initial custom status: {e}")

    def update_status(self, text: str, force: bool = False) -> bool:
        """Queue or send a custom status update."""
        if not self.enabled:
            return False

        now = time.time()
        if now < self._rate_limited_until:
            self._pending_text = text
            return False

        # Clean text
        text = text[:128].strip()
        if not force and text == self._last_text:
            return True

        elapsed = now - self._last_update_time
        if elapsed >= self.min_update_interval or force:
            return self._dispatch_status(text)
        else:
            self._pending_text = text
            return True

    def flush_pending(self) -> bool:
        """Dispatch any queued status if the rate-limit interval has passed."""
        if not self._pending_text or not self.enabled:
            return False

        now = time.time()
        if now < self._rate_limited_until:
            return False

        if now - self._last_update_time >= self.min_update_interval:
            text = self._pending_text
            self._pending_text = None
            return self._dispatch_status(text)
        return False

    def clear(self):
        """Clear or restore user's status."""
        if not self.enabled:
            return
        try:
            payload = {"custom_status": self._original_status}
            self._session.patch(
                "https://discord.com/api/v9/users/@me/settings",
                headers=self._get_headers(),
                json=payload,
                timeout=5,
            )
            self._last_text = None
            self._pending_text = None
        except Exception as e:
            logger.debug(f"Error restoring original status: {e}")

    def _dispatch_status(self, text: str) -> bool:
        try:
            payload = {
                "custom_status": {
                    "text": text,
                    "emoji_name": self.emoji_name if self.emoji_name else None,
                }
            }
            resp = self._session.patch(
                "https://discord.com/api/v9/users/@me/settings",
                headers=self._get_headers(),
                json=payload,
                timeout=5,
            )

            if resp.status_code == 200:
                self._last_update_time = time.time()
                self._last_text = text
                return True
            elif resp.status_code == 429:
                retry_after = 5.0
                try:
                    data = resp.json()
                    retry_after = float(data.get("retry_after", 5.0))
                except Exception:
                    pass
                self._rate_limited_until = time.time() + retry_after + 0.5
                logger.warning(f"Discord Custom Status rate limited. Backing off for {retry_after}s.")
                return False
            else:
                logger.warning(f"Failed to update Custom Status: HTTP {resp.status_code}")
                return False
        except Exception as e:
            logger.warning(f"Exception during status update: {e}")
            return False
