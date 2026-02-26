"""
Device configuration for the device_control app.

Defines all controllable entities organized by category (tab),
floor, and room. Each device entry specifies:
  - entity_id: The Home Assistant entity ID
  - name: Display name
  - type: 'switch', 'light', 'cover', 'media_player'
  - icon: Font Awesome icon class (optional)
"""

# ──────────────────────────────────────────────
# Tab: TVs
# ──────────────────────────────────────────────
TV_DEVICES = {
    "Living Room": [
        {
            "entity_id": "media_player.living_room_television",
            "name": "Living Room TV (85\" Frame)",
            "type": "media_player",
            "icon": "fa-tv",
        },
        {
            "entity_id": "switch.living_room_tv_socket_1",
            "name": "TV Power Socket",
            "type": "switch",
            "icon": "fa-plug",
        },
        {
            "entity_id": "switch.living_room_tv_socket_2",
            "name": "Sonos Arc Ultra",
            "type": "switch",
            "icon": "fa-plug",
        },
    ],
    "Master Bedroom": [
        {
            "entity_id": "switch.master_bedroom_tv_socket_1",
            "name": "TV Power Socket",
            "type": "switch",
            "icon": "fa-plug",
        },
        {
            "entity_id": "switch.master_bedroom_tv_socket_2",
            "name": "Sonos Arc Ultra",
            "type": "switch",
            "icon": "fa-plug",
        },
    ],
    "Basement Master": [
        {
            "entity_id": "switch.basement_master_tv_socket_1",
            "name": "TV Power Socket",
            "type": "switch",
            "icon": "fa-plug",
        },
        {
            "entity_id": "switch.smart_outlet_2_socket_2",
            "name": "Sonos Arc Ultra",
            "type": "switch",
            "icon": "fa-plug",
        },
    ],
    "Media Room": [
        {
            "entity_id": "media_player.65_the_frame",
            "name": "Media Room TV (65\" Frame)",
            "type": "media_player",
            "icon": "fa-tv",
        },
        {
            "entity_id": "switch.media_room_tv_socket_1",
            "name": "TV Power Socket",
            "type": "switch",
            "icon": "fa-plug",
        },
        {
            "entity_id": "switch.media_room_tv_socket_2",
            "name": "Sonos Arc Ultra",
            "type": "switch",
            "icon": "fa-plug",
        },
    ],
    "Office": [
        {
            "entity_id": "media_player.office_television",
            "name": "Office TV",
            "type": "media_player",
            "icon": "fa-tv",
        },
        {
            "entity_id": "switch.office_tv_socket_1",
            "name": "TV Power Socket",
            "type": "switch",
            "icon": "fa-plug",
        },
        {
            "entity_id": "switch.office_tv_socket_2",
            "name": "Sonos Arc Ultra",
            "type": "switch",
            "icon": "fa-plug",
        },
    ],
}

# ──────────────────────────────────────────────
# Tab: Sonos (PDU-powered amps for in-wall/ceiling speakers)
# ──────────────────────────────────────────────
SONOS_DEVICES = {
    "In-Wall / Ceiling Amps": [
        {
            "entity_id": "switch.pdu_audio_rack_deck_sonos",
            "name": "Deck Sonos Amp",
            "type": "switch",
            "icon": "fa-volume-high",
        },
        {
            "entity_id": "switch.pdu_audio_rack_dining_room_sonos",
            "name": "Dining Room Sonos Amp",
            "type": "switch",
            "icon": "fa-volume-high",
        },
        {
            "entity_id": "switch.pdu_audio_rack_basement_master_en_suite",
            "name": "Basement Master En-suite Sonos Amp",
            "type": "switch",
            "icon": "fa-volume-high",
        },
        {
            "entity_id": "switch.pdu_audio_rack_master_en_suite",
            "name": "Master En-suite Sonos Amp",
            "type": "switch",
            "icon": "fa-volume-high",
        },
        {
            "entity_id": "switch.pdu_audio_rack_outlet_10",
            "name": "Lower Deck Sonos Amp",
            "type": "switch",
            "icon": "fa-volume-high",
        },
        {
            "entity_id": "switch.pdu_audio_rack_outlet_9",
            "name": "Hot Tub Sonos Amp",
            "type": "switch",
            "icon": "fa-volume-high",
        },
    ],
}

