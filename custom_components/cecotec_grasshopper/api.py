"""Cecotec GrassHopper cloud API client.

Communicates with the sk-robot.com OEM backend that powers the
"Conga GrassHopper 500 Map" app (es.cecotec.congagrasshopper500map).

Protocol notes
--------------
* Auth:  POST /auth/oauth/token  (OAuth2 password grant)
* Devices: GET /mower/device-user/list
* Commands: POST /mower/device/operate  (body: {"deviceSn": ..., "operate": N})
* State is pushed via MQTT; polling /mower/device/detail is the fallback.

TODO: If login fails against URL_CECOTEC, the app may use a white-labelled
      host.  Capture traffic from the app with mitmproxy to confirm:
        adb shell settings put global http_proxy <your-pc-ip>:8080
      Look for POST /auth/oauth/token and note the Host header.
"""

from __future__ import annotations

import logging
from threading import Timer
from typing import Any

import requests

from .const import (
    HOST_CECOTEC,
    PATH_AUTH,
    PATH_DEVICE_LIST,
    URL_CECOTEC,
)

_LOGGER = logging.getLogger(__name__)

# OAuth2 Basic auth header — same value used by all sk-robot OEM apps
_BASIC_AUTH = "Basic YXBwOmFwcA=="

# Operate codes sent to /mower/device/operate
CMD_START = 1
CMD_PAUSE = 2
CMD_HOME = 3
CMD_BORDER = 4


