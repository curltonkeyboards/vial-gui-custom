# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import json
import lzma
import time
from collections import OrderedDict

from keycodes.keycodes import RESET_KEYCODE, Keycode, recreate_keyboard_keycodes
from kle_serial import Serial as KleSerial
from protocol.combo import ProtocolCombo
from protocol.constants import CMD_VIA_GET_PROTOCOL_VERSION, CMD_VIA_GET_KEYBOARD_VALUE, CMD_VIA_SET_KEYBOARD_VALUE, \
    CMD_VIA_SET_KEYCODE, CMD_VIA_LIGHTING_SET_VALUE, CMD_VIA_LIGHTING_GET_VALUE, CMD_VIA_LIGHTING_SAVE, \
    CMD_VIA_GET_LAYER_COUNT, CMD_VIA_KEYMAP_GET_BUFFER, CMD_VIA_VIAL_PREFIX, VIA_LAYOUT_OPTIONS, \
    VIA_SWITCH_MATRIX_STATE, QMK_BACKLIGHT_BRIGHTNESS, QMK_BACKLIGHT_EFFECT, QMK_RGBLIGHT_BRIGHTNESS, \
    QMK_RGBLIGHT_EFFECT, QMK_RGBLIGHT_EFFECT_SPEED, QMK_RGBLIGHT_COLOR, VIALRGB_GET_INFO, VIALRGB_GET_MODE, \
    VIALRGB_GET_SUPPORTED, VIALRGB_SET_MODE, CMD_VIAL_GET_KEYBOARD_ID, CMD_VIAL_GET_SIZE, CMD_VIAL_GET_DEFINITION, \
    CMD_VIAL_GET_ENCODER, CMD_VIAL_SET_ENCODER, CMD_VIAL_GET_UNLOCK_STATUS, CMD_VIAL_UNLOCK_START, CMD_VIAL_UNLOCK_POLL, \
    CMD_VIAL_LOCK, CMD_VIAL_QMK_SETTINGS_QUERY, CMD_VIAL_QMK_SETTINGS_GET, CMD_VIAL_QMK_SETTINGS_SET, \
    CMD_VIAL_QMK_SETTINGS_RESET, BUFFER_FETCH_CHUNK, VIAL_PROTOCOL_QMK_SETTINGS, \
    CMD_VIAL_LAYER_RGB_SAVE, CMD_VIAL_LAYER_RGB_LOAD, CMD_VIAL_LAYER_RGB_ENABLE, CMD_VIAL_LAYER_RGB_GET_STATUS, \
    CMD_VIAL_CUSTOM_ANIM_SET_PARAM, CMD_VIAL_CUSTOM_ANIM_GET_PARAM, CMD_VIAL_CUSTOM_ANIM_SET_ALL, \
    CMD_VIAL_CUSTOM_ANIM_GET_ALL, CMD_VIAL_CUSTOM_ANIM_SAVE, CMD_VIAL_CUSTOM_ANIM_LOAD, \
    CMD_VIAL_CUSTOM_ANIM_RESET_SLOT, CMD_VIAL_CUSTOM_ANIM_GET_STATUS, CMD_VIAL_CUSTOM_ANIM_RESCAN_LEDS
from protocol.dynamic import ProtocolDynamic
from protocol.key_override import ProtocolKeyOverride
from protocol.macro import ProtocolMacro
from protocol.tap_dance import ProtocolTapDance
from unlocker import Unlocker
from util import MSG_LEN, hid_send

SUPPORTED_VIA_PROTOCOL = [-1, 9]
SUPPORTED_VIAL_PROTOCOL = [-1, 0, 1, 2, 3, 4, 5, 6]

HID_MANUFACTURER_ID = 0x7D
HID_SUB_ID = 0x00
HID_DEVICE_ID = 0x4D
HID_PACKET_SIZE = 32

# ThruLoop Commands (0xB0-0xB5)
HID_CMD_SET_LOOP_CONFIG = 0xB0
HID_CMD_SET_MAIN_LOOP_CCS = 0xB1  
HID_CMD_SET_OVERDUB_CCS = 0xB2
HID_CMD_SET_NAVIGATION_CONFIG = 0xB3
HID_CMD_GET_ALL_CONFIG = 0xB4
HID_CMD_RESET_LOOP_CONFIG = 0xB5

# MIDIswitch Commands (0xB6-0xBB)
HID_CMD_SET_KEYBOARD_CONFIG = 0xB6
HID_CMD_GET_KEYBOARD_CONFIG = 0xB7
HID_CMD_RESET_KEYBOARD_CONFIG = 0xB8
HID_CMD_SAVE_KEYBOARD_SLOT = 0xB9
HID_CMD_LOAD_KEYBOARD_SLOT = 0xBA
HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED = 0xBB

class ProtocolError(Exception):
    pass

