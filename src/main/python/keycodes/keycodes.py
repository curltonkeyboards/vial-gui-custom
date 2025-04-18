# coding: utf-8

# SPDX-License-Identifier: GPL-2.0-or-later

import sys

from keycodes.keycodes_v5 import keycodes_v5
from keycodes.keycodes_v6 import keycodes_v6


class Keycode:

    masked_keycodes = set()
    recorder_alias_to_keycode = dict()
    qmk_id_to_keycode = dict()
    protocol = 0

    def __init__(self, qmk_id, label, tooltip=None, masked=False, printable=None, recorder_alias=None, alias=None):
        self.qmk_id = qmk_id
        self.qmk_id_to_keycode[qmk_id] = self
        self.label = label
        # we cannot embed full CJK fonts due to large size, workaround like this for now
        if sys.platform == "emscripten" and not label.isascii() and qmk_id != "KC_TRNS":
            self.label = qmk_id.replace("KC_", "")

        self.tooltip = tooltip
        # whether this keycode requires another sub-keycode
        self.masked = masked

        # if this is printable keycode, what character does it normally output (i.e. non-shifted state)
        self.printable = printable

        self.alias = [self.qmk_id]
        if alias:
            self.alias += alias

        if recorder_alias:
            for alias in recorder_alias:
                if alias in self.recorder_alias_to_keycode:
                    raise RuntimeError("Misconfigured: two keycodes claim the same alias {}".format(alias))
                self.recorder_alias_to_keycode[alias] = self

        if masked:
            assert qmk_id.endswith("(kc)")
            self.masked_keycodes.add(qmk_id.replace("(kc)", ""))

    @classmethod
    def find(cls, qmk_id):
        # this is to handle cases of qmk_id LCTL(kc) propagated here from find_inner_keycode
        if qmk_id == "kc":
            qmk_id = "KC_NO"
        return KEYCODES_MAP.get(qmk_id)

    @classmethod
    def find_outer_keycode(cls, qmk_id):
        """
        Finds outer keycode, i.e. if it is masked like 0x5Fxx, just return the 0x5F00 portion
        """
        if cls.is_mask(qmk_id):
            qmk_id = qmk_id[:qmk_id.find("(")]
        return cls.find(qmk_id)

    @classmethod
    def find_inner_keycode(cls, qmk_id):
        """
        Finds inner keycode, i.e. if it is masked like 0x5F12, just return the 0x12 portion
        """
        if cls.is_mask(qmk_id):
            qmk_id = qmk_id[qmk_id.find("(")+1:-1]
        return cls.find(qmk_id)

    @classmethod
    def find_by_recorder_alias(cls, alias):
        return cls.recorder_alias_to_keycode.get(alias)

    @classmethod
    def find_by_qmk_id(cls, qmk_id):
        return cls.qmk_id_to_keycode.get(qmk_id)

    @classmethod
    def is_mask(cls, qmk_id):
        return "(" in qmk_id and qmk_id[:qmk_id.find("(")] in cls.masked_keycodes

    @classmethod
    def is_basic(cls, qmk_id):
        return cls.deserialize(qmk_id) < 0x00FF

    @classmethod
    def label(cls, qmk_id):
        keycode = cls.find_outer_keycode(qmk_id)
        if keycode is None:
            return qmk_id
        return keycode.label

    @classmethod
    def tooltip(cls, qmk_id):
        keycode = cls.find_outer_keycode(qmk_id)
        if keycode is None:
            return None
        tooltip = keycode.qmk_id
        if keycode.tooltip:
            tooltip = "{}: {}".format(tooltip, keycode.tooltip)
        return tooltip

    @classmethod
    def serialize(cls, code):
        """ Converts integer keycode to string """
        if cls.protocol == 6:
            masked = keycodes_v6.masked
        else:
            masked = keycodes_v5.masked

        if (code & 0xFF00) not in masked:
            kc = RAWCODES_MAP.get(code)
            if kc is not None:
                return kc.qmk_id
        else:
            outer = RAWCODES_MAP.get(code & 0xFF00)
            inner = RAWCODES_MAP.get(code & 0x00FF)
            if outer is not None and inner is not None:
                return outer.qmk_id.replace("kc", inner.qmk_id)
        return hex(code)

    @classmethod
    def deserialize(cls, val, reraise=False):
        """ Converts string keycode to integer """

        from any_keycode import AnyKeycode

        if isinstance(val, int):
            return val
        if val in cls.qmk_id_to_keycode:
            return cls.resolve(cls.qmk_id_to_keycode[val].qmk_id)
        anykc = AnyKeycode()
        try:
            return anykc.decode(val)
        except Exception:
            if reraise:
                raise
        return 0

    @classmethod
    def normalize(cls, code):
        """ Changes e.g. KC_PERC to LSFT(KC_5) """

        return Keycode.serialize(Keycode.deserialize(code))

    @classmethod
    def resolve(cls, qmk_constant):
        """ Translates a qmk_constant into firmware-specific integer keycode or macro constant """
        if cls.protocol == 6:
            kc = keycodes_v6.kc
        else:
            kc = keycodes_v5.kc

        if qmk_constant not in kc:
            raise RuntimeError("unable to resolve qmk_id={}".format(qmk_constant))
        return kc[qmk_constant]
        
    @classmethod
    def description(cls, qmk_id):
        keycode = cls.find_outer_keycode(qmk_id)
        if keycode is None or keycode.tooltip is None:
            return ""
        return keycode.tooltip


K = Keycode

BASIC_KEYCODES = {
    "KC_NO",
    "KC_TRNS",
    "KC_A",
    "KC_B",
    "KC_C",
    "KC_D",
    "KC_E",
    "KC_F",
    "KC_G",
    "KC_H",
    "KC_I",
    "KC_J",
    "KC_K",
    "KC_L",
    "KC_M",
    "KC_N",
    "KC_O",
    "KC_P",
    "KC_Q",
    "KC_R",
    "KC_S",
    "KC_T",
    "KC_U",
    "KC_V",
    "KC_W",
    "KC_X",
    "KC_Y",
    "KC_Z",
    "KC_1",
    "KC_2",
    "KC_3",
    "KC_4",
    "KC_5",
    "KC_6",
    "KC_7",
    "KC_8",
    "KC_9",
    "KC_0",
    "KC_ENTER",
    "KC_ESCAPE",
    "KC_BSPACE",
    "KC_TAB",
    "KC_SPACE",
    "KC_MINUS",
    "KC_EQUAL",
    "KC_LBRACKET",
    "KC_RBRACKET",
    "KC_BSLASH",
    "KC_NONUS_HASH",
    "KC_SCOLON",
    "KC_QUOTE",
    "KC_GRAVE",
    "KC_COMMA",
    "KC_DOT",
    "KC_SLASH",
    "KC_CAPSLOCK",
    "KC_F1",
    "KC_F2",
    "KC_F3",
    "KC_F4",
    "KC_F5",
    "KC_F6",
    "KC_F7",
    "KC_F8",
    "KC_F9",
    "KC_F10",
    "KC_F11",
    "KC_F12",
    "KC_PSCREEN",
    "KC_SCROLLLOCK",
    "KC_PAUSE",
    "KC_INSERT",
    "KC_HOME",
    "KC_PGUP",
    "KC_DELETE",
    "KC_END",
    "KC_PGDOWN",
    "KC_RIGHT",
    "KC_LEFT",
    "KC_DOWN",
    "KC_UP",
    "KC_NUMLOCK",
    "KC_KP_SLASH",
    "KC_KP_ASTERISK",
    "KC_KP_MINUS",
    "KC_KP_PLUS",
    "KC_KP_ENTER",
    "KC_KP_1",
    "KC_KP_2",
    "KC_KP_3",
    "KC_KP_4",
    "KC_KP_5",
    "KC_KP_6",
    "KC_KP_7",
    "KC_KP_8",
    "KC_KP_9",
    "KC_KP_0",
    "KC_KP_DOT",
    "KC_NONUS_BSLASH",
    "KC_APPLICATION",
    "KC_KP_EQUAL",
    "KC_F13",
    "KC_F14",
    "KC_F15",
    "KC_F16",
    "KC_F17",
    "KC_F18",
    "KC_F19",
    "KC_F20",
    "KC_F21",
    "KC_F22",
    "KC_F23",
    "KC_F24",
    "KC_EXEC",
    "KC_HELP",
    "KC_SLCT",
    "KC_STOP",
    "KC_AGIN",
    "KC_UNDO",
    "KC_CUT",
    "KC_COPY",
    "KC_PSTE",
    "KC_FIND",
    "KC__VOLUP",
    "KC__VOLDOWN",
    "KC_LCAP",
    "KC_LNUM",
    "KC_LSCR",
    "KC_KP_COMMA",
    "KC_RO",
    "KC_KANA",
    "KC_JYEN",
    "KC_HENK",
    "KC_MHEN",
    "KC_LANG1",
    "KC_LANG2",
    "KC_PWR",
    "KC_SLEP",
    "KC_WAKE",
    "KC_MUTE",
    "KC_VOLU",
    "KC_VOLD",
    "KC_MNXT",
    "KC_MPRV",
    "KC_MSTP",
    "KC_MPLY",
    "KC_MSEL",
    "KC_EJCT",
    "KC_MAIL",
    "KC_CALC",
    "KC_MYCM",
    "KC_WSCH",
    "KC_WHOM",
    "KC_WBAK",
    "KC_WFWD",
    "KC_WSTP",
    "KC_WREF",
    "KC_WFAV",
    "KC_MFFD",
    "KC_MRWD",
    "KC_BRIU",
    "KC_BRID",
    "KC_LCTRL",
    "KC_LSHIFT",
    "KC_LALT",
    "KC_LGUI",
    "KC_RCTRL",
    "KC_RSHIFT",
    "KC_RALT",
    "KC_RGUI",
}

KEYCODES_CLEAR = [
]

KEYCODES_SPECIAL = [
    K("KC_NO", ""),
    K("KC_TRNS", "▽", alias=["KC_TRANSPARENT"]),
]

KEYCODES_BASIC_NUMPAD = [
    K("KC_NUMLOCK", "Num\nLock", recorder_alias=["num lock"], alias=["KC_NLCK"]),
    K("KC_KP_SLASH", "/", alias=["KC_PSLS"]),
    K("KC_KP_ASTERISK", "*", alias=["KC_PAST"]),
    K("KC_KP_MINUS", "-", alias=["KC_PMNS"]),
    K("KC_KP_PLUS", "+", alias=["KC_PPLS"]),
    K("KC_KP_ENTER", "Num\nEnter", alias=["KC_PENT"]),
    K("KC_KP_1", "1", alias=["KC_P1"]),
    K("KC_KP_2", "2", alias=["KC_P2"]),
    K("KC_KP_3", "3", alias=["KC_P3"]),
    K("KC_KP_4", "4", alias=["KC_P4"]),
    K("KC_KP_5", "5", alias=["KC_P5"]),
    K("KC_KP_6", "6", alias=["KC_P6"]),
    K("KC_KP_7", "7", alias=["KC_P7"]),
    K("KC_KP_8", "8", alias=["KC_P8"]),
    K("KC_KP_9", "9", alias=["KC_P9"]),
    K("KC_KP_0", "0", alias=["KC_P0"]),
    K("KC_KP_DOT", ".", alias=["KC_PDOT"]),
    K("KC_KP_EQUAL", "=", alias=["KC_PEQL"]),
    K("KC_KP_COMMA", ",", alias=["KC_PCMM"]),
]

KEYCODES_BASIC_NAV = [
    K("KC_PSCREEN", "Print\nScreen", alias=["KC_PSCR"]),
    K("KC_SCROLLLOCK", "Scroll\nLock", recorder_alias=["scroll lock"], alias=["KC_SLCK", "KC_BRMD"]),
    K("KC_PAUSE", "Pause", recorder_alias=["pause", "break"], alias=["KC_PAUS", "KC_BRK", "KC_BRMU"]),
    K("KC_INSERT", "Insert", recorder_alias=["insert"], alias=["KC_INS"]),
    K("KC_HOME", "Home", recorder_alias=["home"]),
    K("KC_PGUP", "Page\nUp", recorder_alias=["page up"]),
    K("KC_DELETE", "Del", recorder_alias=["delete"], alias=["KC_DEL"]),
    K("KC_END", "End", recorder_alias=["end"]),
    K("KC_PGDOWN", "Page\nDown", recorder_alias=["page down"], alias=["KC_PGDN"]),
    K("KC_RIGHT", "Right", recorder_alias=["right"], alias=["KC_RGHT"]),
    K("KC_LEFT", "Left", recorder_alias=["left"]),
    K("KC_DOWN", "Down", recorder_alias=["down"]),
    K("KC_UP", "Up", recorder_alias=["up"]),
]

KEYCODES_BASIC = [
    K("KC_A", "A", printable="a", recorder_alias=["a"]),
    K("KC_B", "B", printable="b", recorder_alias=["b"]),
    K("KC_C", "C", printable="c", recorder_alias=["c"]),
    K("KC_D", "D", printable="d", recorder_alias=["d"]),
    K("KC_E", "E", printable="e", recorder_alias=["e"]),
    K("KC_F", "F", printable="f", recorder_alias=["f"]),
    K("KC_G", "G", printable="g", recorder_alias=["g"]),
    K("KC_H", "H", printable="h", recorder_alias=["h"]),
    K("KC_I", "I", printable="i", recorder_alias=["i"]),
    K("KC_J", "J", printable="j", recorder_alias=["j"]),
    K("KC_K", "K", printable="k", recorder_alias=["k"]),
    K("KC_L", "L", printable="l", recorder_alias=["l"]),
    K("KC_M", "M", printable="m", recorder_alias=["m"]),
    K("KC_N", "N", printable="n", recorder_alias=["n"]),
    K("KC_O", "O", printable="o", recorder_alias=["o"]),
    K("KC_P", "P", printable="p", recorder_alias=["p"]),
    K("KC_Q", "Q", printable="q", recorder_alias=["q"]),
    K("KC_R", "R", printable="r", recorder_alias=["r"]),
    K("KC_S", "S", printable="s", recorder_alias=["s"]),
    K("KC_T", "T", printable="t", recorder_alias=["t"]),
    K("KC_U", "U", printable="u", recorder_alias=["u"]),
    K("KC_V", "V", printable="v", recorder_alias=["v"]),
    K("KC_W", "W", printable="w", recorder_alias=["w"]),
    K("KC_X", "X", printable="x", recorder_alias=["x"]),
    K("KC_Y", "Y", printable="y", recorder_alias=["y"]),
    K("KC_Z", "Z", printable="z", recorder_alias=["z"]),
    K("KC_1", "!\n1", printable="1", recorder_alias=["1"]),
    K("KC_2", "@\n2", printable="2", recorder_alias=["2"]),
    K("KC_3", "#\n3", printable="3", recorder_alias=["3"]),
    K("KC_4", "$\n4", printable="4", recorder_alias=["4"]),
    K("KC_5", "%\n5", printable="5", recorder_alias=["5"]),
    K("KC_6", "^\n6", printable="6", recorder_alias=["6"]),
    K("KC_7", "&\n7", printable="7", recorder_alias=["7"]),
    K("KC_8", "*\n8", printable="8", recorder_alias=["8"]),
    K("KC_9", "(\n9", printable="9", recorder_alias=["9"]),
    K("KC_0", ")\n0", printable="0", recorder_alias=["0"]),
    K("KC_ENTER", "Enter", recorder_alias=["enter"], alias=["KC_ENT"]),
    K("KC_ESCAPE", "Esc", recorder_alias=["esc"], alias=["KC_ESC"]),
    K("KC_BSPACE", "Bksp", recorder_alias=["backspace"], alias=["KC_BSPC"]),
    K("KC_TAB", "Tab", recorder_alias=["tab"]),
    K("KC_SPACE", "Space", recorder_alias=["space"], alias=["KC_SPC"]),
    K("KC_MINUS", "_\n-", printable="-", recorder_alias=["-"], alias=["KC_MINS"]),
    K("KC_EQUAL", "+\n=", printable="=", recorder_alias=["="], alias=["KC_EQL"]),
    K("KC_LBRACKET", "{\n[", printable="[", recorder_alias=["["], alias=["KC_LBRC"]),
    K("KC_RBRACKET", "}\n]", printable="]", recorder_alias=["]"], alias=["KC_RBRC"]),
    K("KC_BSLASH", "|\n\\", printable="\\", recorder_alias=["\\"], alias=["KC_BSLS"]),
    K("KC_SCOLON", ":\n;", printable=";", recorder_alias=[";"], alias=["KC_SCLN"]),
    K("KC_QUOTE", "\"\n'", printable="'", recorder_alias=["'"], alias=["KC_QUOT"]),
    K("KC_GRAVE", "~\n`", printable="`", recorder_alias=["`"], alias=["KC_GRV", "KC_ZKHK"]),
    K("KC_COMMA", "<\n,", printable=",", recorder_alias=[","], alias=["KC_COMM"]),
    K("KC_DOT", ">\n.", printable=".", recorder_alias=["."]),
    K("KC_SLASH", "?\n/", printable="/", recorder_alias=["/"], alias=["KC_SLSH"]),
    K("KC_CAPSLOCK", "Caps\nLock", recorder_alias=["caps lock"], alias=["KC_CLCK", "KC_CAPS"]),
    K("KC_F1", "F1", recorder_alias=["f1"]),
    K("KC_F2", "F2", recorder_alias=["f2"]),
    K("KC_F3", "F3", recorder_alias=["f3"]),
    K("KC_F4", "F4", recorder_alias=["f4"]),
    K("KC_F5", "F5", recorder_alias=["f5"]),
    K("KC_F6", "F6", recorder_alias=["f6"]),
    K("KC_F7", "F7", recorder_alias=["f7"]),
    K("KC_F8", "F8", recorder_alias=["f8"]),
    K("KC_F9", "F9", recorder_alias=["f9"]),
    K("KC_F10", "F10", recorder_alias=["f10"]),
    K("KC_F11", "F11", recorder_alias=["f11"]),
    K("KC_F12", "F12", recorder_alias=["f12"]),

    K("KC_APPLICATION", "Menu", recorder_alias=["menu", "left menu", "right menu"], alias=["KC_APP"]),
    K("KC_LCTRL", "LCtrl", recorder_alias=["left ctrl", "ctrl"], alias=["KC_LCTL"]),
    K("KC_LSHIFT", "LShift", recorder_alias=["left shift", "shift"], alias=["KC_LSFT"]),
    K("KC_LALT", "LAlt", recorder_alias=["alt"], alias=["KC_LOPT"]),
    K("KC_LGUI", "LGui", recorder_alias=["left windows", "windows"], alias=["KC_LCMD", "KC_LWIN"]),
    K("KC_RCTRL", "RCtrl", recorder_alias=["right ctrl"], alias=["KC_RCTL"]),
    K("KC_RSHIFT", "RShift", recorder_alias=["right shift"], alias=["KC_RSFT"]),
    K("KC_RALT", "RAlt", alias=["KC_ALGR", "KC_ROPT"]),
    K("KC_RGUI", "RGui", recorder_alias=["right windows"], alias=["KC_RCMD", "KC_RWIN"]),
]

KEYCODES_BASIC.extend(KEYCODES_BASIC_NUMPAD)
KEYCODES_BASIC.extend(KEYCODES_BASIC_NAV)

KEYCODES_SHIFTED = [
    K("KC_TILD", "~"),
    K("KC_EXLM", "!"),
    K("KC_AT", "@"),
    K("KC_HASH", "#"),
    K("KC_DLR", "$"),
    K("KC_PERC", "%"),
    K("KC_CIRC", "^"),
    K("KC_AMPR", "&"),
    K("KC_ASTR", "*"),
    K("KC_LPRN", "("),
    K("KC_RPRN", ")"),
    K("KC_UNDS", "_"),
    K("KC_PLUS", "+"),
    K("KC_LCBR", "{"),
    K("KC_RCBR", "}"),
    K("KC_LT", "<"),
    K("KC_GT", ">"),
    K("KC_COLN", ":"),
    K("KC_PIPE", "|"),
    K("KC_QUES", "?"),
    K("KC_DQUO", '"'),
]

KEYCODES_ISO = [
    K("KC_NONUS_HASH", "~\n#", "Non-US # and ~", alias=["KC_NUHS"]),
    K("KC_NONUS_BSLASH", "|\n\\", "Non-US \\ and |", alias=["KC_NUBS"]),
    K("KC_RO", "_\n\\", "JIS \\ and _", alias=["KC_INT1"]),
    K("KC_KANA", "カタカナ\nひらがな", "JIS Katakana/Hiragana", alias=["KC_INT2"]),
    K("KC_JYEN", "|\n¥", alias=["KC_INT3"]),
    K("KC_HENK", "変換", "JIS Henkan", alias=["KC_INT4"]),
    K("KC_MHEN", "無変換", "JIS Muhenkan", alias=["KC_INT5"]),
]

KEYCODES_ISO_KR = [
    K("KC_LANG1", "한영\nかな", "Korean Han/Yeong / JP Mac Kana", alias=["KC_HAEN"]),
    K("KC_LANG2", "漢字\n英数", "Korean Hanja / JP Mac Eisu", alias=["KC_HANJ"]),
]

KEYCODES_ISO.extend(KEYCODES_ISO_KR)

KEYCODES_LAYERS = []

KEYCODES_OLED = [
    K("OLED_1", "Screen\nKeyboard\nShift", "Momentarily turn on layer when pressed"),
    K("OLED_2", "SmartChord\nLight\nMode", "Momentarily turn on layer when pressed"),
   # K("OLED_3", "SmartChord\nPiano\nModes", "Momentarily turn on layer when pressed"),
  #  K("OLED_1", "Hold\nLayer\n3", "Momentarily turn on layer when pressed"),
  #  K("OLED_1", "Hold\nLayer\n4", "Momentarily turn on layer when pressed"),
]

KEYCODES_LAYERS_MO = [
    K("MO(0)", "Hold\nLayer\n0", "Momentarily turn on layer when pressed"),
    K("MO(1)", "Hold\nLayer\n1", "Momentarily turn on layer when pressed"),
    K("MO(2)", "Hold\nLayer\n2", "Momentarily turn on layer when pressed"),
    K("MO(3)", "Hold\nLayer\n3", "Momentarily turn on layer when pressed"),
    K("MO(4)", "Hold\nLayer\n4", "Momentarily turn on layer when pressed"),
    K("MO(5)", "Hold\nLayer\n5", "Momentarily turn on layer when pressed"),
    K("MO(6)", "Hold\nLayer\n6", "Momentarily turn on layer when pressed"),
    K("MO(7)", "Hold\nLayer\n7", "Momentarily turn on layer when pressed"),
    K("MO(8)", "Hold\nLayer\n8", "Momentarily turn on layer when pressed"),
    K("MO(9)", "Hold\nLayer\n9", "Momentarily turn on layer when pressed"),
    K("MO(10)", "Hold\nLayer\n10", "Momentarily turn on layer when pressed"),
    K("MO(11)", "Hold\nLayer\n11", "Momentarily turn on layer when pressed"),
]


KEYCODES_LAYERS_DF = [
    K("DF(0)", "Default\nLayer\n0", "Set to default (active)\nLayer)"),
    K("DF(1)", "Default\nLayer\n1", "Set to default (active)\nLayer)"),
    K("DF(2)", "Default\nLayer\n2", "Set to default (active)\nLayer)"),
    K("DF(3)", "Default\nLayer\n3", "Set to default (active)\nLayer)"),
    K("DF(4)", "Default\nLayer\n4", "Set to default (active)\nLayer)"),
    K("DF(5)", "Default\nLayer\n5", "Set to default (active)\nLayer)"),
    K("DF(6)", "Default\nLayer\n6", "Set to default (active)\nLayer)"),
    K("DF(7)", "Default\nLayer\n7", "Set to default (active)\nLayer)"),
    K("DF(8)", "Default\nLayer\n8", "Set to default (active)\nLayer)"),
    K("DF(9)", "Default\nLayer\n9", "Set to default (active)\nLayer)"),
    K("DF(10)", "Default\nLayer\n10", "Set to default (active)\nLayer)"),
    K("DF(11)", "Default\nLayer\n11", "Set to default (active)\nLayer)"),
]

KEYCODES_LAYERS_TG = [
    K("TG(0)", "Toggle\nLayer\n0", "Toggle\nLayer on or off)"),
    K("TG(1)", "Toggle\nLayer\n1", "Toggle\nLayer on or off)"),
    K("TG(2)", "Toggle\nLayer\n2", "Toggle\nLayer on or off)"),
    K("TG(3)", "Toggle\nLayer\n3", "Toggle\nLayer on or off)"),
    K("TG(4)", "Toggle\nLayer\n4", "Toggle\nLayer on or off)"),
    K("TG(5)", "Toggle\nLayer\n5", "Toggle\nLayer on or off)"),
    K("TG(6)", "Toggle\nLayer\n6", "Toggle\nLayer on or off)"),
    K("TG(7)", "Toggle\nLayer\n7", "Toggle\nLayer on or off)"),
    K("TG(8)", "Toggle\nLayer\n8", "Toggle\nLayer on or off)"),
    K("TG(9)", "Toggle\nLayer\n9", "Toggle\nLayer on or off)"),
    K("TG(10)", "Toggle\nLayer\n10", "Toggle\nLayer on or off)"),
    K("TG(11)", "Toggle\nLayer\n11", "Toggle\nLayer on or off)"),
]

KEYCODES_LAYERS_TT = [
    K("TT(0)", "TT\nLayer\n0", "Normally acts like MO unless it's tapped multiple times, which toggles\nLayer on)"),
    K("TT(1)", "TT\nLayer\n1", "Normally acts like MO unless it's tapped multiple times, which toggles\nLayer on)"),
    K("TT(2)", "TT\nLayer\n2", "Normally acts like MO unless it's tapped multiple times, which toggles\nLayer on)"),
    K("TT(3)", "TT\nLayer\n3", "Normally acts like MO unless it's tapped multiple times, which toggles\nLayer on)"),
    K("TT(4)", "TT\nLayer\n4", "Normally acts like MO unless it's tapped multiple times, which toggles\nLayer on)"),
    K("TT(5)", "TT\nLayer\n5", "Normally acts like MO unless it's tapped multiple times, which toggles\nLayer on)"),
    K("TT(6)", "TT\nLayer\n6", "Normally acts like MO unless it's tapped multiple times, which toggles\nLayer on)"),
    K("TT(7)", "TT\nLayer\n7", "Normally acts like MO unless it's tapped multiple times, which toggles\nLayer on)"),
    K("TT(8)", "TT\nLayer\n8", "Normally acts like MO unless it's tapped multiple times, which toggles\nLayer on)"),
    K("TT(9)", "TT\nLayer\n9", "Normally acts like MO unless it's tapped multiple times, which toggles\nLayer on)"),
    K("TT(10)", "TT\nLayer\n10", "Normally acts like MO unless it's tapped multiple times, which toggles\nLayer on)"),
    K("TT(11)", "TT\nLayer\n11", "Normally acts like MO unless it's tapped multiple times, which toggles\nLayer on)"),
]

KEYCODES_LAYERS_OSL = [
    K("OSL(0)", "One Shot\nLayer\n0", "Momentarily activates\nLayer until a key is pressed)"),
    K("OSL(1)", "One Shot\nLayer\n1", "Momentarily activates\nLayer until a key is pressed)"),
    K("OSL(2)", "One Shot\nLayer\n2", "Momentarily activates\nLayer until a key is pressed)"),
    K("OSL(3)", "One Shot\nLayer\n3", "Momentarily activates\nLayer until a key is pressed)"),
    K("OSL(4)", "One Shot\nLayer\n4", "Momentarily activates\nLayer until a key is pressed)"),
    K("OSL(5)", "One Shot\nLayer\n5", "Momentarily activates\nLayer until a key is pressed)"),
    K("OSL(6)", "One Shot\nLayer\n6", "Momentarily activates\nLayer until a key is pressed)"),
    K("OSL(7)", "One Shot\nLayer\n7", "Momentarily activates\nLayer until a key is pressed)"),
    K("OSL(8)", "One Shot\nLayer\n8", "Momentarily activates\nLayer until a key is pressed)"),
    K("OSL(9)", "One Shot\nLayer\n9", "Momentarily activates\nLayer until a key is pressed)"),
    K("OSL(10)", "One Shot\nLayer\n10", "Momentarily activates\nLayer until a key is pressed)"),
    K("OSL(11)", "One Shot\nLayer\n11", "Momentarily activates\nLayer until a key is pressed)"),
]

KEYCODES_LAYERS_TO = [
    K("TO(0)", "TO\nLayer\n0", "Turns on\nLayer and turns off all other\nLayers, except the default\nLayer)"),
    K("TO(1)", "TO\nLayer\n1", "Turns on\nLayer and turns off all other\nLayers, except the default\nLayer)"),
    K("TO(2)", "TO\nLayer\n2", "Turns on\nLayer and turns off all other\nLayers, except the default\nLayer)"),
    K("TO(3)", "TO\nLayer\n3", "Turns on\nLayer and turns off all other\nLayers, except the default\nLayer)"),
    K("TO(4)", "TO\nLayer\n4", "Turns on\nLayer and turns off all other\nLayers, except the default\nLayer)"),
    K("TO(5)", "TO\nLayer\n5", "Turns on\nLayer and turns off all other\nLayers, except the default\nLayer)"),
    K("TO(6)", "TO\nLayer\n6", "Turns on\nLayer and turns off all other\nLayers, except the default\nLayer)"),
    K("TO(7)", "TO\nLayer\n7", "Turns on\nLayer and turns off all other\nLayers, except the default\nLayer)"),
    K("TO(8)", "TO\nLayer\n8", "Turns on\nLayer and turns off all other\nLayers, except the default\nLayer)"),
    K("TO(9)", "TO\nLayer\n9", "Turns on\nLayer and turns off all other\nLayers, except the default\nLayer)"),
    K("TO(10)", "TO\nLayer\n10", "Turns on\nLayer and turns off all other\nLayers, except the default\nLayer)"),
    K("TO(11)", "TO\nLayer\n11", "Turns on\nLayer and turns off all other\nLayers, except the default\nLayer)"),
]