class GrassHopperDevice:
    """Represents a single mower returned by the device list."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self.device_sn: str = raw["deviceSn"]
        self.device_id: str = raw.get("deviceId", "")
        self.name: str = raw.get("deviceName", self.device_sn)
        self.model: str = raw.get("deviceModelName", "GrassHopper 500")
        self.firmware: str = raw.get("firmwareVersion", "")
        self.wifi_address: str = raw.get("ipAddr", "")
        self.bluetooth_mac: str = raw.get("bluetoothMac", "")

        # Store raw API response for state parsing
        self.raw_data: dict[str, Any] = raw

        # Mutable state — updated by coordinator
        self.mode: int = int(raw.get("workStatusCode", 0))
        self.battery: int = int(raw.get("electricity", 0))
        self.wifi_level: int = int(raw.get("wifiLv", 0))
        self.error_code: int = 0 if raw.get("faultStatusCode") == "normal" else int(raw.get("faultStatusCode", 0))
        self.error_text: str = raw.get("faultStatusName", "") or ""
        self.online: bool = bool(raw.get("deviceOnlineFlag", False))


class GrassHopperAPI:
    """Thin wrapper around the sk-robot REST API."""

    def __init__(self, email: str, password: str, language: str = "en") -> None:
        self._email = email
        self._password = password
        self._language = language
        self._session: dict[str, Any] = {}
        self._refresh_timer: Timer | None = None
        self.login_ok: bool = False
        self.devices: list[GrassHopperDevice] = []

    # ── Auth ──────────────────────────────────────────────────────────────────

    def login(self) -> bool:
        """Perform OAuth2 password-grant login. Returns True on success."""
        try:
            response = requests.post(
                url=URL_CECOTEC + PATH_AUTH,
                headers={
                    "Accept-Language": self._language,
                    "Authorization": _BASIC_AUTH,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Connection": "Keep-Alive",
                    "User-Agent": "okhttp/4.8.1",
                    "Host": HOST_CECOTEC,
                },
                data={
                    "username": self._email,
                    "password": self._password,
                    "grant_type": "password",
                    "scope": "server",
                },
                timeout=10,
            )
            data = response.json()
            if "access_token" not in data:
                _LOGGER.error("Login failed — no access_token in response: %s", data)
                return False
            self._session = data
            self.login_ok = True
            _LOGGER.debug("Login successful, token expires in %s s", data.get("expires_in"))
            self._schedule_token_refresh(data.get("expires_in", 3600))
            return True
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Login exception: %s", exc)
            return False

    def _schedule_token_refresh(self, expires_in: int) -> None:
        if self._refresh_timer:
            self._refresh_timer.cancel()
        # Refresh 60 s before expiry
        delay = max(expires_in - 60, 60)
        self._refresh_timer = Timer(delay, self._refresh_token)
        self._refresh_timer.daemon = True
        self._refresh_timer.start()

    def _refresh_token(self) -> None:
        _LOGGER.debug("Refreshing access token")
        try:
            response = requests.post(
                url=URL_CECOTEC + PATH_AUTH,
                headers={
                    "Accept-Language": self._language,
                    "Authorization": _BASIC_AUTH,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Connection": "Keep-Alive",
                    "User-Agent": "okhttp/4.8.1",
                    "Host": HOST_CECOTEC,
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._session.get("refresh_token", ""),
                    "scope": "server",
                },
                timeout=10,
            )
            data = response.json()
            if "access_token" in data:
                self._session = data
                self._schedule_token_refresh(data.get("expires_in", 3600))
                _LOGGER.debug("Token refreshed successfully")
            else:
                _LOGGER.warning("Token refresh failed: %s", data)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Token refresh exception: %s", exc)

    @property
    def _auth_header(self) -> dict[str, str]:
        return {
            "Authorization": "bearer " + self._session.get("access_token", ""),
            "Content-Type": "application/json",
            "Accept-Language": self._language,
            "Host": HOST_CECOTEC,
            "Connection": "Keep-Alive",
            "User-Agent": "okhttp/4.4.1",
        }

    # ── Device discovery ──────────────────────────────────────────────────────

    def fetch_device_list(self) -> list[GrassHopperDevice]:
        """Fetch the list of mowers linked to this account."""
        try:
            response = requests.get(
                url=URL_CECOTEC + PATH_DEVICE_LIST,
                headers=self._auth_header,
                timeout=10,
            )
            data = response.json()
            if data.get("code", -1) != 0:
                _LOGGER.error("Device list error: %s", data)
                return []
            self.devices = [GrassHopperDevice(d) for d in data.get("data", [])]
            _LOGGER.debug("Found %d device(s)", len(self.devices))
            return self.devices
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("fetch_device_list exception: %s", exc)
            return []

    # ── State polling ─────────────────────────────────────────────────────────

    def fetch_device_state(self, device_sn: str) -> dict[str, Any] | None:
        """Poll the current state of a single mower."""
        try:
            response = requests.get(
                url=URL_CECOTEC + f"/mower/device/detail?deviceSn={device_sn}",
                headers=self._auth_header,
                timeout=10,
            )
            data = response.json()
            if data.get("code", -1) != 0:
                _LOGGER.debug("State poll error for %s: %s", device_sn, data)
                return None
            return data.get("data")
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("fetch_device_state exception: %s", exc)
            return None

    def update_device(self, device: GrassHopperDevice) -> bool:
        """Refresh a device object in-place. Returns True if data was received."""
        # The device list already contains all the state we need
        # We only need to re-fetch the device list to get updated state
        devices = self.fetch_device_list()
        if not devices:
            device.online = False
            return False
        # Find the matching device in the refreshed list
        for fresh in devices:
            if fresh.device_sn == device.device_sn:
                # Copy all state from the fresh device
                device.raw_data = fresh.raw_data
                device.mode = fresh.mode
                device.battery = fresh.battery
                device.wifi_level = fresh.wifi_level
                device.error_code = fresh.error_code
                device.error_text = fresh.error_text
                device.online = fresh.online
                return True
        device.online = False
        return False

    # ── Commands ──────────────────────────────────────────────────────────────

    def send_command(self, device_sn: str, operate: int) -> bool:
        """Send an operate command to the mower."""
        try:
            # Try the standard endpoint first
            response = requests.post(
                url=URL_CECOTEC + "/mower/device/operate",
                headers=self._auth_header,
                json={"deviceSn": device_sn, "operate": operate},
                timeout=10,
            )
            data = response.json()
            _LOGGER.debug("send_command response: %s", data)
            if data.get("code", -1) != 0:
                _LOGGER.error("Command %d failed for %s: %s", operate, device_sn, data)
                return False
            return True
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("send_command exception: %s", exc)
            return False

    def start_mowing(self, device_sn: str) -> bool:
        """Start mowing."""
        return self.send_command(device_sn, CMD_START)

    def pause(self, device_sn: str) -> bool:
        """Pause the mower."""
        return self.send_command(device_sn, CMD_PAUSE)

    def dock(self, device_sn: str) -> bool:
        """Send the mower home."""
        return self.send_command(device_sn, CMD_HOME)

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def unload(self) -> None:
        """Cancel background timers."""
        if self._refresh_timer:
            self._refresh_timer.cancel()
            self._refresh_timer = None
