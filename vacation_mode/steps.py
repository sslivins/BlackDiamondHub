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
                "description": "Setting water heater to Off",
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
                "description": "Setting hot tub to Away From Home",
            },
        ],
    },
    {
        "alias": "Heat Pump Vacation Setup",
        "icon": "fas fa-temperature-arrow-down",
        "actions": [
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": "switch.aeco_1988_hot_tank_outdoor_reset",
                },
                "description": "Disabling outdoor reset",
                "delay_after": 2,
            },
            {
                "action": "number/set_value",
                "data": {
                    "entity_id": "number.aeco_1988_hot_tank_target_temperature",
                    "value": "28",
                },
                "description": "Setting target temperature to 28°C",
                "verify_delay": 10,
            },
            {
                "action": "number/set_value",
                "data": {
                    "entity_id": "number.aeco_1988_backup_differential",
                    "value": "8",
                },
                "description": "Setting backup differential to 8°C",
                "verify_delay": 10,
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
                "description": "Master Bedroom → 13.5°C",
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.basement_bunk_rooms",
                    "temperature": 13.5,
                    "hvac_mode": "heat",
                },
                "description": "Basement Bunk Rooms → 13.5°C",
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.main_floor",
                    "temperature": 13.5,
                    "hvac_mode": "heat",
                },
                "description": "Main Floor → 13.5°C",
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.basement_master",
                    "temperature": 13.5,
                    "hvac_mode": "heat",
                },
                "description": "Basement Master → 13.5°C",
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.ski_room",
                    "temperature": 13.5,
                    "hvac_mode": "heat",
                },
                "description": "Ski Room → 13.5°C",
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
                "description": "Garage → 5°C",
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.storage_room_thermostat_thermostat",
                    "temperature": 5,
                },
                "description": "Storage Room → 5°C",
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
                "description": "Enabling freezer eco mode",
            },
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": "switch.freezer_dispenser",
                },
                "description": "Disabling freezer dispenser",
            },
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": "switch.refrigerator_eco_mode",
                },
                "description": "Enabling fridge eco mode",
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
                "description": "Living Room TV",
                "delay_after": 1,
            },
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": "switch.basement_master_tv_socket_1",
                },
                "description": "Basement Master TV",
                "delay_after": 1,
            },
            # TODO: Media Room TV socket powers hot tub controller — re-enable
            # when hot tub controller is moved to a dedicated outlet.
            # {
            #     "action": "switch/turn_off",
            #     "data": {
            #         "entity_id": "switch.media_room_tv_socket_1",
            #     },
            #     "description": "Media Room TV",
            #     "delay_after": 1,
            # },
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": "switch.office_tv_socket_1",
                },
                "description": "Office TV",
                "delay_after": 1,
            },
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": "switch.master_bedroom_tv_socket_1",
                },
                "description": "Master Bedroom TV",
            },
        ],
    },
    {
        "alias": "Turn Off Patio Heaters",
        "icon": "fas fa-fire-flame-curved",
        "actions": [
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": "switch.patio_deck_heaters",
                },
                "description": "Turning off patio deck heaters",
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
                "description": "Enabling away mode flag",
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
                "description": "Setting water heater to Eco Mode",
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
                "description": "Setting hot tub to Standard mode",
            },
        ],
    },
    {
        "alias": "Heat Pump Home Setup",
        "icon": "fas fa-temperature-arrow-up",
        "actions": [
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": "switch.aeco_1988_hot_tank_outdoor_reset",
                },
                "description": "Enabling outdoor reset",
                "delay_after": 2,
            },
            {
                "action": "number/set_value",
                "data": {
                    "entity_id": "number.aeco_1988_hot_tank_min_temperature",
                    "value": "27",
                },
                "description": "Setting min temperature to 27°C",
                "verify_delay": 10,
            },
            {
                "action": "number/set_value",
                "data": {
                    "entity_id": "number.aeco_1988_hot_tank_max_temperature",
                    "value": "38",
                },
                "description": "Setting max temperature to 38°C",
                "verify_delay": 10,
            },
            {
                "action": "number/set_value",
                "data": {
                    "entity_id": "number.aeco_1988_hot_tank_outdoor_reset",
                    "value": "-20",
                },
                "description": "Setting outdoor reset to -20°C",
                "verify_delay": 10,
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
                "description": "Clearing presets on all thermostats",
                "delay_after": 2,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.master_bedroom",
                    "temperature": 20,
                    "hvac_mode": "heat",
                },
                "description": "Master Bedroom → 20°C",
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.basement_bunk_rooms",
                    "temperature": 20,
                    "hvac_mode": "heat",
                },
                "description": "Basement Bunk Rooms → 20°C",
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.main_floor",
                    "temperature": 20,
                    "hvac_mode": "heat",
                },
                "description": "Main Floor → 20°C",
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.basement_master",
                    "temperature": 20,
                    "hvac_mode": "heat",
                },
                "description": "Basement Master → 20°C",
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.ski_room",
                    "temperature": 19,
                    "hvac_mode": "heat",
                },
                "description": "Ski Room → 19°C",
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.garage_thermostat_thermostat",
                    "temperature": 10,
                },
                "description": "Garage → 10°C",
                "delay_after": 1,
            },
            {
                "action": "climate/set_temperature",
                "data": {
                    "entity_id": "climate.storage_room_thermostat_thermostat",
                    "temperature": 10,
                },
                "description": "Storage Room → 10°C",
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
                "description": "Disabling freezer eco mode",
            },
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": "switch.freezer_dispenser",
                },
                "description": "Enabling freezer dispenser",
            },
            {
                "action": "switch/turn_off",
                "data": {
                    "entity_id": "switch.refrigerator_eco_mode",
                },
                "description": "Disabling fridge eco mode",
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
                "description": "Living Room TV",
                "delay_after": 1,
            },
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": "switch.basement_master_tv_socket_1",
                },
                "description": "Basement Master TV",
                "delay_after": 1,
            },
            # TODO: Media Room TV socket powers hot tub controller — re-enable
            # when hot tub controller is moved to a dedicated outlet.
            # {
            #     "action": "switch/turn_on",
            #     "data": {
            #         "entity_id": "switch.media_room_tv_socket_1",
            #     },
            #     "description": "Media Room TV",
            #     "delay_after": 1,
            # },
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": "switch.office_tv_socket_1",
                },
                "description": "Office TV",
                "delay_after": 1,
            },
            {
                "action": "switch/turn_on",
                "data": {
                    "entity_id": "switch.master_bedroom_tv_socket_1",
                },
                "description": "Master Bedroom TV",
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
                "description": "Disabling away mode flag",
            },
        ],
    },
]