KEYCODES_LAYERS_LT = [
    K("LT1(kc)", "LT\nLayer\n0", "kc on tap, switch to specified\nLayer while held)"),
    K("LT1(kc)", "LT\nLayer\n1", "kc on tap, switch to specified\nLayer while held)"),
    K("LT2(kc)", "LT\nLayer\n2", "kc on tap, switch to specified\nLayer while held)"),
    K("LT3(kc)", "LT\nLayer\n3", "kc on tap, switch to specified\nLayer while held)"),
    K("LT4(kc)", "LT\nLayer\n4", "kc on tap, switch to specified\nLayer while held)"),
    K("LT5(kc)", "LT\nLayer\n5", "kc on tap, switch to specified\nLayer while held)"),
    K("LT6(kc)", "LT\nLayer\n6", "kc on tap, switch to specified\nLayer while held)"),
    K("LT7(kc)", "LT\nLayer\n7", "kc on tap, switch to specified\nLayer while held)"),
    K("LT8(kc)", "LT\nLayer\n8", "kc on tap, switch to specified\nLayer while held)"),
    K("LT9(kc)", "LT\nLayer\n9", "kc on tap, switch to specified\nLayer while held)"),
    K("LT10(kc)", "LT\nLayer\n10", "kc on tap, switch to specified\nLayer while held)"),
    K("LT11(kc)", "LT\nLayer\n11", "kc on tap, switch to specified\nLayer while held)"),
]





RESET_KEYCODE = "RESET"

KEYCODES_BOOT = [
    K("RESET", "Reset", "Reboot to bootloader")
]

KEYCODES_MODIFIERS = [
    K("OSM(MOD_LSFT)", "OSM\nLSft", "Enable Left Shift for one keypress"),
    K("OSM(MOD_LCTL)", "OSM\nLCtl", "Enable Left Control for one keypress"),
    K("OSM(MOD_LALT)", "OSM\nLAlt", "Enable Left Alt for one keypress"),
    K("OSM(MOD_LGUI)", "OSM\nLGUI", "Enable Left GUI for one keypress"),
    K("OSM(MOD_RSFT)", "OSM\nRSft", "Enable Right Shift for one keypress"),
    K("OSM(MOD_RCTL)", "OSM\nRCtl", "Enable Right Control for one keypress"),
    K("OSM(MOD_RALT)", "OSM\nRAlt", "Enable Right Alt for one keypress"),
    K("OSM(MOD_RGUI)", "OSM\nRGUI", "Enable Right GUI for one keypress"),
    K("OSM(MOD_LCTL|MOD_LSFT)", "OSM\nCS", "Enable Left Control and Shift for one keypress"),
    K("OSM(MOD_LCTL|MOD_LALT)", "OSM\nCA", "Enable Left Control and Alt for one keypress"),
    K("OSM(MOD_LCTL|MOD_LGUI)", "OSM\nCG", "Enable Left Control and GUI for one keypress"),
    K("OSM(MOD_LSFT|MOD_LALT)", "OSM\nSA", "Enable Left Shift and Alt for one keypress"),
    K("OSM(MOD_LSFT|MOD_LGUI)", "OSM\nSG", "Enable Left Shift and GUI for one keypress"),
    K("OSM(MOD_LALT|MOD_LGUI)", "OSM\nAG", "Enable Left Alt and GUI for one keypress"),
    K("OSM(MOD_RCTL|MOD_RSFT)", "OSM\nRCS", "Enable Right Control and Shift for one keypress"),
    K("OSM(MOD_RCTL|MOD_RALT)", "OSM\nRCA", "Enable Right Control and Alt for one keypress"),
    K("OSM(MOD_RCTL|MOD_RGUI)", "OSM\nRCG", "Enable Right Control and GUI for one keypress"),
    K("OSM(MOD_RSFT|MOD_RALT)", "OSM\nRSA", "Enable Right Shift and Alt for one keypress"),
    K("OSM(MOD_RSFT|MOD_RGUI)", "OSM\nRSG", "Enable Right Shift and GUI for one keypress"),
    K("OSM(MOD_RALT|MOD_RGUI)", "OSM\nRAG", "Enable Right Alt and GUI for one keypress"),
    K("OSM(MOD_LCTL|MOD_LSFT|MOD_LGUI)", "OSM\nCSG", "Enable Left Control, Shift, and GUI for one keypress"),
    K("OSM(MOD_LCTL|MOD_LALT|MOD_LGUI)", "OSM\nCAG", "Enable Left Control, Alt, and GUI for one keypress"),
    K("OSM(MOD_LSFT|MOD_LALT|MOD_LGUI)", "OSM\nSAG", "Enable Left Shift, Alt, and GUI for one keypress"),
    K("OSM(MOD_RCTL|MOD_RSFT|MOD_RGUI)", "OSM\nRCSG", "Enable Right Control, Shift, and GUI for one keypress"),
    K("OSM(MOD_RCTL|MOD_RALT|MOD_RGUI)", "OSM\nRCAG", "Enable Right Control, Alt, and GUI for one keypress"),
    K("OSM(MOD_RSFT|MOD_RALT|MOD_RGUI)", "OSM\nRSAG", "Enable Right Shift, Alt, and GUI for one keypress"),
    K("OSM(MOD_MEH)", "OSM\nMeh", "Enable Left Control, Shift, and Alt for one keypress"),
    K("OSM(MOD_HYPR)", "OSM\nHyper", "Enable Left Control, Shift, Alt, and GUI for one keypress"),
    K("OSM(MOD_RCTL|MOD_RSFT|MOD_RALT)", "OSM\nRMeh", "Enable Right Control, Shift, and Alt for one keypress"),
    K("OSM(MOD_RCTL|MOD_RSFT|MOD_RALT|MOD_RGUI)", "OSM\nRHyp", "Enable Right Control, Shift, Alt, and GUI for one keypress"),

    K("KC_GESC", "~\nEsc", "Esc normally, but ~ when Shift or GUI is pressed"),
    K("KC_LSPO", "LS\n(", "Left Shift when held, ( when tapped"),
    K("KC_RSPC", "RS\n)", "Right Shift when held, ) when tapped"),
    K("KC_LCPO", "LC\n(", "Left Control when held, ( when tapped"),
    K("KC_RCPC", "RC\n)", "Right Control when held, ) when tapped"),
    K("KC_LAPO", "LA\n(", "Left Alt when held, ( when tapped"),
    K("KC_RAPC", "RA\n)", "Right Alt when held, ) when tapped"),
    K("KC_SFTENT", "RS\nEnter", "Right Shift when held, Enter when tapped"),
]

KEYCODES_KC = [
    K("LSFT(kc)", "LSft\n(kc)", masked=True),
    K("LCTL(kc)", "LCtl\n(kc)", masked=True),
    K("LALT(kc)", "LAlt\n(kc)", masked=True),
    K("LGUI(kc)", "LGui\n(kc)", masked=True),
    K("RSFT(kc)", "RSft\n(kc)", masked=True),
    K("RCTL(kc)", "RCtl\n(kc)", masked=True),
    K("RALT(kc)", "RAlt\n(kc)", masked=True),
    K("RGUI(kc)", "RGui\n(kc)", masked=True),
    K("C_S(kc)", "LCS\n(kc)", "LCTL + LSFT", masked=True, alias=["LCS(kc)"]),
    K("LCA(kc)", "LCA\n(kc)", "LCTL + LALT", masked=True),
    K("LCG(kc)", "LCG\n(kc)", "LCTL + LGUI", masked=True),
    K("LSA(kc)", "LSA\n(kc)", "LSFT + LALT", masked=True),
    K("SGUI(kc)", "LSG\n(kc)", "LGUI + LSFT", masked=True, alias=["LSG(kc)"]),
    K("LCAG(kc)", "LCAG\n(kc)", "LCTL + LALT + LGUI", masked=True),
    K("RCG(kc)", "RCG\n(kc)", "RCTL + RGUI", masked=True),
    K("MEH(kc)", "Meh\n(kc)", "LCTL + LSFT + LALT", masked=True),
    K("HYPR(kc)", "Hyper\n(kc)", "LCTL + LSFT + LALT + LGUI", masked=True),

    K("LSFT_T(kc)", "LSft_T\n(kc)", "Left Shift when held, kc when tapped", masked=True),
    K("LCTL_T(kc)", "LCtl_T\n(kc)", "Left Control when held, kc when tapped", masked=True),
    K("LALT_T(kc)", "LAlt_T\n(kc)", "Left Alt when held, kc when tapped", masked=True),
    K("LGUI_T(kc)", "LGui_T\n(kc)", "Left GUI when held, kc when tapped", masked=True),
    K("RSFT_T(kc)", "RSft_T\n(kc)", "Right Shift when held, kc when tapped", masked=True),
    K("RCTL_T(kc)", "RCtl_T\n(kc)", "Right Control when held, kc when tapped", masked=True),
    K("RALT_T(kc)", "RAlt_T\n(kc)", "Right Alt when held, kc when tapped", masked=True),
    K("RGUI_T(kc)", "RGui_T\n(kc)", "Right GUI when held, kc when tapped", masked=True),
    K("C_S_T(kc)", "LCS_T\n(kc)", "Left Control + Left Shift when held, kc when tapped", masked=True, alias=["LCS_T(kc)"] ),
    K("LCA_T(kc)", "LCA_T\n(kc)", "LCTL + LALT when held, kc when tapped", masked=True),
    K("LCG_T(kc)", "LCG_T\n(kc)", "LCTL + LGUI when held, kc when tapped", masked=True),
    K("LSA_T(kc)", "LSA_T\n(kc)", "LSFT + LALT when held, kc when tapped", masked=True),
    K("SGUI_T(kc)", "LSG_T\n(kc)", "LGUI + LSFT when held, kc when tapped", masked=True, alias=["LSG_T(kc)"]),
    K("LCAG_T(kc)", "LCAG_T\n(kc)", "LCTL + LALT + LGUI when held, kc when tapped", masked=True),
    K("RCG_T(kc)", "RCG_T\n(kc)", "RCTL + RGUI when held, kc when tapped", masked=True),
    K("RCAG_T(kc)", "RCAG_T\n(kc)", "RCTL + RALT + RGUI when held, kc when tapped", masked=True),
    K("MEH_T(kc)", "Meh_T\n(kc)", "LCTL + LSFT + LALT when held, kc when tapped", masked=True),
    K("ALL_T(kc)", "ALL_T\n(kc)", "LCTL + LSFT + LALT + LGUI when held, kc when tapped", masked=True),
]

KEYCODES_QUANTUM = [
    K("MAGIC_SWAP_CONTROL_CAPSLOCK", "Swap\nCtrl\nCaps", "Swap Caps Lock and Left Control", alias=["CL_SWAP"]),
    K("MAGIC_UNSWAP_CONTROL_CAPSLOCK", "Unswap\nCtrl\nCaps", "Unswap Caps Lock and Left Control", alias=["CL_NORM"]),
    K("MAGIC_CAPSLOCK_TO_CONTROL", "Caps\nto\nCtrl", "Treat Caps Lock as Control", alias=["CL_CTRL"]),
    K("MAGIC_UNCAPSLOCK_TO_CONTROL", "Caps\nnot to\nCtrl", "Stop treating Caps Lock as Control", alias=["CL_CAPS"]),
    K("MAGIC_SWAP_LCTL_LGUI", "Swap\nLCtl\nLGui", "Swap Left Control and GUI", alias=["LCG_SWP"]),
    K("MAGIC_UNSWAP_LCTL_LGUI", "Unswap\nLCtl\nLGui", "Unswap Left Control and GUI", alias=["LCG_NRM"]),
    K("MAGIC_SWAP_RCTL_RGUI", "Swap\nRCtl\nRGui", "Swap Right Control and GUI", alias=["RCG_SWP"]),
    K("MAGIC_UNSWAP_RCTL_RGUI", "Unswap\nRCtl\nRGui", "Unswap Right Control and GUI", alias=["RCG_NRM"]),
    K("MAGIC_SWAP_CTL_GUI", "Swap\nCtl\nGui", "Swap Control and GUI on both sides", alias=["CG_SWAP"]),
    K("MAGIC_UNSWAP_CTL_GUI", "Unswap\nCtl\nGui", "Unswap Control and GUI on both sides", alias=["CG_NORM"]),
    K("MAGIC_TOGGLE_CTL_GUI", "Toggle\nCtl\nGui", "Toggle Control and GUI swap on both sides", alias=["CG_TOGG"]),
    K("MAGIC_SWAP_LALT_LGUI", "Swap\nLAlt\nLGui", "Swap Left Alt and GUI", alias=["LAG_SWP"]),
    K("MAGIC_UNSWAP_LALT_LGUI", "Unswap\nLAlt\nLGui", "Unswap Left Alt and GUI", alias=["LAG_NRM"]),
    K("MAGIC_SWAP_RALT_RGUI", "Swap\nRAlt\nRGui", "Swap Right Alt and GUI", alias=["RAG_SWP"]),
    K("MAGIC_UNSWAP_RALT_RGUI", "Unswap\nRAlt\nRGui", "Unswap Right Alt and GUI", alias=["RAG_NRM"]),
    K("MAGIC_SWAP_ALT_GUI", "Swap\nAlt\nGui", "Swap Alt and GUI on both sides", alias=["AG_SWAP"]),
    K("MAGIC_UNSWAP_ALT_GUI", "Unswap\nAlt\nGui", "Unswap Alt and GUI on both sides", alias=["AG_NORM"]),
    K("MAGIC_TOGGLE_ALT_GUI", "Toggle\nAlt\nGui", "Toggle Alt and GUI swap on both sides", alias=["AG_TOGG"]),
    K("MAGIC_NO_GUI", "GUI\nOff", "Disable the GUI keys", alias=["GUI_OFF"]),
    K("MAGIC_UNNO_GUI", "GUI\nOn", "Enable the GUI keys", alias=["GUI_ON"]),
    K("MAGIC_SWAP_GRAVE_ESC", "Swap\n`\nEsc", "Swap ` and Escape", alias=["GE_SWAP"]),
    K("MAGIC_UNSWAP_GRAVE_ESC", "Unswap\n`\nEsc", "Unswap ` and Escape", alias=["GE_NORM"]),
    K("MAGIC_SWAP_BACKSLASH_BACKSPACE", "Swap\n\\\nBS", "Swap \\ and Backspace", alias=["BS_SWAP"]),
    K("MAGIC_UNSWAP_BACKSLASH_BACKSPACE", "Unswap\n\\\nBS", "Unswap \\ and Backspace", alias=["BS_NORM"]),
    K("MAGIC_HOST_NKRO", "NKRO\nOn", "Enable N-key rollover", alias=["NK_ON"]),
    K("MAGIC_UNHOST_NKRO", "NKRO\nOff", "Disable N-key rollover", alias=["NK_OFF"]),
    K("MAGIC_TOGGLE_NKRO", "NKRO\nToggle", "Toggle N-key rollover", alias=["NK_TOGG"]),
    K("MAGIC_EE_HANDS_LEFT", "EEH\nLeft", "Set the master half of a split keyboard as the left hand (for EE_HANDS)",
      alias=["EH_LEFT"]),
    K("MAGIC_EE_HANDS_RIGHT", "EEH\nRight", "Set the master half of a split keyboard as the right hand (for EE_HANDS)",
      alias=["EH_RGHT"]),

    K("AU_ON", "Audio\nON", "Audio mode on"),
    K("AU_OFF", "Audio\nOFF", "Audio mode off"),
    K("AU_TOG", "Audio\nToggle", "Toggles Audio mode"),
    K("CLICKY_TOGGLE", "Clicky\nToggle", "Toggles Audio clicky mode", alias=["CK_TOGG"]),
    K("CLICKY_UP", "Clicky\nUp", "Increases frequency of the clicks", alias=["CK_UP"]),
    K("CLICKY_DOWN", "Clicky\nDown", "Decreases frequency of the clicks", alias=["CK_DOWN"]),
    K("CLICKY_RESET", "Clicky\nReset", "Resets frequency to default", alias=["CK_RST"]),
    K("MU_ON", "Music\nOn", "Turns on Music Mode"),
    K("MU_OFF", "Music\nOff", "Turns off Music Mode"),
    K("MU_TOG", "Music\nToggle", "Toggles Music Mode"),
    K("MU_MOD", "Music\nCycle", "Cycles through the music modes"),

    K("HPT_ON", "Haptic\nOn", "Turn haptic feedback on"),
    K("HPT_OFF", "Haptic\nOff", "Turn haptic feedback off"),
    K("HPT_TOG", "Haptic\nToggle", "Toggle haptic feedback on/off"),
    K("HPT_RST", "Haptic\nReset", "Reset haptic feedback config to default"),
    K("HPT_FBK", "Haptic\nFeed\nback", "Toggle feedback to occur on keypress, release or both"),
    K("HPT_BUZ", "Haptic\nBuzz", "Toggle solenoid buzz on/off"),
    K("HPT_MODI", "Haptic\nNext", "Go to next DRV2605L waveform"),
    K("HPT_MODD", "Haptic\nPrev", "Go to previous DRV2605L waveform"),
    K("HPT_CONT", "Haptic\nCont.", "Toggle continuous haptic mode on/off"),
    K("HPT_CONI", "Haptic\n+", "Increase DRV2605L continous haptic strength"),
    K("HPT_COND", "Haptic\n-", "Decrease DRV2605L continous haptic strength"),
    K("HPT_DWLI", "Haptic\nDwell+", "Increase Solenoid dwell time"),
    K("HPT_DWLD", "Haptic\nDwell-", "Decrease Solenoid dwell time"),

    K("KC_ASDN", "Auto-\nshift\nDown", "Lower the Auto Shift timeout variable (down)"),
    K("KC_ASUP", "Auto-\nshift\nUp", "Raise the Auto Shift timeout variable (up)"),
    K("KC_ASRP", "Auto-\nshift\nReport", "Report your current Auto Shift timeout value"),
    K("KC_ASON", "Auto-\nshift\nOn", "Turns on the Auto Shift Function"),
    K("KC_ASOFF", "Auto-\nshift\nOff", "Turns off the Auto Shift Function"),
    K("KC_ASTG", "Auto-\nshift\nToggle", "Toggles the state of the Auto Shift feature"),

    K("CMB_ON", "Combo\nOn", "Turns on Combo feature"),
    K("CMB_OFF", "Combo\nOff", "Turns off Combo feature"),
    K("CMB_TOG", "Combo\nToggle", "Toggles Combo feature on and off"),
]

KEYCODES_BACKLIGHT = [
    K("RGB_TOG", "RGB\nToggle", "Toggle RGB lighting on or off"),
    K("RGB_MOD", "RGB\nMode +", "Next RGB mode"),
    K("RGB_RMOD", "RGB\nMode -", "Previous RGB mode"),
    K("RGB_HUI", "Hue +", "Increase hue"),
    K("RGB_HUD", "Hue -", "Decrease hue"),
    K("RGB_SAI", "Sat +", "Increase saturation"),
    K("RGB_SAD", "Sat -", "Decrease saturation"),
    K("RGB_VAI", "Bright +", "Increase value"),
    K("RGB_VAD", "Bright -", "Decrease value"),
    K("RGB_SPI", "Speed +", "Increase RGB effect speed"),
    K("RGB_SPD", "Speed -", "Decrease RGB effect speed"),
]

KEYCODES_MEDIA = [
    K("KC_F13", "F13"),
    K("KC_F14", "F14"),
    K("KC_F15", "F15"),
    K("KC_F16", "F16"),
    K("KC_F17", "F17"),
    K("KC_F18", "F18"),
    K("KC_F19", "F19"),
    K("KC_F20", "F20"),
    K("KC_F21", "F21"),
    K("KC_F22", "F22"),
    K("KC_F23", "F23"),
    K("KC_F24", "F24"),

    K("KC_PWR", "Power", "System Power Down", alias=["KC_SYSTEM_POWER"]),
    K("KC_SLEP", "Sleep", "System Sleep", alias=["KC_SYSTEM_SLEEP"]),
    K("KC_WAKE", "Wake", "System Wake", alias=["KC_SYSTEM_WAKE"]),
    K("KC_EXEC", "Exec", "Execute", alias=["KC_EXECUTE"]),
    K("KC_HELP", "Help"),
    K("KC_SLCT", "Select", alias=["KC_SELECT"]),
    K("KC_STOP", "Stop"),
    K("KC_AGIN", "Again", alias=["KC_AGAIN"]),
    K("KC_UNDO", "Undo"),
    K("KC_CUT", "Cut"),
    K("KC_COPY", "Copy"),
    K("KC_PSTE", "Paste", alias=["KC_PASTE"]),
    K("KC_FIND", "Find"),

    K("KC_CALC", "Calc", "Launch Calculator (Windows)", alias=["KC_CALCULATOR"]),
    K("KC_MAIL", "Mail", "Launch Mail (Windows)"),
    K("KC_MSEL", "Media\nPlayer", "Launch Media Player (Windows)", alias=["KC_MEDIA_SELECT"]),
    K("KC_MYCM", "My\nPC", "Launch My Computer (Windows)", alias=["KC_MY_COMPUTER"]),
    K("KC_WSCH", "Browser\nSearch", "Browser Search (Windows)", alias=["KC_WWW_SEARCH"]),
    K("KC_WHOM", "Browser\nHome", "Browser Home (Windows)", alias=["KC_WWW_HOME"]),
    K("KC_WBAK", "Browser\nBack", "Browser Back (Windows)", alias=["KC_WWW_BACK"]),
    K("KC_WFWD", "Browser\nForward", "Browser Forward (Windows)", alias=["KC_WWW_FORWARD"]),
    K("KC_WSTP", "Browser\nStop", "Browser Stop (Windows)", alias=["KC_WWW_STOP"]),
    K("KC_WREF", "Browser\nRefresh", "Browser Refresh (Windows)", alias=["KC_WWW_REFRESH"]),
    K("KC_WFAV", "Browser\nFav.", "Browser Favorites (Windows)", alias=["KC_WWW_FAVORITES"]),
    K("KC_BRIU", "Bright.\nUp", "Increase the brightness of screen (Laptop)", alias=["KC_BRIGHTNESS_UP"]),
    K("KC_BRID", "Bright.\nDown", "Decrease the brightness of screen (Laptop)", alias=["KC_BRIGHTNESS_DOWN"]),

    K("KC_MPRV", "Media\nPrev", "Previous Track", alias=["KC_MEDIA_PREV_TRACK"]),
    K("KC_MNXT", "Media\nNext", "Next Track", alias=["KC_MEDIA_NEXT_TRACK"]),
    K("KC_MUTE", "Mute", "Mute Audio", alias=["KC_AUDIO_MUTE"]),
    K("KC_VOLD", "Vol -", "Volume Down", alias=["KC_AUDIO_VOL_DOWN"]),
    K("KC_VOLU", "Vol +", "Volume Up", alias=["KC_AUDIO_VOL_UP"]),
    K("KC__VOLDOWN", "Vol -\nAlt", "Volume Down Alternate"),
    K("KC__VOLUP", "Vol +\nAlt", "Volume Up Alternate"),
    K("KC_MSTP", "Media\nStop", alias=["KC_MEDIA_STOP"]),
    K("KC_MPLY", "Media\nPlay", "Play/Pause", alias=["KC_MEDIA_PLAY_PAUSE"]),
    K("KC_MRWD", "Prev\nTrack\n(macOS)", "Previous Track / Rewind (macOS)", alias=["KC_MEDIA_REWIND"]),
    K("KC_MFFD", "Next\nTrack\n(macOS)", "Next Track / Fast Forward (macOS)", alias=["KC_MEDIA_FAST_FORWARD"]),
    K("KC_EJCT", "Eject", "Eject (macOS)", alias=["KC_MEDIA_EJECT"]),

    K("KC_MS_U", "Mouse\nUp", "Mouse Cursor Up", alias=["KC_MS_UP"]),
    K("KC_MS_D", "Mouse\nDown", "Mouse Cursor Down", alias=["KC_MS_DOWN"]),
    K("KC_MS_L", "Mouse\nLeft", "Mouse Cursor Left", alias=["KC_MS_LEFT"]),
    K("KC_MS_R", "Mouse\nRight", "Mouse Cursor Right", alias=["KC_MS_RIGHT"]),
    K("KC_BTN1", "Mouse\n1", "Mouse Button 1", alias=["KC_MS_BTN1"]),
    K("KC_BTN2", "Mouse\n2", "Mouse Button 2", alias=["KC_MS_BTN2"]),
    K("KC_BTN3", "Mouse\n3", "Mouse Button 3", alias=["KC_MS_BTN3"]),
    K("KC_BTN4", "Mouse\n4", "Mouse Button 4", alias=["KC_MS_BTN4"]),
    K("KC_BTN5", "Mouse\n5", "Mouse Button 5", alias=["KC_MS_BTN5"]),
    K("KC_WH_U", "Mouse\nWheel\nUp", alias=["KC_MS_WH_UP"]),
    K("KC_WH_D", "Mouse\nWheel\nDown", alias=["KC_MS_WH_DOWN"]),
    K("KC_WH_L", "Mouse\nWheel\nLeft", alias=["KC_MS_WH_LEFT"]),
    K("KC_WH_R", "Mouse\nWheel\nRight", alias=["KC_MS_WH_RIGHT"]),
    K("KC_ACL0", "Mouse\nAccel\n0", "Set mouse acceleration to 0", alias=["KC_MS_ACCEL0"]),
    K("KC_ACL1", "Mouse\nAccel\n1", "Set mouse acceleration to 1", alias=["KC_MS_ACCEL1"]),
    K("KC_ACL2", "Mouse\nAccel\n2", "Set mouse acceleration to 2", alias=["KC_MS_ACCEL2"]),

    K("KC_LCAP", "Locking\nCaps", "Locking Caps Lock", alias=["KC_LOCKING_CAPS"]),
    K("KC_LNUM", "Locking\nNum", "Locking Num Lock", alias=["KC_LOCKING_NUM"]),
    K("KC_LSCR", "Locking\nScroll", "Locking Scroll Lock", alias=["KC_LOCKING_SCROLL"]),
]

KEYCODES_SAVE = [
    K("SAVE_SETTINGS", "Save as\nDefault\nSettings", "save settings"),
    K("DEFAULT_SETTINGS", "Reset to\nFactory\nSettings", "reset to factory"),
]

KEYCODES_SETTINGS1 = [
    K("DEFAULT_SETTINGS", "Reset to\nFactory\nSettings", "reset to factory"),    
    K("SAVE_SETTINGS", "Save as\nDefault\nSettings", "save settings"),     
    K("LOAD_SETTINGS", "Load\nDefault\nSettings", "load settings"),
]    

KEYCODES_SETTINGS2 = [
    K("SAVE_SETTINGS_2", "Save\nto\nPreset 1", "save preset 1"),
    K("SAVE_SETTINGS_3", "Save\nto\nPreset 2", "save preset 2"),
    K("SAVE_SETTINGS_4", "Save\nto\nPreset 3", "save preset 3"),
    K("SAVE_SETTINGS_5", "Save\nto\nPreset 4", "save preset 4"),
]

KEYCODES_SETTINGS3 = [
    K("LOAD_SETTINGS_2", "Load\nPreset 1", "load preset 1"),
    K("LOAD_SETTINGS_3", "Load\nPreset 2", "load preset 2"),
    K("LOAD_SETTINGS_4", "Load\nPreset 3", "load preset 3"),
    K("LOAD_SETTINGS_5", "Load\nPreset 4", "load preset 4"),
]

KEYCODES_TAP_DANCE = [
    K("TD(0)", "TapDance\n0", "TapDance0"),
    K("TD(1)", "TapDance\n1", "TapDance1"),
    K("TD(2)", "TapDance\n2", "TapDance2"),
    K("TD(3)", "TapDance\n3", "TapDance3"),
    K("TD(4)", "TapDance\n4", "TapDance4"),
    K("TD(5)", "TapDance\n5", "TapDance5"),
    K("TD(6)", "TapDance\n6", "TapDance6"),
    K("TD(7)", "TapDance\n7", "TapDance7"),
    K("TD(8)", "TapDance\n8", "TapDance8"),
    K("TD(9)", "TapDance\n9", "TapDance9"),
    K("TD(10)", "TapDance\n10", "TapDance10"),
    K("TD(11)", "TapDance\n11", "TapDance11"),
    K("TD(12)", "TapDance\n12", "TapDance12"),
    K("TD(13)", "TapDance\n13", "TapDance13"),
    K("TD(14)", "TapDance\n14", "TapDance14"),
    K("TD(15)", "TapDance\n15", "TapDance15"),
    K("TD(16)", "TapDance\n16", "TapDance16"),
    K("TD(17)", "TapDance\n17", "TapDance17"),
    K("TD(18)", "TapDance\n18", "TapDance18"),
    K("TD(19)", "TapDance\n19", "TapDance19"),
    K("TD(20)", "TapDance\n20", "TapDance20"),
    K("TD(21)", "TapDance\n21", "TapDance21"),
    K("TD(22)", "TapDance\n22", "TapDance22"),
    K("TD(23)", "TapDance\n23", "TapDance23"),
    K("TD(24)", "TapDance\n24", "TapDance24"),
    K("TD(25)", "TapDance\n25", "TapDance25"),
    K("TD(26)", "TapDance\n26", "TapDance26"),
    K("TD(27)", "TapDance\n27", "TapDance27"),
    K("TD(28)", "TapDance\n28", "TapDance28"),
    K("TD(29)", "TapDance\n29", "TapDance29"),
    K("TD(30)", "TapDance\n30", "TapDance30"),
    K("TD(31)", "TapDance\n31", "TapDance31"),
]

KEYCODES_USER = [
    K("USER00", "USER00", "USER00"),
    K("USER01", "USER01", "USER01"),
    K("USER02", "USER02", "USER02"),
    K("USER03", "USER03", "USER03"),
    K("USER04", "USER04", "USER04"),
    K("USER05", "USER05", "USER05"),
    K("USER06", "USER06", "USER06"),
    K("USER07", "USER07", "USER07"),
    K("USER08", "USER08", "USER08"),
    K("USER09", "USER09", "USER09"),
    K("USER10", "USER10", "USER10"),
    K("USER11", "USER11", "USER11"),
    K("USER12", "USER12", "USER12"),
    K("USER13", "USER13", "USER13"),
    K("USER14", "USER14", "USER14"),
    K("USER15", "USER15", "USER15"),
]

