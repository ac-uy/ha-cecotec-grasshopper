"""Cecotec GrassHopper cloud API client.

Communicates with the sk-robot.com OEM backend that powers the
"Conga GrassHopper 500 Map" app (es.cecotec.congagrasshopper500map).

Protocol notes
--------------
* Auth:  POST /auth/oauth/token  (OAuth2 password grant)
* Devices: GET /mower/device-user/list
* Commands: POST /app_mower/device/setWorkStatus
* Settings: GET /mower/device-setting/{deviceSn}
* MQTT status push: mqtts.sk-robot.com:1883 (user: app, pass: h4ijwkTnyrA)
"""

from __future__ import annotations

import json
import logging
from threading import Timer
from typing import Any

import requests

from .const import (
    CMD_BORDER,
    CMD_HOME,
    CMD_PAUSE,
    CMD_START,
    HOST_CECOTEC,
    MQTT_HOST,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_USERNAME,
    PATH_AUTH,
    PATH_DEVICE_LIST,
    PATH_DEVICE_SETTINGS,
    PATH_SET_WORK_STATUS,
    URL_CECOTEC,
)

_LOGGER = logging.getLogger(__name__)

# OAuth2 Basic auth header — same value used by all sk-robot OEM apps
_BASIC_AUTH = "Basic YXBwOmFwcA=="


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

        # Rain sensor state
        self.rain_status: int = int(raw.get("rainStatusCode", 0) or 0)
        self.rain_delay_left: int = int(raw.get("rainDelayLeft", 0) or 0)

        # Settings — updated by coordinator from device-setting endpoint
        self.rain_delay_enabled: bool = bool(raw.get("rainFlag", False))
        self.rain_delay_duration: int = int(raw.get("rainDelayDuration", 180) or 180)
        self.schedule_paused: bool = bool(raw.get("pause", False))
        self.schedule: list[dict] = []  # list of {dayOfWeek, startAt, endAt, trimFlag}
        self.zone_percentages: list[int] = []  # [zone1%, zone2%, zone3%, zone4%]
        self.border_length: int = 0  # in cm


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
        self.user_id: int | None = None

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
            self.user_id = data.get("user_id")
            self.login_ok = True
            _LOGGER.debug("Login successful, user_id=%s, token expires in %s s", self.user_id, data.get("expires_in"))
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
                self.user_id = data.get("user_id", self.user_id)
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

    def update_device(self, device: GrassHopperDevice) -> bool:
        """Refresh a device object in-place. Returns True if data was received."""
        devices = self.fetch_device_list()
        if not devices:
            device.online = False
            return False
        for fresh in devices:
            if fresh.device_sn == device.device_sn:
                device.raw_data = fresh.raw_data
                device.mode = fresh.mode
                device.battery = fresh.battery
                device.wifi_level = fresh.wifi_level
                device.error_code = fresh.error_code
                device.error_text = fresh.error_text
                device.online = fresh.online
                device.rain_status = fresh.rain_status
                device.rain_delay_left = fresh.rain_delay_left
                return True
        device.online = False
        return False

    # ── Commands ──────────────────────────────────────────────────────────────

    def send_command(self, device_sn: str, mode: int) -> bool:
        """Send a work status command to the mower.

        Modes: 1=Start, 0=Pause, 2=Home, 4=Border
        """
        try:
            response = requests.post(
                url=URL_CECOTEC + PATH_SET_WORK_STATUS,
                headers={
                    "Accept-Language": self._language,
                    "Authorization": "bearer " + self._session.get("access_token", ""),
                    "Content-Type": "application/json",
                    "Host": HOST_CECOTEC,
                    "Connection": "Keep-Alive",
                    "User-Agent": "okhttp/4.8.1",
                },
                json={
                    "appId": self.user_id,
                    "deviceSn": device_sn,
                    "mode": mode,
                },
                timeout=10,
            )
            data = response.json()
            _LOGGER.debug("send_command(mode=%d) response: %s", mode, data)
            if data.get("code", -1) != 0:
                _LOGGER.error("Command mode=%d failed for %s: %s", mode, device_sn, data)
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

    def start_border(self, device_sn: str) -> bool:
        """Start border/edge mowing."""
        return self.send_command(device_sn, CMD_BORDER)

    # ── Settings & Schedule ───────────────────────────────────────────────────

    def fetch_device_settings(self, device_sn: str) -> dict | None:
        """Fetch device settings including schedule, zones, rain delay."""
        try:
            response = requests.get(
                url=URL_CECOTEC + PATH_DEVICE_SETTINGS + "/" + device_sn,
                headers=self._auth_header,
                timeout=10,
            )
            data = response.json()
            if data.get("code", -1) != 0:
                _LOGGER.error("Device settings error: %s", data)
                return None
            return data.get("data", {})
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("fetch_device_settings exception: %s", exc)
            return None

    def set_schedule(self, device_sn: str, schedule_entries: list[dict], auto_flag: bool = False) -> bool:
        """Set the mowing schedule.

        schedule_entries: list of dicts with keys:
            dayOfWeek (1=Mon..7=Sun), startAt (HH:MM:SS), endAt (HH:MM:SS), trimFlag (bool)
        Only include days that should be active. Days not included will be cleared.
        """
        try:
            response = requests.post(
                url=URL_CECOTEC + "/app_mower/device-schedule/setScheduling",
                headers={
                    "Accept-Language": self._language,
                    "Authorization": "bearer " + self._session.get("access_token", ""),
                    "Content-Type": "application/json; charset=UTF-8",
                    "Host": HOST_CECOTEC,
                    "Connection": "Keep-Alive",
                    "User-Agent": "okhttp/4.8.1",
                },
                json={
                    "appId": self.user_id,
                    "autoFlag": auto_flag,
                    "deviceSn": device_sn,
                    "deviceScheduleBOS": schedule_entries,
                },
                timeout=10,
            )
            data = response.json()
            _LOGGER.debug("set_schedule response: %s", data)
            if not data.get("ok", False):
                _LOGGER.error("set_schedule failed: %s", data.get("msg"))
                return False
            return True
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("set_schedule exception: %s", exc)
            return False

    def set_rain_delay(self, device_sn: str, enabled: bool, duration_minutes: int = 180) -> bool:
        """Set rain delay settings."""
        try:
            response = requests.post(
                url=URL_CECOTEC + "/app_mower/device-setting/setRainDelay",
                headers={
                    "Accept-Language": self._language,
                    "Authorization": "bearer " + self._session.get("access_token", ""),
                    "Content-Type": "application/json; charset=UTF-8",
                    "Host": HOST_CECOTEC,
                    "Connection": "Keep-Alive",
                    "User-Agent": "okhttp/4.8.1",
                },
                json={
                    "appId": self.user_id,
                    "deviceSn": device_sn,
                    "rainFlag": enabled,
                    "rainDelayDuration": str(duration_minutes),
                },
                timeout=10,
            )
            data = response.json()
            _LOGGER.debug("set_rain_delay response: %s", data)
            return data.get("ok", False)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("set_rain_delay exception: %s", exc)
            return False

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def unload(self) -> None:
        """Cancel background timers."""
        if self._refresh_timer:
            self._refresh_timer.cancel()
            self._refresh_timer = None
