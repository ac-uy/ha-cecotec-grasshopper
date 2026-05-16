"""Constants for the Cecotec GrassHopper integration."""

DOMAIN = "cecotec_grasshopper"
ROBOTS = "robots"
DATAHANDLER = "data_handler"

# ── Connection ────────────────────────────────────────────────────────────────
URL_CECOTEC = "https://server.sk-robot.com/api"
HOST_CECOTEC = "server.sk-robot.com"

# Endpoint paths
PATH_AUTH = "/auth/oauth/token"
PATH_DEVICE_LIST = "/mower/device-user/list"
PATH_SET_WORK_STATUS = "/app_mower/device/setWorkStatus"
PATH_DEVICE_SETTINGS = "/mower/device-setting"

# ── MQTT ──────────────────────────────────────────────────────────────────────
MQTT_HOST = "mqtts.sk-robot.com"
MQTT_PORT = 1883
MQTT_USERNAME = "app"
MQTT_PASSWORD = "h4ijwkTnyrA"

# ── Command modes ─────────────────────────────────────────────────────────────
CMD_START = 1
CMD_PAUSE = 0
CMD_HOME = 2
CMD_BORDER = 4

# ── Mower states ──────────────────────────────────────────────────────────────
STATE_STANDBY = "standby"
STATE_MOWING = "mowing"
STATE_GOING_HOME = "going_home"
STATE_CHARGING = "charging"
STATE_CHARGING_FULL = "charging_full"
STATE_BORDER = "mowing_border"
STATE_PAUSE = "pause"
STATE_ERROR = "error"
STATE_OFFLINE = "offline"
STATE_UNKNOWN = "unknown"

# ── Config entry keys ─────────────────────────────────────────────────────────
CONF_ACCOUNT_NAME = "account_name"