KEYCODES_MACRO = [
    K("M0", "Macro 0", "Macro 1"),
    K("M1", "Macro 1", "Macro 1"),
    K("M2", "Macro 2", "Macro 2"),
    K("M3", "Macro 3", "Macro 3"),
    K("M4", "Macro 4", "Macro 4"),
    K("M5", "Macro 5", "Macro 5"),
    K("M6", "Macro 6", "Macro 6"),
    K("M7", "Macro 7", "Macro 7"),
    K("M8", "Macro 8", "Macro 8"),
    K("M9", "Macro 9", "Macro 9"),
    K("M10", "Macro 10", "Macro 10"),
    K("M11", "Macro 11", "Macro 11"),
    K("M12", "Macro 12", "Macro 12"),
    K("M13", "Macro 13", "Macro 13"),
    K("M14", "Macro 14", "Macro 14"),
    K("M15", "Macro 15", "Macro 15"),
    K("M16", "Macro 16", "Macro 16"),
    K("M17", "Macro 17", "Macro 17"),
    K("M18", "Macro 18", "Macro 18"),
    K("M19", "Macro 19", "Macro 19"),
    K("M20", "Macro 20", "Macro 20"),
    K("M21", "Macro 21", "Macro 21"),
    K("M22", "Macro 22", "Macro 22"),
    K("M23", "Macro 23", "Macro 23"),
    K("M24", "Macro 24", "Macro 24"),
    K("M25", "Macro 25", "Macro 25"),
    K("M26", "Macro 26", "Macro 26"),
    K("M27", "Macro 27", "Macro 27"),
    K("M28", "Macro 28", "Macro 28"),
    K("M29", "Macro 29", "Macro 29"),
    K("M30", "Macro 30", "Macro 30"),
    K("M31", "Macro 31", "Macro 31"),
    K("M32", "Macro 32", "Macro 32"),
    K("M33", "Macro 33", "Macro 33"),
    K("M34", "Macro 34", "Macro 34"),
    K("M35", "Macro 35", "Macro 35"),
    K("M36", "Macro 36", "Macro 36"),
    K("M37", "Macro 37", "Macro 37"),
    K("M38", "Macro 38", "Macro 38"),
    K("M39", "Macro 39", "Macro 39"),
    K("M40", "Macro 40", "Macro 40"),
    K("M41", "Macro 41", "Macro 41"),
    K("M42", "Macro 42", "Macro 42"),
    K("M43", "Macro 43", "Macro 43"),
    K("M44", "Macro 44", "Macro 44"),
    K("M45", "Macro 45", "Macro 45"),
    K("M46", "Macro 46", "Macro 46"),
    K("M47", "Macro 47", "Macro 47"),
    K("M48", "Macro 48", "Macro 48"),
    K("M49", "Macro 49", "Macro 49"),
    K("M50", "Macro 50", "Macro 50"),
    K("M51", "Macro 51", "Macro 51"),
    K("M52", "Macro 52", "Macro 52"),
    K("M53", "Macro 53", "Macro 53"),
    K("M54", "Macro 54", "Macro 54"),
    K("M55", "Macro 55", "Macro 55"),
    K("M56", "Macro 56", "Macro 56"),
    K("M57", "Macro 57", "Macro 57"),
    K("M58", "Macro 58", "Macro 58"),
    K("M59", "Macro 59", "Macro 59"),
    K("M60", "Macro 60", "Macro 60"),
    K("M61", "Macro 61", "Macro 61"),
    K("M62", "Macro 62", "Macro 62"),
    K("M63", "Macro 63", "Macro 63"),
    K("M64", "Macro 64", "Macro 64"),
    K("M65", "Macro 65", "Macro 65"),
    K("M66", "Macro 66", "Macro 66"),
    K("M67", "Macro 67", "Macro 67"),
    K("M68", "Macro 68", "Macro 68"),
    K("M69", "Macro 69", "Macro 69"),
    K("M70", "Macro 70", "Macro 70"),
    K("M71", "Macro 71", "Macro 71"),
    K("M72", "Macro 72", "Macro 72"),
    K("M73", "Macro 73", "Macro 73"),
    K("M74", "Macro 74", "Macro 74"),
    K("M75", "Macro 75", "Macro 75"),
    K("M76", "Macro 76", "Macro 76"),
    K("M77", "Macro 77", "Macro 77"),
    K("M78", "Macro 78", "Macro 78"),
    K("M79", "Macro 79", "Macro 79"),
    K("M80", "Macro 80", "Macro 80"),
    K("M81", "Macro 81", "Macro 81"),
    K("M82", "Macro 82", "Macro 82"),
    K("M83", "Macro 83", "Macro 83"),
    K("M84", "Macro 84", "Macro 84"),
    K("M85", "Macro 85", "Macro 85"),
    K("M86", "Macro 86", "Macro 86"),
    K("M87", "Macro 87", "Macro 87"),
    K("M88", "Macro 88", "Macro 88"),
    K("M89", "Macro 89", "Macro 89"),
    K("M90", "Macro 90", "Macro 90"),
    K("M91", "Macro 91", "Macro 91"),
    K("M92", "Macro 92", "Macro 92"),
    K("M93", "Macro 93", "Macro 93"),
    K("M94", "Macro 94", "Macro 94"),
    K("M95", "Macro 95", "Macro 95"),
    K("M96", "Macro 96", "Macro 96"),
    K("M97", "Macro 97", "Macro 97"),
    K("M98", "Macro 98", "Macro 98"),
    K("M99", "Macro 99", "Macro 99"),
    K("M100", "Macro 100", "Macro 100"),
    K("M101", "Macro 101", "Macro 101"),
    K("M102", "Macro 102", "Macro 102"),
    K("M103", "Macro 103", "Macro 103"),
    K("M104", "Macro 104", "Macro 104"),
    K("M105", "Macro 105", "Macro 105"),
    K("M106", "Macro 106", "Macro 106"),
    K("M107", "Macro 107", "Macro 107"),
    K("M108", "Macro 108", "Macro 108"),
    K("M109", "Macro 109", "Macro 109"),
    K("M110", "Macro 110", "Macro 110"),
    K("M111", "Macro 111", "Macro 111"),
    K("M112", "Macro 112", "Macro 112"),
    K("M113", "Macro 113", "Macro 113"),
    K("M114", "Macro 114", "Macro 114"),
    K("M115", "Macro 115", "Macro 115"),
    K("M116", "Macro 116", "Macro 116"),
    K("M117", "Macro 117", "Macro 117"),
    K("M118", "Macro 118", "Macro 118"),
    K("M119", "Macro 119", "Macro 119"),
    K("M120", "Macro 120", "Macro 120"),
    K("M121", "Macro 121", "Macro 121"),
    K("M122", "Macro 122", "Macro 122"),
    K("M123", "Macro 123", "Macro 123"),
    K("M124", "Macro 124", "Macro 124"),
    K("M125", "Macro 125", "Macro 125"),
    K("M126", "Macro 126", "Macro 126"),
    K("M127", "Macro 127", "Macro 127"),
    K("M128", "Macro 128", "Macro 128"),
    K("M129", "Macro 129", "Macro 129"),
    K("M130", "Macro 130", "Macro 130"),
    K("M131", "Macro 131", "Macro 131"),
    K("M132", "Macro 132", "Macro 132"),
    K("M133", "Macro 133", "Macro 133"),
    K("M134", "Macro 134", "Macro 134"),
    K("M135", "Macro 135", "Macro 135"),
    K("M136", "Macro 136", "Macro 136"),
    K("M137", "Macro 137", "Macro 137"),
    K("M138", "Macro 138", "Macro 138"),
    K("M139", "Macro 139", "Macro 139"),
    K("M140", "Macro 140", "Macro 140"),
    K("M141", "Macro 141", "Macro 141"),
    K("M142", "Macro 142", "Macro 142"),
    K("M143", "Macro 143", "Macro 143"),
    K("M144", "Macro 144", "Macro 144"),
    K("M145", "Macro 145", "Macro 145"),
    K("M146", "Macro 146", "Macro 146"),
    K("M147", "Macro 147", "Macro 147"),
    K("M148", "Macro 148", "Macro 148"),
    K("M149", "Macro 149", "Macro 149"),
    K("M150", "Macro 150", "Macro 150"),
    K("M151", "Macro 151", "Macro 151"),
    K("M152", "Macro 152", "Macro 152"),
    K("M153", "Macro 153", "Macro 153"),
    K("M154", "Macro 154", "Macro 154"),
    K("M155", "Macro 155", "Macro 155"),
    K("M156", "Macro 156", "Macro 156"),
    K("M157", "Macro 157", "Macro 157"),
    K("M158", "Macro 158", "Macro 158"),
    K("M159", "Macro 159", "Macro 159"),
    K("M160", "Macro 160", "Macro 160"),
    K("M161", "Macro 161", "Macro 161"),
    K("M162", "Macro 162", "Macro 162"),
    K("M163", "Macro 163", "Macro 163"),
    K("M164", "Macro 164", "Macro 164"),
    K("M165", "Macro 165", "Macro 165"),
    K("M166", "Macro 166", "Macro 166"),
    K("M167", "Macro 167", "Macro 167"),
    K("M168", "Macro 168", "Macro 168"),
    K("M169", "Macro 169", "Macro 169"),
    K("M170", "Macro 170", "Macro 170"),
    K("M171", "Macro 171", "Macro 171"),
    K("M172", "Macro 172", "Macro 172"),
    K("M173", "Macro 173", "Macro 173"),
    K("M174", "Macro 174", "Macro 174"),
    K("M175", "Macro 175", "Macro 175"),
    K("M176", "Macro 176", "Macro 176"),
    K("M177", "Macro 177", "Macro 177"),
    K("M178", "Macro 178", "Macro 178"),
    K("M179", "Macro 179", "Macro 179"),
    K("M180", "Macro 180", "Macro 180"),
    K("M181", "Macro 181", "Macro 181"),
    K("M182", "Macro 182", "Macro 182"),
    K("M183", "Macro 183", "Macro 183"),
    K("M184", "Macro 184", "Macro 184"),
    K("M185", "Macro 185", "Macro 185"),
    K("M186", "Macro 186", "Macro 186"),
    K("M187", "Macro 187", "Macro 187"),
    K("M188", "Macro 188", "Macro 188"),
    K("M189", "Macro 189", "Macro 189"),
    K("M190", "Macro 190", "Macro 190"),
    K("M191", "Macro 191", "Macro 191"),
    K("M192", "Macro 192", "Macro 192"),
    K("M193", "Macro 193", "Macro 193"),
    K("M194", "Macro 194", "Macro 194"),
    K("M195", "Macro 195", "Macro 195"),
    K("M196", "Macro 196", "Macro 196"),
    K("M197", "Macro 197", "Macro 197"),
    K("M198", "Macro 198", "Macro 198"),
    K("M199", "Macro 199", "Macro 199"),
    K("M200", "Macro 200", "Macro 200"),
    K("M201", "Macro 201", "Macro 201"),
    K("M202", "Macro 202", "Macro 202"),
    K("M203", "Macro 203", "Macro 203"),
    K("M204", "Macro 204", "Macro 204"),
    K("M205", "Macro 205", "Macro 205"),
    K("M206", "Macro 206", "Macro 206"),
    K("M207", "Macro 207", "Macro 207"),
    K("M208", "Macro 208", "Macro 208"),
    K("M209", "Macro 209", "Macro 209"),
    K("M210", "Macro 210", "Macro 210"),
    K("M211", "Macro 211", "Macro 211"),
    K("M212", "Macro 212", "Macro 212"),
    K("M213", "Macro 213", "Macro 213"),
    K("M214", "Macro 214", "Macro 214"),
    K("M215", "Macro 215", "Macro 215"),
    K("M216", "Macro 216", "Macro 216"),
    K("M217", "Macro 217", "Macro 217"),
    K("M218", "Macro 218", "Macro 218"),
    K("M219", "Macro 219", "Macro 219"),
    K("M220", "Macro 220", "Macro 220"),
    K("M221", "Macro 221", "Macro 221"),
    K("M222", "Macro 222", "Macro 222"),
    K("M223", "Macro 223", "Macro 223"),
    K("M224", "Macro 224", "Macro 224"),
    K("M225", "Macro 225", "Macro 225"),
    K("M226", "Macro 226", "Macro 226"),
    K("M227", "Macro 227", "Macro 227"),
    K("M228", "Macro 228", "Macro 228"),
    K("M229", "Macro 229", "Macro 229"),
    K("M230", "Macro 230", "Macro 230"),
    K("M231", "Macro 231", "Macro 231"),
    K("M232", "Macro 232", "Macro 232"),
    K("M233", "Macro 233", "Macro 233"),
    K("M234", "Macro 234", "Macro 234"),
    K("M235", "Macro 235", "Macro 235"),
    K("M236", "Macro 236", "Macro 236"),
    K("M237", "Macro 237", "Macro 237"),
    K("M238", "Macro 238", "Macro 238"),
    K("M239", "Macro 239", "Macro 239"),
    K("M240", "Macro 240", "Macro 240"),
    K("M241", "Macro 241", "Macro 241"),
    K("M242", "Macro 242", "Macro 242"),
    K("M243", "Macro 243", "Macro 243"),
    K("M244", "Macro 244", "Macro 244"),
    K("M245", "Macro 245", "Macro 245"),
    K("M246", "Macro 246", "Macro 246"),
    K("M247", "Macro 247", "Macro 247"),
    K("M248", "Macro 248", "Macro 248"),
    K("M249", "Macro 249", "Macro 249"),
    K("M250", "Macro 250", "Macro 250"),
    K("M251", "Macro 251", "Macro 251"),
    K("M252", "Macro 252", "Macro 252"),
    K("M253", "Macro 253", "Macro 253"),
    K("M254", "Macro 254", "Macro 254"),
    K("M255", "Macro 255", "Macro 255")
]


KEYCODES_MACRO_BASE = [
    K("DYN_REC_START1", "DM1\nRec", "Dynamic Macro 1 Rec Start", alias=["DM_REC1"]),
    K("DYN_REC_START2", "DM2\nRec", "Dynamic Macro 2 Rec Start", alias=["DM_REC2"]),    
    K("DYN_MACRO_PLAY1", "DM1\nPlay", "Dynamic Macro 1 Play", alias=["DM_PLY1"]),
    K("DYN_MACRO_PLAY2", "DM2\nPlay", "Dynamic Macro 2 Play", alias=["DM_PLY2"]),
    K("DYN_REC_STOP", "DM Rec\nStop", "Dynamic Macro Rec Stop", alias=["DM_RSTP"]),
]

KEYCODES_EARTRAINER = [
     K("MI_ET_1", "Basic\nIntervals\nLevel 1", "Ear Train\nLevel 1"),
     K("MI_ET_4", "Octave\nIntervals\nLevel 1", "Interval\nLevel 4"),
     K("MI_ET_7", "Extended\nIntervals\nLevel 1", "Interval\nLevel 7"),
     K("MI_ET_10", "All\nIntervals\nLevel 1", "Interval\nLevel 9"),
     K("MI_ET_2", "Basic\nIntervals\nLevel 2", "Ear Train\nLevel 2"),
     K("MI_ET_5", "Octave\nIntervals\nLevel 2", "Interval\nLevel 5"),
     K("MI_ET_8", "Extended\nIntervals\nLevel 2", "Interval\nLevel 8"),
     K("MI_ET_11", "All\nIntervals\nLevel 2", "Interval\nLevel 9"),
     K("MI_ET_13", "Basic\nIntervals\nLevel 3", "Interval\nLevel 9"),     
     K("MI_ET_14", "Octave\nIntervals\nLevel 3", "Interval\nLevel 9"),          
     K("MI_ET_15", "Extended\nIntervals\nLevel 3", "Interval\nLevel 9"),            
     K("MI_ET_16", "All\nIntervals\nLevel 3", "Ear Train\nLevel 9"),
]

KEYCODES_CHORDTRAINER = [
     K("MI_CET_1", "Triads\nLevel 1", "Chord Train\nLevel 1"),
     K("MI_CET_2", "Basic\n7ths\nLevel 1", "Chord Train\nLevel 2"),
     K("MI_CET_3", "All 7ths\nLevel 1", "Chord Train\nLevel 3"),
     K("MI_CET_4", "Triads &\nBasic 7ths\nLevel 1", "Chord Train\nLevel 4"),
     K("MI_CET_5", "Triads &\nAll 7ths\nLevel 1", "Chord Train\nLevel 5"),
     
     K("MI_CET_6", "Triads\nLevel 2", "Chord Train\nLevel 6"),
     K("MI_CET_7", "Basic\n7ths\nLevel 2", "Chord Train\nLevel 7"),
     K("MI_CET_8", "All 7ths\nLevel 2", "Chord Train\nLevel 8"),
     K("MI_CET_9", "Triads &\nBasic 7ths\nLevel 2", "Chord Train\nLevel 9"),
     K("MI_CET_10", "Triads &\nAll 7ths\nLevel 2", "Chord Train\nLevel 9"),
     
     K("MI_CET_11", "Triads\nLevel 3", "Chord Train\nLevel 9"),
     K("MI_CET_12", "Basic\n7ths\nLevel 3", "Chord Train\nLevel 9"),
     K("MI_CET_13", "All 7ths\nLevel 3", "Chord Train\nLevel 9"),
     K("MI_CET_14", "Triads &\nBasic 7ths\nLevel 3", "Chord Train\nLevel 9"),
     K("MI_CET_15", "Triads &\nAll 7ths\nLevel 3", "Chord Train\nLevel 9"),
     
     K("MI_CET_16", "Triads\nLevel 4", "Chord Train\nLevel 9"),
     K("MI_CET_17", "Basic\n7ths\nLevel 4", "Chord Train\nLevel 9"),
     K("MI_CET_18", "All 7ths\nLevel 4", "Chord Train\nLevel 9"),
     K("MI_CET_19", "Triads &\nBasic 7ths\nLevel 4", "Chord Train\nLevel 9"),
     K("MI_CET_20", "Triads &\nAll 7ths\nLevel 4", "Chord Train\nLevel 9"),
]

KEYCODES_MIDI = []

KEYCODES_MIDI_BASIC = [
    K("MI_C", "Midi\nC", "Midi send note C"),
    K("MI_Cs", "Midi\nC#/Dᵇ", "Midi send note C#/Dᵇ", alias=["MI_Db"]),
    K("MI_D", "Midi\nD", "Midi send note D"),
    K("MI_Ds", "Midi\nD#/Eᵇ", "Midi send note D#/Eᵇ", alias=["MI_Eb"]),
    K("MI_E", "Midi\nE", "Midi send note E"),
    K("MI_F", "Midi\nF", "Midi send note F"),
    K("MI_Fs", "Midi\nF#/Gᵇ", "Midi send note F#/Gᵇ", alias=["MI_Gb"]),
    K("MI_G", "Midi\nG", "Midi send note G"),
    K("MI_Gs", "Midi\nG#/Aᵇ", "Midi send note G#/Aᵇ", alias=["MI_Ab"]),
    K("MI_A", "Midi\nA", "Midi send note A"),
    K("MI_As", "Midi\nA#/Bᵇ", "Midi send note A#/Bᵇ", alias=["MI_Bb"]),
    K("MI_B", "Midi\nB", "Midi send note B"),

    K("MI_C_1", "Midi\nC₁", "Midi send note C₁"),
    K("MI_Cs_1", "Midi\nC#₁/Dᵇ₁", "Midi send note C#₁/Dᵇ₁", alias=["MI_Db_1"]),
    K("MI_D_1", "Midi\nD₁", "Midi send note D₁"),
    K("MI_Ds_1", "Midi\nD#₁/Eᵇ₁", "Midi send note D#₁/Eᵇ₁", alias=["MI_Eb_1"]),
    K("MI_E_1", "Midi\nE₁", "Midi send note E₁"),
    K("MI_F_1", "Midi\nF₁", "Midi send note F₁"),
    K("MI_Fs_1", "Midi\nF#₁/Gᵇ₁", "Midi send note F#₁/Gᵇ₁", alias=["MI_Gb_1"]),
    K("MI_G_1", "Midi\nG₁", "Midi send note G₁"),
    K("MI_Gs_1", "Midi\nG#₁/Aᵇ₁", "Midi send note G#₁/Aᵇ₁", alias=["MI_Ab_1"]),
    K("MI_A_1", "Midi\nA₁", "Midi send note A₁"),
    K("MI_As_1", "Midi\nA#₁/Bᵇ₁", "Midi send note A#₁/Bᵇ₁", alias=["MI_Bb_1"]),
    K("MI_B_1", "Midi\nB₁", "Midi send note B₁"),

    K("MI_C_2", "Midi\nC₂", "Midi send note C₂"),
    K("MI_Cs_2", "Midi\nC#₂/Dᵇ₂", "Midi send note C#₂/Dᵇ₂", alias=["MI_Db_2"]),
    K("MI_D_2", "Midi\nD₂", "Midi send note D₂"),
    K("MI_Ds_2", "Midi\nD#₂/Eᵇ₂", "Midi send note D#₂/Eᵇ₂", alias=["MI_Eb_2"]),
    K("MI_E_2", "Midi\nE₂", "Midi send note E₂"),
    K("MI_F_2", "Midi\nF₂", "Midi send note F₂"),
    K("MI_Fs_2", "Midi\nF#₂/Gᵇ₂", "Midi send note F#₂/Gᵇ₂", alias=["MI_Gb_2"]),
    K("MI_G_2", "Midi\nG₂", "Midi send note G₂"),
    K("MI_Gs_2", "Midi\nG#₂/Aᵇ₂", "Midi send note G#₂/Aᵇ₂", alias=["MI_Ab_2"]),
    K("MI_A_2", "Midi\nA₂", "Midi send note A₂"),
    K("MI_As_2", "Midi\nA#₂/Bᵇ₂", "Midi send note A#₂/Bᵇ₂", alias=["MI_Bb_2"]),
    K("MI_B_2", "Midi\nB₂", "Midi send note B₂"),

    K("MI_C_3", "Midi\nC₃", "Midi send note C₃"),
    K("MI_Cs_3", "Midi\nC#₃/Dᵇ₃", "Midi send note C#₃/Dᵇ₃", alias=["MI_Db_3"]),
    K("MI_D_3", "Midi\nD₃", "Midi send note D₃"),
    K("MI_Ds_3", "Midi\nD#₃/Eᵇ₃", "Midi send note D#₃/Eᵇ₃", alias=["MI_Eb_3"]),
    K("MI_E_3", "Midi\nE₃", "Midi send note E₃"),
    K("MI_F_3", "Midi\nF₃", "Midi send note F₃"),
    K("MI_Fs_3", "Midi\nF#₃/Gᵇ₃", "Midi send note F#₃/Gᵇ₃", alias=["MI_Gb_3"]),
    K("MI_G_3", "Midi\nG₃", "Midi send note G₃"),
    K("MI_Gs_3", "Midi\nG#₃/Aᵇ₃", "Midi send note G#₃/Aᵇ₃", alias=["MI_Ab_3"]),
    K("MI_A_3", "Midi\nA₃", "Midi send note A₃"),
    K("MI_As_3", "Midi\nA#₃/Bᵇ₃", "Midi send note A#₃/Bᵇ₃", alias=["MI_Bb_3"]),
    K("MI_B_3", "Midi\nB₃", "Midi send note B₃"),

    K("MI_C_4", "Midi\nC₄", "Midi send note C₄"),
    K("MI_Cs_4", "Midi\nC#₄/Dᵇ₄", "Midi send note C#₄/Dᵇ₄", alias=["MI_Db_4"]),
    K("MI_D_4", "Midi\nD₄", "Midi send note D₄"),
    K("MI_Ds_4", "Midi\nD#₄/Eᵇ₄", "Midi send note D#₄/Eᵇ₄", alias=["MI_Eb_4"]),
    K("MI_E_4", "Midi\nE₄", "Midi send note E₄"),
    K("MI_F_4", "Midi\nF₄", "Midi send note F₄"),
    K("MI_Fs_4", "Midi\nF#₄/Gᵇ₄", "Midi send note F#₄/Gᵇ₄", alias=["MI_Gb_4"]),
    K("MI_G_4", "Midi\nG₄", "Midi send note G₄"),
    K("MI_Gs_4", "Midi\nG#₄/Aᵇ₄", "Midi send note G#₄/Aᵇ₄", alias=["MI_Ab_4"]),
    K("MI_A_4", "Midi\nA₄", "Midi send note A₄"),
    K("MI_As_4", "Midi\nA#₄/Bᵇ₄", "Midi send note A#₄/Bᵇ₄", alias=["MI_Bb_4"]),
    K("MI_B_4", "Midi\nB₄", "Midi send note B₄"),

    K("MI_C_5", "Midi\nC₅", "Midi send note C₅"),
    K("MI_Cs_5", "Midi\nC#₅/Dᵇ₅", "Midi send note C#₅/Dᵇ₅", alias=["MI_Db_5"]),
    K("MI_D_5", "Midi\nD₅", "Midi send note D₅"),
    K("MI_Ds_5", "Midi\nD#₅/Eᵇ₅", "Midi send note D#₅/Eᵇ₅", alias=["MI_Eb_5"]),
    K("MI_E_5", "Midi\nE₅", "Midi send note E₅"),
    K("MI_F_5", "Midi\nF₅", "Midi send note F₅"),
    K("MI_Fs_5", "Midi\nF#₅/Gᵇ₅", "Midi send note F#₅/Gᵇ₅", alias=["MI_Gb_5"]),
    K("MI_G_5", "Midi\nG₅", "Midi send note G₅"),
    K("MI_Gs_5", "Midi\nG#₅/Aᵇ₅", "Midi send note G#₅/Aᵇ₅", alias=["MI_Ab_5"]),
    K("MI_A_5", "Midi\nA₅", "Midi send note A₅"),
    K("MI_As_5", "Midi\nA#₅/Bᵇ₅", "Midi send note A#₅/Bᵇ₅", alias=["MI_Bb_5"]),
    K("MI_B_5", "Midi\nB₅", "Midi send note B₅"),

    K("MI_ALLOFF", "All\nNotes\nOff", "Midi send all notes OFF"),
    K("MI_SUS", "Sustain\nPedal", "Midi Sustain"),
    K("KC_NO", "", "None"),
    K("MI_CHORD_99", "Smart\nChord", "Press QuickChord"),  
]