class Keyboard(ProtocolMacro, ProtocolDynamic, ProtocolTapDance, ProtocolCombo, ProtocolKeyOverride):
    """ Low-level communication with a vial-enabled keyboard """

    def __init__(self, dev, usb_send=hid_send):
        self.dev = dev
        self.usb_send = usb_send
        self.definition = None

        # n.b. using OrderedDict here to make order of layout requests consistent for tests
        self.rowcol = OrderedDict()
        self.encoderpos = OrderedDict()
        self.encoder_count = 0
        self.layout = dict()
        self.encoder_layout = dict()
        self.rows = self.cols = self.layers = 0
        self.layout_labels = None
        self.layout_options = -1
        self.keys = []
        self.encoders = []
        self.vibl = False
        self.custom_keycodes = None
        self.midi = None

        self.lighting_qmk_rgblight = self.lighting_qmk_backlight = self.lighting_vialrgb = False

        # underglow
        self.underglow_brightness = self.underglow_effect = self.underglow_effect_speed = -1
        self.underglow_color = (0, 0)
        # backlight
        self.backlight_brightness = self.backlight_effect = -1
        # vialrgb
        self.rgb_mode = self.rgb_speed = self.rgb_version = self.rgb_maximum_brightness = -1
        self.rgb_hsv = (0, 0, 0)
        self.rgb_supported_effects = set()
        
        # Add your custom initializations here:
        self.reload_thruloop_config()
        self.reload_midi_config()
        self.reload_layer_actuations()

        # layer RGB - always initialize as supported for GUI purposes
        self.layer_rgb_supported = True
        self.layer_rgb_enabled = False

        self.via_protocol = self.vial_protocol = self.keyboard_id = -1

    def reload(self, sideload_json=None):
        """ Load information about the keyboard: number of layers, physical key layout """

        self.rowcol = OrderedDict()
        self.encoderpos = OrderedDict()
        self.layout = dict()
        self.encoder_layout = dict()

        self.reload_layout(sideload_json)
        self.reload_layers()

        self.reload_macros_early()
        self.reload_persistent_rgb()
        self.reload_rgb()
        self.reload_layer_rgb_support()
        self.reload_settings()

        self.reload_dynamic()

        # based on the number of macros, tapdance, etc, this will generate global keycode arrays
        recreate_keyboard_keycodes(self)

        # at this stage we have correct keycode info and can reload everything that depends on keycodes
        self.reload_keymap()
        self.reload_macros_late()
        self.reload_tap_dance()
        self.reload_combo()
        self.reload_key_override()

    def reload_layers(self):
        """ Get how many layers the keyboard has """
        self.layers = self.usb_send(self.dev, struct.pack("B", CMD_VIA_GET_LAYER_COUNT), retries=20)[1]

    def reload_via_protocol(self):
        data = self.usb_send(self.dev, struct.pack("B", CMD_VIA_GET_PROTOCOL_VERSION), retries=20)
        self.via_protocol = struct.unpack(">H", data[1:3])[0]

    def check_protocol_version(self):
        if self.via_protocol not in SUPPORTED_VIA_PROTOCOL or self.vial_protocol not in SUPPORTED_VIAL_PROTOCOL:
            raise ProtocolError()

    def reload_layout(self, sideload_json=None):
        """ Requests layout data from the current device """

        self.reload_via_protocol()

        self.sideload = False
        if sideload_json is not None:
            self.sideload = True
            payload = sideload_json
        else:
            # get keyboard identification
            data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_GET_KEYBOARD_ID), retries=20)
            self.vial_protocol, self.keyboard_id = struct.unpack("<IQ", data[0:12])

            # get the size
            data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_GET_SIZE), retries=20)
            sz = struct.unpack("<I", data[0:4])[0]

            # get the payload
            payload = b""
            block = 0
            while sz > 0:
                data = self.usb_send(self.dev, struct.pack("<BBI", CMD_VIA_VIAL_PREFIX, CMD_VIAL_GET_DEFINITION, block),
                                     retries=20)
                if sz < MSG_LEN:
                    data = data[:sz]
                payload += data
                block += 1
                sz -= MSG_LEN

            payload = json.loads(lzma.decompress(payload))

        self.check_protocol_version()

        self.definition = payload

        if "vial" in payload:
            vial = payload["vial"]
            self.vibl = vial.get("vibl", False)
            self.midi = vial.get("midi", None)

        self.layout_labels = payload["layouts"].get("labels")

        self.rows = payload["matrix"]["rows"]
        self.cols = payload["matrix"]["cols"]

        self.custom_keycodes = payload.get("customKeycodes", None)

        serial = KleSerial()
        kb = serial.deserialize(payload["layouts"]["keymap"])

        self.keys = []
        self.encoders = []

        for key in kb.keys:
            key.row = key.col = None
            key.encoder_idx = key.encoder_dir = None
            if key.labels[4] == "e":
                idx, direction = key.labels[0].split(",")
                idx, direction = int(idx), int(direction)
                key.encoder_idx = idx
                key.encoder_dir = direction
                self.encoderpos[idx] = True
                self.encoder_count = max(self.encoder_count, idx + 1)
                self.encoders.append(key)
            elif key.decal or (key.labels[0] and "," in key.labels[0]):
                row, col = 0, 0
                if key.labels[0] and "," in key.labels[0]:
                    row, col = key.labels[0].split(",")
                    row, col = int(row), int(col)
                key.row = row
                key.col = col
                self.rowcol[(row, col)] = True
                self.keys.append(key)

            # bottom right corner determines layout index and option in this layout
            key.layout_index = -1
            key.layout_option = -1
            if key.labels[8]:
                idx, opt = key.labels[8].split(",")
                key.layout_index, key.layout_option = int(idx), int(opt)

    def reload_keymap(self):
        """ Load current key mapping from the keyboard """

        keymap = b""
        # calculate what the size of keymap will be and retrieve the entire binary buffer
        size = self.layers * self.rows * self.cols * 2
        for x in range(0, size, BUFFER_FETCH_CHUNK):
            offset = x
            sz = min(size - offset, BUFFER_FETCH_CHUNK)
            data = self.usb_send(self.dev, struct.pack(">BHB", CMD_VIA_KEYMAP_GET_BUFFER, offset, sz), retries=20)
            keymap += data[4:4+sz]

        for layer in range(self.layers):
            for row, col in self.rowcol.keys():
                if row >= self.rows or col >= self.cols:
                    raise RuntimeError("malformed vial.json, key references {},{} but matrix declares rows={} cols={}"
                                       .format(row, col, self.rows, self.cols))
                # determine where this (layer, row, col) will be located in keymap array
                offset = layer * self.rows * self.cols * 2 + row * self.cols * 2 + col * 2
                keycode = Keycode.serialize(struct.unpack(">H", keymap[offset:offset+2])[0])
                self.layout[(layer, row, col)] = keycode

        for layer in range(self.layers):
            for idx in self.encoderpos:
                data = self.usb_send(self.dev, struct.pack("BBBB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_GET_ENCODER, layer, idx),
                                     retries=20)
                self.encoder_layout[(layer, idx, 0)] = Keycode.serialize(struct.unpack(">H", data[0:2])[0])
                self.encoder_layout[(layer, idx, 1)] = Keycode.serialize(struct.unpack(">H", data[2:4])[0])

        if self.layout_labels:
            data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_GET_KEYBOARD_VALUE, VIA_LAYOUT_OPTIONS),
                                 retries=20)
            self.layout_options = struct.unpack(">I", data[2:6])[0]

    def reload_persistent_rgb(self):
        """
            Reload RGB properties which are slow, and do not change while keyboard is plugged in
            e.g. VialRGB supported effects list
        """

        if "lighting" in self.definition:
            self.lighting_qmk_rgblight = self.definition["lighting"] in ["qmk_rgblight", "qmk_backlight_rgblight"]
            self.lighting_qmk_backlight = self.definition["lighting"] in ["qmk_backlight", "qmk_backlight_rgblight"]
            self.lighting_vialrgb = self.definition["lighting"] == "vialrgb"

        if self.lighting_vialrgb:
            data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_LIGHTING_GET_VALUE, VIALRGB_GET_INFO),
                                 retries=20)[2:]
            self.rgb_version = data[0] | (data[1] << 8)
            if self.rgb_version != 1:
                raise RuntimeError("Unsupported VialRGB protocol ({}), update your Vial version to latest"
                                   .format(self.rgb_version))
            self.rgb_maximum_brightness = data[2]

            self.rgb_supported_effects = {0}
            max_effect = 0
            while max_effect < 0xFFFF:
                data = self.usb_send(self.dev, struct.pack("<BBH", CMD_VIA_LIGHTING_GET_VALUE, VIALRGB_GET_SUPPORTED,
                                                           max_effect))[2:]
                for x in range(0, len(data), 2):
                    value = int.from_bytes(data[x:x+2], byteorder="little")
                    if value != 0xFFFF:
                        self.rgb_supported_effects.add(value)
                    max_effect = max(max_effect, value)

    def reload_rgb(self):
        if self.lighting_qmk_rgblight:
            self.underglow_brightness = self.usb_send(
                self.dev, struct.pack(">BB", CMD_VIA_LIGHTING_GET_VALUE, QMK_RGBLIGHT_BRIGHTNESS), retries=20)[2]
            self.underglow_effect = self.usb_send(
                self.dev, struct.pack(">BB", CMD_VIA_LIGHTING_GET_VALUE, QMK_RGBLIGHT_EFFECT), retries=20)[2]
            self.underglow_effect_speed = self.usb_send(
                self.dev, struct.pack(">BB", CMD_VIA_LIGHTING_GET_VALUE, QMK_RGBLIGHT_EFFECT_SPEED), retries=20)[2]
            color = self.usb_send(
                self.dev, struct.pack(">BB", CMD_VIA_LIGHTING_GET_VALUE, QMK_RGBLIGHT_COLOR), retries=20)[2:4]
            # hue, sat
            self.underglow_color = (color[0], color[1])

        if self.lighting_qmk_backlight:
            self.backlight_brightness = self.usb_send(
                self.dev, struct.pack(">BB", CMD_VIA_LIGHTING_GET_VALUE, QMK_BACKLIGHT_BRIGHTNESS), retries=20)[2]
            self.backlight_effect = self.usb_send(
                self.dev, struct.pack(">BB", CMD_VIA_LIGHTING_GET_VALUE, QMK_BACKLIGHT_EFFECT), retries=20)[2]

        if self.lighting_vialrgb:
            data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_LIGHTING_GET_VALUE, VIALRGB_GET_MODE),
                                 retries=20)[2:]
            self.rgb_mode = int.from_bytes(data[0:2], byteorder="little")
            self.rgb_speed = data[2]
            self.rgb_hsv = (data[3], data[4], data[5])

    def reload_settings(self):
        self.settings = dict()
        self.supported_settings = set()
        if self.vial_protocol < VIAL_PROTOCOL_QMK_SETTINGS:
            return
        cur = 0
        while cur != 0xFFFF:
            data = self.usb_send(self.dev, struct.pack("<BBH", CMD_VIA_VIAL_PREFIX, CMD_VIAL_QMK_SETTINGS_QUERY, cur),
                                 retries=20)
            for x in range(0, len(data), 2):
                qsid = int.from_bytes(data[x:x+2], byteorder="little")
                cur = max(cur, qsid)
                if qsid != 0xFFFF:
                    self.supported_settings.add(qsid)

        for qsid in self.supported_settings:
            from editor.qmk_settings import QmkSettings

            if not QmkSettings.is_qsid_supported(qsid):
                continue

            data = self.usb_send(self.dev, struct.pack("<BBH", CMD_VIA_VIAL_PREFIX, CMD_VIAL_QMK_SETTINGS_GET, qsid),
                                 retries=20)
            if data[0] == 0:
                self.settings[qsid] = QmkSettings.qsid_deserialize(qsid, data[1:])

    def set_key(self, layer, row, col, code):
        key = (layer, row, col)
        if self.layout[key] != code:
            if code == RESET_KEYCODE:
                Unlocker.unlock(self)

            self.usb_send(self.dev, struct.pack(">BBBBH", CMD_VIA_SET_KEYCODE, layer, row, col,
                                                Keycode.deserialize(code)), retries=20)
            self.layout[key] = code

    def set_encoder(self, layer, index, direction, code):
        key = (layer, index, direction)
        if self.encoder_layout[key] != code:
            if code == RESET_KEYCODE:
                Unlocker.unlock(self)

            self.usb_send(self.dev, struct.pack(">BBBBBH", CMD_VIA_VIAL_PREFIX, CMD_VIAL_SET_ENCODER,
                                                layer, index, direction, Keycode.deserialize(code)), retries=20)
            self.encoder_layout[key] = code

    def set_layout_options(self, options):
        if self.layout_options != -1 and self.layout_options != options:
            self.layout_options = options
            self.usb_send(self.dev, struct.pack(">BBI", CMD_VIA_SET_KEYBOARD_VALUE, VIA_LAYOUT_OPTIONS, options),
                          retries=20)

    def set_qmk_rgblight_brightness(self, value):
        self.underglow_brightness = value
        self.usb_send(self.dev, struct.pack(">BBB", CMD_VIA_LIGHTING_SET_VALUE, QMK_RGBLIGHT_BRIGHTNESS, value),
                      retries=20)

    def set_qmk_rgblight_effect(self, index):
        self.underglow_effect = index
        self.usb_send(self.dev, struct.pack(">BBB", CMD_VIA_LIGHTING_SET_VALUE, QMK_RGBLIGHT_EFFECT, index),
                      retries=20)

    def set_qmk_rgblight_effect_speed(self, value):
        self.underglow_effect_speed = value
        self.usb_send(self.dev, struct.pack(">BBB", CMD_VIA_LIGHTING_SET_VALUE, QMK_RGBLIGHT_EFFECT_SPEED, value),
                      retries=20)

    def set_qmk_rgblight_color(self, h, s, v):
        self.set_qmk_rgblight_brightness(v)
        self.usb_send(self.dev, struct.pack(">BBBB", CMD_VIA_LIGHTING_SET_VALUE, QMK_RGBLIGHT_COLOR, h, s))

    def set_qmk_backlight_brightness(self, value):
        self.backlight_brightness = value
        self.usb_send(self.dev, struct.pack(">BBB", CMD_VIA_LIGHTING_SET_VALUE, QMK_BACKLIGHT_BRIGHTNESS, value))

    def set_qmk_backlight_effect(self, value):
        self.backlight_effect = value
        self.usb_send(self.dev, struct.pack(">BBB", CMD_VIA_LIGHTING_SET_VALUE, QMK_BACKLIGHT_EFFECT, value))

    def save_rgb(self):
        self.usb_send(self.dev, struct.pack(">B", CMD_VIA_LIGHTING_SAVE), retries=20)

    def save_layout(self):
        """ Serializes current layout to a binary """

        data = {"version": 1, "uid": self.keyboard_id}

        layout = []
        for l in range(self.layers):
            layer = []
            layout.append(layer)
            for r in range(self.rows):
                row = []
                layer.append(row)
                for c in range(self.cols):
                    val = self.layout.get((l, r, c), -1)
                    row.append(val)

        encoder_layout = []
        for l in range(self.layers):
            layer = []
            for e in range(self.encoder_count):
                cw = (l, e, 0)
                ccw = (l, e, 1)
                layer.append([self.encoder_layout.get(cw, -1),
                              self.encoder_layout.get(ccw, -1)])
            encoder_layout.append(layer)

        data["layout"] = layout
        data["encoder_layout"] = encoder_layout
        data["layout_options"] = self.layout_options
        data["macro"] = self.save_macro()
        data["vial_protocol"] = self.vial_protocol
        data["via_protocol"] = self.via_protocol
        data["tap_dance"] = self.save_tap_dance()
        data["combo"] = self.save_combo()
        data["key_override"] = self.save_key_override()
        data["settings"] = self.settings

        return json.dumps(data).encode("utf-8")

    def restore_layout(self, data):
        """ Restores saved layout """

        data = json.loads(data.decode("utf-8"))

        # restore keymap
        for l, layer in enumerate(data["layout"]):
            for r, row in enumerate(layer):
                for c, code in enumerate(row):
                    if (l, r, c) in self.layout:
                        self.set_key(l, r, c, Keycode.serialize(Keycode.deserialize(code)))

        # restore encoders
        for l, layer in enumerate(data["encoder_layout"]):
            for e, encoder in enumerate(layer):
                self.set_encoder(l, e, 0, Keycode.serialize(Keycode.deserialize(encoder[0])))
                self.set_encoder(l, e, 1, Keycode.serialize(Keycode.deserialize(encoder[1])))

        self.set_layout_options(data["layout_options"])
        self.restore_macros(data.get("macro"))

        self.restore_tap_dance(data.get("tap_dance", []))
        self.restore_combo(data.get("combo", []))
        self.restore_key_override(data.get("key_override", []))

        for qsid, value in data.get("settings", dict()).items():
            from editor.qmk_settings import QmkSettings

            qsid = int(qsid)
            if QmkSettings.is_qsid_supported(qsid):
                self.qmk_settings_set(qsid, value)

    def reset(self):
        self.usb_send(self.dev, struct.pack("B", 0xB))
        self.dev.close()

    def get_uid(self):
        """ Retrieve UID from the keyboard, explicitly sending a query packet """
        data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_GET_KEYBOARD_ID), retries=20)
        keyboard_id = data[4:12]
        return keyboard_id

    def get_unlock_status(self, retries=20):
        # VIA keyboards are always unlocked
        if self.vial_protocol < 0:
            return 1

        data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_GET_UNLOCK_STATUS),
                             retries=retries)
        return data[0]

    def get_unlock_in_progress(self):
        # VIA keyboards are never being unlocked
        if self.vial_protocol < 0:
            return 0

        data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_GET_UNLOCK_STATUS), retries=20)
        return data[1]

    def get_unlock_keys(self):
        """ Return keys users have to hold to unlock the keyboard as a list of rowcols """

        # VIA keyboards don't have unlock keys
        if self.vial_protocol < 0:
            return []

        data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_GET_UNLOCK_STATUS), retries=20)
        rowcol = []
        for x in range(15):
            row = data[2 + x * 2]
            col = data[3 + x * 2]
            if row != 255 and col != 255:
                rowcol.append((row, col))
        return rowcol

    def unlock_start(self):
        if self.vial_protocol < 0:
            return

        self.usb_send(self.dev, struct.pack("BB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_UNLOCK_START), retries=20)

    def unlock_poll(self):
        if self.vial_protocol < 0:
            return b""

        data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_UNLOCK_POLL), retries=20)
        return data

    def lock(self):
        if self.vial_protocol < 0:
            return

        self.usb_send(self.dev, struct.pack("BB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_LOCK), retries=20)

    def matrix_poll(self):
        if self.via_protocol < 0:
            return

        data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_GET_KEYBOARD_VALUE, VIA_SWITCH_MATRIX_STATE),
                             retries=3)
        return data

    def qmk_settings_set(self, qsid, value):
        from editor.qmk_settings import QmkSettings
        self.settings[qsid] = value
        data = self.usb_send(self.dev, struct.pack("<BBH", CMD_VIA_VIAL_PREFIX, CMD_VIAL_QMK_SETTINGS_SET, qsid)
                             + QmkSettings.qsid_serialize(qsid, value),
                             retries=20)
        return data[0]

    def qmk_settings_reset(self):
        self.usb_send(self.dev, struct.pack("BB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_QMK_SETTINGS_RESET))

    def _vialrgb_set_mode(self):
        self.usb_send(self.dev, struct.pack("BBHBBBB", CMD_VIA_LIGHTING_SET_VALUE, VIALRGB_SET_MODE,
                                            self.rgb_mode, self.rgb_speed,
                                            self.rgb_hsv[0], self.rgb_hsv[1], self.rgb_hsv[2]))

    def set_vialrgb_brightness(self, value):
        self.rgb_hsv = (self.rgb_hsv[0], self.rgb_hsv[1], value)
        self._vialrgb_set_mode()

    def set_vialrgb_speed(self, value):
        self.rgb_speed = value
        self._vialrgb_set_mode()

    def set_vialrgb_mode(self, value):
        self.rgb_mode = value
        self._vialrgb_set_mode()

    def set_vialrgb_color(self, h, s, v):
        self.rgb_hsv = (h, s, v)
        self._vialrgb_set_mode()

    def reload_layer_rgb_support(self):
        """Check if keyboard supports per-layer RGB and get initial status"""
        self.layer_rgb_supported = True
        
        try:
            data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_LAYER_RGB_GET_STATUS), retries=20)
            self.layer_rgb_enabled = bool(data[2])
            return True
        except:
            self.layer_rgb_enabled = False
            return True

    def get_layer_rgb_status(self):
        """Get current per-layer RGB status"""
        try:
            data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_LAYER_RGB_GET_STATUS), retries=20)
            return data[2:]
        except:
            return bytes([
                0x01 if self.layer_rgb_enabled else 0x00,
                self.layers if hasattr(self, 'layers') and self.layers > 0 else 4,
                0, 0, 0, 0, 0, 0
            ])

    def set_layer_rgb_enable(self, enabled):
        """Enable or disable per-layer RGB functionality"""
        try:
            data = self.usb_send(self.dev, struct.pack("BBB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_LAYER_RGB_ENABLE, int(enabled)), retries=20)
            success = data[2] == 0x01
            if success:
                self.layer_rgb_enabled = enabled
            return success
        except:
            self.layer_rgb_enabled = enabled
            return True

    def save_rgb_to_layer(self, layer):
        """Save current RGB settings to specified layer"""
        try:
            data = self.usb_send(self.dev, struct.pack("BBB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_LAYER_RGB_SAVE, layer), retries=20)
            return data[2] == 0x01
        except:
            return True

    def load_rgb_from_layer(self, layer):
        """Load RGB settings from specified layer"""
        try:
            data = self.usb_send(self.dev, struct.pack("BBB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_LAYER_RGB_LOAD, layer), retries=20)
            return data[2] == 0x01
        except:
            return True
            
    def get_custom_slot_config(self, slot, from_eeprom=True):
        """Get all parameters for a custom animation slot"""
        try:
            if slot >= 50:
                return None
            
            source = 1 if from_eeprom else 0
            data = self.usb_send(self.dev, struct.pack("BBBB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_CUSTOM_ANIM_GET_ALL, slot, source), retries=20)
            if data and len(data) > 2 and data[0] == 0x01:
                return data[3:15]
            return None
        except Exception as e:
            return None

    def get_custom_slot_ram_state(self, slot):
        """Get current RAM state for a custom animation slot"""
        return self.get_custom_slot_config(slot, from_eeprom=False)

    def set_custom_slot_parameter(self, slot, param_index, value):
        """Set a single parameter for a custom animation slot"""
        try:
            if slot >= 50 or param_index >= 12:
                return False
                
            data = self.usb_send(self.dev, struct.pack("BBBBB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_CUSTOM_ANIM_SET_PARAM, slot, param_index, value), retries=20)
            return data and len(data) > 0 and data[0] == 0x01
        except Exception as e:
            return False

    def set_custom_slot_all_parameters(self, slot, live_pos, macro_pos, live_anim, macro_anim, influence, 
                                     background, sustain, color_type, enabled, bg_brightness, live_speed, macro_speed):
        """Set all parameters for a custom animation slot"""
        try:
            if slot >= 50:
                return False
                
            params = [slot, live_pos, macro_pos, live_anim, macro_anim, influence, 
                     background, sustain, color_type, enabled, bg_brightness, live_speed, macro_speed]
            data = self.usb_send(self.dev, struct.pack("BB" + "B" * len(params), CMD_VIA_VIAL_PREFIX, CMD_VIAL_CUSTOM_ANIM_SET_ALL, *params), retries=20)
            return data and len(data) > 0 and data[0] == 0x01
            
        except Exception as e:
            return False
            
    def save_custom_slot(self, slot):
        """Save a specific custom slot configuration to EEPROM"""
        try:
            if slot >= 50:
                return False
                
            data = self.usb_send(self.dev, struct.pack("BBB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_CUSTOM_ANIM_SAVE, slot), retries=20)
            return data and len(data) > 0 and data[0] == 0x01
        except Exception as e:
            return False     

    def save_custom_slots(self):
        """Save all custom slot configurations to EEPROM"""
        try:
            data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_CUSTOM_ANIM_SAVE), retries=20)
            return data and len(data) > 0 and data[0] == 0x01
        except Exception as e:
            return False

    def reset_custom_slot(self, slot):
        """Reset a custom slot to default values"""
        try:
            if slot >= 50:
                return False
                
            data = self.usb_send(self.dev, struct.pack("BBB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_CUSTOM_ANIM_RESET_SLOT, slot), retries=20)
            return data and len(data) > 0 and data[0] == 0x01
        except Exception as e:
            return False
            
    def rescan_led_positions(self):
        """Rescan LED positions on the keyboard"""
        try:
            data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_CUSTOM_ANIM_RESCAN_LEDS), retries=20)
            return data and len(data) > 0 and data[0] == 0x01
        except Exception as e:
            return False

    def get_custom_animation_status(self):
        """Get custom animation status including active slot"""
        try:
            data = self.usb_send(self.dev, struct.pack("BB", CMD_VIA_VIAL_PREFIX, CMD_VIAL_CUSTOM_ANIM_GET_STATUS), retries=20)
            if data and len(data) >= 12:
                return data[1:]
            return bytes([50, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0])
        except Exception as e:
            return bytes([50, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0])

    def get_current_custom_slot(self):
        """Get the currently active custom slot number"""
        try:
            status = self.get_custom_animation_status()
            if len(status) > 1:
                return status[1]
                
            current_mode = self.rgb_mode
            if 57 <= current_mode <= 105:
                return current_mode - 57
            if current_mode in [106, 107, 108, 109, 110, 111, 112, 113, 114]:
                return 49
            return 0
        except Exception as e:
            return 0
         
    def _create_hid_packet(self, command, macro_num, data):
        """Create a properly formatted 32-byte HID packet"""
        packet = bytearray(HID_PACKET_SIZE)
        packet[0] = HID_MANUFACTURER_ID
        packet[1] = HID_SUB_ID
        packet[2] = HID_DEVICE_ID
        packet[3] = command
        packet[4] = macro_num
        packet[5] = 0  # Status
        
        if data:
            data_len = min(len(data), HID_PACKET_SIZE - 6)
            packet[6:6+data_len] = data[:data_len]
        
        return bytes(packet)

    def set_thruloop_config(self, loop_config_data):
        """Set basic ThruLoop configuration"""
        try:
            packet = self._create_hid_packet(HID_CMD_SET_LOOP_CONFIG, 0, loop_config_data)
            data = self.usb_send(self.dev, packet, retries=20)
            return data and len(data) > 0 and data[5] == 0
        except Exception as e:
            return False

    def set_thruloop_main_ccs(self, cc_values):
        """Set main loop CC values"""
        try:
            packet = self._create_hid_packet(HID_CMD_SET_MAIN_LOOP_CCS, 0, cc_values)
            data = self.usb_send(self.dev, packet, retries=20)
            return data and len(data) > 0 and data[5] == 0
        except Exception as e:
            return False

    def set_thruloop_overdub_ccs(self, cc_values):
        """Set overdub CC values"""
        try:
            packet = self._create_hid_packet(HID_CMD_SET_OVERDUB_CCS, 0, cc_values)
            data = self.usb_send(self.dev, packet, retries=20)
            return data and len(data) > 0 and data[5] == 0
        except Exception as e:
            return False

    def set_thruloop_navigation(self, nav_data):
        """Set ThruLoop navigation configuration"""
        try:
            packet = self._create_hid_packet(HID_CMD_SET_NAVIGATION_CONFIG, 0, nav_data)
            data = self.usb_send(self.dev, packet, retries=20)
            return data and len(data) > 0 and data[5] == 0
        except Exception as e:
            return False

    def get_thruloop_config(self):
        """Get all ThruLoop configuration using multi-packet collection"""
        try:
            # Send request for all config
            packet = self._create_hid_packet(HID_CMD_GET_ALL_CONFIG, 0, None)
            response = self.usb_send(self.dev, packet, retries=20)
            
            if not response or len(response) == 0 or response[5] != 0:
                return None
            
            # Collect response packets using proper HID read method
            packets = {}
            expected_commands = [HID_CMD_SET_LOOP_CONFIG, HID_CMD_SET_MAIN_LOOP_CCS, 
                               HID_CMD_SET_OVERDUB_CCS, HID_CMD_SET_NAVIGATION_CONFIG]
            
            # Try multiple times to collect all expected packets
            for attempt in range(20):
                try:
                    # Use the device's read method directly
                    if hasattr(self.dev, 'read'):
                        data = self.dev.read(32, timeout_ms=100)
                    else:
                        # Fallback: try to read using get_feature
                        data = self.dev.get_feature_report(0, 32)
                    
                    if data and len(data) >= 4 and data[0] == HID_MANUFACTURER_ID:
                        cmd = data[3]
                        if cmd in expected_commands:
                            packets[cmd] = data
                            
                    if len(packets) >= 4:
                        break
                        
                except:
                    # If direct read fails, try a small delay and continue
                    time.sleep(0.01)
                    continue
            
            # If we didn't get packets through direct reading, try alternative method
            if len(packets) < 4:
                # Send another request and try to get the cached responses
                for cmd in expected_commands:
                    if cmd not in packets:
                        try:
                            # Send a specific request for this command type
                            test_packet = self._create_hid_packet(cmd, 0, None)
                            data = self.usb_send(self.dev, test_packet, retries=1)
                            if data and len(data) >= 4 and data[0] == HID_MANUFACTURER_ID and data[3] == cmd:
                                packets[cmd] = data
                        except:
                            pass
            
            # Parse collected packets
            config = {}
            
            if HID_CMD_SET_LOOP_CONFIG in packets:
                data = packets[HID_CMD_SET_LOOP_CONFIG][6:]
                config['loopEnabled'] = data[0] != 0
                config['loopChannel'] = data[1] 
                config['syncMidi'] = data[2] != 0
                config['alternateRestart'] = data[3] != 0
                config['restartCCs'] = list(data[4:8])
                if len(data) > 8:
                    config['ccLoopRecording'] = data[8] != 0
                else:
                    config['ccLoopRecording'] = False
                    
            if HID_CMD_SET_MAIN_LOOP_CCS in packets:
                data = packets[HID_CMD_SET_MAIN_LOOP_CCS][6:]
                config['mainCCs'] = list(data[:20])
                
            if HID_CMD_SET_OVERDUB_CCS in packets:
                data = packets[HID_CMD_SET_OVERDUB_CCS][6:]
                config['overdubCCs'] = list(data[:20])
                
            if HID_CMD_SET_NAVIGATION_CONFIG in packets:
                data = packets[HID_CMD_SET_NAVIGATION_CONFIG][6:]
                config['separateLoopChopCC'] = data[0] != 0
                config['masterCC'] = data[1]
                config['navCCs'] = list(data[2:10])
                
            return config if config else None
            
        except Exception as e:
            return None

    def reset_thruloop_config(self):
        """Reset ThruLoop configuration to defaults"""
        try:
            packet = self._create_hid_packet(HID_CMD_RESET_LOOP_CONFIG, 0, None)
            data = self.usb_send(self.dev, packet, retries=20)
            return data and len(data) > 0 and data[5] == 0
        except Exception as e:
            return False

    def set_midi_config(self, config_data):
        """Set MIDIswitch basic configuration"""
        try:
            packet = self._create_hid_packet(HID_CMD_SET_KEYBOARD_CONFIG, 0, config_data)
            data = self.usb_send(self.dev, packet, retries=20)
            return data and len(data) > 0 and data[5] == 0
        except Exception as e:
            return False

    def set_midi_advanced_config(self, advanced_data):
        """Set MIDIswitch advanced configuration"""
        try:
            packet = self._create_hid_packet(HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED, 0, advanced_data)
            data = self.usb_send(self.dev, packet, retries=20)
            return data and len(data) > 0 and data[5] == 0
        except Exception as e:
            return False

    def save_midi_slot(self, slot, config_data):
        """Save MIDIswitch configuration to slot"""
        try:
            slot_data = [slot] + list(config_data)
            packet = self._create_hid_packet(HID_CMD_SAVE_KEYBOARD_SLOT, 0, slot_data)
            data = self.usb_send(self.dev, packet, retries=20)
            return data and len(data) > 0 and data[5] == 0
        except Exception as e:
            return False

    def load_midi_slot(self, slot):
        """Load MIDIswitch configuration from slot"""
        try:
            packet = self._create_hid_packet(HID_CMD_LOAD_KEYBOARD_SLOT, 0, [slot])
            data = self.usb_send(self.dev, packet, retries=20)
            return data and len(data) > 0 and data[5] == 0
        except Exception as e:
            return False

    def reset_midi_config(self):
        """Reset MIDIswitch configuration to defaults"""
        try:
            packet = self._create_hid_packet(HID_CMD_RESET_KEYBOARD_CONFIG, 0, None)
            data = self.usb_send(self.dev, packet, retries=20)
            return data and len(data) > 0 and data[5] == 0
        except Exception as e:
            return False

    def get_midi_config(self):
        """Get MIDIswitch configuration using multi-packet collection"""
        try:
            # Send request for keyboard config
            packet = self._create_hid_packet(HID_CMD_GET_KEYBOARD_CONFIG, 0, None)
            response = self.usb_send(self.dev, packet, retries=20)
            
            if not response or len(response) == 0 or response[5] != 0:
                return None
            
            # Collect response packets using proper HID read method
            packets = {}
            expected_commands = [HID_CMD_GET_KEYBOARD_CONFIG, HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED]
            
            # Try multiple times to collect all expected packets
            for attempt in range(20):
                try:
                    # Use the device's read method directly
                    if hasattr(self.dev, 'read'):
                        data = self.dev.read(32, timeout_ms=100)
                    else:
                        # Fallback: try to read using get_feature
                        data = self.dev.get_feature_report(0, 32)
                    
                    if data and len(data) >= 4 and data[0] == HID_MANUFACTURER_ID:
                        cmd = data[3]
                        if cmd in expected_commands:
                            packets[cmd] = data
                            
                    if len(packets) >= 2:
                        break
                        
                except:
                    # If direct read fails, try a small delay and continue
                    time.sleep(0.01)
                    continue
            
            # If we didn't get packets through direct reading, try alternative method
            if len(packets) < 2:
                # Send another request and try to get the cached responses
                for cmd in expected_commands:
                    if cmd not in packets:
                        try:
                            # Send a specific request for this command type
                            test_packet = self._create_hid_packet(cmd, 0, None)
                            data = self.usb_send(self.dev, test_packet, retries=1)
                            if data and len(data) >= 4 and data[0] == HID_MANUFACTURER_ID and data[3] == cmd:
                                packets[cmd] = data
                        except:
                            pass
            
            # Parse collected packets
            config = {}
            
            if HID_CMD_GET_KEYBOARD_CONFIG in packets:
                data = packets[HID_CMD_GET_KEYBOARD_CONFIG][6:]
                
                velocity_sensitivity = struct.unpack('<I', data[0:4])[0]
                cc_sensitivity = struct.unpack('<I', data[4:8])[0] 
                channel_number = data[8]
                transpose_number = struct.unpack('<b', data[9:10])[0]
                octave_number = struct.unpack('<b', data[10:11])[0]
                transpose_number2 = struct.unpack('<b', data[11:12])[0]
                octave_number2 = struct.unpack('<b', data[12:13])[0]
                transpose_number3 = struct.unpack('<b', data[13:14])[0]
                octave_number3 = struct.unpack('<b', data[14:15])[0]
                velocity_number = data[15]
                velocity_number2 = data[16]
                velocity_number3 = data[17]
                random_velocity_modifier = data[18]
                oled_keyboard = struct.unpack('<I', data[19:23])[0]
                smart_chord_light = data[23]
                smart_chord_light_mode = data[24]
                
                config.update({
                    "velocity_sensitivity": velocity_sensitivity,
                    "cc_sensitivity": cc_sensitivity,
                    "channel_number": channel_number,
                    "transpose_number": transpose_number,
                    "transpose_number2": transpose_number2,
                    "transpose_number3": transpose_number3,
                    "velocity_number": velocity_number,
                    "velocity_number2": velocity_number2,
                    "velocity_number3": velocity_number3,
                    "random_velocity_modifier": random_velocity_modifier,
                    "oled_keyboard": oled_keyboard,
                    "smart_chord_light": smart_chord_light,
                    "smart_chord_light_mode": smart_chord_light_mode
                })
                
            if HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED in packets:
                data = packets[HID_CMD_SET_KEYBOARD_CONFIG_ADVANCED][6:]
                
                config.update({
                    "key_split_channel": data[0],
                    "key_split2_channel": data[1], 
                    "key_split_status": data[2],
                    "key_split_transpose_status": data[3],
                    "key_split_velocity_status": data[4],
                    "custom_layer_animations_enabled": data[5] != 0,
                    "unsynced_mode_active": data[6],
                    "sample_mode_active": data[7] != 0,
                    "loop_messaging_enabled": data[8] != 0,
                    "loop_messaging_channel": data[9],
                    "sync_midi_mode": data[10] != 0,
                    "alternate_restart_mode": data[11] != 0,
                    "colorblindmode": data[12],
                    "cclooprecording": data[13] != 0,
                    "truesustain": data[14] != 0
                })
                
            return config if config else None
            
        except Exception as e:
            return None
            
    def set_layer_actuation(self, data):
        """Set actuation for a specific layer
        
        Args:
            data: bytearray [layer, normal_actuation, midi_actuation, aftertouch_mode,
                            velocity_mode, rapidfire_sensitivity, midi_rapidfire_sensitivity,
                            velocity_speed_scale, aftertouch_cc]
        """
        try:
            packet = self._create_hid_packet(0xCA, 0, data)  # HID_CMD_SET_LAYER_ACTUATION
            response = self.usb_send(self.dev, packet, retries=20)
            return response and len(response) > 0 and response[5] == 0
        except Exception as e:
            return False

    def set_layer_actuation(self, data):
        """Set actuation for a specific layer
        
        Args:
            data: bytearray [layer, normal_actuation, midi_actuation, aftertouch_mode,
                            velocity_mode, rapidfire_sensitivity, midi_rapidfire_sensitivity,
                            midi_rapidfire_velocity, velocity_speed_scale, aftertouch_cc, flags]
        """
        try:
            packet = self._create_hid_packet(0xCA, 0, data)
            response = self.usb_send(self.dev, packet, retries=20)
            return response and len(response) > 0 and response[5] == 0
        except Exception as e:
            return False

    def get_layer_actuation(self, layer):
        """Get actuation for a specific layer
        
        Args:
            layer: Layer number (0-11)
            
        Returns:
            dict: {normal, midi, aftertouch, velocity, rapid, midi_rapid_sens, midi_rapid_vel,
                   vel_speed, aftertouch_cc, rapidfire_enabled, midi_rapidfire_enabled} or None
        """
        try:
            packet = self._create_hid_packet(0xCB, layer, None)
            response = self.usb_send(self.dev, packet, retries=20)
            
            if not response or len(response) < 16:
                return None
            
            flags = response[15]
            return {
                'normal': response[6],
                'midi': response[7],
                'aftertouch': response[8],
                'velocity': response[9],
                'rapid': response[10],
                'midi_rapid_sens': response[11],
                'midi_rapid_vel': response[12],
                'vel_speed': response[13],
                'aftertouch_cc': response[14],
                'rapidfire_enabled': (flags & 0x01) != 0,
                'midi_rapidfire_enabled': (flags & 0x02) != 0
            }
        except Exception as e:
            return None

    def get_all_layer_actuations(self):
        """Get all layer actuations at once
        
        Returns:
            list: 120 values (12 layers × 10 bytes) or None on error
        """
        try:
            packet = self._create_hid_packet(0xCC, 0, None)
            self.usb_send(self.dev, packet, retries=20)
            
            # Collect 5 packets (120 bytes total, 26 bytes per packet except last)
            packets = []
            for attempt in range(30):
                try:
                    if hasattr(self.dev, 'read'):
                        data = self.dev.read(32, timeout_ms=100)
                    else:
                        data = self.dev.get_feature_report(0, 32)
                    
                    if data and len(data) >= 4 and data[0] == HID_MANUFACTURER_ID and data[3] == 0xCC:
                        packet_num = data[4]
                        if packet_num < 5:
                            packets.append((packet_num, data[6:32]))
                        
                    if len(packets) >= 5:
                        break
                except:
                    time.sleep(0.01)
                    continue
            
            if len(packets) < 5:
                return None
            
            # Sort packets and combine
            packets.sort(key=lambda x: x[0])
            actuations = bytearray()
            for _, packet_data in packets:
                actuations.extend(packet_data)
            
            return actuations[:120]  # 12 layers × 10 bytes
        except Exception as e:
            return None

    def reset_layer_actuations(self):
        """Reset all layer actuations to defaults"""
        try:
            packet = self._create_hid_packet(0xCD, 0, None)
            response = self.usb_send(self.dev, packet, retries=20)
            return response and len(response) > 0 and response[5] == 0
        except Exception as e:
            return False
            
    def reload_thruloop_config(self):
        """Load ThruLoop configuration from keyboard"""
        try:
            self.thruloop_config = self.get_thruloop_config()
        except:
            self.thruloop_config = None

    def reload_midi_config(self):
        """Load MIDI configuration from keyboard"""
        try:
            self.midi_config = self.get_midi_config()
        except:
            self.midi_config = None

    def reload_layer_actuations(self):
        """Load layer actuations from keyboard"""
        try:
            self.layer_actuations = self.get_all_layer_actuations()
        except:
            self.layer_actuations = None