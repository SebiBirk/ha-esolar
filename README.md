# Home Assistant SAJ eSolar Elekeeper Custom Integration

![elekeeper](https://github.com/erelke/ha-esolar/blob/main/images/elekeeper.png)

Custom Home Assistant integration for SAJ Elekeeper cloud systems.
It uses signed requests against SAJ cloud endpoints and maps plant/device data into Home Assistant sensors.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=erelke&repository=ha-esolar&category=integration)

## Highlights
- Polling interval configurable down to `1` second.
- Expanded dataset: values aligned with the SAJ WebUI dataset, including grid import/export related values.
- Plant and inverter focused entities with rich attributes.
- Support for modern Elekeeper portal authentication/signing.
- Diagnostics support for easier troubleshooting.

Integration:

![integration](https://github.com/erelke/ha-esolar/blob/main/images/ee_3.png)

Config options:

![config](https://github.com/erelke/ha-esolar/blob/main/images/ee_4.png)

Sensors:

![sensors](https://github.com/erelke/ha-esolar/blob/main/images/ee_1.png)

Diagnostics:

![diagnostics](https://github.com/erelke/ha-esolar/blob/main/images/ee_2.png)

---

## What is included
The integration collects and exposes data such as:
- Plant status and production totals.
- Today/month/year energy counters.
- Live power values (PV, load, battery, grid, backup).
- Battery state of charge and battery flow values.
- Device/inverter details and diagnostics attributes.
- Additional values visible in SAJ WebUI where available from cloud endpoints.

### Grid power semantics
`sysGridPowerwatt` is intended to indicate import/export direction.
In this integration:
- Positive value: grid import (buy from grid).
- Negative value: grid export (feed-in).
- `gridDirection` is used together with power to keep direction consistent.

---

## Installation
### HACS
Use the HACS button above, or add the repository manually in HACS as an Integration.

### Manual
1. Copy `custom_components/saj_esolar_air` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

---

## Setup
1. Go to **Settings -> Devices & Services -> Integrations**.
2. Click **Add Integration**.
3. Search for **SAJ eSolar**.
4. Enter region, username, and password.
5. Select monitored site(s).

Setup images:

![setup step 1](https://github.com/erelke/ha-esolar/blob/main/images/setup_step_1.png)
![setup step 2](https://github.com/erelke/ha-esolar/blob/main/images/setup_step_2.png)
![setup step 3](https://github.com/erelke/ha-esolar/blob/main/images/setup_step_3.png)
![setup step 4](https://github.com/erelke/ha-esolar/blob/main/images/setup_step_4.png)
![setup step 5](https://github.com/erelke/ha-esolar/blob/main/images/setup_step_5.png)

---

## Configuration
Open the integration and configure options:
- `show_inverter_sensors`
- `show_pv_grid_data`
- `plant_update_interval` (seconds)

### Polling interval
- Minimum supported setting is `1` second.
- Very low intervals create significantly higher API load.
- If you use very aggressive polling, monitor stability and consider increasing interval if SAJ throttles or blocks requests.

Configuration images:

![configure step 1](https://github.com/erelke/ha-esolar/blob/main/images/configure_step_1.png)
![configure step 2](https://github.com/erelke/ha-esolar/blob/main/images/configure_step_2.png)
![configure step 3](https://github.com/erelke/ha-esolar/blob/main/images/configure_step_3.png)

Final result example:

![final](https://github.com/erelke/ha-esolar/blob/main/images/all_done.png)

---

## Advanced
Example: build a template sensor from integration attributes.

```yaml
template:
  - sensor:
      - name: "Battery Direction"
        unique_id: inverter_ass111111111111111_energy_total_battery_direction
        state: >
          {{ state_attr('sensor.inverter_ass111111111111111_energy_total', 'Battery Direction') }}
```

---

## Troubleshooting
If values do not refresh as expected:
1. Check `plant_update_interval` in integration options.
2. Restart Home Assistant after updating via HACS.
3. Enable debug logs for `custom_components.saj_esolar_air`.
4. Verify diagnostics timestamp (`stamp`) changes over time.

If configuration menu fails with 500:
1. Restart Home Assistant after update.
2. Reproduce once.
3. Share traceback from `home-assistant.log`.

If you see messages about other SAJ integrations (for example missing `saj_h2_modbus`), those are separate integrations and not this component.

---

## Bug reports
Please include:
- Home Assistant version.
- Integration version.
- Diagnostics export from this integration.
- Relevant log excerpt with traceback.

Diagnostics screenshot:

![diagnostics data](https://github.com/erelke/ha-esolar/blob/main/images/ee_6.png)

---

## Credits
- Original inspiration: [faanskit/ha-esolar](https://github.com/faanskit/ha-esolar)
- SAJ cloud reverse engineering contributors and users providing diagnostics.

## Donations
If this integration helps you and you want to support development:

[![Donate](https://img.shields.io/badge/Donate-BuyMeCoffe-green.svg)](https://www.buymeacoffee.com/erelke)
