# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-05-15

### Added
- ✅ **Commands now work!** MQTT support for sending commands (start, pause, dock)
- Commands sent via cloud MQTT broker (server.sk-robot.com:1883)
- Added `paho-mqtt>=2.1.0` dependency

### Changed
- Changed from `cloud_polling` to `cloud_push` IoT class
- Commands now use MQTT protocol instead of REST API
- Lawn mower entity now fully functional with start_mowing, pause, and dock actions

### Technical
- REST API does not support commands (returns "method not supported")
- Commands must be sent via MQTT to `/device/{deviceSn}/get` topic
- MQTT connection is established on-demand when commands are sent
- No router configuration needed - connects directly to cloud MQTT broker

## [0.2.1] - 2026-05-15

### Changed
- Documented integration as read-only (status monitoring only)
- Removed Bluetooth reverse engineering files (abandoned approach)
- Updated README to clarify command limitations

### Known Issues
- ⚠️ **Commands not working**: The sk-robot.com cloud API does not expose a working command endpoint via REST
  - Start/Pause/Dock commands return "method not supported" error
  - Mowing mode selector UI exists but commands don't execute
  - Status monitoring (battery, WiFi, online, errors) works correctly
  - Investigating alternative methods: MQTT, Bluetooth, undocumented endpoints

## [0.2.0] - 2026-05-15

### Added
- Mowing mode selector (normal/edge) - choose mode before starting
- Start mowing now respects the selected mowing mode
- Select entity for easy mode switching in Home Assistant UI

### Changed
- Improved start_mowing to use selected mode instead of custom service

## [0.1.2] - 2026-05-15

### Added
- Custom service `cecotec_grasshopper.start_border_mowing` for edge/border mowing mode
- Bluetooth scanner tools for protocol exploration (development)

### Fixed
- Error sensors now only display when there's an actual error (hide "normal", "OK", "none" states)
- Improved entity naming and display logic
- Corrected license badge link in README
- Added icon to manifest for proper display in Home Assistant

## [0.1.1] - 2026-05-15

### Fixed
- Correct license badge link in README
- Add icon to manifest for proper display in Home Assistant

## [0.1.0] - 2026-05-15

### Added
- Initial release of Cecotec GrassHopper integration
- Support for Cecotec Conga GrassHopper 500 robot mower
- Lawn mower entity with start/pause/dock commands
- Battery level sensor (0-100%)
- WiFi signal strength sensor (0-3)
- Online status binary sensor
- Error detection with error codes and messages
- OAuth2 authentication with automatic token refresh
- Config flow for easy setup
- English and Spanish translations
- 30-second auto-refresh polling interval

### Features
- Control mower directly from Home Assistant
- Real-time status monitoring
- Multi-language support (EN/ES)
- HACS integration ready

---

## Versioning

This project uses Semantic Versioning:
- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.X.0): New features (backward compatible)
- **PATCH** (0.0.X): Bug fixes (backward compatible)

## Unreleased

### Planned
- Support for additional sk-robot.com devices
- Mower location tracking (GPS)
- Scheduled mowing automation
- Error history tracking