KEYCODES_MIDI_SPLIT = [
        K("MI_SPLIT_C", "KS\nC", "Midi send note C"),
        K("MI_SPLIT_Cs", "KS\nC#/Dᵇ", "Midi send note C#/Dᵇ", alias=["MI_SPLIT_Db"]),
        K("MI_SPLIT_D", "KS\nD", "Midi send note D"),
        K("MI_SPLIT_Ds", "KS\nD#/Eᵇ", "Midi send note D#/Eᵇ", alias=["MI_SPLIT_Eb"]),
        K("MI_SPLIT_E", "KS\nE", "Midi send note E"),
        K("MI_SPLIT_F", "KS\nF", "Midi send note F"),
        K("MI_SPLIT_Fs", "KS\nF#/Gᵇ", "Midi send note F#/Gᵇ", alias=["MI_SPLIT_Gb"]),
        K("MI_SPLIT_G", "KS\nG", "Midi send note G"),
        K("MI_SPLIT_Gs", "KS\nG#/Aᵇ", "Midi send note G#/Aᵇ", alias=["MI_SPLIT_Ab"]),
        K("MI_SPLIT_A", "KS\nA", "Midi send note A"),
        K("MI_SPLIT_As", "KS\nA#/Bᵇ", "Midi send note A#/Bᵇ", alias=["MI_SPLIT_Bb"]),
        K("MI_SPLIT_B", "KS\nB", "Midi send note B"),

        K("MI_SPLIT_C_1", "KS\nC₁", "Midi send note C₁"),
        K("MI_SPLIT_Cs_1", "KS\nC#₁/Dᵇ₁", "Midi send note C#₁/Dᵇ₁", alias=["MI_SPLIT_Db_1"]),
        K("MI_SPLIT_D_1", "KS\nD₁", "Midi send note D₁"),
        K("MI_SPLIT_Ds_1", "KS\nD#₁/Eᵇ₁", "Midi send note D#₁/Eᵇ₁", alias=["MI_SPLIT_Eb_1"]),
        K("MI_SPLIT_E_1", "KS\nE₁", "Midi send note E₁"),
        K("MI_SPLIT_F_1", "KS\nF₁", "Midi send note F₁"),
        K("MI_SPLIT_Fs_1", "KS\nF#₁/Gᵇ₁", "Midi send note F#₁/Gᵇ₁", alias=["MI_SPLIT_Gb_1"]),
        K("MI_SPLIT_G_1", "KS\nG₁", "Midi send note G₁"),
        K("MI_SPLIT_Gs_1", "KS\nG#₁/Aᵇ₁", "Midi send note G#₁/Aᵇ₁", alias=["MI_SPLIT_Ab_1"]),
        K("MI_SPLIT_A_1", "KS\nA₁", "Midi send note A₁"),
        K("MI_SPLIT_As_1", "KS\nA#₁/Bᵇ₁", "Midi send note A#₁/Bᵇ₁", alias=["MI_SPLIT_Bb_1"]),
        K("MI_SPLIT_B_1", "KS\nB₁", "Midi send note B₁"),

        K("MI_SPLIT_C_2", "KS\nC₂", "Midi send note C₂"),
        K("MI_SPLIT_Cs_2", "KS\nC#₂/Dᵇ₂", "Midi send note C#₂/Dᵇ₂", alias=["MI_SPLIT_Db_2"]),
        K("MI_SPLIT_D_2", "KS\nD₂", "Midi send note D₂"),
        K("MI_SPLIT_Ds_2", "KS\nD#₂/Eᵇ₂", "Midi send note D#₂/Eᵇ₂", alias=["MI_SPLIT_Eb_2"]),
        K("MI_SPLIT_E_2", "KS\nE₂", "Midi send note E₂"),
        K("MI_SPLIT_F_2", "KS\nF₂", "Midi send note F₂"),
        K("MI_SPLIT_Fs_2", "KS\nF#₂/Gᵇ₂", "Midi send note F#₂/Gᵇ₂", alias=["MI_SPLIT_Gb_2"]),
        K("MI_SPLIT_G_2", "KS\nG₂", "Midi send note G₂"),
        K("MI_SPLIT_Gs_2", "KS\nG#₂/Aᵇ₂", "Midi send note G#₂/Aᵇ₂", alias=["MI_SPLIT_Ab_2"]),
        K("MI_SPLIT_A_2", "KS\nA₂", "Midi send note A₂"),
        K("MI_SPLIT_As_2", "KS\nA#₂/Bᵇ₂", "Midi send note A#₂/Bᵇ₂", alias=["MI_SPLIT_Bb_2"]),
        K("MI_SPLIT_B_2", "KS\nB₂", "Midi send note B₂"),

        K("MI_SPLIT_C_3", "KS\nC₃", "Midi send note C₃"),
        K("MI_SPLIT_Cs_3", "KS\nC#₃/Dᵇ₃", "Midi send note C#₃/Dᵇ₃", alias=["MI_SPLIT_Db_3"]),
        K("MI_SPLIT_D_3", "KS\nD₃", "Midi send note D₃"),
        K("MI_SPLIT_Ds_3", "KS\nD#₃/Eᵇ₃", "Midi send note D#₃/Eᵇ₃", alias=["MI_SPLIT_Eb_3"]),
        K("MI_SPLIT_E_3", "KS\nE₃", "Midi send note E₃"),
        K("MI_SPLIT_F_3", "KS\nF₃", "Midi send note F₃"),
        K("MI_SPLIT_Fs_3", "KS\nF#₃/Gᵇ₃", "Midi send note F#₃/Gᵇ₃", alias=["MI_SPLIT_Gb_3"]),
        K("MI_SPLIT_G_3", "KS\nG₃", "Midi send note G₃"),
        K("MI_SPLIT_Gs_3", "KS\nG#₃/Aᵇ₃", "Midi send note G#₃/Aᵇ₃", alias=["MI_SPLIT_Ab_3"]),
        K("MI_SPLIT_A_3", "KS\nA₃", "Midi send note A₃"),
        K("MI_SPLIT_As_3", "KS\nA#₃/Bᵇ₃", "Midi send note A#₃/Bᵇ₃", alias=["MI_SPLIT_Bb_3"]),
        K("MI_SPLIT_B_3", "KS\nB₃", "Midi send note B₃"),

        K("MI_SPLIT_C_4", "KS\nC₄", "Midi send note C₄"),
        K("MI_SPLIT_Cs_4", "KS\nC#₄/Dᵇ₄", "Midi send note C#₄/Dᵇ₄", alias=["MI_SPLIT_Db_4"]),
        K("MI_SPLIT_D_4", "KS\nD₄", "Midi send note D₄"),
        K("MI_SPLIT_Ds_4", "KS\nD#₄/Eᵇ₄", "Midi send note D#₄/Eᵇ₄", alias=["MI_SPLIT_Eb_4"]),
        K("MI_SPLIT_E_4", "KS\nE₄", "Midi send note E₄"),
        K("MI_SPLIT_F_4", "KS\nF₄", "Midi send note F₄"),
        K("MI_SPLIT_Fs_4", "KS\nF#₄/Gᵇ₄", "Midi send note F#₄/Gᵇ₄", alias=["MI_SPLIT_Gb_4"]),
        K("MI_SPLIT_G_4", "KS\nG₄", "Midi send note G₄"),
        K("MI_SPLIT_Gs_4", "KS\nG#₄/Aᵇ₄", "Midi send note G#₄/Aᵇ₄", alias=["MI_SPLIT_Ab_4"]),
        K("MI_SPLIT_A_4", "KS\nA₄", "Midi send note A₄"),
        K("MI_SPLIT_As_4", "KS\nA#₄/Bᵇ₄", "Midi send note A#₄/Bᵇ₄", alias=["MI_SPLIT_Bb_4"]),
        K("MI_SPLIT_B_4", "KS\nB₄", "Midi send note B₄"),

        K("MI_SPLIT_C_5", "KS\nC₅", "Midi send note C₅"),
        K("MI_SPLIT_Cs_5", "KS\nC#₅/Dᵇ₅", "Midi send note C#₅/Dᵇ₅", alias=["MI_SPLIT_Db_5"]),
        K("MI_SPLIT_D_5", "KS\nD₅", "Midi send note D₅"),
        K("MI_SPLIT_Ds_5", "KS\nD#₅/Eᵇ₅", "Midi send note D#₅/Eᵇ₅", alias=["MI_SPLIT_Eb_5"]),
        K("MI_SPLIT_E_5", "KS\nE₅", "Midi send note E₅"),
        K("MI_SPLIT_F_5", "KS\nF₅", "Midi send note F₅"),
        K("MI_SPLIT_Fs_5", "KS\nF#₅/Gᵇ₅", "Midi send note F#₅/Gᵇ₅", alias=["MI_SPLIT_Gb_5"]),
        K("MI_SPLIT_G_5", "KS\nG₅", "Midi send note G₅"),
        K("MI_SPLIT_Gs_5", "KS\nG#₅/Aᵇ₅", "Midi send note G#₅/Aᵇ₅", alias=["MI_SPLIT_Ab_5"]),
        K("MI_SPLIT_A_5", "KS\nA₅", "Midi send note A₅"),
        K("MI_SPLIT_As_5", "KS\nA#₅/Bᵇ₅", "Midi send note A#₅/Bᵇ₅", alias=["MI_SPLIT_Bb_5"]),
        K("MI_SPLIT_B_5", "KS\nB₅", "Midi send note B₅"),

        K("MI_ALLOFF", "All\nNotes\nOff", "Midi send all notes OFF"),
        K("MI_SUS", "Sustain\nPedal", "Midi Sustain"),
        K("KC_NO", "", "None"),
        K("MI_CHORD_99", "Smart\nChord", "Press QuickChord"),  
        K("KS_CHAN_DOWN", "KS\nChannel▼", "Midi set key split channel Down"),
        K("KS_CHAN_UP", "KS\nChannel▲", "Midi set key split channel UP"),
        K("KS2_CHAN_DOWN", "TS\nChannel▼", "Midi set key split channel Down"),
        K("KS2_CHAN_UP", "TS\nChannel▲", "Midi set key split channel UP"),
        K("MI_VELOCITY2_DOWN", "KS\nVelocity▼", "Midi set key split channel Down"),
        K("MI_VELOCITY2_UP", "KS\nVelocity▲", "Midi set key split channel UP"),
        K("MI_VELOCITY3_DOWN", "TS\nVelocity▼", "Midi set key split channel Down"),
        K("MI_VELOCITY3_UP", "TS\nVelocity▲", "Midi set key split channel UP"),
        K("MI_TRANSPOSE2_DOWN", "KS\nTranspose▼", "Midi set key split channel Down"),
        K("MI_TRANSPOSE2_UP", "KS\nTranspose▲", "Midi set key split channel UP"),
        K("MI_TRANSPOSE3_DOWN", "TS\nTranspose▼", "Midi set key split channel Down"),
        K("MI_TRANSPOSE3_UP", "TS\nTranspose▲", "Midi set key split channel UP"),
        K("MI_OCTAVE2_DOWN", "KS\nOctave▼", "Midi set key split channel Down"),
        K("MI_OCTAVE2_UP", "KS\nOctave▲", "Midi set key split channel UP"),
        K("MI_OCTAVE3_DOWN", "TS\nOctave▼", "Midi set key split channel Down"),
        K("MI_OCTAVE3_UP", "TS\nOctave▲", "Midi set key split channel UP"),
]

KEYCODES_MIDI_SPLIT_BUTTONS = [        
        K("KS_CHAN_UP", "KS\nChannel\n▲", "Midi set key split channel UP"),       
        K("KS2_CHAN_UP", "TS\nChannel\n▲", "Midi set key split channel UP"),       
        K("MI_VELOCITY2_UP", "KS\nVelocity\n▲", "Midi set key split channel UP"),       
        K("MI_VELOCITY3_UP", "TS\nVelocity\n▲", "Midi set key split channel UP"),       
        K("MI_TRANSPOSE2_UP", "KS\nTranspose\n▲", "Midi set key split channel UP"),        
        K("MI_TRANSPOSE3_UP", "TS\nTranspose\n▲", "Midi set key split channel UP"),      
        K("MI_OCTAVE2_UP", "KS\nOctave\n▲", "Midi set key split channel UP"),       
        K("MI_OCTAVE3_UP", "TS\nOctave\n▲", "Midi set key split channel UP"),        
        K("KS_CHAN_DOWN", "KS\nChannel\n▼", "Midi set key split channel Down"),
        K("KS2_CHAN_DOWN", "TS\nChannel\n▼", "Midi set key split channel Down"),
        K("MI_VELOCITY2_DOWN", "KS\nVelocity\n▼", "Midi set key split channel Down"),
        K("MI_VELOCITY3_DOWN", "TS\nVelocity\n▼", "Midi set key split channel Down"),
        K("MI_TRANSPOSE2_DOWN", "KS\nTranspose\n▼", "Midi set key split channel Down"),
        K("MI_TRANSPOSE3_DOWN", "TS\nTranspose\n▼", "Midi set key split channel Down"),
        K("MI_OCTAVE2_DOWN", "KS\nOctave\n▼", "Midi set key split channel Down"),
        K("MI_OCTAVE3_DOWN", "TS\nOctave\n▼", "Midi set key split channel Down"),
]

KEYCODES_MIDI_SPLIT2 = [
        K("MI_SPLIT2_C", "TS\nC", "Midi send note C"),
        K("MI_SPLIT2_Cs", "TS\nC#/Dᵇ", "Midi send note C#/Dᵇ", alias=["MI_SPLIT2_Db"]),
        K("MI_SPLIT2_D", "TS\nD", "Midi send note D"),
        K("MI_SPLIT2_Ds", "TS\nD#/Eᵇ", "Midi send note D#/Eᵇ", alias=["MI_SPLIT2_Eb"]),
        K("MI_SPLIT2_E", "TS\nE", "Midi send note E"),
        K("MI_SPLIT2_F", "TS\nF", "Midi send note F"),
        K("MI_SPLIT2_Fs", "TS\nF#/Gᵇ", "Midi send note F#/Gᵇ", alias=["MI_SPLIT2_Gb"]),
        K("MI_SPLIT2_G", "TS\nG", "Midi send note G"),
        K("MI_SPLIT2_Gs", "TS\nG#/Aᵇ", "Midi send note G#/Aᵇ", alias=["MI_SPLIT2_Ab"]),
        K("MI_SPLIT2_A", "TS\nA", "Midi send note A"),
        K("MI_SPLIT2_As", "TS\nA#/Bᵇ", "Midi send note A#/Bᵇ", alias=["MI_SPLIT2_Bb"]),
        K("MI_SPLIT2_B", "TS\nB", "Midi send note B"),

        K("MI_SPLIT2_C_1", "TS\nC₁", "Midi send note C₁"),
        K("MI_SPLIT2_Cs_1", "TS\nC#₁/Dᵇ₁", "Midi send note C#₁/Dᵇ₁", alias=["MI_SPLIT2_Db_1"]),
        K("MI_SPLIT2_D_1", "TS\nD₁", "Midi send note D₁"),
        K("MI_SPLIT2_Ds_1", "TS\nD#₁/Eᵇ₁", "Midi send note D#₁/Eᵇ₁", alias=["MI_SPLIT2_Eb_1"]),
        K("MI_SPLIT2_E_1", "TS\nE₁", "Midi send note E₁"),
        K("MI_SPLIT2_F_1", "TS\nF₁", "Midi send note F₁"),
        K("MI_SPLIT2_Fs_1", "TS\nF#₁/Gᵇ₁", "Midi send note F#₁/Gᵇ₁", alias=["MI_SPLIT2_Gb_1"]),
        K("MI_SPLIT2_G_1", "TS\nG₁", "Midi send note G₁"),
        K("MI_SPLIT2_Gs_1", "TS\nG#₁/Aᵇ₁", "Midi send note G#₁/Aᵇ₁", alias=["MI_SPLIT2_Ab_1"]),
        K("MI_SPLIT2_A_1", "TS\nA₁", "Midi send note A₁"),
        K("MI_SPLIT2_As_1", "TS\nA#₁/Bᵇ₁", "Midi send note A#₁/Bᵇ₁", alias=["MI_SPLIT2_Bb_1"]),
        K("MI_SPLIT2_B_1", "TS\nB₁", "Midi send note B₁"),

        K("MI_SPLIT2_C_2", "TS\nC₂", "Midi send note C₂"),
        K("MI_SPLIT2_Cs_2", "TS\nC#₂/Dᵇ₂", "Midi send note C#₂/Dᵇ₂", alias=["MI_SPLIT2_Db_2"]),
        K("MI_SPLIT2_D_2", "TS\nD₂", "Midi send note D₂"),
        K("MI_SPLIT2_Ds_2", "TS\nD#₂/Eᵇ₂", "Midi send note D#₂/Eᵇ₂", alias=["MI_SPLIT2_Eb_2"]),
        K("MI_SPLIT2_E_2", "TS\nE₂", "Midi send note E₂"),
        K("MI_SPLIT2_F_2", "TS\nF₂", "Midi send note F₂"),
        K("MI_SPLIT2_Fs_2", "TS\nF#₂/Gᵇ₂", "Midi send note F#₂/Gᵇ₂", alias=["MI_SPLIT2_Gb_2"]),
        K("MI_SPLIT2_G_2", "TS\nG₂", "Midi send note G₂"),
        K("MI_SPLIT2_Gs_2", "TS\nG#₂/Aᵇ₂", "Midi send note G#₂/Aᵇ₂", alias=["MI_SPLIT2_Ab_2"]),
        K("MI_SPLIT2_A_2", "TS\nA₂", "Midi send note A₂"),
        K("MI_SPLIT2_As_2", "TS\nA#₂/Bᵇ₂", "Midi send note A#₂/Bᵇ₂", alias=["MI_SPLIT2_Bb_2"]),
        K("MI_SPLIT2_B_2", "TS\nB₂", "Midi send note B₂"),

        K("MI_SPLIT2_C_3", "TS\nC₃", "Midi send note C₃"),
        K("MI_SPLIT2_Cs_3", "TS\nC#₃/Dᵇ₃", "Midi send note C#₃/Dᵇ₃", alias=["MI_SPLIT2_Db_3"]),
        K("MI_SPLIT2_D_3", "TS\nD₃", "Midi send note D₃"),
        K("MI_SPLIT2_Ds_3", "TS\nD#₃/Eᵇ₃", "Midi send note D#₃/Eᵇ₃", alias=["MI_SPLIT2_Eb_3"]),
        K("MI_SPLIT2_E_3", "TS\nE₃", "Midi send note E₃"),
        K("MI_SPLIT2_F_3", "TS\nF₃", "Midi send note F₃"),
        K("MI_SPLIT2_Fs_3", "TS\nF#₃/Gᵇ₃", "Midi send note F#₃/Gᵇ₃", alias=["MI_SPLIT2_Gb_3"]),
        K("MI_SPLIT2_G_3", "TS\nG₃", "Midi send note G₃"),
        K("MI_SPLIT2_Gs_3", "TS\nG#₃/Aᵇ₃", "Midi send note G#₃/Aᵇ₃", alias=["MI_SPLIT2_Ab_3"]),
        K("MI_SPLIT2_A_3", "TS\nA₃", "Midi send note A₃"),
        K("MI_SPLIT2_As_3", "TS\nA#₃/Bᵇ₃", "Midi send note A#₃/Bᵇ₃", alias=["MI_SPLIT2_Bb_3"]),
        K("MI_SPLIT2_B_3", "TS\nB₃", "Midi send note B₃"),

        K("MI_SPLIT2_C_4", "TS\nC₄", "Midi send note C₄"),
        K("MI_SPLIT2_Cs_4", "TS\nC#₄/Dᵇ₄", "Midi send note C#₄/Dᵇ₄", alias=["MI_SPLIT2_Db_4"]),
        K("MI_SPLIT2_D_4", "TS\nD₄", "Midi send note D₄"),
        K("MI_SPLIT2_Ds_4", "TS\nD#₄/Eᵇ₄", "Midi send note D#₄/Eᵇ₄", alias=["MI_SPLIT2_Eb_4"]),
        K("MI_SPLIT2_E_4", "TS\nE₄", "Midi send note E₄"),
        K("MI_SPLIT2_F_4", "TS\nF₄", "Midi send note F₄"),
        K("MI_SPLIT2_Fs_4", "TS\nF#₄/Gᵇ₄", "Midi send note F#₄/Gᵇ₄", alias=["MI_SPLIT2_Gb_4"]),
        K("MI_SPLIT2_G_4", "TS\nG₄", "Midi send note G₄"),
        K("MI_SPLIT2_Gs_4", "TS\nG#₄/Aᵇ₄", "Midi send note G#₄/Aᵇ₄", alias=["MI_SPLIT2_Ab_4"]),
        K("MI_SPLIT2_A_4", "TS\nA₄", "Midi send note A₄"),
        K("MI_SPLIT2_As_4", "TS\nA#₄/Bᵇ₄", "Midi send note A#₄/Bᵇ₄", alias=["MI_SPLIT2_Bb_4"]),
        K("MI_SPLIT2_B_4", "TS\nB₄", "Midi send note B₄"),

        K("MI_SPLIT2_C_5", "TS\nC₅", "Midi send note C₅"),
        K("MI_SPLIT2_Cs_5", "TS\nC#₅/Dᵇ₅", "Midi send note C#₅/Dᵇ₅", alias=["MI_SPLIT2_Db_5"]),
        K("MI_SPLIT2_D_5", "TS\nD₅", "Midi send note D₅"),
        K("MI_SPLIT2_Ds_5", "TS\nD#₅/Eᵇ₅", "Midi send note D#₅/Eᵇ₅", alias=["MI_SPLIT2_Eb_5"]),
        K("MI_SPLIT2_E_5", "TS\nE₅", "Midi send note E₅"),
        K("MI_SPLIT2_F_5", "TS\nF₅", "Midi send note F₅"),
        K("MI_SPLIT2_Fs_5", "TS\nF#₅/Gᵇ₅", "Midi send note F#₅/Gᵇ₅", alias=["MI_SPLIT2_Gb_5"]),
        K("MI_SPLIT2_G_5", "TS\nG₅", "Midi send note G₅"),
        K("MI_SPLIT2_Gs_5", "TS\nG#₅/Aᵇ₅", "Midi send note G#₅/Aᵇ₅", alias=["MI_SPLIT2_Ab_5"]),
        K("MI_SPLIT2_A_5", "TS\nA₅", "Midi send note A₅"),
        K("MI_SPLIT2_As_5", "TS\nA#₅/Bᵇ₅", "Midi send note A#₅/Bᵇ₅", alias=["MI_SPLIT2_Bb_5"]),
        K("MI_SPLIT2_B_5", "TS\nB₅", "Midi send note B₅"),

        K("MI_ALLOFF", "All\nNotes\nOff", "Midi send all notes OFF"),
        K("MI_SUS", "Sustain\nPedal", "Midi Sustain"),
        K("KC_NO", "", "None"),
        K("MI_CHORD_99", "Smart\nChord", "Press QuickChord"),  
]

KEYCODES_MIDI_ADVANCED = [
    K("MI_TRNSU", "Transpose\n▲", "Midi increase transposition"), 
    K("MI_OCTU", "Octave\n▲", "Midi move up an octave"),  
    K("MI_VELOCITY_UP", "Velocity\n▲", "Midi increase velocity"),  
    K("MI_CHU", "Channel\n▲", "Midi increase channel"),   
    K("MI_BENDU", "Pitch\nBend ▲", "Midi bend pitch up"),   
    K("MI_MODSU", "Mod\nSpeed ▲", "Midi increase modulation speed"), 
    K("MI_PROG_UP", "Program\n▲", "Program up")  ,  
    K("MI_BANK_UP", "Bank\n▲", "Bank up"),     
    K("MI_TRNSD", "Transpose\n▼", "Midi decrease transposition"),  
    K("MI_OCTD", "Octave\n▼", "Midi move down an octave"),
    K("MI_VELOCITY_DOWN", "Velocity\n▼", "Midi decrease velocity"), 
    K("MI_CHD", "Channel\n▼", "Midi decrease channel"),
    K("MI_BENDD", "Pitch\nBend ▼", "Midi bend pitch down"),
    K("MI_MODSD", "Mod\nSpeed ▼", "Midi decrease modulation speed"), 
    K("MI_PROG_DWN", "Program\n▼", "Program down"),
    K("MI_BANK_DWN", "Bank\n▼", "Bank down"),
    K("MI_ALLOFF", "All\nNotes\nOff", "Midi send all notes OFF"),    
    K("MI_PORT", "Portmento", "Midi Portmento"),
    K("MI_SOST", "Sostenuto", "Midi Sostenuto"),
    K("MI_LEG", "Legato", "Midi Legato"),    
    K("MI_MOD", "Modulation", "Midi Modulation"),
    K("MI_SUS", "Sustain\nPedal", "Midi Sustain"),
    K("MI_SOFT", "Soft\nSPedal", "Midi Soft Pedal"),
    K("OLED_1", "Screen\nKeyboard\nShift", "Momentarily turn on layer when pressed"),
    K("MI_TAP", "Set\nBPM", "Set BPM"),
]

KEYCODES_MIDI_PEDAL = [
    K("MI_ALLOFF", "All\nNotes\nOff", "Midi send all notes OFF"),
    K("MI_SUS", "Sustain\nPedal", "Midi Sustain"),
]

KEYCODES_MIDI_OCTAVE = [
    K("MI_OCT_N2", "Octave\n-2", "Midi set octave to -2"),
    K("MI_OCT_N1", "Octave\n-1", "Midi set octave to -1"),
    K("MI_OCT_0", "Octave\n 0", "Midi set octave to 0"),
    K("MI_OCT_1", "Octave\n+1", "Midi set octave to 1"),
    K("MI_OCT_2", "Octave\n+2", "Midi set octave to 2"),
    K("MI_OCT_3", "Octave\n+3", "Midi set octave to 3"),
    K("MI_OCT_4", "Octave\n+4", "Midi set octave to 4"),
    K("MI_OCT_5", "Octave\n+5", "Midi set octave to 5"),
    K("MI_OCT_6", "Octave\n+6", "Midi set octave to 6"),
    K("MI_OCT_7", "Octave\n+7", "Midi set octave to 7"),
] 

KEYCODES_MIDI_OCTAVE2 = [
    K("MI_OCTAVE2_N2", "KS\nOctave\n-2", "Midi set octave to -2"),
    K("MI_OCTAVE2_N1", "KS\nOctave\n-1", "Midi set octave to -1"),
    K("MI_OCTAVE2_0", "KS\nOctave\n 0", "Midi set octave to 0"),
    K("MI_OCTAVE2_1", "KS\nOctave\n+1", "Midi set octave to 1"),
    K("MI_OCTAVE2_2", "KS\nOctave\n+2", "Midi set octave to 2"),
    K("MI_OCTAVE2_3", "KS\nOctave\n+3", "Midi set octave to 3"),
    K("MI_OCTAVE2_4", "KS\nOctave\n+4", "Midi set octave to 4"),
    K("MI_OCTAVE2_5", "KS\nOctave\n+5", "Midi set octave to 5"),
    K("MI_OCTAVE2_6", "KS\nOctave\n+6", "Midi set octave to 6"),
    K("MI_OCTAVE2_7", "KS\nOctave\n+7", "Midi set octave to 7"),
] 

KEYCODES_MIDI_OCTAVE3 = [
    K("MI_OCTAVE3_N2", "TS\nOctave\n-2", "Midi set octave to -2"),
    K("MI_OCTAVE3_N1", "TS\nOctave\n-1", "Midi set octave to -1"),
    K("MI_OCTAVE3_0", "TS\nOctave\n 0", "Midi set octave to 0"),
    K("MI_OCTAVE3_1", "TS\nOctave\n+1", "Midi set octave to 1"),
    K("MI_OCTAVE3_2", "TS\nOctave\n+2", "Midi set octave to 2"),
    K("MI_OCTAVE3_3", "TS\nOctave\n+3", "Midi set octave to 3"),
    K("MI_OCTAVE3_4", "TS\nOctave\n+4", "Midi set octave to 4"),
    K("MI_OCTAVE3_5", "TS\nOctave\n+5", "Midi set octave to 5"),
    K("MI_OCTAVE3_6", "TS\nOctave\n+6", "Midi set octave to 6"),
    K("MI_OCTAVE3_7", "TS\nOctave\n+7", "Midi set octave to 7"),
] 

KEYCODES_MIDI_UPDOWN = [  
    K("MI_TRNSU", "Transpose\n▲", "Midi increase transposition"),    
    K("MI_OCTU", "Octave\n▲", "Midi move up an octave"),   
    K("MI_CHU", "Channel\n▲", "Midi increase channel"),    
    K("MI_VELOCITY_UP", "Velocity\n▲", "Midi increase velocity"),  
    K("SMARTCHORD_UP", "Smart\nChord\n▲", "QuickChord Up"),    
    K("MI_TRNSD", "Transpose\n▼", "Midi decrease transposition"),
    K("MI_OCTD", "Octave\n▼", "Midi move down an octave"),
    K("MI_CHD", "Channel\n▼", "Midi decrease channel"),
    K("MI_VELOCITY_DOWN", "Velocity\n▼", "Midi decrease velocity"), 
    K("SMARTCHORD_DOWN", "Smart\nChord\n▼", "QuickChord Down"),
   
]    

KEYCODES_MIDI_KEY = [
    K("MI_TRNS_0", "Key\nC Major\nA minor", "Midi set no transposition"),
    K("MI_TRNS_1", "Key\nC# Major\nA# minor", "Midi set transposition to +1 semitones"),
    K("MI_TRNS_2", "Key\nD Major\nB minor", "Midi set transposition to +2 semitones"),
    K("MI_TRNS_3", "Key\nD# Major\nC minor", "Midi set transposition to +3 semitones"),
    K("MI_TRNS_4", "Key\nE Major\nC# minor", "Midi set transposition to +4 semitones"),
    K("MI_TRNS_5", "Key\nF Major\nD minor", "Midi set transposition to +5 semitones"),
    K("MI_TRNS_6", "Key\nF# Major\nD# minor", "Midi set transposition to +6 semitones"),
    K("MI_TRNS_N5", "Key\nG Major\nE minor", "Midi set transposition to -5 semitones"),
    K("MI_TRNS_N4", "Key\nG# Major\nF minor", "Midi set transposition to -4 semitones"),
    K("MI_TRNS_N3", "Key\nA Major\nF# minor", "Midi set transposition to -3 semitones"),
    K("MI_TRNS_N2", "Key\nA# Major\nG minor", "Midi set transposition to -2 semitones"),
    K("MI_TRNS_N1", "Key B Major\n G# Minor", "Midi set transposition to -1 semitones"),
]

KEYCODES_MIDI_KEY2 = [
    K("MI_TRNS2_0", "KS\nC Major\nA minor", "Midi set no transposition"),
    K("MI_TRNS2_1", "KS\nC# Major\nA# minor", "Midi set transposition to +1 semitones"),
    K("MI_TRNS2_2", "KS\nD Major\nB minor", "Midi set transposition to +2 semitones"),
    K("MI_TRNS2_3", "KS\nD# Major\nC minor", "Midi set transposition to +3 semitones"),
    K("MI_TRNS2_4", "KS\nE Major\nC# minor", "Midi set transposition to +4 semitones"),
    K("MI_TRNS2_5", "KS\nF Major\nD minor", "Midi set transposition to +5 semitones"),
    K("MI_TRNS2_6", "KS\nF# Major\nD# minor", "Midi set transposition to +6 semitones"),
    K("MI_TRNS2_N5", "KS\nG Major\nE minor", "Midi set transposition to -5 semitones"),
    K("MI_TRNS2_N4", "KS\nG# Major\nF minor", "Midi set transposition to -4 semitones"),
    K("MI_TRNS2_N3", "KS\nA Major\nF# minor", "Midi set transposition to -3 semitones"),
    K("MI_TRNS2_N2", "KS\nA# Major\nG minor", "Midi set transposition to -2 semitones"),
    K("MI_TRNS2_N1", "KS B Major\n G# Minor", "Midi set transposition to -1 semitones"),
]

KEYCODES_MIDI_KEY3 = [
    K("MI_TRNS3_0", "TS\nC Major\nA minor", "Midi set no transposition"),
    K("MI_TRNS3_1", "TS\nC# Major\nA# minor", "Midi set transposition to +1 semitones"),
    K("MI_TRNS3_2", "TS\nD Major\nB minor", "Midi set transposition to +2 semitones"),
    K("MI_TRNS3_3", "TS\nD# Major\nC minor", "Midi set transposition to +3 semitones"),
    K("MI_TRNS3_4", "TS\nE Major\nC# minor", "Midi set transposition to +4 semitones"),
    K("MI_TRNS3_5", "TS\nF Major\nD minor", "Midi set transposition to +5 semitones"),
    K("MI_TRNS3_6", "TS\nF# Major\nD# minor", "Midi set transposition to +6 semitones"),
    K("MI_TRNS3_N5", "TS\nG Major\nE minor", "Midi set transposition to -5 semitones"),
    K("MI_TRNS3_N4", "TS\nG# Major\nF minor", "Midi set transposition to -4 semitones"),
    K("MI_TRNS3_N3", "TS\nA Major\nF# minor", "Midi set transposition to -3 semitones"),
    K("MI_TRNS3_N2", "TS\nA# Major\nG minor", "Midi set transposition to -2 semitones"),
    K("MI_TRNS3_N1", "TS B Major\n G# Minor", "Midi set transposition to -1 semitones"),
]

KEYCODES_MIDI_CHANNEL = [
    K("MI_CH1", "Channel\n1", "Midi set channel to 1"),
    K("MI_CH2", "Channel\n2", "Midi set channel to 2"),
    K("MI_CH3", "Channel\n3", "Midi set channel to 3"),
    K("MI_CH4", "Channel\n4", "Midi set channel to 4"),
    K("MI_CH5", "Channel\n5", "Midi set channel to 5"),
    K("MI_CH6", "Channel\n6", "Midi set channel to 6"),
    K("MI_CH7", "Channel\n7", "Midi set channel to 7"),
    K("MI_CH8", "Channel\n8", "Midi set channel to 8"),
    K("MI_CH9", "Channel\n9", "Midi set channel to 9"),
    K("MI_CH10", "Channel\n10", "Midi set channel to 10"),
    K("MI_CH11", "Channel\n11", "Midi set channel to 11"),
    K("MI_CH12", "Channel\n12", "Midi set channel to 12"),
    K("MI_CH13", "Channel\n13", "Midi set channel to 13"),
    K("MI_CH14", "Channel\n14", "Midi set channel to 14"),
    K("MI_CH15", "Channel\n15", "Midi set channel to 15"),
    K("MI_CH16", "Channel\n16", "Midi set channel to 16"),
]

