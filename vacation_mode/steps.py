"""
Step definitions for Vacation Mode and Home Mode.

Each step is a dict with:
- alias: Human-readable name
- icon: Font Awesome icon class
- actions: List of HA API calls to execute sequentially
  Each action has:
    - action: HA service to call (e.g. "climate/set_temperature")
    - data: Payload to send
    - delay_after: Optional delay in seconds after this action
"""

# ============================================================
# VACATION MODE STEPS (Leaving)
# ============================================================
VACATION_STEPS = [
    {
        "alias": "Turn Off Water Heater",
        "icon": "fas fa-fire",
        "actions": [
            {
                "action": "climate/set_preset_mode",
                "data": {
                    "entity_id": "climate.econet_hpwh",
                    "preset_mode": "Off",
                },
            },
        ],
    },
    {
        "alias": "Set Hot Tub to Vacation Mode",
        "icon": "fas fa-hot-tub-person",
        "actions": [
            {
                "action": "climate/set_preset_mode",
                "data": {
                    "entity_id": "climate.hot_tub_heater",
                    "preset_mode": "Away From Home",
                },
            },
        ],
    },
    {
        "alias": "Set Buffer Tank & Backup Differential",
        "icon": "fas fa-temperature-arrow-down",
        "actions": [
            {
                "action": "number/set_value",
                "data": {
                    "entity_id": "number.aeco_1988_hot_tank_target_temperature",
                    "value": "28",
                },
            },
            {
                "action": "number/set_value",
                "data": {
                    "entity_id": "number.aeco_1988_backup_differential",
                    "value": "8",
                },
            },
        ],
    },
    {
        "alias": "Set Thermostats to 13.5°C",
        "icon": "fas fa-snowflake",
        "actions": [
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.master_bedroom",
                    "temperature": 13.5,
                    "hvac_mode": "heat",
                },
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.basement_bunk_rooms",
                    "temperature": 13.5,
                    "hvac_mode": "heat",
                },
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.main_floor",
                    "temperature": 13.5,
                    "hvac_mode": "heat",
                },
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.basement_master",
                    "temperature": 13.5,
                    "hvac_mode": "heat",
                },
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.ski_room",
                    "temperature": 13.5,
                    "hvac_mode": "heat",
                },
            },
        ],
    },
    {
        "alias": "Set Garage Heaters to 5°C",
        "icon": "fas fa-warehouse",
        "actions": [
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.garage_thermostat_thermostat",
                    "temperature": 5,
                },
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.storage_room_thermostat_thermostat",
                    "temperature": 5,
                },
            },
        ],
    },
    {
        "alias": "Set Fridge & Freezer to Vacation Mode",
        "icon": "fas fa-icicles",
        "actions": [
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": "switch.freezer_eco_mode",
                },
            },
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": "switch.freezer_dispenser",
                },
            },
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": "switch.refrigerator_eco_mode",
                },
            },
        ],
    },
    {
        "alias": "Turn Off Televisions",
        "icon": "fas fa-tv",
        "actions": [
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": "switch.living_room_tv_socket_1",
                },
                "delay_after": 1,
            },
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": "switch.basement_master_tv_socket_1",
                },
                "delay_after": 1,
            },
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": "switch.media_room_tv_socket_1",
                },
                "delay_after": 1,
            },
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": "switch.office_tv_socket_1",
                },
                "delay_after": 1,
            },
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": "switch.master_bedroom_tv_socket_1",
                },
            },
        ],
    },
    {
        "alias": "Enable Home Away Mode",
        "icon": "fas fa-plane-departure",
        "actions": [
            {
                "action": "input_boolean/turn_on",
                "data": {
                    "entity_id": "input_boolean.home_away_mode_enabled",
                },
            },
        ],
    },
]

# ============================================================
# HOME MODE STEPS (Arriving)
# ============================================================
HOME_STEPS = [
    {
        "alias": "Start Water Heater",
        "icon": "fas fa-fire",
        "actions": [
            {
                "action": "climate/set_preset_mode",
                "data": {
                    "entity_id": "climate.econet_hpwh",
                    "preset_mode": "Eco Mode",
                },
            },
        ],
    },
    {
        "alias": "Start Hot Tub",
        "icon": "fas fa-hot-tub-person",
        "actions": [
            {
                "action": "climate/set_preset_mode",
                "data": {
                    "entity_id": "climate.hot_tub_heater",
                    "preset_mode": "Standard",
                },
            },
        ],
    },
    {
        "alias": "Set Buffer Tank & Backup Differential",
        "icon": "fas fa-temperature-arrow-up",
        "actions": [
            {
                "action": "number/set_value",
                "data": {
                    "entity_id": "number.aeco_1988_hot_tank_target_temperature",
                    "value": "36",
                },
            },
            {
                "action": "number/set_value",
                "data": {
                    "entity_id": "number.aeco_1988_backup_differential",
                    "value": "6",
                },
            },
        ],
    },
    {
        "alias": "Set Thermostats to Home Temperatures",
        "icon": "fas fa-house-chimney",
        "actions": [
            {
                "action": "climate/set_preset_mode",
                "data": {
                    "entity_id": [
                        "climate.master_bedroom",
                        "climate.basement_bunk_rooms",
                        "climate.main_floor",
                        "climate.basement_master",
                        "climate.ski_room",
                    ],
                    "preset_mode": "none",
                },
                "delay_after": 2,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.master_bedroom",
                    "temperature": 20,
                    "hvac_mode": "heat",
                },
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.basement_bunk_rooms",
                    "temperature": 20,
                    "hvac_mode": "heat",
                },
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.main_floor",
                    "temperature": 20,
                    "hvac_mode": "heat",
                },
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.basement_master",
                    "temperature": 20,
                    "hvac_mode": "heat",
                },
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.ski_room",
                    "temperature": 19,
                    "hvac_mode": "heat",
                },
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.garage_thermostat_thermostat",
                    "temperature": 10,
                },
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.storage_room_thermostat_thermostat",
                    "temperature": 10,
                },
            },
        ],
    },
    {
        "alias": "Setup Fridge/Freezer for Arrival",
        "icon": "fas fa-icicles",
        "actions": [
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": "switch.freezer_eco_mode",
                },
            },
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": "switch.freezer_dispenser",
                },
            },
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": "switch.refrigerator_eco_mode",
                },
            },
        ],
    },
    {
        "alias": "Turn On Televisions",
        "icon": "fas fa-tv",
        "actions": [
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": "switch.living_room_tv_socket_1",
                },
                "delay_after": 1,
            },
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": "switch.basement_master_tv_socket_1",
                },
                "delay_after": 1,
            },
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": "switch.media_room_tv_socket_1",
                },
                "delay_after": 1,
            },
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": "switch.office_tv_socket_1",
                },
                "delay_after": 1,
            },
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": "switch.master_bedroom_tv_socket_1",
                },
            },
        ],
    },
    {
        "alias": "Disable Home Away Mode",
        "icon": "fas fa-house-flag",
        "actions": [
            {
                "action": "input_boolean/turn_off",
                "data": {
                    "entity_id": "input_boolean.home_away_mode_enabled",
                },
            },
        ],
    },
]
