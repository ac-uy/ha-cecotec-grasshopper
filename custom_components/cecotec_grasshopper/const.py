"""Constants for the Cecotec GrassHopper integration."""

DOMAIN = "cecotec_grasshopper"
ROBOTS = "robots"
DATAHANDLER = "data_handler"

# ── Connection ────────────────────────────────────────────────────────────────
# The GrassHopper 500 uses the sk-robot.com OEM cloud backend.
# Cecotec may white-label this under their own domain; if login fails with
# URL_CECOTEC, fall back to URL_SKROBOT.
#
# TODO: Confirm the exact host by sniffing the "Conga GrassHopper 500 Map"
#       app traffic (package: es.cecotec.congagrasshopper500map).
#       Use mitmproxy + Android emulator and look for POST /auth/oauth/token.
#       Replace URL_CECOTEC with whatever host the app actually calls.
URL_CECOTEC = "https://server.sk-robot.com/api"   # best guess — update if needed
HOST_CECOTEC = "server.sk-robot.com"

# Endpoint paths (same as sk-robot OEM platform)
PATH_AUTH = "/auth/oauth/token"
PATH_DEVICE_LIST = "/mower/device-user/list"

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