KEYCODES_MIDI_CHANNEL_KEYSPLIT = [
    K("MI_CHANNEL_KEYSPLIT_1", "KS\nChannel 1", "Midi set key split channel to 1"),
    K("MI_CHANNEL_KEYSPLIT_2", "KS\nChannel 2", "Midi set key split channel to 2"),
    K("MI_CHANNEL_KEYSPLIT_3", "KS\nChannel 3", "Midi set key split channel to 3"),
    K("MI_CHANNEL_KEYSPLIT_4", "KS\nChannel 4", "Midi set key split channel to 4"),
    K("MI_CHANNEL_KEYSPLIT_5", "KS\nChannel 5", "Midi set key split channel to 5"),
    K("MI_CHANNEL_KEYSPLIT_6", "KS\nChannel 6", "Midi set key split channel to 6"),
    K("MI_CHANNEL_KEYSPLIT_7", "KS\nChannel 7", "Midi set key split channel to 7"),
    K("MI_CHANNEL_KEYSPLIT_8", "KS\nChannel 8", "Midi set key split channel to 8"),
    K("MI_CHANNEL_KEYSPLIT_9", "KS\nChannel 9", "Midi set key split channel to 9"),
    K("MI_CHANNEL_KEYSPLIT_10", "KS\nChannel 10", "Midi set key split channel to 10"),
    K("MI_CHANNEL_KEYSPLIT_11", "KS\nChannel 11", "Midi set key split channel to 11"),
    K("MI_CHANNEL_KEYSPLIT_12", "KS\nChannel 12", "Midi set key split channel to 12"),
    K("MI_CHANNEL_KEYSPLIT_13", "KS\nChannel 13", "Midi set key split channel to 13"),
    K("MI_CHANNEL_KEYSPLIT_14", "KS\nChannel 14", "Midi set key split channel to 14"),
    K("MI_CHANNEL_KEYSPLIT_15", "KS\nChannel 15", "Midi set key split channel to 15"),
    K("MI_CHANNEL_KEYSPLIT_16", "KS\nChannel 16", "Midi set key split channel to 16"),
]

KEYCODES_KEYSPLIT_BUTTONS = [
    K("KS_TOGGLE", "Channel\nSplit\nToggle", "Toggle keysplit mode"),
    K("KS_TRANSPOSE_TOGGLE", "Transpose\nSplit\nToggle", "Toggle keysplit mode"),
    K("KS_VELOCITY_TOGGLE", "Velocity\nSplit\nToggle", "Toggle keysplit mode"),
]

KEYCODES_MIDI_CHANNEL_KEYSPLIT2 = [
    K("MI_CHANNEL_KEYSPLIT2_1", "TS\nChannel 1", "Midi set key split channel to 1"),
    K("MI_CHANNEL_KEYSPLIT2_2", "TS\nChannel 2", "Midi set key split channel to 2"),
    K("MI_CHANNEL_KEYSPLIT2_3", "TS\nChannel 3", "Midi set key split channel to 3"),
    K("MI_CHANNEL_KEYSPLIT2_4", "TS\nChannel 4", "Midi set key split channel to 4"),
    K("MI_CHANNEL_KEYSPLIT2_5", "TS\nChannel 5", "Midi set key split channel to 5"),
    K("MI_CHANNEL_KEYSPLIT2_6", "TS\nChannel 6", "Midi set key split channel to 6"),
    K("MI_CHANNEL_KEYSPLIT2_7", "TS\nChannel 7", "Midi set key split channel to 7"),
    K("MI_CHANNEL_KEYSPLIT2_8", "TS\nChannel 8", "Midi set key split channel to 8"),
    K("MI_CHANNEL_KEYSPLIT2_9", "TS\nChannel 9", "Midi set key split channel to 9"),
    K("MI_CHANNEL_KEYSPLIT2_10", "TS\nChannel 10", "Midi set key split channel to 10"),
    K("MI_CHANNEL_KEYSPLIT2_11", "TS\nChannel 11", "Midi set key split channel to 11"),
    K("MI_CHANNEL_KEYSPLIT2_12", "TS\nChannel 12", "Midi set key split channel to 12"),
    K("MI_CHANNEL_KEYSPLIT2_13", "TS\nChannel 13", "Midi set key split channel to 13"),
    K("MI_CHANNEL_KEYSPLIT2_14", "TS\nChannel 14", "Midi set key split channel to 14"),
    K("MI_CHANNEL_KEYSPLIT2_15", "TS\nChannel 15", "Midi set key split channel to 15"),
    K("MI_CHANNEL_KEYSPLIT2_16", "TS\nChannel 16", "Midi set key split channel to 16"),
]

KEYCODES_VELOCITY_SHUFFLE = [
    K("MI_RVEL_0", "Velocity\nShuffle\nOff", "Midi set key split channel to 1"),
    K("MI_RVEL_1", "Velocity\nShuffle\n +/01", "Midi set key split channel to 1"),
    K("MI_RVEL_2", "Velocity\nShuffle\n +/02", "Midi set key split channel to 2"),
    K("MI_RVEL_3", "Velocity\nShuffle\n +/03", "Midi set key split channel to 3"),
    K("MI_RVEL_4", "Velocity\nShuffle\n +/04", "Midi set key split channel to 4"),
    K("MI_RVEL_5", "Velocity\nShuffle\n +/05", "Midi set key split channel to 5"),
    K("MI_RVEL_6", "Velocity\nShuffle\n +/06", "Midi set key split channel to 6"),
    K("MI_RVEL_7", "Velocity\nShuffle\n +/07", "Midi set key split channel to 7"),
    K("MI_RVEL_8", "Velocity\nShuffle\n +/08", "Midi set key split channel to 8"),
    K("MI_RVEL_9", "Velocity\nShuffle\n +/09", "Midi set key split channel to 9"),
    K("MI_RVEL_10", "Velocity\nShuffle\n +/10", "Midi set key split channel to 10"),
    K("MI_RVEL_11", "Velocity\nShuffle\n +/11", "Midi set key split channel to 11"),
    K("MI_RVEL_12", "Velocity\nShuffle\n +/12", "Midi set key split channel to 12"),
    K("MI_RVEL_13", "Velocity\nShuffle\n +/13", "Midi set key split channel to 13"),
    K("MI_RVEL_14", "Velocity\nShuffle\n +/14", "Midi set key split channel to 14"),
    K("MI_RVEL_15", "Velocity\nShuffle\n +/15", "Midi set key split channel to 15"),
    K("MI_RVEL_16", "Velocity\nShuffle\n +/16", "Midi set key split channel to 16"),
]

KEYCODES_CC_ENCODERVALUE = [
    K("MI_CCENCODER_0", "CC 0\nTouch\nDial", "CC Expression wheel 0"),
    K("MI_CCENCODER_1", "CC 1\nTouch\nDial", "CC Expression wheel 1"),
    K("MI_CCENCODER_2", "CC 2\nTouch\nDial", "CC Expression wheel 2"),
    K("MI_CCENCODER_3", "CC 3\nTouch\nDial", "CC Expression wheel 3"),
    K("MI_CCENCODER_4", "CC 4\nTouch\nDial", "CC Expression wheel 4"),
    K("MI_CCENCODER_5", "CC 5\nTouch\nDial", "CC Expression wheel 5"),
    K("MI_CCENCODER_6", "CC 6\nTouch\nDial", "CC Expression wheel 6"),
    K("MI_CCENCODER_7", "CC 7\nTouch\nDial", "CC Expression wheel 7"),
    K("MI_CCENCODER_8", "CC 8\nTouch\nDial", "CC Expression wheel 8"),
    K("MI_CCENCODER_9", "CC 9\nTouch\nDial", "CC Expression wheel 9"),
    K("MI_CCENCODER_10", "CC 10\nTouch\nDial", "CC Expression wheel 10"),
    K("MI_CCENCODER_11", "CC 11\nTouch\nDial", "CC Expression wheel 11"),
    K("MI_CCENCODER_12", "CC 12\nTouch\nDial", "CC Expression wheel 12"),
    K("MI_CCENCODER_13", "CC 13\nTouch\nDial", "CC Expression wheel 13"),
    K("MI_CCENCODER_14", "CC 14\nTouch\nDial", "CC Expression wheel 14"),
    K("MI_CCENCODER_15", "CC 15\nTouch\nDial", "CC Expression wheel 15"),
    K("MI_CCENCODER_16", "CC 16\nTouch\nDial", "CC Expression wheel 16"),
    K("MI_CCENCODER_17", "CC 17\nTouch\nDial", "CC Expression wheel 17"),
    K("MI_CCENCODER_18", "CC 18\nTouch\nDial", "CC Expression wheel 18"),
    K("MI_CCENCODER_19", "CC 19\nTouch\nDial", "CC Expression wheel 19"),
    K("MI_CCENCODER_20", "CC 20\nTouch\nDial", "CC Expression wheel 20"),
    K("MI_CCENCODER_21", "CC 21\nTouch\nDial", "CC Expression wheel 21"),
    K("MI_CCENCODER_22", "CC 22\nTouch\nDial", "CC Expression wheel 22"),
    K("MI_CCENCODER_23", "CC 23\nTouch\nDial", "CC Expression wheel 23"),
    K("MI_CCENCODER_24", "CC 24\nTouch\nDial", "CC Expression wheel 24"),
    K("MI_CCENCODER_25", "CC 25\nTouch\nDial", "CC Expression wheel 25"),
    K("MI_CCENCODER_26", "CC 26\nTouch\nDial", "CC Expression wheel 26"),
    K("MI_CCENCODER_27", "CC 27\nTouch\nDial", "CC Expression wheel 27"),
    K("MI_CCENCODER_28", "CC 28\nTouch\nDial", "CC Expression wheel 28"),
    K("MI_CCENCODER_29", "CC 29\nTouch\nDial", "CC Expression wheel 29"),
    K("MI_CCENCODER_30", "CC 30\nTouch\nDial", "CC Expression wheel 30"),
    K("MI_CCENCODER_31", "CC 31\nTouch\nDial", "CC Expression wheel 31"),
    K("MI_CCENCODER_32", "CC 32\nTouch\nDial", "CC Expression wheel 32"),
    K("MI_CCENCODER_33", "CC 33\nTouch\nDial", "CC Expression wheel 33"),
    K("MI_CCENCODER_34", "CC 34\nTouch\nDial", "CC Expression wheel 34"),
    K("MI_CCENCODER_35", "CC 35\nTouch\nDial", "CC Expression wheel 35"),
    K("MI_CCENCODER_36", "CC 36\nTouch\nDial", "CC Expression wheel 36"),
    K("MI_CCENCODER_37", "CC 37\nTouch\nDial", "CC Expression wheel 37"),
    K("MI_CCENCODER_38", "CC 38\nTouch\nDial", "CC Expression wheel 38"),
    K("MI_CCENCODER_39", "CC 39\nTouch\nDial", "CC Expression wheel 39"),
    K("MI_CCENCODER_40", "CC 40\nTouch\nDial", "CC Expression wheel 40"),
    K("MI_CCENCODER_41", "CC 41\nTouch\nDial", "CC Expression wheel 41"),
    K("MI_CCENCODER_42", "CC 42\nTouch\nDial", "CC Expression wheel 42"),
    K("MI_CCENCODER_43", "CC 43\nTouch\nDial", "CC Expression wheel 43"),
    K("MI_CCENCODER_44", "CC 44\nTouch\nDial", "CC Expression wheel 44"),
    K("MI_CCENCODER_45", "CC 45\nTouch\nDial", "CC Expression wheel 45"),
    K("MI_CCENCODER_46", "CC 46\nTouch\nDial", "CC Expression wheel 46"),
    K("MI_CCENCODER_47", "CC 47\nTouch\nDial", "CC Expression wheel 47"),
    K("MI_CCENCODER_48", "CC 48\nTouch\nDial", "CC Expression wheel 48"),
    K("MI_CCENCODER_49", "CC 49\nTouch\nDial", "CC Expression wheel 49"),
    K("MI_CCENCODER_50", "CC 50\nTouch\nDial", "CC Expression wheel 50"),
    K("MI_CCENCODER_51", "CC 51\nTouch\nDial", "CC Expression wheel 51"),
    K("MI_CCENCODER_52", "CC 52\nTouch\nDial", "CC Expression wheel 52"),
    K("MI_CCENCODER_53", "CC 53\nTouch\nDial", "CC Expression wheel 53"),
    K("MI_CCENCODER_54", "CC 54\nTouch\nDial", "CC Expression wheel 54"),
    K("MI_CCENCODER_55", "CC 55\nTouch\nDial", "CC Expression wheel 55"),
    K("MI_CCENCODER_56", "CC 56\nTouch\nDial", "CC Expression wheel 56"),
    K("MI_CCENCODER_57", "CC 57\nTouch\nDial", "CC Expression wheel 57"),
    K("MI_CCENCODER_58", "CC 58\nTouch\nDial", "CC Expression wheel 58"),
    K("MI_CCENCODER_59", "CC 59\nTouch\nDial", "CC Expression wheel 59"),
    K("MI_CCENCODER_60", "CC 60\nTouch\nDial", "CC Expression wheel 60"),
    K("MI_CCENCODER_61", "CC 61\nTouch\nDial", "CC Expression wheel 61"),
    K("MI_CCENCODER_62", "CC 62\nTouch\nDial", "CC Expression wheel 62"),
    K("MI_CCENCODER_63", "CC 63\nTouch\nDial", "CC Expression wheel 63"),
    K("MI_CCENCODER_64", "CC 64\nTouch\nDial", "CC Expression wheel 64"),
    K("MI_CCENCODER_65", "CC 65\nTouch\nDial", "CC Expression wheel 65"),
    K("MI_CCENCODER_66", "CC 66\nTouch\nDial", "CC Expression wheel 66"),
    K("MI_CCENCODER_67", "CC 67\nTouch\nDial", "CC Expression wheel 67"),
    K("MI_CCENCODER_68", "CC 68\nTouch\nDial", "CC Expression wheel 68"),
    K("MI_CCENCODER_69", "CC 69\nTouch\nDial", "CC Expression wheel 69"),
    K("MI_CCENCODER_70", "CC 70\nTouch\nDial", "CC Expression wheel 70"),
    K("MI_CCENCODER_71", "CC 71\nTouch\nDial", "CC Expression wheel 71"),
    K("MI_CCENCODER_72", "CC 72\nTouch\nDial", "CC Expression wheel 72"),
    K("MI_CCENCODER_73", "CC 73\nTouch\nDial", "CC Expression wheel 73"),
    K("MI_CCENCODER_74", "CC 74\nTouch\nDial", "CC Expression wheel 74"),
    K("MI_CCENCODER_75", "CC 75\nTouch\nDial", "CC Expression wheel 75"),
    K("MI_CCENCODER_76", "CC 76\nTouch\nDial", "CC Expression wheel 76"),
    K("MI_CCENCODER_77", "CC 77\nTouch\nDial", "CC Expression wheel 77"),
    K("MI_CCENCODER_78", "CC 78\nTouch\nDial", "CC Expression wheel 78"),
    K("MI_CCENCODER_79", "CC 79\nTouch\nDial", "CC Expression wheel 79"),
    K("MI_CCENCODER_80", "CC 80\nTouch\nDial", "CC Expression wheel 80"),
    K("MI_CCENCODER_81", "CC 81\nTouch\nDial", "CC Expression wheel 81"),
    K("MI_CCENCODER_82", "CC 82\nTouch\nDial", "CC Expression wheel 82"),
    K("MI_CCENCODER_83", "CC 83\nTouch\nDial", "CC Expression wheel 83"),
    K("MI_CCENCODER_84", "CC 84\nTouch\nDial", "CC Expression wheel 84"),
    K("MI_CCENCODER_85", "CC 85\nTouch\nDial", "CC Expression wheel 85"),
    K("MI_CCENCODER_86", "CC 86\nTouch\nDial", "CC Expression wheel 86"),
    K("MI_CCENCODER_87", "CC 87\nTouch\nDial", "CC Expression wheel 87"),
    K("MI_CCENCODER_88", "CC 88\nTouch\nDial", "CC Expression wheel 88"),
    K("MI_CCENCODER_89", "CC 89\nTouch\nDial", "CC Expression wheel 89"),
    K("MI_CCENCODER_90", "CC 90\nTouch\nDial", "CC Expression wheel 90"),
    K("MI_CCENCODER_91", "CC 91\nTouch\nDial", "CC Expression wheel 91"),
    K("MI_CCENCODER_92", "CC 92\nTouch\nDial", "CC Expression wheel 92"),
    K("MI_CCENCODER_93", "CC 93\nTouch\nDial", "CC Expression wheel 93"),
    K("MI_CCENCODER_94", "CC 94\nTouch\nDial", "CC Expression wheel 94"),
    K("MI_CCENCODER_95", "CC 95\nTouch\nDial", "CC Expression wheel 95"),
    K("MI_CCENCODER_96", "CC 96\nTouch\nDial", "CC Expression wheel 96"),
    K("MI_CCENCODER_97", "CC 97\nTouch\nDial", "CC Expression wheel 97"),
    K("MI_CCENCODER_98", "CC 98\nTouch\nDial", "CC Expression wheel 98"),
    K("MI_CCENCODER_99", "CC 99\nTouch\nDial", "CC Expression wheel 99"),
    K("MI_CCENCODER_100", "CC 100\nTouch\nDial", "CC Expression wheel 100"),
    K("MI_CCENCODER_101", "CC 101\nTouch\nDial", "CC Expression wheel 101"),
    K("MI_CCENCODER_102", "CC 102\nTouch\nDial", "CC Expression wheel 102"),
    K("MI_CCENCODER_103", "CC 103\nTouch\nDial", "CC Expression wheel 103"),
    K("MI_CCENCODER_104", "CC 104\nTouch\nDial", "CC Expression wheel 104"),
    K("MI_CCENCODER_105", "CC 105\nTouch\nDial", "CC Expression wheel 105"),
    K("MI_CCENCODER_106", "CC 106\nTouch\nDial", "CC Expression wheel 106"),
    K("MI_CCENCODER_107", "CC 107\nTouch\nDial", "CC Expression wheel 107"),
    K("MI_CCENCODER_108", "CC 108\nTouch\nDial", "CC Expression wheel 108"),
    K("MI_CCENCODER_109", "CC 109\nTouch\nDial", "CC Expression wheel 109"),
    K("MI_CCENCODER_110", "CC 110\nTouch\nDial", "CC Expression wheel 110"),
    K("MI_CCENCODER_111", "CC 111\nTouch\nDial", "CC Expression wheel 111"),
    K("MI_CCENCODER_112", "CC 112\nTouch\nDial", "CC Expression wheel 112"),
    K("MI_CCENCODER_113", "CC 113\nTouch\nDial", "CC Expression wheel 113"),
    K("MI_CCENCODER_114", "CC 114\nTouch\nDial", "CC Expression wheel 114"),
    K("MI_CCENCODER_115", "CC 115\nTouch\nDial", "CC Expression wheel 115"),
    K("MI_CCENCODER_116", "CC 116\nTouch\nDial", "CC Expression wheel 116"),
    K("MI_CCENCODER_117", "CC 117\nTouch\nDial", "CC Expression wheel 117"),
    K("MI_CCENCODER_118", "CC 118\nTouch\nDial", "CC Expression wheel 118"),
    K("MI_CCENCODER_119", "CC 119\nTouch\nDial", "CC Expression wheel 119"),
    K("MI_CCENCODER_120", "CC 120\nTouch\nDial", "CC Expression wheel 120"),
    K("MI_CCENCODER_121", "CC 121\nTouch\nDial", "CC Expression wheel 121"),
    K("MI_CCENCODER_122", "CC 122\nTouch\nDial", "CC Expression wheel 122"),
    K("MI_CCENCODER_123", "CC 123\nTouch\nDial", "CC Expression wheel 123"),
    K("MI_CCENCODER_124", "CC 124\nTouch\nDial", "CC Expression wheel 124"),
    K("MI_CCENCODER_125", "CC 125\nTouch\nDial", "CC Expression wheel 125"),
    K("MI_CCENCODER_126", "CC 126\nTouch\nDial", "CC Expression wheel 126"),
    K("MI_CCENCODER_127", "CC 127\nTouch\nDial", "CC Expression wheel 127"),
]

KEYCODES_CC_STEPSIZE = [
    K("CC_STEPSIZE_1", "CC\nIncrement\n1", "SET CC Up/Down TO X1"),
    K("CC_STEPSIZE_2", "CC\nIncrement\n2", "SET CC Up/Down TO X2"),
    K("CC_STEPSIZE_3", "CC\nIncrement\n3", "SET CC Up/Down TO X3"),
    K("CC_STEPSIZE_4", "CC\nIncrement\n4", "SET CC Up/Down TO X4"),
    K("CC_STEPSIZE_5", "CC\nIncrement\n5", "SET CC Up/Down TO X5"),
    K("CC_STEPSIZE_6", "CC\nIncrement\n6", "SET CC Up/Down TO X6"),
    K("CC_STEPSIZE_7", "CC\nIncrement\n7", "SET CC Up/Down TO X7"),
    K("CC_STEPSIZE_8", "CC\nIncrement\n8", "SET CC Up/Down TO X8"),
    K("CC_STEPSIZE_9", "CC\nIncrement\n9", "SET CC Up/Down TO X9"),
    K("CC_STEPSIZE_10", "CC\nIncrement\n10", "SET CC Up/Down TO X10"),
]

KEYCODES_VELOCITY_STEPSIZE = [
    K("MI_VELOCITY_STEPSIZE_1", "Velocity\nIncrement\n1", "SET Velocity Up/Down x1"),
    K("MI_VELOCITY_STEPSIZE_2", "Velocity\nIncrement\n2", "SET Velocity Up/Down TO x2"),
    K("MI_VELOCITY_STEPSIZE_3", "Velocity\nIncrement\n3", "SET Velocity Up/Down TO x3"),
    K("MI_VELOCITY_STEPSIZE_4", "Velocity\nIncrement\n4", "SET Velocity Up/Down TO x4"),
    K("MI_VELOCITY_STEPSIZE_5", "Velocity\nIncrement\n5", "SET Velocity Up/Down TO x5"),
    K("MI_VELOCITY_STEPSIZE_6", "Velocity\nIncrement\n6", "SET Velocity Up/Down TO x6"),
    K("MI_VELOCITY_STEPSIZE_7", "Velocity\nIncrement\n7", "SET Velocity Up/Down TO x7"),
    K("MI_VELOCITY_STEPSIZE_8", "Velocity\nIncrement\n8", "SET Velocity Up/Down TO x8"),
    K("MI_VELOCITY_STEPSIZE_9", "Velocity\nIncrement\n9", "SET Velocity Up/Down TO x9"),
    K("MI_VELOCITY_STEPSIZE_10", "Velocity\nIncrement\n10", "SET Velocity Up/Down TO x10"),
]

KEYCODES_MIDI_SMARTCHORDBUTTONS = [
    K("SMARTCHORD_DOWN", "Smart\nChord\n▼", "QuickChord Down"),
    K("MI_CHORD_99", "Smart\nChord", "Press QuickChord"),
    K("SMARTCHORD_UP", "Smart\nChord\n▲", "QuickChord Up"),
    K("MI_INV_DOWN", "Inversion\nPosition\n▼", "Inv Up"),
    K("MI_INV_UP", "Inversion\nPosition\n▲", "Inv Up"),
    K("COLORBLIND_TOGGLE", "Colorblind\nMode\nOn/Off", "Colorblind"),
    #K("SMARTCHORDCOLOR_TOGGLE", "Smartchord\nRGB\nOn/Off", "Smartchord LEDs Toggle"),
    K("OLED_2", "SmartChord\nRGB\nMode", "Toggle Smartchord Light mode"),
    K("OLED_1", "Screen\nKeyboard\nShift", "Adjust Keyboard Screen"),
    # K("OLED_3", "SmartChord\nPiano\nModes", "Momentarily turn on layer when pressed"),
    
]

KEYCODES_MIDI_CHANNEL_HOLD = [
    K("MI_CHANNEL_HOLD_1", "Hold\nChannel\n1", "Hold for MIDI channel 1, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_2", "Hold\nChannel\n2", "Hold for MIDI channel 2, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_3", "Hold\nChannel\n3", "Hold for MIDI channel 3, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_4", "Hold\nChannel\n4", "Hold for MIDI channel 4, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_5", "Hold\nChannel\n5", "Hold for MIDI channel 5, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_6", "Hold\nChannel\n6", "Hold for MIDI channel 6, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_7", "Hold\nChannel\n7", "Hold for MIDI channel 7, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_8", "Hold\nChannel\n8", "Hold for MIDI channel 8, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_9", "Hold\nChannel\n9", "Hold for MIDI channel 9, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_10", "Hold\nChannel\n10", "Hold for MIDI channel 10, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_11", "Hold\nChannel\n11", "Hold for MIDI channel 11, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_12", "Hold\nChannel\n12", "Hold for MIDI channel 12, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_13", "Hold\nChannel\n13", "Hold for MIDI channel 13, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_14", "Hold\nChannel\n14", "Hold for MIDI channel 14, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_15", "Hold\nChannel\n15", "Hold for MIDI channel 15, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_16", "Hold\nChannel\n16", "Hold for MIDI channel 16, release for default MIDI channel"),
]

KEYCODES_MIDI_CHANNEL_OS = [
    K("MI_CHANNEL_OS_1", "Temporary\nChannel\n1", "Temporary switch to MIDI channel 1"),
    K("MI_CHANNEL_OS_2", "Temporary\nChannel\n2", "Temporary switch to MIDI channel 2"),
    K("MI_CHANNEL_OS_3", "Temporary\nChannel\n3", "Temporary switch to MIDI channel 3"),
    K("MI_CHANNEL_OS_4", "Temporary\nChannel\n4", "Temporary switch to MIDI channel 4"),
    K("MI_CHANNEL_OS_5", "Temporary\nChannel\n5", "Temporary switch to MIDI channel 5"),
    K("MI_CHANNEL_OS_6", "Temporary\nChannel\n6", "Temporary switch to MIDI channel 6"),
    K("MI_CHANNEL_OS_7", "Temporary\nChannel\n7", "Temporary switch to MIDI channel 7"),
    K("MI_CHANNEL_OS_8", "Temporary\nChannel\n8", "Temporary switch to MIDI channel 8"),
    K("MI_CHANNEL_OS_9", "Temporary\nChannel\n9", "Temporary switch to MIDI channel 9"),
    K("MI_CHANNEL_OS_10", "Temporary\nChannel\n10", "Temporary switch to MIDI channel 10"),
    K("MI_CHANNEL_OS_11", "Temporary\nChannel\n11", "Temporary switch to MIDI channel 11"),
    K("MI_CHANNEL_OS_12", "Temporary\nChannel\n12", "Temporary switch to MIDI channel 12"),
    K("MI_CHANNEL_OS_13", "Temporary\nChannel\n13", "Temporary switch to MIDI channel 13"),
    K("MI_CHANNEL_OS_14", "Temporary\nChannel\n14", "Temporary switch to MIDI channel 14"),
    K("MI_CHANNEL_OS_15", "Temporary\nChannel\n15", "Temporary switch to MIDI channel 15"),
    K("MI_CHANNEL_OS_16", "Temporary\nChannel\n16", "Temporary switch to MIDI channel 16"),
]

KEYCODES_MIDI_CHORD_0 = [
K("MI_INV_1", "Minor\n2nd", "Major 2nd"),
K("MI_INV_2", "Major\n2nd", "Minor 2nd"), 
K("MI_INV_3", "Minor\n3rd", "Minor 3rd"),
K("MI_INV_4", "Major\n3rd", "Major 3rd"),
K("MI_INV_5", "Perfect\nFourth", "Perfect Fourth"),
K("MI_INV_6", "Tritone", "Tritone"),
K("MI_INV_7", "Perfect\nFifth", "Perfect 5th"),
K("MI_INV_8", "Minor\n6th", "Minor 6th"),
K("MI_INV_9", "Major\n6th", "Major 6th"),
K("MI_INV_10", "Minor\n7th", "Minor 7th"),
K("MI_INV_11", "Major\n7th", "Major 7th"),
]

KEYCODES_MIDI_CHORD_1 = [
K("MI_CHORD_0", "Major", ""),
K("MI_CHORD_1", "Minor", "m"),
K("MI_CHORD_2", "Diminished", "dim"),
K("MI_CHORD_3", "Augmented", "aug"),
K("MI_CHORD_4", "b5", "b5"),
K("MI_CHORD_5", "Sus2", "sus2"),
K("MI_CHORD_6", "Sus4", "sus4"),
K("MI_CHORD_7", "7 no 3", "7no3"),
K("MI_CHORD_8", "Major 7 no 3", "maj7no3"),
K("MI_CHORD_9", "7 no 5", "7no5"),
K("MI_CHORD_10", "Minor 7 no 5", "m7no5"),
K("MI_CHORD_11", "Major 7 no 5", "maj7no5"),
]

KEYCODES_MIDI_CHORD_2 = [
K("MI_CHORD_12", "Major 6", "6"),
K("MI_CHORD_13", "Minor 6", "m6"), 
K("MI_CHORD_14", "Add2", "add2"),
K("MI_CHORD_15", "Minor Add2", "m(add2)"),
K("MI_CHORD_16", "Add4", "add4"),
K("MI_CHORD_17", "Minor Add4", "m(add4)"),
K("MI_CHORD_18", "7", "7"),
K("MI_CHORD_19", "Major 7", "Maj7"),
K("MI_CHORD_20", "Minor 7", "m7"),
K("MI_CHORD_21", "Minor 7 b5", "m7b5"),
K("MI_CHORD_22", "Diminished 7", "dim7"),
K("MI_CHORD_23", "Minor Major 7", "minMaj7"),
K("MI_CHORD_24", "7 Sus4", "7sus4"),
K("MI_CHORD_25", "Add9", "add9"),
K("MI_CHORD_26", "Minor Add9", "m(add9)"),
K("MI_CHORD_27", "Add11", "add11"),
K("MI_CHORD_28", "Minor Add11", "m(add11)"),
]

KEYCODES_MIDI_CHORD_3 = [
K("MI_CHORD_29", "9", "9"),
K("MI_CHORD_30", "Minor 9", "m9"),
K("MI_CHORD_31", "Major 9", "Maj9"),
K("MI_CHORD_32", "6/9", "6/9"),
K("MI_CHORD_33", "Minor 6/9", "m6/9"),
K("MI_CHORD_34", "7 b9", "7b9"),
K("MI_CHORD_35", "7(11)", "7(11)"),
K("MI_CHORD_36", "7(#11)", "7(#11)"),
K("MI_CHORD_37", "Minor 7(11)", "m7(11)"),
K("MI_CHORD_38", "Major 7(11)", "maj7(11)"),
K("MI_CHORD_39", "Major 7(#11)", "Maj7(#11)"),
K("MI_CHORD_40", "7(13)", "7(13)"),
K("MI_CHORD_41", "Minor 7(13)", "m7(13)"),
K("MI_CHORD_42", "Major 7(13)", "Maj7(13)"),
]

