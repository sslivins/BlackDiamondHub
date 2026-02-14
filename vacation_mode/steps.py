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
                "action": "water_heater/set_operation_mode",
                "data": {
                    "entity_id": None,  # Uses device_id targeting
                    "operation_mode": "off",
                },
                "device_id": "ddc7ec36bd2d3df1a200ca80e92ce757",
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
                    "entity_id": None,
                    "preset_mode": "Away From Home",
                },
                "device_id": "a24f0f48e3a062d31841e7602de80f7b",
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
                    "temperature": 5,
                },
                "area_id": ["garage", "garage_storage_room"],
            },
        ],
    },
    {
        "alias": "Set Freezer to Vacation Mode",
        "icon": "fas fa-icicles",
        "actions": [
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": None,
                },
                "device_id": "84b64f7a7a57a0653c0e97fbd4930737",
                "entity_id_override": "e043466b0b08145b26f28eff99d1ffd4",
            },
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": None,
                },
                "device_id": "84b64f7a7a57a0653c0e97fbd4930737",
                "entity_id_override": "6da74fdfb7d977912538b3363173099f",
            },
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": None,
                },
                "device_id": "0abe97d22992d228895650b8c985f68a",
                "entity_id_override": "6ca02d2dbf190374822573ac052c2d48",
            },
        ],
    },
    {
        "alias": "Turn Off Televisions",
        "icon": "fas fa-tv",
        "actions": [
            {
                "action": "remote/turn_off",
                "data": {
                    "entity_id": None,
                },
                "device_id": "53ddc5429f77069b67290347729b2e72",
            },
            {
                "action": "remote/turn_off",
                "data": {
                    "entity_id": None,
                },
                "device_id": "db27e57cdcb1d7e835afb4721210a568",
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
                "action": "water_heater/set_operation_mode",
                "data": {
                    "entity_id": None,
                    "operation_mode": "eco",
                },
                "device_id": "ddc7ec36bd2d3df1a200ca80e92ce757",
            },
        ],
    },
    {
        "alias": "Start Hot Tub",
        "icon": "fas fa-hot-tub-person",
        "actions": [
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": None,
                },
                "device_id": "a24f0f48e3a062d31841e7602de80f7b",
                "entity_id_override": "ea06b7842bd1dbc3247f99a31b5abff5",
            },
            {
                "action": "climate/set_preset_mode",
                "data": {
                    "entity_id": None,
                    "preset_mode": "Standard",
                },
                "device_id": "a24f0f48e3a062d31841e7602de80f7b",
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
                    "entity_id": None,
                    "preset_mode": "none",
                },
                "device_id": [
                    "710aecb39bd6d0c6b4553a371eb99895",
                    "652c56dece31b19b0e56d46e87290d43",
                    "3c8299f7d84395386348e53cd9a1546d",
                    "c5569f4e6018519213237a1959466f73",
                    "c1a18960f155608d8e51d3602b440c0c",
                ],
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
                    "temperature": 10,
                },
                "area_id": ["garage", "garage_storage_room"],
            },
        ],
    },
    {
        "alias": "Setup Fridge/Freezer for Arrival",
        "icon": "fas fa-icicles",
        "actions": [
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": None,
                },
                "device_id": "84b64f7a7a57a0653c0e97fbd4930737",
                "entity_id_override": "6da74fdfb7d977912538b3363173099f",
            },
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": None,
                },
                "device_id": "84b64f7a7a57a0653c0e97fbd4930737",
                "entity_id_override": "e043466b0b08145b26f28eff99d1ffd4",
            },
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": None,
                },
                "device_id": "0abe97d22992d228895650b8c985f68a",
                "entity_id_override": "6ca02d2dbf190374822573ac052c2d48",
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