# ──────────────────────────────────────────────
# Tab: Blinds / Shades
# ──────────────────────────────────────────────
BLIND_DEVICES = {
    "Basement": [
        {
            "entity_id": "cover.basement_game_area_small_window",
            "name": "Game Area Small Window",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.basement_master_bedroom_large_window_shade",
            "name": "Master Bedroom Large Window",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.basement_master_bedroom_small_shades",
            "name": "Master Bedroom Small Shades",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
    ],
    "Main Floor": [
        {
            "entity_id": "cover.kitchen_left_window",
            "name": "Kitchen Left Window",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.kitchen_right_window",
            "name": "Kitchen Right Window",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.living_room_large_window_shade",
            "name": "Living Room Large Window",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.living_room_small_window",
            "name": "Living Room Small Window",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.office_large_window_shades",
            "name": "Office Large Window",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.office_small_window",
            "name": "Office Small Window",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
    ],
    "Upper Floor": [
        {
            "entity_id": "cover.master_bedroom_large_window_shade",
            "name": "Master Bedroom Large Window",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.master_bedroom_window_24",
            "name": "Master Bedroom Window 24",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.master_bedroom_window_24_1",
            "name": "Master Bedroom Window 24-1",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.master_bedroom_window_25",
            "name": "Master Bedroom Window 25",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.master_bedroom_window_25_1",
            "name": "Master Bedroom Window 25-1",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.master_bedroom_window_26",
            "name": "Master Bedroom Window 26",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.double_bunk_room_bedroom_shades",
            "name": "Double Bunk Room Shades",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.queen_and_bunk_bedroom_window_shade",
            "name": "Queen & Bunk Bedroom Shade",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
    ],
    "Deck / Exterior": [
        {
            "entity_id": "cover.all_deck_roller_shades",
            "name": "All Deck Roller Shades",
            "type": "cover",
            "icon": "fa-layer-group",
        },
        {
            "entity_id": "cover.bbq_deck_roller_shade",
            "name": "BBQ Deck Roller Shade",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.left_deck_roller_shade",
            "name": "Left Deck Roller Shade",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.right_deck_roller_shade",
            "name": "Right Deck Roller Shade",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
        {
            "entity_id": "cover.side_deck_roller_shade",
            "name": "Side Deck Roller Shade",
            "type": "cover",
            "icon": "fa-window-maximize",
        },
    ],
}

# ──────────────────────────────────────────────
# Tab: Lights (by floor → room)
# ──────────────────────────────────────────────
LIGHT_DEVICES = {
    "Upper Floor": [
        # Master Bedroom
        {"entity_id": "light.master_bedroom_main_lights", "name": "Master Bedroom Main", "type": "light", "icon": "fa-lightbulb", "room": "Master Bedroom"},
        {"entity_id": "light.master_bedroom_chandelier", "name": "Master Bedroom Chandelier", "type": "light", "icon": "fa-lightbulb", "room": "Master Bedroom"},
        {"entity_id": "light.master_bedroom_left_reading_light", "name": "Master Bedroom Right Reading", "type": "light", "icon": "fa-lightbulb", "room": "Master Bedroom"},
        {"entity_id": "light.master_bedroom_right_reading_light", "name": "Master Bedroom Left Reading", "type": "light", "icon": "fa-lightbulb", "room": "Master Bedroom"},
        {"entity_id": "light.master_bedroom_accent_lights", "name": "Master Bedroom Desk Light", "type": "light", "icon": "fa-lightbulb", "room": "Master Bedroom"},
        {"entity_id": "light.master_bedroom_closet_light", "name": "Master Bedroom Closet", "type": "light", "icon": "fa-lightbulb", "room": "Master Bedroom"},
        # Master Bathroom
        {"entity_id": "light.master_bathroom_main_lights", "name": "Master Bathroom Main", "type": "light", "icon": "fa-lightbulb", "room": "Master Bathroom"},
        {"entity_id": "light.master_bathroom_vanity_lights", "name": "Master Bathroom Vanity", "type": "light", "icon": "fa-lightbulb", "room": "Master Bathroom"},
        # Bedrooms
        {"entity_id": "light.double_bunk_bedroom_main_lights", "name": "Double Bunk Bedroom Main", "type": "light", "icon": "fa-lightbulb", "room": "Double Bunk Bedroom"},
        {"entity_id": "light.bunk_with_queen_bedroom_main_lights", "name": "Bunk + Queen Bedroom Main", "type": "light", "icon": "fa-lightbulb", "room": "Bunk + Queen Bedroom"},
        # Kids Bathroom
        {"entity_id": "light.kids_bathroom_main_lights", "name": "Kids Bathroom Main", "type": "light", "icon": "fa-lightbulb", "room": "Kids Bathroom"},
        {"entity_id": "light.kids_bathroom_toilet_room_lights", "name": "Kids Bathroom Toilet Room", "type": "light", "icon": "fa-lightbulb", "room": "Kids Bathroom"},
        {"entity_id": "light.kids_bathroom_tub_lights", "name": "Kids Bathroom Tub", "type": "light", "icon": "fa-lightbulb", "room": "Kids Bathroom"},
        {"entity_id": "light.kids_bathroom_vanity_lights", "name": "Kids Bathroom Vanity", "type": "light", "icon": "fa-lightbulb", "room": "Kids Bathroom"},
        # Hallway & Stairs
        {"entity_id": "light.hallway_main_lights", "name": "Hallway Main", "type": "light", "icon": "fa-lightbulb", "room": "Hallway"},
        {"entity_id": "light.stairs_upper_step_lights", "name": "Stairs Upper Steps", "type": "light", "icon": "fa-lightbulb", "room": "Stairs"},
        {"entity_id": "light.stairs_upstairs_hanging_lights", "name": "Stairs Hanging Lights", "type": "light", "icon": "fa-lightbulb", "room": "Stairs"},
        {"entity_id": "light.stairs_screen_accent_lights", "name": "Stairs Screen Accent", "type": "light", "icon": "fa-lightbulb", "room": "Stairs"},
        {"entity_id": "light.stairs_downstairs_sconce_lights", "name": "Stairs Downstairs Sconces", "type": "light", "icon": "fa-lightbulb", "room": "Stairs"},
        {"entity_id": "light.stairs_lower_step_lights", "name": "Stairs Lower Steps", "type": "light", "icon": "fa-lightbulb", "room": "Stairs"},
    ],
    "Main Floor": [
        # Living Room
        {"entity_id": "light.living_room_main_lights", "name": "Living Room Main", "type": "light", "icon": "fa-lightbulb", "room": "Living Room"},
        # Kitchen
        {"entity_id": "light.kitchen_main_lights", "name": "Kitchen Main", "type": "light", "icon": "fa-lightbulb", "room": "Kitchen"},
        {"entity_id": "light.kitchen_island_pendants", "name": "Kitchen Island Pendants", "type": "light", "icon": "fa-lightbulb", "room": "Kitchen"},
        {"entity_id": "light.kitchen_shelf_lights", "name": "Kitchen Shelf Lights", "type": "light", "icon": "fa-lightbulb", "room": "Kitchen"},
        # Dining Room
        {"entity_id": "light.dining_room_chandelier", "name": "Dining Room Chandelier", "type": "light", "icon": "fa-lightbulb", "room": "Dining Room"},
        # Office
        {"entity_id": "light.office_main_lights", "name": "Office Main", "type": "light", "icon": "fa-lightbulb", "room": "Office"},
        {"entity_id": "light.office_table_lamp", "name": "Office Floor Lamp", "type": "light", "icon": "fa-lightbulb", "room": "Office"},
        # Bar
        {"entity_id": "light.bar_main_lights", "name": "Bar Main", "type": "light", "icon": "fa-lightbulb", "room": "Bar"},
        {"entity_id": "light.bar_shelf_lights", "name": "Bar Shelf Lights", "type": "light", "icon": "fa-lightbulb", "room": "Bar"},
        # Foyer & Powder Room
        {"entity_id": "light.front_foyer_chandelier", "name": "Front Foyer Chandelier", "type": "light", "icon": "fa-lightbulb", "room": "Front Foyer"},
        {"entity_id": "light.powder_room_main_lights", "name": "Powder Room Main", "type": "light", "icon": "fa-lightbulb", "room": "Powder Room"},
        {"entity_id": "light.powder_room_vanity_lights", "name": "Powder Room Vanity", "type": "light", "icon": "fa-lightbulb", "room": "Powder Room"},
        # Ski Room
        {"entity_id": "light.ski_room_main_lights", "name": "Ski Room Main", "type": "light", "icon": "fa-lightbulb", "room": "Ski Room"},
        {"entity_id": "switch.ski_room_ceiling_fan_light", "name": "Ski Room Ceiling Fan Light", "type": "switch", "icon": "fa-lightbulb", "room": "Ski Room"},
    ],
    "Basement": [
        # Basement Master Bedroom
        {"entity_id": "light.basement_master_bedroom_main_lights", "name": "Basement Master Main", "type": "light", "icon": "fa-lightbulb", "room": "Basement Master Bedroom"},
        {"entity_id": "light.basement_master_bedroom_accent_lights", "name": "Basement Master Accent", "type": "light", "icon": "fa-lightbulb", "room": "Basement Master Bedroom"},
        {"entity_id": "light.basement_master_bedroom_left_reading_light", "name": "Basement Master Left Reading", "type": "light", "icon": "fa-lightbulb", "room": "Basement Master Bedroom"},
        {"entity_id": "light.basement_master_bedroom_right_reading_light", "name": "Basement Master Right Reading", "type": "light", "icon": "fa-lightbulb", "room": "Basement Master Bedroom"},
        # Basement Master Ensuite
        {"entity_id": "light.basement_master_ensuite_bathroom_main_lights", "name": "Basement Ensuite Main", "type": "light", "icon": "fa-lightbulb", "room": "Basement Master Ensuite"},
        {"entity_id": "light.basement_master_ensuite_bathroom_vanity_lights", "name": "Basement Ensuite Vanity", "type": "light", "icon": "fa-lightbulb", "room": "Basement Master Ensuite"},
        # Game Area
        {"entity_id": "light.basement_game_area_main_lights", "name": "Game Area Main", "type": "light", "icon": "fa-lightbulb", "room": "Game Area"},
        # Hallway & Storage
        {"entity_id": "light.downstairs_hallway_main_lights", "name": "Downstairs Hallway Main", "type": "light", "icon": "fa-lightbulb", "room": "Downstairs Hallway"},
        {"entity_id": "light.under_stairs_storage_room_main_lights", "name": "Under Stairs Storage", "type": "light", "icon": "fa-lightbulb", "room": "Storage"},
    ],
    "Exterior": [
        {"entity_id": "light.exterior_deck_ceiling_lights", "name": "Deck Ceiling Lights", "type": "light", "icon": "fa-lightbulb", "room": "Deck"},
        {"entity_id": "light.exterior_deck_sconce_lights", "name": "Deck Sconce Lights", "type": "light", "icon": "fa-lightbulb", "room": "Deck"},
        {"entity_id": "switch.exterior_lower_deck_sconces", "name": "Lower Deck Sconces", "type": "switch", "icon": "fa-lightbulb", "room": "Lower Deck"},
        {"entity_id": "light.exterior_front_sconces", "name": "Front Sconces", "type": "light", "icon": "fa-lightbulb", "room": "Front"},
        {"entity_id": "light.hot_tub_light", "name": "Hot Tub Light", "type": "light", "icon": "fa-lightbulb", "room": "Hot Tub"},
    ],
}

# ──────────────────────────────────────────────
# Tab: Fans (exhaust fans by floor)
# ──────────────────────────────────────────────
FAN_DEVICES = {
    "Upper Floor": [
        {"entity_id": "switch.kids_bathroom_toilet_exhaust_fan", "name": "Kids Bathroom Toilet Exhaust Fan", "type": "switch", "icon": "fa-fan"},
        {"entity_id": "switch.kids_bathroom_tub_exhaust_fan", "name": "Kids Bathroom Tub Exhaust Fan", "type": "switch", "icon": "fa-fan"},
    ],
    "Main Floor": [
        {"entity_id": "switch.powder_room_exhaust_fan", "name": "Powder Room Exhaust Fan", "type": "switch", "icon": "fa-fan"},
        {"entity_id": "switch.master_bedroom_ceiling_fan", "name": "Master Bathroom Exhaust Fan", "type": "switch", "icon": "fa-fan"},
    ],
    "Basement": [
        {"entity_id": "switch.basement_master_ensuite_bathroom_exhaust_fan", "name": "Basement Master Ensuite Exhaust Fan", "type": "switch", "icon": "fa-fan"},
    ],
}

# ──────────────────────────────────────────────
# Tab: Garage
# ──────────────────────────────────────────────
GARAGE_DEVICES = {
    "Garage": [
        {"entity_id": "switch.garage_main_lights", "name": "Garage Main Lights", "type": "switch", "icon": "fa-lightbulb"},
        {"entity_id": "light.garage_storage_room_main_lights", "name": "Garage Storage Room Lights", "type": "light", "icon": "fa-lightbulb"},
    ],
}

# ──────────────────────────────────────────────
# Tab: Patio
# ──────────────────────────────────────────────
PATIO_DEVICES = {
    "Patio": [
        {"entity_id": "switch.patio_deck_heaters", "name": "Patio Deck Heaters", "type": "switch", "icon": "fa-fire"},
    ],
}

# ──────────────────────────────────────────────
# All tabs in display order
# ──────────────────────────────────────────────
TABS = [
    {"key": "tvs", "label": "TVs", "icon": "fa-tv", "devices": TV_DEVICES},
    {"key": "sonos", "label": "Sonos", "icon": "fa-music", "devices": SONOS_DEVICES},
    {"key": "blinds", "label": "Blinds", "icon": "fa-window-maximize", "devices": BLIND_DEVICES},
    {"key": "lights", "label": "Lights", "icon": "fa-lightbulb", "devices": LIGHT_DEVICES},
    {"key": "fans", "label": "Fans", "icon": "fa-fan", "devices": FAN_DEVICES},
    {"key": "garage", "label": "Garage", "icon": "fa-warehouse", "devices": GARAGE_DEVICES},
    {"key": "patio", "label": "Patio", "icon": "fa-umbrella-beach", "devices": PATIO_DEVICES},
]


def get_all_entity_ids():
    """Return a flat set of every entity_id referenced in the config."""
    ids = set()
    for tab in TABS:
        for _group, devices in tab["devices"].items():
            for dev in devices:
                ids.add(dev["entity_id"])
    return ids