KEYCODES_MIDI_CHORD_4 = [
K("MI_CHORD_43", "11", "11"),
K("MI_CHORD_44", "Minor 11", "m11"),
K("MI_CHORD_45", "Major 11", "Maj11"),
K("MI_CHORD_46", "7(11)(13)", "7(11)(13)"),
K("MI_CHORD_47", "Minor 7(11)(13)", "m7(11)(13)"),
K("MI_CHORD_48", "Major 7(11)(13)", "maj7(11)(13)"),
K("MI_CHORD_49", "9(13)", "9(13)"),
K("MI_CHORD_50", "Minor 9(13)", "m9(13)"),
K("MI_CHORD_51", "Major 9(13)", "maj9(13)"),
K("MI_CHORD_52", "13", "13"),
K("MI_CHORD_53", "Minor 13", "m13"),
K("MI_CHORD_54", "Major 13", "Maj13"),
]

KEYCODES_MIDI_CHORD_5 = [
K("MI_CHORD_55", "7 b9(11)", "7b9(11)"),
K("MI_CHORD_56", "7 Sus2", "7sus2"),
K("MI_CHORD_57", "7 #5", "7#5"),
K("MI_CHORD_58", "7 b5", "7b5"),
K("MI_CHORD_59", "7 #9", "7#9"),
K("MI_CHORD_60", "7 b5 b9", "7b5b9"),
K("MI_CHORD_61", "7 b5 #9", "7b5#9"),
K("MI_CHORD_62", "7 b9(13)", "7b9(13)"),
K("MI_CHORD_63", "7 #9(13)", "7#9(13)"),
K("MI_CHORD_64", "7 #5 b9", "7#5b9"),
K("MI_CHORD_65", "7 #5 #9", "7#5#9"),
K("MI_CHORD_66", "7 b5(11)", "7b5(11)"),
K("MI_CHORD_67", "Major 7 Sus4", "maj7sus4"),
K("MI_CHORD_68", "Major 7 #5", "maj7#5"),
K("MI_CHORD_69", "Major 7 b5", "maj7b5"),
K("MI_CHORD_70", "Minor Major 7(11)", "minMaj7(11)"),
K("MI_CHORD_71", "Add b5", "(addb5)"),
K("MI_CHORD_72", "9 #11", "9#11"),
K("MI_CHORD_73", "9 b5", "9b5"),
K("MI_CHORD_74", "9 #5", "9#5"),
K("MI_CHORD_75", "Minor 9 b5", "m9b5"),
K("MI_CHORD_76", "Minor 9 #11", "m9#11"),
K("MI_CHORD_77", "9 Sus4", "9sus4"),
]

KEYCODES_MIDI_SCALES = [ 
K("MI_CHORD_100", "Major Scale / Ionian", "Major(Ionian)"),
K("MI_CHORD_101", "Dorian Scale", "Dorian"),
K("MI_CHORD_102", "Phrygian Scale", "Phrygian"),
K("MI_CHORD_103", "Lydian Scale", "Lydian"),
K("MI_CHORD_104", "Mixolydian Scale", "Mixolydian"),
K("MI_CHORD_105", "Minor Scale / Aeolian", "Minor(Aeolian)"),
K("MI_CHORD_106", "Locrian Scale", "Locrian"),
K("MI_CHORD_107", "Melodic Minor Scale", "Melodic Minor"),
K("MI_CHORD_108", "Lydian Dominant Scale", "Lydian Dominant"),
K("MI_CHORD_109", "Altered Scale", "Altered Scale"),
K("MI_CHORD_110", "Harmonic Minor Scale", "Harmonic Minor"),
K("MI_CHORD_111", "Major Pentatonic Scale", "Major Pentatonic"),
K("MI_CHORD_112", "Minor Pentatonic Scale", "Minor Pentatonic"),
K("MI_CHORD_113", "Whole Tone Scale", "Whole Tone"),
K("MI_CHORD_114", "Diminished Scale", "Diminished"),
K("MI_CHORD_115", "Blues Scale", "Blues"),
]

    
KEYCODES_MIDI_INVERSION = [
 K ("MI_INVERSION_DEF", "Root \nPosition", "Root Position"),
 K ("MI_INVERSION_1", "1st \nInversion", "1st Inversion"),
 K ("MI_INVERSION_2", "2nd \nInversion", "2nd Inversion"),
 K ("MI_INVERSION_3", "3rd \nInversion", "3rd Inversion"),
 K ("MI_INVERSION_4", "4th \nInversion", "4th Inversion"),
 K ("MI_INVERSION_5", "5th \nInversion", "5th Inversion"),
 K ("MI_INVERSION_6", "6th \nInversion", "6th Inversion"),
]

KEYCODES_RGB_KC_CUSTOM = [
    K("RGB_KC_1", "None", "RGB Mode: None"),
    K("RGB_KC_2", "Solid\nColor", "RGB Mode: Solid Color"),
    K("RGB_KC_3", "Alphas\nMods", "RGB Mode: Alphas Mods"),
    K("RGB_KC_4", "Gradient\nUp Down", "RGB Mode: Gradient Up Down"),
    K("RGB_KC_5", "Gradient\nLeft Right", "RGB Mode: Gradient Left Right"),
    K("RGB_KC_6", "Breathing", "RGB Mode: Breathing"),
    K("RGB_KC_7", "Band SAT", "RGB Mode: Band Saturation"),
    K("RGB_KC_8", "Band VAL", "RGB Mode: Band Brightness"),
    K("RGB_KC_9", "Band\nPinwheel SAT", "RGB Mode: Band Pinwheel Saturation"),
    K("RGB_KC_10", "Band\nPinwheel VAL", "RGB Mode: Band Pinwheel Brightness"),
    K("RGB_KC_11", "Band\nSpiral SAT", "RGB Mode: Band Spiral Saturation"),
    K("RGB_KC_12", "Band\nSpiral VAL", "RGB Mode: Band Spiral Brightness"),
    K("RGB_KC_13", "Cycle\nAll", "RGB Mode: Cycle All"),
    K("RGB_KC_14", "Cycle\nLeft Right", "RGB Mode: Cycle Left Right"),
    K("RGB_KC_15", "Cycle\nUp Down", "RGB Mode: Cycle Up Down"),
    K("RGB_KC_16", "Cycle\nOut In", "RGB Mode: Cycle Out In"),
    K("RGB_KC_17", "Cycle\nOut In Dual", "RGB Mode: Cycle Out In Dual"),
    K("RGB_KC_18", "Rainbow\nMoving\nChevron", "RGB Mode: Rainbow Moving Chevron"),
    K("RGB_KC_19", "Cycle\nPinwheel", "RGB Mode: Cycle Pinwheel"),
    K("RGB_KC_20", "Cycle\nSpiral", "RGB Mode: Cycle Spiral"),
    K("RGB_KC_21", "Dual\nBeacon", "RGB Mode: Dual Beacon"),
    K("RGB_KC_22", "Rainbow\nBeacon", "RGB Mode: Rainbow Beacon"),
    K("RGB_KC_23", "Rainbow\nPinwheels", "RGB Mode: Rainbow Pinwheels"),
    K("RGB_KC_24", "Raindrops", "RGB Mode: Raindrops"),
    K("RGB_KC_25", "Jellybean\nRaindrops", "RGB Mode: Jellybean Raindrops"),
    K("RGB_KC_26", "Hue\nBreathing", "RGB Mode: Hue Breathing"),
    K("RGB_KC_27", "Hue\nPendulum", "RGB Mode: Hue Pendulum"),
    K("RGB_KC_28", "Hue\nWave", "RGB Mode: Hue Wave"),
    K("RGB_KC_29", "Pixel\nFractal", "RGB Mode: Pixel Fractal"),
    K("RGB_KC_30", "Pixel\nFlow", "RGB Mode: Pixel Flow"),
    K("RGB_KC_31", "Pixel\nRain", "RGB Mode: Pixel Rain"),
    K("RGB_KC_32", "Typing\nHeatmap", "RGB Mode: Typing Heatmap"),
    K("RGB_KC_33", "Digital\nRain", "RGB Mode: Digital Rain"),
    K("RGB_KC_34", "Solid\nReactive\nSimple", "RGB Mode: Solid Reactive Simple"),
    K("RGB_KC_35", "Solid\nReactive", "RGB Mode: Solid Reactive"),
    K("RGB_KC_36", "Solid\nReactive\nWide", "RGB Mode: Solid Reactive Wide"),
    K("RGB_KC_37", "Solid\nReactive\nMultiWide", "RGB Mode: Solid Reactive MultiWide"),
    K("RGB_KC_38", "Solid\nReactive\nCross", "RGB Mode: Solid Reactive Cross"),
    K("RGB_KC_39", "Solid\nReactive\nMultiCross", "RGB Mode: Solid Reactive MultiCross"),
    K("RGB_KC_40", "Solid\nReactive\nNexus", "RGB Mode: Solid Reactive Nexus"),
    K("RGB_KC_41", "Solid\nReactive\nMultiNexus", "RGB Mode: Solid Reactive MultiNexus"),
    K("RGB_KC_42", "Splash", "RGB Mode: Splash"),
    K("RGB_KC_43", "MultiSplash", "RGB Mode: MultiSplash"),
    K("RGB_KC_44", "Solid\nSplash", "RGB Mode: Solid Splash"),
    K("RGB_KC_45", "Solid\nMultiSplash", "RGB Mode: Solid MultiSplash"),
    K("RGB_MIDISWITCH", "RGB\nMIDIswitch\nBeta", "RGB Mode: MIDIswitch Beta"),
]

KEYCODES_RGB_KC_CUSTOM2 = [
    K("RGB_LAYERRECORD0", "Record\nRGB\nLyr 0", "Record Lighting Layer 0"),
    K("RGB_LAYERRECORD1", "Record\nRGB\nLyr 1", "Record Lighting Layer 0"),
    K("RGB_LAYERRECORD2", "Record\nRGB\nLyr 2", "Record Lighting Layer 0"),
    K("RGB_LAYERRECORD3", "Record\nRGB\nLyr 3", "Record Lighting Layer 0"),
    K("RGB_LAYERRECORD4", "Record\nRGB\nLyr 4", "Record Lighting Layer 0"),
    K("RGB_LAYERRECORD5", "Record\nRGB\nLyr 5", "Record Lighting Layer 0"),
    K("RGB_LAYERRECORD6", "Record\nRGB\nLyr 6", "Record Lighting Layer 0"),
    K("RGB_LAYERRECORD7", "Record\nRGB\nLyr 7", "Record Lighting Layer 0"),
    K("RGB_LAYERRECORD8", "Record\nRGB\nLyr 8", "Record Lighting Layer 0"),
    K("RGB_LAYERRECORD9", "Record\nRGB\nLyr 9", "Record Lighting Layer 0"),
    K("RGB_LAYERRECORD10", "Record\nRGB\nLyr 10", "Record Lighting Layer 0"),
    K("RGB_LAYERRECORD11", "Record\nRGB\nLyr 11", "Record Lighting Layer 0"),
]

KEYCODES_RGBSAVE = [
    K("RGB_LAYERSAVE", "RGB\nLayer\nMode On", "Save RGB settings"),
    K("RGB_LAYER_CUSTOM", "RGB\nLayer\nMode Off", "Save RGB settings"),
]

KEYCODES_EXWHEEL = [
    K("EXWHEEL_TRA", "Touch\nDial\nTranspose", "Save RGB settings"),
    K("EXWHEEL_VEL", "Touch\nDial\nVelocity", "Save RGB settings"),
    K("EXWHEEL_CHA", "Touch\nDial\nChannel", "Save RGB settings"),
]

KEYCODES_RGB_KC_COLOR = [
    K("RGB_KC_COLOR_1", "Azure", "RGB Color: Azure"),
    K("RGB_KC_COLOR_2", "Black", "RGB Color: Black/Off"),
    K("RGB_KC_COLOR_3", "Blue", "RGB Color: Blue"),
    K("RGB_KC_COLOR_4", "Chartreuse", "RGB Color: Chartreuse"),
    K("RGB_KC_COLOR_5", "Coral", "RGB Color: Coral"),
    K("RGB_KC_COLOR_6", "Cyan", "RGB Color: Cyan"),
    K("RGB_KC_COLOR_7", "Gold", "RGB Color: Gold"),
    K("RGB_KC_COLOR_8", "Goldenrod", "RGB Color: Goldenrod"),
    K("RGB_KC_COLOR_9", "Green", "RGB Color: Green"),
    K("RGB_KC_COLOR_10", "Magenta", "RGB Color: Magenta"),
    K("RGB_KC_COLOR_11", "Orange", "RGB Color: Orange"),
    K("RGB_KC_COLOR_12", "Pink", "RGB Color: Pink"),
    K("RGB_KC_COLOR_13", "Purple", "RGB Color: Purple"),
    K("RGB_KC_COLOR_14", "Red", "RGB Color: Red"),
    K("RGB_KC_COLOR_15", "Spring Green", "RGB Color: Spring Green"),
    K("RGB_KC_COLOR_16", "Teal", "RGB Color: Teal"),
    K("RGB_KC_COLOR_17", "Turquoise", "RGB Color: Turquoise"),
    K("RGB_KC_COLOR_18", "White", "RGB Color: White"),
    K("RGB_KC_COLOR_19", "Yellow", "RGB Color: Yellow")
]

# C KEY - MINOR PROGRESSIONS
KEYCODES_C_CHORDPROG_MINOR = [
    K("C_CHORDPROG1", "i-VII-VI", "The Simple Minor\n(Am-G-F)"),
    K("C_CHORDPROG2", "VI-VII-i", "The Simple Minor Reverse\n(F-G-Am)"),
    K("C_CHORDPROG8", "vi-IV-I-V", "The Axis Progression\n(Am-F-C-G)"),
    K("C_CHORDPROG9", "i-VII-VI-V", "The Andalusian Cadence\n(Am-G-F-E)"),
    K("C_CHORDPROG10", "i-VII-v-VI", "The Sensitive Minor\n(Am-G-Em-F)"),
    K("C_CHORDPROG11", "vi-V-IV-V", "The Eternal Progression\n(Am-G-F-G)"),
    K("C_CHORDPROG24", "vim9-IVmaj7-iim9-V6", "The Smooth Minor 9 Progression\n(Am9-Fmaj7-Dm9-G6)"),
    K("C_CHORDPROG29", "iim7b5-V7-im7", "The Minor ii-V-i\n(Bm7b5-E7-Am7)"),
    K("C_CHORDPROG30", "iim7b5-V7-im7-IVmaj7", "The Minor Jazz Walk\n(Bm7b5-E7-Am7-Dmaj7)"),
    K("C_CHORDPROG31", "im7-IVmaj7-VII7-IIIm7b5", "The Autumnal Progression\n(Am7-Dmaj7-G7-Cm7b5)"),
    K("C_CHORDPROG32", "im7-bVImaj7-bVII7-bIIImaj7", "The Backdoor Progression\n(Am7-Fmaj7-G7-Cmaj7)"),
]

# C KEY - MAJOR PROGRESSIONS
KEYCODES_C_CHORDPROG_MAJOR = [
    K("C_CHORDPROG3", "I-V-vi-IV", "The Classic Four-Chord\n(C-G-Am-F)"),
    K("C_CHORDPROG4", "I-vi-IV-V", "The 50s Progression\n(C-Am-F-G)"),
    K("C_CHORDPROG5", "I-V-vi-iii-IV-I-IV-V", "The Canon Progression\n(C-G-Am-Em-F-C-F-G)"),
    K("C_CHORDPROG6", "I-IV-V", "The Blues Progression\n(C-F-G)"),
    K("C_CHORDPROG7", "I-V-IV-IV", "The Rock Progression\n(C-G-F-F)"),
    K("C_CHORDPROG12", "I-III-IV-iv", "The Creep Progression\n(C-E-F-Fm)"),
    K("C_CHORDPROG13", "I-vi-bVI-V", "The Melancholic Major\n(C-Am-Ab-G)"),
    K("C_CHORDPROG14", "Isus2-vi-IVsus2-V", "The Dreamy Sus Progression\n(Csus2-Am-Fsus2-G)"),
    K("C_CHORDPROG15", "Isus2-IVsus2-vi-V", "The Ambient Float Progression\n(Csus2-Fsus2-Am-G)"),
    K("C_CHORDPROG16", "IVsus2-Vsus4-Isus2-vi", "The Shoegaze Shimmer Progression\n(Fsus2-Gsus4-Csus2-Am)"),
    K("C_CHORDPROG17", "ii7-V7-Imaj7", "The ii-V-I Progression\n(Dm7-G7-Cmaj7)"),
    K("C_CHORDPROG18", "Imaj7-iim7-iiim7-IVmaj7", "The Gentle City Progression\n(Cmaj7-Dm7-Em7-Fmaj7)"),
    K("C_CHORDPROG19", "Imaj7-iim7-vim7-V", "The Smooth Flow\n(Cmaj7-Dm7-Am7-G)"),
    K("C_CHORDPROG20", "IVmaj7-III7-vim7-v7", "The Just The Two Of Us\n(Fmaj7-E7-Am7-Gm7)"),
    K("C_CHORDPROG21", "IVmaj7-V-iiim7-vim7-iim7-III7-vim7-v7", "The Anime Progression\n(Fmaj7-G-Em7-Am7-Dm7-E7-Am7-Gm7)"),
    K("C_CHORDPROG22", "IVmaj7-iiim7-#iii°7-iim7-ii°7-Imaj7", "The Enhanced Urban Sunset\n(Fmaj7-Em7-Ebdim7-Dm7-Dm7b5-Cmaj7)"),
    K("C_CHORDPROG23", "IVmaj7-V7-iiim9-vim7", "The Neo-Pop Turnaround\n(Fmaj7-G7-Em9-Am7)"),
    K("C_CHORDPROG25", "iiim9-Imaj9-vim9-iisus4", "The Contemplative 9th\n(Em9-Cmaj9-Am9-Dsus4)"),
    K("C_CHORDPROG26", "Imaj9-IVmaj9-viiø7-iii7", "The Neo-Soul Cadence\n(Cmaj9-Fmaj9-Bm7b5-Em7)"),
    K("C_CHORDPROG27", "Imaj7-bIII°7-iim7-V7b9-Imaj7", "The Jazz-Pop Passing Progression\n(Cmaj7-Ebdim7-Dm7-G7b9-Cmaj7)"),
    K("C_CHORDPROG28", "iim7-V7/ii-iim7-V7/V-V7sus4-V7-Imaj7", "The Enhanced ii-V-I\n(Dm7-A7b9-Dm7-D7b9-G7sus4-G7-Cmaj7)"),
]

# C# KEY - MINOR PROGRESSIONS
KEYCODES_CS_CHORDPROG_MINOR = [
    K("CS_CHORDPROG1", "i-VII-VI", "The Simple Minor\n(A#m-G#-F#)"),
    K("CS_CHORDPROG2", "VI-VII-i", "The Simple Minor Reverse\n(F#-G#-A#m)"),
    K("CS_CHORDPROG8", "vi-IV-I-V", "The Axis Progression\n(A#m-F#-C#-G#)"),
    K("CS_CHORDPROG9", "i-VII-VI-V", "The Andalusian Cadence\n(A#m-G#-F#-F)"),
    K("CS_CHORDPROG10", "i-VII-v-VI", "The Sensitive Minor\n(A#m-G#-Fm-F#)"),
    K("CS_CHORDPROG11", "vi-V-IV-V", "The Eternal Progression\n(A#m-G#-F#-G#)"),
    K("CS_CHORDPROG24", "vim9-IVmaj7-iim9-V6", "The Smooth Minor 9 Progression\n(A#m9-F#maj7-D#m9-G#6)"),
    K("CS_CHORDPROG29", "iim7b5-V7-im7", "The Minor ii-V-i\n(Cm7b5-F7-A#m7)"),
    K("CS_CHORDPROG30", "iim7b5-V7-im7-IVmaj7", "The Minor Jazz Walk\n(Cm7b5-F7-A#m7-D#maj7)"),
    K("CS_CHORDPROG31", "im7-IVmaj7-VII7-IIIm7b5", "The Autumnal Progression\n(A#m7-D#maj7-G#7-C#m7b5)"),
    K("CS_CHORDPROG32", "im7-bVImaj7-bVII7-bIIImaj7", "The Backdoor Progression\n(A#m7-F#maj7-G#7-C#maj7)"),
]

# C# KEY - MAJOR PROGRESSIONS
KEYCODES_CS_CHORDPROG_MAJOR = [
    K("CS_CHORDPROG3", "I-V-vi-IV", "The Classic Four-Chord\n(C#-G#-A#m-F#)"),
    K("CS_CHORDPROG4", "I-vi-IV-V", "The 50s Progression\n(C#-A#m-F#-G#)"),
    K("CS_CHORDPROG5", "I-V-vi-iii-IV-I-IV-V", "The Canon Progression\n(C#-G#-A#m-Fm-F#-C#-F#-G#)"),
    K("CS_CHORDPROG6", "I-IV-V", "The Blues Progression\n(C#-F#-G#)"),
    K("CS_CHORDPROG7", "I-V-IV-IV", "The Rock Progression\n(C#-G#-F#-F#)"),
    K("CS_CHORDPROG12", "I-III-IV-iv", "The Creep Progression\n(C#-F-F#-F#m)"),
    K("CS_CHORDPROG13", "I-vi-bVI-V", "The Melancholic Major\n(C#-A#m-A-G#)"),
    K("CS_CHORDPROG14", "Isus2-vi-IVsus2-V", "The Dreamy Sus Progression\n(C#sus2-A#m-F#sus2-G#)"),
    K("CS_CHORDPROG15", "Isus2-IVsus2-vi-V", "The Ambient Float Progression\n(C#sus2-F#sus2-A#m-G#)"),
    K("CS_CHORDPROG16", "IVsus2-Vsus4-Isus2-vi", "The Shoegaze Shimmer Progression\n(F#sus2-G#sus4-C#sus2-A#m)"),
    K("CS_CHORDPROG17", "ii7-V7-Imaj7", "The ii-V-I Progression\n(D#m7-G#7-C#maj7)"),
    K("CS_CHORDPROG18", "Imaj7-iim7-iiim7-IVmaj7", "The Gentle City Progression\n(C#maj7-D#m7-Fm7-F#maj7)"),
    K("CS_CHORDPROG19", "Imaj7-iim7-vim7-V", "The Smooth Flow\n(C#maj7-D#m7-A#m7-G#)"),
    K("CS_CHORDPROG20", "IVmaj7-III7-vim7-v7", "The Just The Two Of Us\n(F#maj7-F7-A#m7-G#m7)"),
    K("CS_CHORDPROG21", "IVmaj7-V-iiim7-vim7-iim7-III7-vim7-v7", "The Anime Progression\n(F#maj7-G#-Fm7-A#m7-D#m7-F7-A#m7-G#m7)"),
    K("CS_CHORDPROG22", "IVmaj7-iiim7-#iii°7-iim7-ii°7-Imaj7", "The Enhanced Urban Sunset\n(F#maj7-Fm7-Edim7-D#m7-D#m7b5-C#maj7)"),
    K("CS_CHORDPROG23", "IVmaj7-V7-iiim9-vim7", "The Neo-Pop Turnaround\n(F#maj7-G#7-Fm9-A#m7)"),
    K("CS_CHORDPROG25", "iiim9-Imaj9-vim9-iisus4", "The Contemplative 9th\n(Fm9-C#maj9-A#m9-D#sus4)"),
    K("CS_CHORDPROG26", "Imaj9-IVmaj9-viiø7-iii7", "The Neo-Soul Cadence\n(C#maj9-F#maj9-Cm7b5-Fm7)"),
    K("CS_CHORDPROG27", "Imaj7-bIII°7-iim7-V7b9-Imaj7", "The Jazz-Pop Passing Progression\n(C#maj7-Edim7-D#m7-G#7b9-C#maj7)"),
    K("CS_CHORDPROG28", "iim7-V7/ii-iim7-V7/V-V7sus4-V7-Imaj7", "The Enhanced ii-V-I\n(D#m7-A#7b9-D#m7-D#7b9-G#7sus4-G#7-C#maj7)"),
]

# D KEY - MINOR PROGRESSIONS
KEYCODES_D_CHORDPROG_MINOR = [
    K("D_CHORDPROG1", "i-VII-VI", "The Simple Minor\n(Bm-A-G)"),
    K("D_CHORDPROG2", "VI-VII-i", "The Simple Minor Reverse\n(G-A-Bm)"),
    K("D_CHORDPROG8", "vi-IV-I-V", "The Axis Progression\n(Bm-G-D-A)"),
    K("D_CHORDPROG9", "i-VII-VI-V", "The Andalusian Cadence\n(Bm-A-G-F#)"),
    K("D_CHORDPROG10", "i-VII-v-VI", "The Sensitive Minor\n(Bm-A-F#m-G)"),
    K("D_CHORDPROG11", "vi-V-IV-V", "The Eternal Progression\n(Bm-A-G-A)"),
    K("D_CHORDPROG24", "vim9-IVmaj7-iim9-V6", "The Smooth Minor 9 Progression\n(Bm9-Gmaj7-Em9-A6)"),
    K("D_CHORDPROG29", "iim7b5-V7-im7", "The Minor ii-V-i\n(C#m7b5-F#7-Bm7)"),
    K("D_CHORDPROG30", "iim7b5-V7-im7-IVmaj7", "The Minor Jazz Walk\n(C#m7b5-F#7-Bm7-Emaj7)"),
    K("D_CHORDPROG31", "im7-IVmaj7-VII7-IIIm7b5", "The Autumnal Progression\n(Bm7-Emaj7-A7-Dm7b5)"),
    K("D_CHORDPROG32", "im7-bVImaj7-bVII7-bIIImaj7", "The Backdoor Progression\n(Bm7-Gmaj7-A7-Dmaj7)"),
]

# D KEY - MAJOR PROGRESSIONS
KEYCODES_D_CHORDPROG_MAJOR = [
    K("D_CHORDPROG3", "I-V-vi-IV", "The Classic Four-Chord\n(D-A-Bm-G)"),
    K("D_CHORDPROG4", "I-vi-IV-V", "The 50s Progression\n(D-Bm-G-A)"),
    K("D_CHORDPROG5", "I-V-vi-iii-IV-I-IV-V", "The Canon Progression\n(D-A-Bm-F#m-G-D-G-A)"),
    K("D_CHORDPROG6", "I-IV-V", "The Blues Progression\n(D-G-A)"),
    K("D_CHORDPROG7", "I-V-IV-IV", "The Rock Progression\n(D-A-G-G)"),
    K("D_CHORDPROG12", "I-III-IV-iv", "The Creep Progression\n(D-F#-G-Gm)"),
    K("D_CHORDPROG13", "I-vi-bVI-V", "The Melancholic Major\n(D-Bm-Bb-A)"),
    K("D_CHORDPROG14", "Isus2-vi-IVsus2-V", "The Dreamy Sus Progression\n(Dsus2-Bm-Gsus2-A)"),
    K("D_CHORDPROG15", "Isus2-IVsus2-vi-V", "The Ambient Float Progression\n(Dsus2-Gsus2-Bm-A)"),
    K("D_CHORDPROG16", "IVsus2-Vsus4-Isus2-vi", "The Shoegaze Shimmer Progression\n(Gsus2-Asus4-Dsus2-Bm)"),
    K("D_CHORDPROG17", "ii7-V7-Imaj7", "The ii-V-I Progression\n(Em7-A7-Dmaj7)"),
    K("D_CHORDPROG18", "Imaj7-iim7-iiim7-IVmaj7", "The Gentle City Progression\n(Dmaj7-Em7-F#m7-Gmaj7)"),
    K("D_CHORDPROG19", "Imaj7-iim7-vim7-V", "The Smooth Flow\n(Dmaj7-Em7-Bm7-A)"),
    K("D_CHORDPROG20", "IVmaj7-III7-vim7-v7", "The Just The Two Of Us\n(Gmaj7-F#7-Bm7-Am7)"),
    K("D_CHORDPROG21", "IVmaj7-V-iiim7-vim7-iim7-III7-vim7-v7", "The Anime Progression\n(Gmaj7-A-F#m7-Bm7-Em7-F#7-Bm7-Am7)"),
    K("D_CHORDPROG22", "IVmaj7-iiim7-#iii°7-iim7-ii°7-Imaj7", "The Enhanced Urban Sunset\n(Gmaj7-F#m7-Fdim7-Em7-Em7b5-Dmaj7)"),
    K("D_CHORDPROG23", "IVmaj7-V7-iiim9-vim7", "The Neo-Pop Turnaround\n(Gmaj7-A7-F#m9-Bm7)"),
    K("D_CHORDPROG25", "iiim9-Imaj9-vim9-iisus4", "The Contemplative 9th\n(F#m9-Dmaj9-Bm9-Esus4)"),
    K("D_CHORDPROG26", "Imaj9-IVmaj9-viiø7-iii7", "The Neo-Soul Cadence\n(Dmaj9-Gmaj9-C#m7b5-F#m7)"),
    K("D_CHORDPROG27", "Imaj7-bIII°7-iim7-V7b9-Imaj7", "The Jazz-Pop Passing Progression\n(Dmaj7-Fdim7-Em7-A7b9-Dmaj7)"),
    K("D_CHORDPROG28", "iim7-V7/ii-iim7-V7/V-V7sus4-V7-Imaj7", "The Enhanced ii-V-I\n(Em7-B7b9-Em7-E7b9-A7sus4-A7-Dmaj7)"),
]

