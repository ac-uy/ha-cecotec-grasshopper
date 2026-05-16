"""DataUpdateCoordinator for Cecotec GrassHopper."""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from threading import Thread

import paho.mqtt.client as mqtt

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GrassHopperAPI, GrassHopperDevice
from .const import MQTT_HOST, MQTT_PASSWORD, MQTT_PORT, MQTT_USERNAME

_LOGGER = logging.getLogger(__name__)

# Poll every 60s as fallback; MQTT push provides real-time updates
SCAN_INTERVAL = timedelta(seconds=60)


class GrassHopperCoordinator(DataUpdateCoordinator[GrassHopperDevice]):
    """Coordinator for a single mower device."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: GrassHopperAPI,
        device: GrassHopperDevice,
        entry: ConfigEntry,
    ) -> None:
        self.api = api
        self.device = device
        self.entry = entry
        self._mqtt_client: mqtt.Client | None = None
        self._mqtt_connected: bool = False

        super().__init__(
            hass,
            _LOGGER,
            name=f"GrassHopper {device.device_sn}",
            update_interval=SCAN_INTERVAL,
        )

    async def async_setup(self) -> None:
        """Start MQTT connection for real-time updates."""
        await self.hass.async_add_executor_job(self._start_mqtt)

    def _start_mqtt(self) -> None:
        """Connect to the sk-robot MQTT broker for status push."""
        if not self.api.user_id:
            _LOGGER.warning("No user_id available, skipping MQTT setup")
            return

        try:
            client_id = f"cecotec_ha_{self.api.user_id}_{self.device.device_sn[-6:]}"
            self._mqtt_client = mqtt.Client(client_id=client_id)
            self._mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            self._mqtt_client.on_connect = self._on_mqtt_connect
            self._mqtt_client.on_message = self._on_mqtt_message
            self._mqtt_client.on_disconnect = self._on_mqtt_disconnect
            self._mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            self._mqtt_client.loop_start()
            _LOGGER.debug("MQTT client started for device %s", self.device.device_sn)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("MQTT connection failed (falling back to polling): %s", exc)

    def _on_mqtt_connect(self, client, userdata, flags, rc) -> None:
        """Handle MQTT connection."""
        if rc == 0:
            self._mqtt_connected = True
            # Subscribe to app-level updates (status push from cloud)
            topic = f"/app/{self.api.user_id}/get"
            client.subscribe(topic, qos=0)
            _LOGGER.debug("MQTT connected, subscribed to %s", topic)
        else:
            self._mqtt_connected = False
            _LOGGER.warning("MQTT connection failed with code %d", rc)

    def _on_mqtt_disconnect(self, client, userdata, rc) -> None:
        """Handle MQTT disconnect."""
        self._mqtt_connected = False
        if rc != 0:
            _LOGGER.debug("MQTT disconnected unexpectedly (rc=%d), will auto-reconnect", rc)

    def _on_mqtt_message(self, client, userdata, message) -> None:
        """Handle incoming MQTT status message."""
        try:
            payload = message.payload.decode("utf-8")
            data = json.loads(payload)
            _LOGGER.debug("MQTT message on %s: %s", message.topic, payload[:200])

            # Update device state from MQTT push
            device_sn = data.get("deviceSn", "")
            if device_sn == self.device.device_sn:
                self._update_device_from_mqtt(data)
                # Notify HA that data changed
                self.hass.loop.call_soon_threadsafe(
                    self.async_set_updated_data, self.device
                )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("MQTT message parse error: %s", exc)

    def _update_device_from_mqtt(self, data: dict) -> None:
        """Update device state from an MQTT push message."""
        if "workStatusCode" in data:
            self.device.mode = int(data["workStatusCode"])
        if "electricity" in data:
            self.device.battery = int(data["electricity"])
        if "wifiLv" in data:
            self.device.wifi_level = int(data["wifiLv"])
        if "deviceOnlineFlag" in data:
            self.device.online = bool(data["deviceOnlineFlag"])
        if "faultStatusCode" in data:
            code = data["faultStatusCode"]
            self.device.error_code = 0 if code == "normal" else int(code)
        if "faultStatusName" in data:
            self.device.error_text = data["faultStatusName"] or ""

    async def _async_update_data(self) -> GrassHopperDevice:
        """Fetch latest state from the API (fallback polling)."""
        success = await self.hass.async_add_executor_job(
            self.api.update_device, self.device
        )
        if not success:
            raise UpdateFailed(
                f"Failed to fetch state for mower {self.device.device_sn}"
            )
        return self.device

    def stop_mqtt(self) -> None:
        """Disconnect MQTT client."""
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
            self._mqtt_client = None
            _LOGGER.debug("MQTT client stopped")
