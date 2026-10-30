"""
Discord Rich Presence (RPC) manager with smart throttling and auto-reconnect.
"""

import logging
import time
from typing import Optional, Dict, Any, List, Union
from pypresence import Presence, PipeClosed, DiscordNotFound, DiscordError, ActivityType

logger = logging.getLogger(__name__)

# Default public Russian Yandex Music application ID (well known, verified with assets)
DEFAULT_CLIENT_ID = "1217562797999784007"


def resolve_activity_type(val: Any) -> ActivityType:
    """Normalize input value to pypresence ActivityType enum."""
    if isinstance(val, ActivityType):
        return val
    if isinstance(val, str):
        v = val.lower().strip()
        if v in ("listening", "listen", "слушает", "слушать", "2"):
            return ActivityType.LISTENING
        elif v in ("playing", "play", "играет", "играть", "0"):
            return ActivityType.PLAYING
        elif v in ("watching", "watch", "смотрит", "смотреть", "3"):
            return ActivityType.WATCHING
        elif v in ("competing", "compete", "соревнуется", "5"):
            return ActivityType.COMPETING
    elif isinstance(val, int):
        try:
            return ActivityType(val)
        except ValueError:
            pass
    return ActivityType.LISTENING


class DiscordRpcManager:
    def __init__(
        self,
        client_id: str = DEFAULT_CLIENT_ID,
        min_update_interval: float = 3.0,
        enabled: bool = True,
        activity_type: Union[ActivityType, str, int] = ActivityType.LISTENING,
    ):
        self.client_id = client_id or DEFAULT_CLIENT_ID
        self.min_update_interval = min_update_interval
        self.enabled = enabled
        self.activity_type = resolve_activity_type(activity_type)

        self._rpc: Optional[Presence] = None
        self._is_connected = False
        self._last_connect_try = 0.0
        self._last_update_time = 0.0

        self._last_state: Optional[str] = None
        self._last_details: Optional[str] = None
        self._last_activity_type: Optional[ActivityType] = None
        self._pending_payload: Optional[Dict[str, Any]] = None

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def connect(self) -> bool:
        """Attempt to connect to Discord IPC socket."""
        if not self.enabled:
            return False

        now = time.time()
        # Don't hammer if Discord isn't running
        if now - self._last_connect_try < 4.0:
            return False

        self._last_connect_try = now
        try:
            if self._rpc is not None:
                try:
                    self._rpc.close()
                except Exception:
                    pass

            self._rpc = Presence(self.client_id)
            self._rpc.connect()
            self._is_connected = True
            logger.info("Connected to Discord RPC successfully.")
            return True
        except (DiscordNotFound, FileNotFoundError):
            self._is_connected = False
            logger.debug("Discord client not found / not running yet.")
            return False
        except Exception as e:
            self._is_connected = False
            logger.debug(f"Discord RPC connection error: {e}")
            return False

    def close(self):
        """Disconnect RPC cleanly."""
        if self._rpc and self._is_connected:
            try:
                self._rpc.clear()
                self._rpc.close()
            except Exception:
                pass
        self._is_connected = False
        self._rpc = None

    def update_presence(
        self,
        details: str,
        state: str,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        large_image: Optional[str] = None,
        large_text: Optional[str] = None,
        small_image: Optional[str] = None,
        small_text: Optional[str] = None,
        buttons: Optional[List[Dict[str, str]]] = None,
        activity_type: Optional[Union[ActivityType, str, int]] = None,
        force: bool = False,
    ) -> bool:
        """
        Queue or immediately send an RPC update respecting rate limits.
        """
        if not self.enabled:
            return False

        if not self._is_connected:
            if not self.connect():
                return False

        act_type = resolve_activity_type(activity_type) if activity_type is not None else self.activity_type

        # Format payload
        payload: Dict[str, Any] = {
            "activity_type": act_type,
            "details": details[:128] if details else None,
            "state": state[:128] if state else None,
            "start": start_timestamp,
            "end": end_timestamp,
            "large_image": large_image or "yandex_music",
            "large_text": large_text[:128] if large_text else "Яндекс Музыка",
            "small_image": small_image or "play",
            "small_text": small_text[:128] if small_text else "Воспроизведение",
        }
        if buttons:
            payload["buttons"] = buttons[:2]

        now = time.time()
        elapsed = now - self._last_update_time

        # Check if contents actually changed
        if (
            not force
            and state == self._last_state
            and details == self._last_details
            and act_type == self._last_activity_type
        ):
            return True

        if elapsed >= self.min_update_interval or force:
            return self._dispatch_update(payload)
        else:
            # Store pending update to dispatch as soon as timer allows
            self._pending_payload = payload
            return True

    def flush_pending(self) -> bool:
        """Called by main loop to send any queued updates when interval elapses."""
        if not self._pending_payload or not self._is_connected:
            return False

        now = time.time()
        if now - self._last_update_time >= self.min_update_interval:
            payload = self._pending_payload
            self._pending_payload = None
            return self._dispatch_update(payload)
        return False

    def clear(self):
        """Clear presence when music stops."""
        if self._is_connected and self._rpc:
            try:
                self._rpc.clear()
            except Exception:
                pass
        self._last_state = None
        self._last_details = None
        self._last_activity_type = None
        self._pending_payload = None

    def _dispatch_update(self, payload: Dict[str, Any]) -> bool:
        if not self._rpc:
            return False

        try:
            clean_args = {k: v for k, v in payload.items() if v is not None}
            self._rpc.update(**clean_args)
            self._last_update_time = time.time()
            self._last_state = payload.get("state")
            self._last_details = payload.get("details")
            self._last_activity_type = payload.get("activity_type")
            return True
        except (PipeClosed, BrokenPipeError, ConnectionResetError) as e:
            logger.warning(f"Discord RPC pipe closed: {e}")
            self._is_connected = False
            self._rpc = None
            return False
        except Exception as e:
            logger.warning(f"Failed to update Discord RPC: {e}")
            return False