# D# KEY - MINOR PROGRESSIONS
KEYCODES_DS_CHORDPROG_MINOR = [
    K("DS_CHORDPROG1", "i-VII-VI", "The Simple Minor\n(Cm-A#-G#)"),
    K("DS_CHORDPROG2", "VI-VII-i", "The Simple Minor Reverse\n(G#-A#-Cm)"),
    K("DS_CHORDPROG8", "vi-IV-I-V", "The Axis Progression\n(Cm-G#-D#-A#)"),
    K("DS_CHORDPROG9", "i-VII-VI-V", "The Andalusian Cadence\n(Cm-A#-G#-G)"),
    K("DS_CHORDPROG10", "i-VII-v-VI", "The Sensitive Minor\n(Cm-A#-Gm-G#)"),
    K("DS_CHORDPROG11", "vi-V-IV-V", "The Eternal Progression\n(Cm-A#-G#-A#)"),
    K("DS_CHORDPROG24", "vim9-IVmaj7-iim9-V6", "The Smooth Minor 9 Progression\n(Cm9-G#maj7-Fm9-A#6)"),
    K("DS_CHORDPROG29", "iim7b5-V7-im7", "The Minor ii-V-i\n(Dm7b5-G7-Cm7)"),
    K("DS_CHORDPROG30", "iim7b5-V7-im7-IVmaj7", "The Minor Jazz Walk\n(Dm7b5-G7-Cm7-Fmaj7)"),
    K("DS_CHORDPROG31", "im7-IVmaj7-VII7-IIIm7b5", "The Autumnal Progression\n(Cm7-Fmaj7-A#7-D#m7b5)"),
    K("DS_CHORDPROG32", "im7-bVImaj7-bVII7-bIIImaj7", "The Backdoor Progression\n(Cm7-G#maj7-A#7-D#maj7)"),
]

# D# KEY - MAJOR PROGRESSIONS
KEYCODES_DS_CHORDPROG_MAJOR = [
    K("DS_CHORDPROG3", "I-V-vi-IV", "The Classic Four-Chord\n(D#-A#-Cm-G#)"),
    K("DS_CHORDPROG4", "I-vi-IV-V", "The 50s Progression\n(D#-Cm-G#-A#)"),
    K("DS_CHORDPROG5", "I-V-vi-iii-IV-I-IV-V", "The Canon Progression\n(D#-A#-Cm-Gm-G#-D#-G#-A#)"),
    K("DS_CHORDPROG6", "I-IV-V", "The Blues Progression\n(D#-G#-A#)"),
    K("DS_CHORDPROG7", "I-V-IV-IV", "The Rock Progression\n(D#-A#-G#-G#)"),
    K("DS_CHORDPROG12", "I-III-IV-iv", "The Creep Progression\n(D#-G-G#-G#m)"),
    K("DS_CHORDPROG13", "I-vi-bVI-V", "The Melancholic Major\n(D#-Cm-B-A#)"),
    K("DS_CHORDPROG14", "Isus2-vi-IVsus2-V", "The Dreamy Sus Progression\n(D#sus2-Cm-G#sus2-A#)"),
    K("DS_CHORDPROG15", "Isus2-IVsus2-vi-V", "The Ambient Float Progression\n(D#sus2-G#sus2-Cm-A#)"),
    K("DS_CHORDPROG16", "IVsus2-Vsus4-Isus2-vi", "The Shoegaze Shimmer Progression\n(G#sus2-A#sus4-D#sus2-Cm)"),
    K("DS_CHORDPROG17", "ii7-V7-Imaj7", "The ii-V-I Progression\n(Fm7-A#7-D#maj7)"),
    K("DS_CHORDPROG18", "Imaj7-iim7-iiim7-IVmaj7", "The Gentle City Progression\n(D#maj7-Fm7-Gm7-G#maj7)"),
    K("DS_CHORDPROG19", "Imaj7-iim7-vim7-V", "The Smooth Flow\n(D#maj7-Fm7-Cm7-A#)"),
    K("DS_CHORDPROG20", "IVmaj7-III7-vim7-v7", "The Just The Two Of Us\n(G#maj7-G7-Cm7-A#m7)"),
    K("DS_CHORDPROG21", "IVmaj7-V-iiim7-vim7-iim7-III7-vim7-v7", "The Anime Progression\n(G#maj7-A#-Gm7-Cm7-Fm7-G7-Cm7-A#m7)"),
    K("DS_CHORDPROG22", "IVmaj7-iiim7-#iii°7-iim7-ii°7-Imaj7", "The Enhanced Urban Sunset\n(G#maj7-Gm7-F#dim7-Fm7-Fm7b5-D#maj7)"),
    K("DS_CHORDPROG23", "IVmaj7-V7-iiim9-vim7", "The Neo-Pop Turnaround\n(G#maj7-A#7-Gm9-Cm7)"),
    K("DS_CHORDPROG25", "iiim9-Imaj9-vim9-iisus4", "The Contemplative 9th\n(Gm9-D#maj9-Cm9-Fsus4)"),
    K("DS_CHORDPROG26", "Imaj9-IVmaj9-viiø7-iii7", "The Neo-Soul Cadence\n(D#maj9-G#maj9-Dm7b5-Gm7)"),
    K("DS_CHORDPROG27", "Imaj7-bIII°7-iim7-V7b9-Imaj7", "The Jazz-Pop Passing Progression\n(D#maj7-F#dim7-Fm7-A#7b9-D#maj7)"),
    K("DS_CHORDPROG28", "iim7-V7/ii-iim7-V7/V-V7sus4-V7-Imaj7", "The Enhanced ii-V-I\n(Fm7-C7b9-Fm7-F7b9-A#7sus4-A#7-D#maj7)"),
]

# E KEY - MINOR PROGRESSIONS
KEYCODES_E_CHORDPROG_MINOR = [
    K("E_CHORDPROG1", "i-VII-VI", "The Simple Minor\n(C#m-B-A)"),
    K("E_CHORDPROG2", "VI-VII-i", "The Simple Minor Reverse\n(A-B-C#m)"),
    K("E_CHORDPROG8", "vi-IV-I-V", "The Axis Progression\n(C#m-A-E-B)"),
    K("E_CHORDPROG9", "i-VII-VI-V", "The Andalusian Cadence\n(C#m-B-A-G#)"),
    K("E_CHORDPROG10", "i-VII-v-VI", "The Sensitive Minor\n(C#m-B-G#m-A)"),
    K("E_CHORDPROG11", "vi-V-IV-V", "The Eternal Progression\n(C#m-B-A-B)"),
    K("E_CHORDPROG24", "vim9-IVmaj7-iim9-V6", "The Smooth Minor 9 Progression\n(C#m9-Amaj7-F#m9-B6)"),
    K("E_CHORDPROG29", "iim7b5-V7-im7", "The Minor ii-V-i\n(D#m7b5-G#7-C#m7)"),
    K("E_CHORDPROG30", "iim7b5-V7-im7-IVmaj7", "The Minor Jazz Walk\n(D#m7b5-G#7-C#m7-F#maj7)"),
    K("E_CHORDPROG31", "im7-IVmaj7-VII7-IIIm7b5", "The Autumnal Progression\n(C#m7-F#maj7-B7-Em7b5)"),
    K("E_CHORDPROG32", "im7-bVImaj7-bVII7-bIIImaj7", "The Backdoor Progression\n(C#m7-Amaj7-B7-Emaj7)"),
]

# E KEY - MAJOR PROGRESSIONS
KEYCODES_E_CHORDPROG_MAJOR = [
    K("E_CHORDPROG3", "I-V-vi-IV", "The Classic Four-Chord\n(E-B-C#m-A)"),
    K("E_CHORDPROG4", "I-vi-IV-V", "The 50s Progression\n(E-C#m-A-B)"),
    K("E_CHORDPROG5", "I-V-vi-iii-IV-I-IV-V", "The Canon Progression\n(E-B-C#m-G#m-A-E-A-B)"),
    K("E_CHORDPROG6", "I-IV-V", "The Blues Progression\n(E-A-B)"),
    K("E_CHORDPROG7", "I-V-IV-IV", "The Rock Progression\n(E-B-A-A)"),
    K("E_CHORDPROG12", "I-III-IV-iv", "The Creep Progression\n(E-G#-A-Am)"),
    K("E_CHORDPROG13", "I-vi-bVI-V", "The Melancholic Major\n(E-C#m-C-B)"),
    K("E_CHORDPROG14", "Isus2-vi-IVsus2-V", "The Dreamy Sus Progression\n(Esus2-C#m-Asus2-B)"),
    K("E_CHORDPROG15", "Isus2-IVsus2-vi-V", "The Ambient Float Progression\n(Esus2-Asus2-C#m-B)"),
    K("E_CHORDPROG16", "IVsus2-Vsus4-Isus2-vi", "The Shoegaze Shimmer Progression\n(Asus2-Bsus4-Esus2-C#m)"),
    K("E_CHORDPROG17", "ii7-V7-Imaj7", "The ii-V-I Progression\n(F#m7-B7-Emaj7)"),
    K("E_CHORDPROG18", "Imaj7-iim7-iiim7-IVmaj7", "The Gentle City Progression\n(Emaj7-F#m7-G#m7-Amaj7)"),
    K("E_CHORDPROG19", "Imaj7-iim7-vim7-V", "The Smooth Flow\n(Emaj7-F#m7-C#m7-B)"),
    K("E_CHORDPROG20", "IVmaj7-III7-vim7-v7", "The Just The Two Of Us\n(Amaj7-G#7-C#m7-Bm7)"),
    K("E_CHORDPROG21", "IVmaj7-V-iiim7-vim7-iim7-III7-vim7-v7", "The Anime Progression\n(Amaj7-B-G#m7-C#m7-F#m7-G#7-C#m7-Bm7)"),
    K("E_CHORDPROG22", "IVmaj7-iiim7-#iii°7-iim7-ii°7-Imaj7", "The Enhanced Urban Sunset\n(Amaj7-G#m7-Gdim7-F#m7-F#m7b5-Emaj7)"),
    K("E_CHORDPROG23", "IVmaj7-V7-iiim9-vim7", "The Neo-Pop Turnaround\n(Amaj7-B7-G#m9-C#m7)"),
    K("E_CHORDPROG25", "iiim9-Imaj9-vim9-iisus4", "The Contemplative 9th\n(G#m9-Emaj9-C#m9-F#sus4)"),
    K("E_CHORDPROG26", "Imaj9-IVmaj9-viiø7-iii7", "The Neo-Soul Cadence\n(Emaj9-Amaj9-D#m7b5-G#m7)"),
    K("E_CHORDPROG27", "Imaj7-bIII°7-iim7-V7b9-Imaj7", "The Jazz-Pop Passing Progression\n(Emaj7-Gdim7-F#m7-B7b9-Emaj7)"),
    K("E_CHORDPROG28", "iim7-V7/ii-iim7-V7/V-V7sus4-V7-Imaj7", "The Enhanced ii-V-I\n(F#m7-C#7b9-F#m7-F#7b9-B7sus4-B7-Emaj7)"),
]

# F KEY - MINOR PROGRESSIONS
KEYCODES_F_CHORDPROG_MINOR = [
    K("F_CHORDPROG1", "i-VII-VI", "The Simple Minor\n(Dm-C-A#)"),
    K("F_CHORDPROG2", "VI-VII-i", "The Simple Minor Reverse\n(A#-C-Dm)"),
    K("F_CHORDPROG8", "vi-IV-I-V", "The Axis Progression\n(Dm-A#-F-C)"),
    K("F_CHORDPROG9", "i-VII-VI-V", "The Andalusian Cadence\n(Dm-C-A#-A)"),
    K("F_CHORDPROG10", "i-VII-v-VI", "The Sensitive Minor\n(Dm-C-Am-A#)"),
    K("F_CHORDPROG11", "vi-V-IV-V", "The Eternal Progression\n(Dm-C-A#-C)"),
    K("F_CHORDPROG24", "vim9-IVmaj7-iim9-V6", "The Smooth Minor 9 Progression\n(Dm9-A#maj7-Gm9-C6)"),
    K("F_CHORDPROG29", "iim7b5-V7-im7", "The Minor ii-V-i\n(Em7b5-A7-Dm7)"),
    K("F_CHORDPROG30", "iim7b5-V7-im7-IVmaj7", "The Minor Jazz Walk\n(Em7b5-A7-Dm7-Gmaj7)"),
    K("F_CHORDPROG31", "im7-IVmaj7-VII7-IIIm7b5", "The Autumnal Progression\n(Dm7-Gmaj7-C7-Fm7b5)"),
    K("F_CHORDPROG32", "im7-bVImaj7-bVII7-bIIImaj7", "The Backdoor Progression\n(Dm7-A#maj7-C7-Fmaj7)"),
]

# F KEY - MAJOR PROGRESSIONS
KEYCODES_F_CHORDPROG_MAJOR = [
    K("F_CHORDPROG3", "I-V-vi-IV", "The Classic Four-Chord\n(F-C-Dm-A#)"),
    K("F_CHORDPROG4", "I-vi-IV-V", "The 50s Progression\n(F-Dm-A#-C)"),
    K("F_CHORDPROG5", "I-V-vi-iii-IV-I-IV-V", "The Canon Progression\n(F-C-Dm-Am-A#-F-A#-C)"),
    K("F_CHORDPROG6", "I-IV-V", "The Blues Progression\n(F-A#-C)"),
    K("F_CHORDPROG7", "I-V-IV-IV", "The Rock Progression\n(F-C-A#-A#)"),
    K("F_CHORDPROG12", "I-III-IV-iv", "The Creep Progression\n(F-A-A#-A#m)"),
    K("F_CHORDPROG13", "I-vi-bVI-V", "The Melancholic Major\n(F-Dm-C#-C)"),
    K("F_CHORDPROG14", "Isus2-vi-IVsus2-V", "The Dreamy Sus Progression\n(Fsus2-Dm-A#sus2-C)"),
    K("F_CHORDPROG15", "Isus2-IVsus2-vi-V", "The Ambient Float Progression\n(Fsus2-A#sus2-Dm-C)"),
    K("F_CHORDPROG16", "IVsus2-Vsus4-Isus2-vi", "The Shoegaze Shimmer Progression\n(A#sus2-Csus4-Fsus2-Dm)"),
    K("F_CHORDPROG17", "ii7-V7-Imaj7", "The ii-V-I Progression\n(Gm7-C7-Fmaj7)"),
    K("F_CHORDPROG18", "Imaj7-iim7-iiim7-IVmaj7", "The Gentle City Progression\n(Fmaj7-Gm7-Am7-A#maj7)"),
    K("F_CHORDPROG19", "Imaj7-iim7-vim7-V", "The Smooth Flow\n(Fmaj7-Gm7-Dm7-C)"),
    K("F_CHORDPROG20", "IVmaj7-III7-vim7-v7", "The Just The Two Of Us\n(A#maj7-A7-Dm7-Cm7)"),
    K("F_CHORDPROG21", "IVmaj7-V-iiim7-vim7-iim7-III7-vim7-v7", "The Anime Progression\n(A#maj7-C-Am7-Dm7-Gm7-A7-Dm7-Cm7)"),
    K("F_CHORDPROG22", "IVmaj7-iiim7-#iii°7-iim7-ii°7-Imaj7", "The Enhanced Urban Sunset\n(A#maj7-Am7-G#dim7-Gm7-Gm7b5-Fmaj7)"),
    K("F_CHORDPROG23", "IVmaj7-V7-iiim9-vim7", "The Neo-Pop Turnaround\n(A#maj7-C7-Am9-Dm7)"),
    K("F_CHORDPROG25", "iiim9-Imaj9-vim9-iisus4", "The Contemplative 9th\n(Am9-Fmaj9-Dm9-Gsus4)"),
    K("F_CHORDPROG26", "Imaj9-IVmaj9-viiø7-iii7", "The Neo-Soul Cadence\n(Fmaj9-A#maj9-Em7b5-Am7)"),
    K("F_CHORDPROG27", "Imaj7-bIII°7-iim7-V7b9-Imaj7", "The Jazz-Pop Passing Progression\n(Fmaj7-G#dim7-Gm7-C7b9-Fmaj7)"),
    K("F_CHORDPROG28", "iim7-V7/ii-iim7-V7/V-V7sus4-V7-Imaj7", "The Enhanced ii-V-I\n(Gm7-D7b9-Gm7-G7b9-C7sus4-C7-Fmaj7)"),
]

# F# KEY - MINOR PROGRESSIONS
KEYCODES_FS_CHORDPROG_MINOR = [
    K("FS_CHORDPROG1", "i-VII-VI", "The Simple Minor\n(D#m-C#-B)"),
    K("FS_CHORDPROG2", "VI-VII-i", "The Simple Minor Reverse\n(B-C#-D#m)"),
    K("FS_CHORDPROG8", "vi-IV-I-V", "The Axis Progression\n(D#m-B-F#-C#)"),
    K("FS_CHORDPROG9", "i-VII-VI-V", "The Andalusian Cadence\n(D#m-C#-B-A#)"),
    K("FS_CHORDPROG10", "i-VII-v-VI", "The Sensitive Minor\n(D#m-C#-A#m-B)"),
    K("FS_CHORDPROG11", "vi-V-IV-V", "The Eternal Progression\n(D#m-C#-B-C#)"),
    K("FS_CHORDPROG24", "vim9-IVmaj7-iim9-V6", "The Smooth Minor 9 Progression\n(D#m9-Bmaj7-G#m9-C#6)"),
    K("FS_CHORDPROG29", "iim7b5-V7-im7", "The Minor ii-V-i\n(Fm7b5-A#7-D#m7)"),
    K("FS_CHORDPROG30", "iim7b5-V7-im7-IVmaj7", "The Minor Jazz Walk\n(Fm7b5-A#7-D#m7-G#maj7)"),
    K("FS_CHORDPROG31", "im7-IVmaj7-VII7-IIIm7b5", "The Autumnal Progression\n(D#m7-G#maj7-C#7-F#m7b5)"),
    K("FS_CHORDPROG32", "im7-bVImaj7-bVII7-bIIImaj7", "The Backdoor Progression\n(D#m7-Bmaj7-C#7-F#maj7)"),
]

# F# KEY - MAJOR PROGRESSIONS
KEYCODES_FS_CHORDPROG_MAJOR = [
    K("FS_CHORDPROG3", "I-V-vi-IV", "The Classic Four-Chord\n(F#-C#-D#m-B)"),
    K("FS_CHORDPROG4", "I-vi-IV-V", "The 50s Progression\n(F#-D#m-B-C#)"),
    K("FS_CHORDPROG5", "I-V-vi-iii-IV-I-IV-V", "The Canon Progression\n(F#-C#-D#m-A#m-B-F#-B-C#)"),
    K("FS_CHORDPROG6", "I-IV-V", "The Blues Progression\n(F#-B-C#)"),
    K("FS_CHORDPROG7", "I-V-IV-IV", "The Rock Progression\n(F#-C#-B-B)"),
    K("FS_CHORDPROG12", "I-III-IV-iv", "The Creep Progression\n(F#-A#-B-Bm)"),
    K("FS_CHORDPROG13", "I-vi-bVI-V", "The Melancholic Major\n(F#-D#m-D-C#)"),
    K("FS_CHORDPROG14", "Isus2-vi-IVsus2-V", "The Dreamy Sus Progression\n(F#sus2-D#m-Bsus2-C#)"),
    K("FS_CHORDPROG15", "Isus2-IVsus2-vi-V", "The Ambient Float Progression\n(F#sus2-Bsus2-D#m-C#)"),
    K("FS_CHORDPROG16", "IVsus2-Vsus4-Isus2-vi", "The Shoegaze Shimmer Progression\n(Bsus2-C#sus4-F#sus2-D#m)"),
    K("FS_CHORDPROG17", "ii7-V7-Imaj7", "The ii-V-I Progression\n(G#m7-C#7-F#maj7)"),
    K("FS_CHORDPROG18", "Imaj7-iim7-iiim7-IVmaj7", "The Gentle City Progression\n(F#maj7-G#m7-A#m7-Bmaj7)"),
    K("FS_CHORDPROG19", "Imaj7-iim7-vim7-V", "The Smooth Flow\n(F#maj7-G#m7-D#m7-C#)"),
    K("FS_CHORDPROG20", "IVmaj7-III7-vim7-v7", "The Just The Two Of Us\n(Bmaj7-A#7-D#m7-C#m7)"),
    K("FS_CHORDPROG21", "IVmaj7-V-iiim7-vim7-iim7-III7-vim7-v7", "The Anime Progression\n(Bmaj7-C#-A#m7-D#m7-G#m7-A#7-D#m7-C#m7)"),
    K("FS_CHORDPROG22", "IVmaj7-iiim7-#iii°7-iim7-ii°7-Imaj7", "The Enhanced Urban Sunset\n(Bmaj7-A#m7-Adim7-G#m7-G#m7b5-F#maj7)"),
    K("FS_CHORDPROG23", "IVmaj7-V7-iiim9-vim7", "The Neo-Pop Turnaround\n(Bmaj7-C#7-A#m9-D#m7)"),
    K("FS_CHORDPROG25", "iiim9-Imaj9-vim9-iisus4", "The Contemplative 9th\n(A#m9-F#maj9-D#m9-G#sus4)"),
    K("FS_CHORDPROG26", "Imaj9-IVmaj9-viiø7-iii7", "The Neo-Soul Cadence\n(F#maj9-Bmaj9-Fm7b5-A#m7)"),
    K("FS_CHORDPROG27", "Imaj7-bIII°7-iim7-V7b9-Imaj7", "The Jazz-Pop Passing Progression\n(F#maj7-Adim7-G#m7-C#7b9-F#maj7)"),
    K("FS_CHORDPROG28", "iim7-V7/ii-iim7-V7/V-V7sus4-V7-Imaj7", "The Enhanced ii-V-I\n(G#m7-D#7b9-G#m7-G#7b9-C#7sus4-C#7-F#maj7)"),
]

# G KEY - MINOR PROGRESSIONS
KEYCODES_G_CHORDPROG_MINOR = [
    K("G_CHORDPROG1", "i-VII-VI", "The Simple Minor\n(Em-D-C)"),
    K("G_CHORDPROG2", "VI-VII-i", "The Simple Minor Reverse\n(C-D-Em)"),
    K("G_CHORDPROG8", "vi-IV-I-V", "The Axis Progression\n(Em-C-G-D)"),
    K("G_CHORDPROG9", "i-VII-VI-V", "The Andalusian Cadence\n(Em-D-C-B)"),
    K("G_CHORDPROG10", "i-VII-v-VI", "The Sensitive Minor\n(Em-D-Bm-C)"),
    K("G_CHORDPROG11", "vi-V-IV-V", "The Eternal Progression\n(Em-D-C-D)"),
    K("G_CHORDPROG24", "vim9-IVmaj7-iim9-V6", "The Smooth Minor 9 Progression\n(Em9-Cmaj7-Am9-D6)"),
    K("G_CHORDPROG29", "iim7b5-V7-im7", "The Minor ii-V-i\n(F#m7b5-B7-Em7)"),
    K("G_CHORDPROG30", "iim7b5-V7-im7-IVmaj7", "The Minor Jazz Walk\n(F#m7b5-B7-Em7-Amaj7)"),
    K("G_CHORDPROG31", "im7-IVmaj7-VII7-IIIm7b5", "The Autumnal Progression\n(Em7-Amaj7-D7-Gm7b5)"),
    K("G_CHORDPROG32", "im7-bVImaj7-bVII7-bIIImaj7", "The Backdoor Progression\n(Em7-Cmaj7-D7-Gmaj7)"),
]

# G KEY - MAJOR PROGRESSIONS
KEYCODES_G_CHORDPROG_MAJOR = [
    K("G_CHORDPROG3", "I-V-vi-IV", "The Classic Four-Chord\n(G-D-Em-C)"),
    K("G_CHORDPROG4", "I-vi-IV-V", "The 50s Progression\n(G-Em-C-D)"),
    K("G_CHORDPROG5", "I-V-vi-iii-IV-I-IV-V", "The Canon Progression\n(G-D-Em-Bm-C-G-C-D)"),
    K("G_CHORDPROG6", "I-IV-V", "The Blues Progression\n(G-C-D)"),
    K("G_CHORDPROG7", "I-V-IV-IV", "The Rock Progression\n(G-D-C-C)"),
    K("G_CHORDPROG12", "I-III-IV-iv", "The Creep Progression\n(G-B-C-Cm)"),
    K("G_CHORDPROG13", "I-vi-bVI-V", "The Melancholic Major\n(G-Em-Eb-D)"),
    K("G_CHORDPROG14", "Isus2-vi-IVsus2-V", "The Dreamy Sus Progression\n(Gsus2-Em-Csus2-D)"),
    K("G_CHORDPROG15", "Isus2-IVsus2-vi-V", "The Ambient Float Progression\n(Gsus2-Csus2-Em-D)"),
    K("G_CHORDPROG16", "IVsus2-Vsus4-Isus2-vi", "The Shoegaze Shimmer Progression\n(Csus2-Dsus4-Gsus2-Em)"),
    K("G_CHORDPROG17", "ii7-V7-Imaj7", "The ii-V-I Progression\n(Am7-D7-Gmaj7)"),
    K("G_CHORDPROG18", "Imaj7-iim7-iiim7-IVmaj7", "The Gentle City Progression\n(Gmaj7-Am7-Bm7-Cmaj7)"),
    K("G_CHORDPROG19", "Imaj7-iim7-vim7-V", "The Smooth Flow\n(Gmaj7-Am7-Em7-D)"),
    K("G_CHORDPROG20", "IVmaj7-III7-vim7-v7", "The Just The Two Of Us\n(Cmaj7-B7-Em7-Dm7)"),
    K("G_CHORDPROG21", "IVmaj7-V-iiim7-vim7-iim7-III7-vim7-v7", "The Anime Progression\n(Cmaj7-D-Bm7-Em7-Am7-B7-Em7-Dm7)"),
    K("G_CHORDPROG22", "IVmaj7-iiim7-#iii°7-iim7-ii°7-Imaj7", "The Enhanced Urban Sunset\n(Cmaj7-Bm7-Bbdim7-Am7-Am7b5-Gmaj7)"),
    K("G_CHORDPROG23", "IVmaj7-V7-iiim9-vim7", "The Neo-Pop Turnaround\n(Cmaj7-D7-Bm9-Em7)"),
    K("G_CHORDPROG25", "iiim9-Imaj9-vim9-iisus4", "The Contemplative 9th\n(Bm9-Gmaj9-Em9-Asus4)"),
    K("G_CHORDPROG26", "Imaj9-IVmaj9-viiø7-iii7", "The Neo-Soul Cadence\n(Gmaj9-Cmaj9-F#m7b5-Bm7)"),
    K("G_CHORDPROG27", "Imaj7-bIII°7-iim7-V7b9-Imaj7", "The Jazz-Pop Passing Progression\n(Gmaj7-Bbdim7-Am7-D7b9-Gmaj7)"),
    K("G_CHORDPROG28", "iim7-V7/ii-iim7-V7/V-V7sus4-V7-Imaj7", "The Enhanced ii-V-I\n(Am7-E7b9-Am7-A7b9-D7sus4-D7-Gmaj7)"),
]

# G# KEY - MINOR PROGRESSIONS
KEYCODES_GS_CHORDPROG_MINOR = [
    K("GS_CHORDPROG1", "i-VII-VI", "The Simple Minor\n(Fm-D#-C#)"),
    K("GS_CHORDPROG2", "VI-VII-i", "The Simple Minor Reverse\n(C#-D#-Fm)"),
    K("GS_CHORDPROG8", "vi-IV-I-V", "The Axis Progression\n(Fm-C#-G#-D#)"),
    K("GS_CHORDPROG9", "i-VII-VI-V", "The Andalusian Cadence\n(Fm-D#-C#-C)"),
    K("GS_CHORDPROG10", "i-VII-v-VI", "The Sensitive Minor\n(Fm-D#-Cm-C#)"),
    K("GS_CHORDPROG11", "vi-V-IV-V", "The Eternal Progression\n(Fm-D#-C#-D#)"),
    K("GS_CHORDPROG24", "vim9-IVmaj7-iim9-V6", "The Smooth Minor 9 Progression\n(Fm9-C#maj7-A#m9-D#6)"),
    K("GS_CHORDPROG29", "iim7b5-V7-im7", "The Minor ii-V-i\n(Gm7b5-C7-Fm7)"),
    K("GS_CHORDPROG30", "iim7b5-V7-im7-IVmaj7", "The Minor Jazz Walk\n(Gm7b5-C7-Fm7-A#maj7)"),
    K("GS_CHORDPROG31", "im7-IVmaj7-VII7-IIIm7b5", "The Autumnal Progression\n(Fm7-A#maj7-D#7-G#m7b5)"),
    K("GS_CHORDPROG32", "im7-bVImaj7-bVII7-bIIImaj7", "The Backdoor Progression\n(Fm7-C#maj7-D#7-G#maj7)"),
]

# G# KEY - MAJOR PROGRESSIONS
KEYCODES_GS_CHORDPROG_MAJOR = [
    K("GS_CHORDPROG3", "I-V-vi-IV", "The Classic Four-Chord\n(G#-D#-Fm-C#)"),
    K("GS_CHORDPROG4", "I-vi-IV-V", "The 50s Progression\n(G#-Fm-C#-D#)"),
    K("GS_CHORDPROG5", "I-V-vi-iii-IV-I-IV-V", "The Canon Progression\n(G#-D#-Fm-Cm-C#-G#-C#-D#)"),
    K("GS_CHORDPROG6", "I-IV-V", "The Blues Progression\n(G#-C#-D#)"),
    K("GS_CHORDPROG7", "I-V-IV-IV", "The Rock Progression\n(G#-D#-C#-C#)"),
    K("GS_CHORDPROG12", "I-III-IV-iv", "The Creep Progression\n(G#-C-C#-C#m)"),
    K("GS_CHORDPROG13", "I-vi-bVI-V", "The Melancholic Major\n(G#-Fm-E-D#)"),
    K("GS_CHORDPROG14", "Isus2-vi-IVsus2-V", "The Dreamy Sus Progression\n(G#sus2-Fm-C#sus2-D#)"),
    K("GS_CHORDPROG15", "Isus2-IVsus2-vi-V", "The Ambient Float Progression\n(G#sus2-C#sus2-Fm-D#)"),
    K("GS_CHORDPROG16", "IVsus2-Vsus4-Isus2-vi", "The Shoegaze Shimmer Progression\n(C#sus2-D#sus4-G#sus2-Fm)"),
    K("GS_CHORDPROG17", "ii7-V7-Imaj7", "The ii-V-I Progression\n(A#m7-D#7-G#maj7)"),
    K("GS_CHORDPROG18", "Imaj7-iim7-iiim7-IVmaj7", "The Gentle City Progression\n(G#maj7-A#m7-Cm7-C#maj7)"),
    K("GS_CHORDPROG19", "Imaj7-iim7-vim7-V", "The Smooth Flow\n(G#maj7-A#m7-Fm7-D#)"),
    K("GS_CHORDPROG20", "IVmaj7-III7-vim7-v7", "The Just The Two Of Us\n(C#maj7-C7-Fm7-D#m7)"),
    K("GS_CHORDPROG21", "IVmaj7-V-iiim7-vim7-iim7-III7-vim7-v7", "The Anime Progression\n(C#maj7-D#-Cm7-Fm7-A#m7-C7-Fm7-D#m7)"),
    K("GS_CHORDPROG22", "IVmaj7-iiim7-#iii°7-iim7-ii°7-Imaj7", "The Enhanced Urban Sunset\n(C#maj7-Cm7-Bdim7-A#m7-A#m7b5-G#maj7)"),
    K("GS_CHORDPROG23", "IVmaj7-V7-iiim9-vim7", "The Neo-Pop Turnaround\n(C#maj7-D#7-Cm9-Fm7)"),
    K("GS_CHORDPROG25", "iiim9-Imaj9-vim9-iisus4", "The Contemplative 9th\n(Cm9-G#maj9-Fm9-A#sus4)"),
    K("GS_CHORDPROG26", "Imaj9-IVmaj9-viiø7-iii7", "The Neo-Soul Cadence\n(G#maj9-C#maj9-Gm7b5-Cm7)"),
    K("GS_CHORDPROG27", "Imaj7-bIII°7-iim7-V7b9-Imaj7", "The Jazz-Pop Passing Progression\n(G#maj7-Bdim7-A#m7-D#7b9-G#maj7)"),
    K("GS_CHORDPROG28", "iim7-V7/ii-iim7-V7/V-V7sus4-V7-Imaj7", "The Enhanced ii-V-I\n(A#m7-F7b9-A#m7-A#7b9-D#7sus4-D#7-G#maj7)"),
]

