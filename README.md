# Cecotec GrassHopper 500 Home Assistant Integration

A custom Home Assistant integration for the **Cecotec GrassHopper 500** robot mower. Control your mower directly from Home Assistant with real-time status monitoring.

[![GitHub Release](https://img.shields.io/github/release/ac-uy/ha-cecotec-grasshopper.svg?style=flat-square)](https://github.com/ac-uy/ha-cecotec-grasshopper/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](https://github.com/ac-uy/ha-cecotec-grasshopper/blob/main/LICENSE)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://hacs.xyz/)

## Features ✅

### Status Monitoring (Real-Time via MQTT)
- 🔋 **Battery level** monitoring (0-100%)
- 📶 **WiFi signal strength** tracking (0-3)
- 🟢 **Online status** detection
- ⚠️ **Error detection** with error codes and messages
- 🔄 **Real-time updates** via MQTT push (with 60s polling fallback)
- 🌍 **Multi-language support** (English, Spanish)

### Commands ✅
- 🚀 **Start mowing** - Begin automatic mowing
- ⏸️ **Pause** - Stop the mower in place
- 🏠 **Return to dock** - Send mower back to charging station
- 🔲 **Edge/border mowing** - Mow along the perimeter

## Supported Devices

- **Cecotec Conga GrassHopper 500** (RMC502E20V-ECWNTS)
- Other Cecotec GrassHopper models using the sk-robot.com backend

## Installation

### Via HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Go to **Integrations** → **⋮ (menu)** → **Custom repositories**
3. Add repository: `https://github.com/ac-uy/ha-cecotec-grasshopper`
4. Select category: **Integration**
5. Click **Create**
6. Find **Cecotec GrassHopper** and click **Install**
7. Restart Home Assistant

### Manual Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/ac-uy/ha-cecotec-grasshopper.git
   ```

2. Copy to your Home Assistant config:
   ```bash
   cp -r ha-cecotec-grasshopper/custom_components/cecotec_grasshopper ~/.homeassistant/custom_components/
   ```

3. Restart Home Assistant

## Setup

1. Go to **Settings** → **Devices & Services** → **Create Integration**
2. Search for **"Cecotec"** or **"GrassHopper"**
3. Enter your Cecotec app credentials:
   - **Email**: Your Cecotec app login email
   - **Password**: Your Cecotec app password
4. Click **Create**

The integration will discover your mower and create the following entities:

### Entities Created

| Entity | Type | Description |
|--------|------|-------------|
| `lawn_mower.mymower` | Lawn Mower | Main control entity (start/pause/dock) |
| `select.mymower_mowing_mode` | Select | Mowing mode selector (normal/edge) |
| `sensor.mymower_battery` | Sensor | Battery percentage (0-100%) |
| `sensor.mymower_wi_fi_level` | Sensor | WiFi signal strength (0-3) |
| `sensor.mymower_error_code` | Sensor | Error code (if any) |
| `sensor.mymower_error_message` | Sensor | Error description |
| `binary_sensor.mymower_online` | Binary Sensor | Online status |
| `binary_sensor.mymower_error` | Binary Sensor | Error flag |

## Usage

### Automations Example

Start mowing at 9 AM on weekdays:

```yaml
automation:
  - alias: "Start mowing at 9 AM"
    trigger:
      platform: time
      at: "09:00:00"
    condition:
      - condition: time
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
    action:
      - service: lawn_mower.start_mowing
        target:
          entity_id: lawn_mower.mymower
```

Send notification when battery is low:

```yaml
automation:
  - alias: "Low battery alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.mymower_battery
      below: 20
    action:
      - service: notify.notify
        data:
          message: "GrassHopper battery is low: {{ states('sensor.mymower_battery') }}%"
```

## Troubleshooting

### Integration not showing entities

1. Check Home Assistant logs: **Settings** → **System** → **Logs** → Search for "cecotec"
2. Verify credentials are correct in the config flow
3. Ensure the mower is powered on and connected to WiFi
4. Restart Home Assistant

### API test fails

- **Login error**: Double-check your email and password
- **Device not found**: Verify the mower appears in the official Cecotec app
- **Connection timeout**: Check your internet connection and firewall

### Entities show 0% or offline

- Restart Home Assistant to reload the integration
- Check if the mower is actually online in the Cecotec app
- Review the error logs for API response issues

## Technical Details

- **Backend**: sk-robot.com OEM platform (shared with Sunseeker, Adano mowers)
- **Authentication**: OAuth2 password grant with automatic token refresh
- **Commands**: REST API (`/app_mower/device/setWorkStatus`)
- **Status Updates**: MQTT push via `mqtts.sk-robot.com:1883` (with REST polling fallback)
- **Update Interval**: Real-time via MQTT; 60s polling fallback

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

The MIT License allows you to:
- ✅ Use this software for any purpose
- ✅ Copy, modify, and distribute it
- ✅ Include it in proprietary applications

The only requirement is to include the license and copyright notice.

## Disclaimer

This is an unofficial integration. Cecotec is not affiliated with this project. Use at your own risk.

## Credits

- Built for Home Assistant
- Command protocol discovered thanks to [Sdahl1234/Sunseeker-lawn-mower](https://github.com/Sdahl1234/Sunseeker-lawn-mower) — the integration that figured out the correct API endpoints and MQTT credentials for the sk-robot.com platform
- MQTT protocol documentation by [OlliKantola/Sunseeker_LawnMower_Control](https://github.com/OlliKantola/Sunseeker_LawnMower_Control)
- Thanks to the Home Assistant community

---

**Questions or Issues?** [Open an issue on GitHub](https://github.com/ac-uy/ha-cecotec-grasshopper/issues)