# A KEY - MINOR PROGRESSIONS
KEYCODES_A_CHORDPROG_MINOR = [
    K("A_CHORDPROG1", "i-VII-VI", "The Simple Minor\n(F#m-E-D)"),
    K("A_CHORDPROG2", "VI-VII-i", "The Simple Minor Reverse\n(D-E-F#m)"),
    K("A_CHORDPROG8", "vi-IV-I-V", "The Axis Progression\n(F#m-D-A-E)"),
    K("A_CHORDPROG9", "i-VII-VI-V", "The Andalusian Cadence\n(F#m-E-D-C#)"),
    K("A_CHORDPROG10", "i-VII-v-VI", "The Sensitive Minor\n(F#m-E-C#m-D)"),
    K("A_CHORDPROG11", "vi-V-IV-V", "The Eternal Progression\n(F#m-E-D-E)"),
    K("A_CHORDPROG24", "vim9-IVmaj7-iim9-V6", "The Smooth Minor 9 Progression\n(F#m9-Dmaj7-Bm9-E6)"),
    K("A_CHORDPROG29", "iim7b5-V7-im7", "The Minor ii-V-i\n(G#m7b5-C#7-F#m7)"),
    K("A_CHORDPROG30", "iim7b5-V7-im7-IVmaj7", "The Minor Jazz Walk\n(G#m7b5-C#7-F#m7-Bmaj7)"),
    K("A_CHORDPROG31", "im7-IVmaj7-VII7-IIIm7b5", "The Autumnal Progression\n(F#m7-Bmaj7-E7-Am7b5)"),
    K("A_CHORDPROG32", "im7-bVImaj7-bVII7-bIIImaj7", "The Backdoor Progression\n(F#m7-Dmaj7-E7-Amaj7)"),
]

# A KEY - MAJOR PROGRESSIONS
KEYCODES_A_CHORDPROG_MAJOR = [
    K("A_CHORDPROG3", "I-V-vi-IV", "The Classic Four-Chord\n(A-E-F#m-D)"),
    K("A_CHORDPROG4", "I-vi-IV-V", "The 50s Progression\n(A-F#m-D-E)"),
    K("A_CHORDPROG5", "I-V-vi-iii-IV-I-IV-V", "The Canon Progression\n(A-E-F#m-C#m-D-A-D-E)"),
    K("A_CHORDPROG6", "I-IV-V", "The Blues Progression\n(A-D-E)"),
    K("A_CHORDPROG7", "I-V-IV-IV", "The Rock Progression\n(A-E-D-D)"),
    K("A_CHORDPROG12", "I-III-IV-iv", "The Creep Progression\n(A-C#-D-Dm)"),
    K("A_CHORDPROG13", "I-vi-bVI-V", "The Melancholic Major\n(A-F#m-F-E)"),
    K("A_CHORDPROG14", "Isus2-vi-IVsus2-V", "The Dreamy Sus Progression\n(Asus2-F#m-Dsus2-E)"),
    K("A_CHORDPROG15", "Isus2-IVsus2-vi-V", "The Ambient Float Progression\n(Asus2-Dsus2-F#m-E)"),
    K("A_CHORDPROG16", "IVsus2-Vsus4-Isus2-vi", "The Shoegaze Shimmer Progression\n(Dsus2-Esus4-Asus2-F#m)"),
    K("A_CHORDPROG17", "ii7-V7-Imaj7", "The ii-V-I Progression\n(Bm7-E7-Amaj7)"),
    K("A_CHORDPROG18", "Imaj7-iim7-iiim7-IVmaj7", "The Gentle City Progression\n(Amaj7-Bm7-C#m7-Dmaj7)"),
    K("A_CHORDPROG19", "Imaj7-iim7-vim7-V", "The Smooth Flow\n(Amaj7-Bm7-F#m7-E)"),
    K("A_CHORDPROG20", "IVmaj7-III7-vim7-v7", "The Just The Two Of Us\n(Dmaj7-C#7-F#m7-Em7)"),
    K("A_CHORDPROG21", "IVmaj7-V-iiim7-vim7-iim7-III7-vim7-v7", "The Anime Progression\n(Dmaj7-E-C#m7-F#m7-Bm7-C#7-F#m7-Em7)"),
    K("A_CHORDPROG22", "IVmaj7-iiim7-#iii°7-iim7-ii°7-Imaj7", "The Enhanced Urban Sunset\n(Dmaj7-C#m7-Cdim7-Bm7-Bm7b5-Amaj7)"),
    K("A_CHORDPROG23", "IVmaj7-V7-iiim9-vim7", "The Neo-Pop Turnaround\n(Dmaj7-E7-C#m9-F#m7)"),
    K("A_CHORDPROG25", "iiim9-Imaj9-vim9-iisus4", "The Contemplative 9th\n(C#m9-Amaj9-F#m9-Bsus4)"),
    K("A_CHORDPROG26", "Imaj9-IVmaj9-viiø7-iii7", "The Neo-Soul Cadence\n(Amaj9-Dmaj9-G#m7b5-C#m7)"),
    K("A_CHORDPROG27", "Imaj7-bIII°7-iim7-V7b9-Imaj7", "The Jazz-Pop Passing Progression\n(Amaj7-Cdim7-Bm7-E7b9-Amaj7)"),
    K("A_CHORDPROG28", "iim7-V7/ii-iim7-V7/V-V7sus4-V7-Imaj7", "The Enhanced ii-V-I\n(Bm7-F#7b9-Bm7-B7b9-E7sus4-E7-Amaj7)"),
]

# A# KEY - MINOR PROGRESSIONS
KEYCODES_AS_CHORDPROG_MINOR = [
    K("AS_CHORDPROG1", "i-VII-VI", "The Simple Minor\n(Gm-F-D#)"),
    K("AS_CHORDPROG2", "VI-VII-i", "The Simple Minor Reverse\n(D#-F-Gm)"),
    K("AS_CHORDPROG8", "vi-IV-I-V", "The Axis Progression\n(Gm-D#-A#-F)"),
    K("AS_CHORDPROG9", "i-VII-VI-V", "The Andalusian Cadence\n(Gm-F-D#-D)"),
    K("AS_CHORDPROG10", "i-VII-v-VI", "The Sensitive Minor\n(Gm-F-Dm-D#)"),
    K("AS_CHORDPROG11", "vi-V-IV-V", "The Eternal Progression\n(Gm-F-D#-F)"),
    K("AS_CHORDPROG24", "vim9-IVmaj7-iim9-V6", "The Smooth Minor 9 Progression\n(Gm9-D#maj7-Cm9-F6)"),
    K("AS_CHORDPROG29", "iim7b5-V7-im7", "The Minor ii-V-i\n(Am7b5-D7-Gm7)"),
    K("AS_CHORDPROG30", "iim7b5-V7-im7-IVmaj7", "The Minor Jazz Walk\n(Am7b5-D7-Gm7-Cmaj7)"),
    K("AS_CHORDPROG31", "im7-IVmaj7-VII7-IIIm7b5", "The Autumnal Progression\n(Gm7-Cmaj7-F7-A#m7b5)"),
    K("AS_CHORDPROG32", "im7-bVImaj7-bVII7-bIIImaj7", "The Backdoor Progression\n(Gm7-D#maj7-F7-A#maj7)"),
]

# A# KEY - MAJOR PROGRESSIONS
KEYCODES_AS_CHORDPROG_MAJOR = [
    K("AS_CHORDPROG3", "I-V-vi-IV", "The Classic Four-Chord\n(A#-F-Gm-D#)"),
    K("AS_CHORDPROG4", "I-vi-IV-V", "The 50s Progression\n(A#-Gm-D#-F)"),
    K("AS_CHORDPROG5", "I-V-vi-iii-IV-I-IV-V", "The Canon Progression\n(A#-F-Gm-Dm-D#-A#-D#-F)"),
    K("AS_CHORDPROG6", "I-IV-V", "The Blues Progression\n(A#-D#-F)"),
    K("AS_CHORDPROG7", "I-V-IV-IV", "The Rock Progression\n(A#-F-D#-D#)"),
    K("AS_CHORDPROG12", "I-III-IV-iv", "The Creep Progression\n(A#-D-D#-D#m)"),
    K("AS_CHORDPROG13", "I-vi-bVI-V", "The Melancholic Major\n(A#-Gm-F#-F)"),
    K("AS_CHORDPROG14", "Isus2-vi-IVsus2-V", "The Dreamy Sus Progression\n(A#sus2-Gm-D#sus2-F)"),
    K("AS_CHORDPROG15", "Isus2-IVsus2-vi-V", "The Ambient Float Progression\n(A#sus2-D#sus2-Gm-F)"),
    K("AS_CHORDPROG16", "IVsus2-Vsus4-Isus2-vi", "The Shoegaze Shimmer Progression\n(D#sus2-Fsus4-A#sus2-Gm)"),
    K("AS_CHORDPROG17", "ii7-V7-Imaj7", "The ii-V-I Progression\n(Cm7-F7-A#maj7)"),
    K("AS_CHORDPROG18", "Imaj7-iim7-iiim7-IVmaj7", "The Gentle City Progression\n(A#maj7-Cm7-Dm7-D#maj7)"),
    K("AS_CHORDPROG19", "Imaj7-iim7-vim7-V", "The Smooth Flow\n(A#maj7-Cm7-Gm7-F)"),
    K("AS_CHORDPROG20", "IVmaj7-III7-vim7-v7", "The Just The Two Of Us\n(D#maj7-D7-Gm7-Fm7)"),
    K("AS_CHORDPROG21", "IVmaj7-V-iiim7-vim7-iim7-III7-vim7-v7", "The Anime Progression\n(D#maj7-F-Dm7-Gm7-Cm7-D7-Gm7-Fm7)"),
    K("AS_CHORDPROG22", "IVmaj7-iiim7-#iii°7-iim7-ii°7-Imaj7", "The Enhanced Urban Sunset\n(D#maj7-Dm7-C#dim7-Cm7-Cm7b5-A#maj7)"),
    K("AS_CHORDPROG23", "IVmaj7-V7-iiim9-vim7", "The Neo-Pop Turnaround\n(D#maj7-F7-Dm9-Gm7)"),
    K("AS_CHORDPROG25", "iiim9-Imaj9-vim9-iisus4", "The Contemplative 9th\n(Dm9-A#maj9-Gm9-Csus4)"),
    K("AS_CHORDPROG26", "Imaj9-IVmaj9-viiø7-iii7", "The Neo-Soul Cadence\n(A#maj9-D#maj9-Am7b5-Dm7)"),
    K("AS_CHORDPROG27", "Imaj7-bIII°7-iim7-V7b9-Imaj7", "The Jazz-Pop Passing Progression\n(A#maj7-C#dim7-Cm7-F7b9-A#maj7)"),
    K("AS_CHORDPROG28", "iim7-V7/ii-iim7-V7/V-V7sus4-V7-Imaj7", "The Enhanced ii-V-I\n(Cm7-G7b9-Cm7-C7b9-F7sus4-F7-A#maj7)"),
]

# B KEY - MINOR PROGRESSIONS
KEYCODES_B_CHORDPROG_MINOR = [
    K("B_CHORDPROG1", "i-VII-VI", "The Simple Minor\n(G#m-F#-E)"),
    K("B_CHORDPROG2", "VI-VII-i", "The Simple Minor Reverse\n(E-F#-G#m)"),
    K("B_CHORDPROG8", "vi-IV-I-V", "The Axis Progression\n(G#m-E-B-F#)"),
    K("B_CHORDPROG9", "i-VII-VI-V", "The Andalusian Cadence\n(G#m-F#-E-D#)"),
    K("B_CHORDPROG10", "i-VII-v-VI", "The Sensitive Minor\n(G#m-F#-D#m-E)"),
    K("B_CHORDPROG11", "vi-V-IV-V", "The Eternal Progression\n(G#m-F#-E-F#)"),
    K("B_CHORDPROG24", "vim9-IVmaj7-iim9-V6", "The Smooth Minor 9 Progression\n(G#m9-Emaj7-C#m9-F#6)"),
    K("B_CHORDPROG29", "iim7b5-V7-im7", "The Minor ii-V-i\n(A#m7b5-D#7-G#m7)"),
    K("B_CHORDPROG30", "iim7b5-V7-im7-IVmaj7", "The Minor Jazz Walk\n(A#m7b5-D#7-G#m7-C#maj7)"),
    K("B_CHORDPROG31", "im7-IVmaj7-VII7-IIIm7b5", "The Autumnal Progression\n(G#m7-C#maj7-F#7-Bm7b5)"),
    K("B_CHORDPROG32", "im7-bVImaj7-bVII7-bIIImaj7", "The Backdoor Progression\n(G#m7-Emaj7-F#7-Bmaj7)"),
]

# B KEY - MAJOR PROGRESSIONS
KEYCODES_B_CHORDPROG_MAJOR = [
    K("B_CHORDPROG3", "I-V-vi-IV", "The Classic Four-Chord\n(B-F#-G#m-E)"),
    K("B_CHORDPROG4", "I-vi-IV-V", "The 50s Progression\n(B-G#m-E-F#)"),
    K("B_CHORDPROG5", "I-V-vi-iii-IV-I-IV-V", "The Canon Progression\n(B-F#-G#m-D#m-E-B-E-F#)"),
    K("B_CHORDPROG6", "I-IV-V", "The Blues Progression\n(B-E-F#)"),
    K("B_CHORDPROG7", "I-V-IV-IV", "The Rock Progression\n(B-F#-E-E)"),
    K("B_CHORDPROG12", "I-III-IV-iv", "The Creep Progression\n(B-D#-E-Em)"),
    K("B_CHORDPROG13", "I-vi-bVI-V", "The Melancholic Major\n(B-G#m-G-F#)"),
    K("B_CHORDPROG14", "Isus2-vi-IVsus2-V", "The Dreamy Sus Progression\n(Bsus2-G#m-Esus2-F#)"),
    K("B_CHORDPROG15", "Isus2-IVsus2-vi-V", "The Ambient Float Progression\n(Bsus2-Esus2-G#m-F#)"),
    K("B_CHORDPROG16", "IVsus2-Vsus4-Isus2-vi", "The Shoegaze Shimmer Progression\n(Esus2-F#sus4-Bsus2-G#m)"),
    K("B_CHORDPROG17", "ii7-V7-Imaj7", "The ii-V-I Progression\n(C#m7-F#7-Bmaj7)"),
    K("B_CHORDPROG18", "Imaj7-iim7-iiim7-IVmaj7", "The Gentle City Progression\n(Bmaj7-C#m7-D#m7-Emaj7)"),
    K("B_CHORDPROG19", "Imaj7-iim7-vim7-V", "The Smooth Flow\n(Bmaj7-C#m7-G#m7-F#)"),
    K("B_CHORDPROG20", "IVmaj7-III7-vim7-v7", "The Just The Two Of Us\n(Emaj7-D#7-G#m7-F#m7)"),
    K("B_CHORDPROG21", "IVmaj7-V-iiim7-vim7-iim7-III7-vim7-v7", "The Anime Progression\n(Emaj7-F#-D#m7-G#m7-C#m7-D#7-G#m7-F#m7)"),
    K("B_CHORDPROG22", "IVmaj7-iiim7-#iii°7-iim7-ii°7-Imaj7", "The Enhanced Urban Sunset\n(Emaj7-D#m7-Ddim7-C#m7-C#m7b5-Bmaj7)"),
    K("B_CHORDPROG23", "IVmaj7-V7-iiim9-vim7", "The Neo-Pop Turnaround\n(Emaj7-F#7-D#m9-G#m7)"),
    K("B_CHORDPROG25", "iiim9-Imaj9-vim9-iisus4", "The Contemplative 9th\n(D#m9-Bmaj9-G#m9-C#sus4)"),
    K("B_CHORDPROG26", "Imaj9-IVmaj9-viiø7-iii7", "The Neo-Soul Cadence\n(Bmaj9-Emaj9-A#m7b5-D#m7)"),
    K("B_CHORDPROG27", "Imaj7-bIII°7-iim7-V7b9-Imaj7", "The Jazz-Pop Passing Progression\n(Bmaj7-Ddim7-C#m7-F#7b9-Bmaj7)"),
    K("B_CHORDPROG28", "iim7-V7/ii-iim7-V7/V-V7sus4-V7-Imaj7", "The Enhanced ii-V-I\n(C#m7-G#7b9-C#m7-C#7b9-F#7sus4-F#7-Bmaj7)"),
]

# VOICINGS AND OCTAVE CONTROLS
KEYCODES_CHORD_PROG_CONTROLS = [
    K("PROG_VOICING_BASIC", "Voicing\nStyle\n1", "Use basic chord voicings for progressions"),
    K("PROG_VOICING_ADVANCED", "Voicing\nStyle\n2", "Use advanced chord voicings for progressions"),
    K("PROG_VOICING_DESCENDING", "Voicing\nStyle\n3", "Use descending voice leading for progressions"),
    K("PROG_VOICING_ASCENDING", "Voicing\nStyle\n4", "Use ascending voice leading for progressions"),
    K("PROG_OCTAVE_UP", "Octave\nUp", "Raise progression octave"),
    K("PROG_OCTAVE_DOWN", "Octave\nDown", "Lower progression octave"),
    K("PROG_OCTAVE_RESET", "Octave\nReset", "Reset progression octave to default"),
]



KEYCODES_HIDDEN = []
for x in range(256):
    KEYCODES_HIDDEN.append(K("TD({})".format(x), "TD({})".format(x)))

KEYCODES = []
KEYCODES_MAP = dict()
RAWCODES_MAP = dict()

KEYCODES_MIDI_CC = []
KEYCODES_MIDI_CC_UP = []
KEYCODES_MIDI_CC_DOWN = []
KEYCODES_MIDI_CC_FIXED = []

for x in range (128):
    KEYCODES_MIDI_CC.append(K("MI_CC_{}_TOG".format(x),
                              "CC{}\nOn/Off".format(x),
                              "Midi CC{} toggle".format(x)))
    KEYCODES_MIDI_CC_UP.append(K("MI_CC_{}_UP".format(x),
                              "CC{}\n▲".format(x),
                              "Midi CC{} up".format(x)))
    KEYCODES_MIDI_CC_DOWN.append(K("MI_CC_{}_DWN".format(x),
                              "CC{}\n▼".format(x),
                              "Midi CC{} down".format(x)))


for x in range(128):
    for y in range(128):
        KEYCODES_MIDI_CC_FIXED.append(K("MI_CC_{}_{}".format(x,y),
                                    "CC{}\n{}".format(x,y),
                                    "Midi CC{} = {}".format(x,y)))



KEYCODES_MIDI_VELOCITY = []

for x in range (128):
    KEYCODES_MIDI_VELOCITY.append(K("MI_VELOCITY_{}".format(x),
                              "Velocity\n{}".format(x),
                              "Velocity {}".format(x)))
                              
KEYCODES_MIDI_VELOCITY2 = []

for x in range (128):
    KEYCODES_MIDI_VELOCITY2.append(K("MI_VELOCITY2_{}".format(x),
                              "KS\nVelocity\n{}".format(x),
                              "KS\nVelocity {}".format(x)))
                              
KEYCODES_MIDI_VELOCITY3 = []

for x in range (128):
    KEYCODES_MIDI_VELOCITY3.append(K("MI_VELOCITY3_{}".format(x),
                              "TS\nVelocity\n{}".format(x),
                              "TS\nVelocity {}".format(x)))

KEYCODES_MIDI_BANK = []
KEYCODES_MIDI_BANK_MSB = []
KEYCODES_MIDI_BANK_LSB = []
KEYCODES_Program_Change = []
KEYCODES_Program_Change_UPDOWN = []

KEYCODES_MIDI_BANK.append(K("MI_BANK_UP",
                            "Bank\nUp",
                            "Bank up"))
KEYCODES_MIDI_BANK.append(K("MI_BANK_DWN",
                            "Bank\nDown",
                            "Bank down"))
KEYCODES_Program_Change_UPDOWN.append(K("MI_PROG_UP",
                            "Program\n▲",
                            "Program up"))
KEYCODES_Program_Change_UPDOWN.append(K("MI_PROG_DWN",
                            "Program\n▼",
                            "Program down"))

for x in range(128):
    KEYCODES_MIDI_BANK_MSB.append(K("MI_BANK_MSB_{}".format(x),
                              "Bank\nMSB\n{}".format(x),
                              "Bank select MSB {}".format(x)))
    KEYCODES_MIDI_BANK_LSB.append(K("MI_BANK_LSB_{}".format(x),
                              "Bank\nLSB\n{}".format(x),
                              "Bank select LSB {}".format(x)))
    KEYCODES_Program_Change.append(K("MI_PROG_{}".format(x),
                              "Program\n{}".format(x),
                              "Program change {}".format(x)))


K = None


def recreate_keycodes():
    """ Regenerates global KEYCODES array """

    KEYCODES.clear()
    KEYCODES.extend(KEYCODES_SPECIAL + KEYCODES_BASIC + KEYCODES_SHIFTED + KEYCODES_ISO + KEYCODES_LAYERS + KEYCODES_LAYERS_DF + KEYCODES_LAYERS_MO + KEYCODES_LAYERS_TG + KEYCODES_LAYERS_TT + KEYCODES_LAYERS_OSL + KEYCODES_LAYERS_TO + KEYCODES_LAYERS_LT +
                    KEYCODES_BOOT + KEYCODES_MODIFIERS + KEYCODES_QUANTUM + KEYCODES_BACKLIGHT + KEYCODES_MEDIA + KEYCODES_OLED + KEYCODES_CLEAR + KEYCODES_RGB_KC_COLOR + KEYCODES_MIDI_OCTAVE2 + KEYCODES_MIDI_OCTAVE3 + KEYCODES_MIDI_KEY2 + KEYCODES_MIDI_KEY3 + KEYCODES_MIDI_VELOCITY2 + KEYCODES_MIDI_VELOCITY3 + 
                    KEYCODES_TAP_DANCE + KEYCODES_MACRO + KEYCODES_MACRO_BASE + KEYCODES_EARTRAINER + KEYCODES_SAVE + KEYCODES_SETTINGS1 + KEYCODES_SETTINGS2 + KEYCODES_SETTINGS3 + KEYCODES_CHORDTRAINER + KEYCODES_USER + KEYCODES_HIDDEN + KEYCODES_MIDI+ KEYCODES_MIDI_CHANNEL_OS + KEYCODES_MIDI_CHANNEL_HOLD + KEYCODES_RGB_KC_CUSTOM + KEYCODES_RGB_KC_CUSTOM2 + KEYCODES_RGBSAVE + KEYCODES_MIDI_CHANNEL_KEYSPLIT + KEYCODES_MIDI_CHANNEL_KEYSPLIT2 + KEYCODES_KEYSPLIT_BUTTONS +
                    KEYCODES_MIDI_CC_FIXED+KEYCODES_MIDI_CC+KEYCODES_MIDI_CC_DOWN+KEYCODES_MIDI_CC_UP+KEYCODES_MIDI_BANK+KEYCODES_Program_Change+KEYCODES_MIDI_SMARTCHORDBUTTONS+KEYCODES_VELOCITY_STEPSIZE+KEYCODES_VELOCITY_SHUFFLE + KEYCODES_CC_ENCODERVALUE+ KEYCODES_EXWHEEL +
                    KEYCODES_MIDI_VELOCITY+KEYCODES_CC_STEPSIZE+KEYCODES_MIDI_CHANNEL+KEYCODES_MIDI_UPDOWN+KEYCODES_MIDI_CHORD_0+KEYCODES_MIDI_CHORD_1+KEYCODES_MIDI_CHORD_2+KEYCODES_MIDI_CHORD_3+KEYCODES_MIDI_CHORD_4+KEYCODES_MIDI_CHORD_5+KEYCODES_MIDI_SPLIT+KEYCODES_MIDI_SPLIT2+
                    KEYCODES_MIDI_INVERSION+KEYCODES_MIDI_SCALES+KEYCODES_MIDI_OCTAVE+KEYCODES_MIDI_KEY+KEYCODES_Program_Change_UPDOWN+KEYCODES_MIDI_BANK_LSB+KEYCODES_MIDI_BANK_MSB+KEYCODES_MIDI_PEDAL+KEYCODES_MIDI_ADVANCED+KEYCODES_MIDI_SPLIT_BUTTONS+KEYCODES_BASIC + KEYCODES_SHIFTED + KEYCODES_C_CHORDPROG_MINOR + KEYCODES_C_CHORDPROG_MAJOR + KEYCODES_CS_CHORDPROG_MINOR + KEYCODES_CS_CHORDPROG_MAJOR + KEYCODES_D_CHORDPROG_MINOR + KEYCODES_D_CHORDPROG_MAJOR + KEYCODES_DS_CHORDPROG_MINOR + KEYCODES_DS_CHORDPROG_MAJOR + KEYCODES_E_CHORDPROG_MINOR + KEYCODES_E_CHORDPROG_MAJOR + KEYCODES_F_CHORDPROG_MINOR + KEYCODES_F_CHORDPROG_MAJOR + KEYCODES_FS_CHORDPROG_MINOR + KEYCODES_FS_CHORDPROG_MAJOR + KEYCODES_G_CHORDPROG_MINOR + KEYCODES_G_CHORDPROG_MAJOR + KEYCODES_GS_CHORDPROG_MINOR + KEYCODES_GS_CHORDPROG_MAJOR + KEYCODES_A_CHORDPROG_MINOR + KEYCODES_A_CHORDPROG_MAJOR + KEYCODES_AS_CHORDPROG_MINOR + KEYCODES_AS_CHORDPROG_MAJOR + KEYCODES_B_CHORDPROG_MINOR + KEYCODES_B_CHORDPROG_MAJOR + KEYCODES_CHORD_PROG_CONTROLS)
    KEYCODES_MAP.clear()
    RAWCODES_MAP.clear()
    for keycode in KEYCODES:
        KEYCODES_MAP[keycode.qmk_id.replace("(kc)", "")] = keycode
        RAWCODES_MAP[Keycode.deserialize(keycode.qmk_id)] = keycode


def create_user_keycodes():
    KEYCODES_USER.clear()
    for x in range(16):
        KEYCODES_USER.append(
            Keycode(
                "USER{:02}".format(x),
                "User {}".format(x),
                "User keycode {}".format(x)
            )
        )


def create_custom_user_keycodes(custom_keycodes):
    KEYCODES_USER.clear()
    for x, c_keycode in enumerate(custom_keycodes):
        KEYCODES_USER.append(
            Keycode(
                "USER{:02}".format(x),
                c_keycode.get("shortName", "USER{:02}".format(x)),
                c_keycode.get("title", "USER{:02}".format(x)),
                alias=[c_keycode.get("name", "USER{:02}".format(x))]
            )
        )


def create_midi_keycodes(midiSettingLevel):
    KEYCODES_MIDI.clear()

    if midiSettingLevel == "basic" or midiSettingLevel == "advanced":
        KEYCODES_MIDI.extend(KEYCODES_MIDI_BASIC)

    if midiSettingLevel == "advanced":
        KEYCODES_MIDI.extend(KEYCODES_MIDI_ADVANCED)


def recreate_keyboard_keycodes(keyboard):
    """ Generates keycodes based on information the keyboard provides (e.g. layer keycodes, macros) """

    Keycode.protocol = keyboard.vial_protocol

    layers = keyboard.layers

    def generate_keycodes_for_mask(label, description):
        keycodes = []
        for layer in range(layers):
            lbl = "{}({})".format(label, layer)
            keycodes.append(Keycode(lbl, lbl, description))
        return keycodes

    KEYCODES_LAYERS.clear()

    if layers >= 4:
        KEYCODES_LAYERS.append(Keycode("FN_MO13", "Fn1\n(Fn3)"))
        KEYCODES_LAYERS.append(Keycode("FN_MO23", "Fn2\n(Fn3)"))


    for x in range(layers):
        KEYCODES_LAYERS_LT.append(Keycode("LT{}(kc)".format(x), "LT {}\n(kc)".format(x),
                                       "kc on tap, switch to layer {} while held".format(x), masked=True))

    KEYCODES_MACRO.clear()
    for x in range(keyboard.macro_count):
        lbl = "M{}".format(x)
        KEYCODES_MACRO.append(Keycode(lbl, lbl))


    KEYCODES_TAP_DANCE.clear()
    for x in range(keyboard.tap_dance_count):
        lbl = "TD({})".format(x)
        KEYCODES_TAP_DANCE.append(Keycode(lbl, lbl, "Tap dance keycode"))

    # Check if custom keycodes are defined in keyboard, and if so add them to user keycodes
    if keyboard.custom_keycodes is not None and len(keyboard.custom_keycodes) > 0:
        create_custom_user_keycodes(keyboard.custom_keycodes)
    else:
        create_user_keycodes()

    create_midi_keycodes(keyboard.midi)

    recreate_keycodes()


recreate_keycodes()
