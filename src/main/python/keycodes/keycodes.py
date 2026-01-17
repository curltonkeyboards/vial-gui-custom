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
    K("OLED_2", "Smart\nChord\nLight\nMode", "Momentarily turn on layer when pressed"),
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
    K("RGB_HUI", "Hue\n+", "Increase hue"),
    K("RGB_HUD", "Hue\n-", "Decrease hue"),
    K("RGB_SAI", "Sat\n+", "Increase saturation"),
    K("RGB_SAD", "Sat\n-", "Decrease saturation"),
    K("RGB_VAI", "Bright\n+", "Increase value"),
    K("RGB_VAD", "Bright\n-", "Decrease value"),
    K("RGB_SPI", "Speed\n+", "Increase RGB effect speed"),
    K("RGB_SPD", "Speed\n-", "Decrease RGB effect speed"),
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
    K("TD(0)", "Tap/\nHold\n0", "TapDance0"),
    K("TD(1)", "Tap/\nHold\n1", "TapDance1"),
    K("TD(2)", "Tap/\nHold\n2", "TapDance2"),
    K("TD(3)", "Tap/\nHold\n3", "TapDance3"),
    K("TD(4)", "Tap/\nHold\n4", "TapDance4"),
    K("TD(5)", "Tap/\nHold\n5", "TapDance5"),
    K("TD(6)", "Tap/\nHold\n6", "TapDance6"),
    K("TD(7)", "Tap/\nHold\n7", "TapDance7"),
    K("TD(8)", "Tap/\nHold\n8", "TapDance8"),
    K("TD(9)", "Tap/\nHold\n9", "TapDance9"),
    K("TD(10)", "Tap/\nHold\n10", "TapDance10"),
    K("TD(11)", "Tap/\nHold\n11", "TapDance11"),
    K("TD(12)", "Tap/\nHold\n12", "TapDance12"),
    K("TD(13)", "Tap/\nHold\n13", "TapDance13"),
    K("TD(14)", "Tap/\nHold\n14", "TapDance14"),
    K("TD(15)", "Tap/\nHold\n15", "TapDance15"),
    K("TD(16)", "Tap/\nHold\n16", "TapDance16"),
    K("TD(17)", "Tap/\nHold\n17", "TapDance17"),
    K("TD(18)", "Tap/\nHold\n18", "TapDance18"),
    K("TD(19)", "Tap/\nHold\n19", "TapDance19"),
    K("TD(20)", "Tap/\nHold\n20", "TapDance20"),
    K("TD(21)", "Tap/\nHold\n21", "TapDance21"),
    K("TD(22)", "Tap/\nHold\n22", "TapDance22"),
    K("TD(23)", "Tap/\nHold\n23", "TapDance23"),
    K("TD(24)", "Tap/\nHold\n24", "TapDance24"),
    K("TD(25)", "Tap/\nHold\n25", "TapDance25"),
    K("TD(26)", "Tap/\nHold\n26", "TapDance26"),
    K("TD(27)", "Tap/\nHold\n27", "TapDance27"),
    K("TD(28)", "Tap/\nHold\n28", "TapDance28"),
    K("TD(29)", "Tap/\nHold\n29", "TapDance29"),
    K("TD(30)", "Tap/\nHold\n30", "TapDance30"),
    K("TD(31)", "Tap/\nHold\n31", "TapDance31"),
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
    K("M0", "Macro\n0", "Macro\n1"),
    K("M1", "Macro\n1", "Macro\n1"),
    K("M2", "Macro\n2", "Macro\n2"),
    K("M3", "Macro\n3", "Macro\n3"),
    K("M4", "Macro\n4", "Macro\n4"),
    K("M5", "Macro\n5", "Macro\n5"),
    K("M6", "Macro\n6", "Macro\n6"),
    K("M7", "Macro\n7", "Macro\n7"),
    K("M8", "Macro\n8", "Macro\n8"),
    K("M9", "Macro\n9", "Macro\n9"),
    K("M10", "Macro\n10", "Macro\n10"),
    K("M11", "Macro\n11", "Macro\n11"),
    K("M12", "Macro\n12", "Macro\n12"),
    K("M13", "Macro\n13", "Macro\n13"),
    K("M14", "Macro\n14", "Macro\n14"),
    K("M15", "Macro\n15", "Macro\n15"),
    K("M16", "Macro\n16", "Macro\n16"),
    K("M17", "Macro\n17", "Macro\n17"),
    K("M18", "Macro\n18", "Macro\n18"),
    K("M19", "Macro\n19", "Macro\n19"),
    K("M20", "Macro\n20", "Macro\n20"),
    K("M21", "Macro\n21", "Macro\n21"),
    K("M22", "Macro\n22", "Macro\n22"),
    K("M23", "Macro\n23", "Macro\n23"),
    K("M24", "Macro\n24", "Macro\n24"),
    K("M25", "Macro\n25", "Macro\n25"),
    K("M26", "Macro\n26", "Macro\n26"),
    K("M27", "Macro\n27", "Macro\n27"),
    K("M28", "Macro\n28", "Macro\n28"),
    K("M29", "Macro\n29", "Macro\n29"),
    K("M30", "Macro\n30", "Macro\n30"),
    K("M31", "Macro\n31", "Macro\n31"),
    K("M32", "Macro\n32", "Macro\n32"),
    K("M33", "Macro\n33", "Macro\n33"),
    K("M34", "Macro\n34", "Macro\n34"),
    K("M35", "Macro\n35", "Macro\n35"),
    K("M36", "Macro\n36", "Macro\n36"),
    K("M37", "Macro\n37", "Macro\n37"),
    K("M38", "Macro\n38", "Macro\n38"),
    K("M39", "Macro\n39", "Macro\n39"),
    K("M40", "Macro\n40", "Macro\n40"),
    K("M41", "Macro\n41", "Macro\n41"),
    K("M42", "Macro\n42", "Macro\n42"),
    K("M43", "Macro\n43", "Macro\n43"),
    K("M44", "Macro\n44", "Macro\n44"),
    K("M45", "Macro\n45", "Macro\n45"),
    K("M46", "Macro\n46", "Macro\n46"),
    K("M47", "Macro\n47", "Macro\n47"),
    K("M48", "Macro\n48", "Macro\n48"),
    K("M49", "Macro\n49", "Macro\n49"),
    K("M50", "Macro\n50", "Macro\n50"),
    K("M51", "Macro\n51", "Macro\n51"),
    K("M52", "Macro\n52", "Macro\n52"),
    K("M53", "Macro\n53", "Macro\n53"),
    K("M54", "Macro\n54", "Macro\n54"),
    K("M55", "Macro\n55", "Macro\n55"),
    K("M56", "Macro\n56", "Macro\n56"),
    K("M57", "Macro\n57", "Macro\n57"),
    K("M58", "Macro\n58", "Macro\n58"),
    K("M59", "Macro\n59", "Macro\n59"),
    K("M60", "Macro\n60", "Macro\n60"),
    K("M61", "Macro\n61", "Macro\n61"),
    K("M62", "Macro\n62", "Macro\n62"),
    K("M63", "Macro\n63", "Macro\n63"),
    K("M64", "Macro\n64", "Macro\n64"),
    K("M65", "Macro\n65", "Macro\n65"),
    K("M66", "Macro\n66", "Macro\n66"),
    K("M67", "Macro\n67", "Macro\n67"),
    K("M68", "Macro\n68", "Macro\n68"),
    K("M69", "Macro\n69", "Macro\n69"),
    K("M70", "Macro\n70", "Macro\n70"),
    K("M71", "Macro\n71", "Macro\n71"),
    K("M72", "Macro\n72", "Macro\n72"),
    K("M73", "Macro\n73", "Macro\n73"),
    K("M74", "Macro\n74", "Macro\n74"),
    K("M75", "Macro\n75", "Macro\n75"),
    K("M76", "Macro\n76", "Macro\n76"),
    K("M77", "Macro\n77", "Macro\n77"),
    K("M78", "Macro\n78", "Macro\n78"),
    K("M79", "Macro\n79", "Macro\n79"),
    K("M80", "Macro\n80", "Macro\n80"),
    K("M81", "Macro\n81", "Macro\n81"),
    K("M82", "Macro\n82", "Macro\n82"),
    K("M83", "Macro\n83", "Macro\n83"),
    K("M84", "Macro\n84", "Macro\n84"),
    K("M85", "Macro\n85", "Macro\n85"),
    K("M86", "Macro\n86", "Macro\n86"),
    K("M87", "Macro\n87", "Macro\n87"),
    K("M88", "Macro\n88", "Macro\n88"),
    K("M89", "Macro\n89", "Macro\n89"),
    K("M90", "Macro\n90", "Macro\n90"),
    K("M91", "Macro\n91", "Macro\n91"),
    K("M92", "Macro\n92", "Macro\n92"),
    K("M93", "Macro\n93", "Macro\n93"),
    K("M94", "Macro\n94", "Macro\n94"),
    K("M95", "Macro\n95", "Macro\n95"),
    K("M96", "Macro\n96", "Macro\n96"),
    K("M97", "Macro\n97", "Macro\n97"),
    K("M98", "Macro\n98", "Macro\n98"),
    K("M99", "Macro\n99", "Macro\n99"),
    K("M100", "Macro\n100", "Macro\n100"),
    K("M101", "Macro\n101", "Macro\n101"),
    K("M102", "Macro\n102", "Macro\n102"),
    K("M103", "Macro\n103", "Macro\n103"),
    K("M104", "Macro\n104", "Macro\n104"),
    K("M105", "Macro\n105", "Macro\n105"),
    K("M106", "Macro\n106", "Macro\n106"),
    K("M107", "Macro\n107", "Macro\n107"),
    K("M108", "Macro\n108", "Macro\n108"),
    K("M109", "Macro\n109", "Macro\n109"),
    K("M110", "Macro\n110", "Macro\n110"),
    K("M111", "Macro\n111", "Macro\n111"),
    K("M112", "Macro\n112", "Macro\n112"),
    K("M113", "Macro\n113", "Macro\n113"),
    K("M114", "Macro\n114", "Macro\n114"),
    K("M115", "Macro\n115", "Macro\n115"),
    K("M116", "Macro\n116", "Macro\n116"),
    K("M117", "Macro\n117", "Macro\n117"),
    K("M118", "Macro\n118", "Macro\n118"),
    K("M119", "Macro\n119", "Macro\n119"),
    K("M120", "Macro\n120", "Macro\n120"),
    K("M121", "Macro\n121", "Macro\n121"),
    K("M122", "Macro\n122", "Macro\n122"),
    K("M123", "Macro\n123", "Macro\n123"),
    K("M124", "Macro\n124", "Macro\n124"),
    K("M125", "Macro\n125", "Macro\n125"),
    K("M126", "Macro\n126", "Macro\n126"),
    K("M127", "Macro\n127", "Macro\n127"),
    K("M128", "Macro\n128", "Macro\n128"),
    K("M129", "Macro\n129", "Macro\n129"),
    K("M130", "Macro\n130", "Macro\n130"),
    K("M131", "Macro\n131", "Macro\n131"),
    K("M132", "Macro\n132", "Macro\n132"),
    K("M133", "Macro\n133", "Macro\n133"),
    K("M134", "Macro\n134", "Macro\n134"),
    K("M135", "Macro\n135", "Macro\n135"),
    K("M136", "Macro\n136", "Macro\n136"),
    K("M137", "Macro\n137", "Macro\n137"),
    K("M138", "Macro\n138", "Macro\n138"),
    K("M139", "Macro\n139", "Macro\n139"),
    K("M140", "Macro\n140", "Macro\n140"),
    K("M141", "Macro\n141", "Macro\n141"),
    K("M142", "Macro\n142", "Macro\n142"),
    K("M143", "Macro\n143", "Macro\n143"),
    K("M144", "Macro\n144", "Macro\n144"),
    K("M145", "Macro\n145", "Macro\n145"),
    K("M146", "Macro\n146", "Macro\n146"),
    K("M147", "Macro\n147", "Macro\n147"),
    K("M148", "Macro\n148", "Macro\n148"),
    K("M149", "Macro\n149", "Macro\n149"),
    K("M150", "Macro\n150", "Macro\n150"),
    K("M151", "Macro\n151", "Macro\n151"),
    K("M152", "Macro\n152", "Macro\n152"),
    K("M153", "Macro\n153", "Macro\n153"),
    K("M154", "Macro\n154", "Macro\n154"),
    K("M155", "Macro\n155", "Macro\n155"),
    K("M156", "Macro\n156", "Macro\n156"),
    K("M157", "Macro\n157", "Macro\n157"),
    K("M158", "Macro\n158", "Macro\n158"),
    K("M159", "Macro\n159", "Macro\n159"),
    K("M160", "Macro\n160", "Macro\n160"),
    K("M161", "Macro\n161", "Macro\n161"),
    K("M162", "Macro\n162", "Macro\n162"),
    K("M163", "Macro\n163", "Macro\n163"),
    K("M164", "Macro\n164", "Macro\n164"),
    K("M165", "Macro\n165", "Macro\n165"),
    K("M166", "Macro\n166", "Macro\n166"),
    K("M167", "Macro\n167", "Macro\n167"),
    K("M168", "Macro\n168", "Macro\n168"),
    K("M169", "Macro\n169", "Macro\n169"),
    K("M170", "Macro\n170", "Macro\n170"),
    K("M171", "Macro\n171", "Macro\n171"),
    K("M172", "Macro\n172", "Macro\n172"),
    K("M173", "Macro\n173", "Macro\n173"),
    K("M174", "Macro\n174", "Macro\n174"),
    K("M175", "Macro\n175", "Macro\n175"),
    K("M176", "Macro\n176", "Macro\n176"),
    K("M177", "Macro\n177", "Macro\n177"),
    K("M178", "Macro\n178", "Macro\n178"),
    K("M179", "Macro\n179", "Macro\n179"),
    K("M180", "Macro\n180", "Macro\n180"),
    K("M181", "Macro\n181", "Macro\n181"),
    K("M182", "Macro\n182", "Macro\n182"),
    K("M183", "Macro\n183", "Macro\n183"),
    K("M184", "Macro\n184", "Macro\n184"),
    K("M185", "Macro\n185", "Macro\n185"),
    K("M186", "Macro\n186", "Macro\n186"),
    K("M187", "Macro\n187", "Macro\n187"),
    K("M188", "Macro\n188", "Macro\n188"),
    K("M189", "Macro\n189", "Macro\n189"),
    K("M190", "Macro\n190", "Macro\n190"),
    K("M191", "Macro\n191", "Macro\n191"),
    K("M192", "Macro\n192", "Macro\n192"),
    K("M193", "Macro\n193", "Macro\n193"),
    K("M194", "Macro\n194", "Macro\n194"),
    K("M195", "Macro\n195", "Macro\n195"),
    K("M196", "Macro\n196", "Macro\n196"),
    K("M197", "Macro\n197", "Macro\n197"),
    K("M198", "Macro\n198", "Macro\n198"),
    K("M199", "Macro\n199", "Macro\n199"),
    K("M200", "Macro\n200", "Macro\n200"),
    K("M201", "Macro\n201", "Macro\n201"),
    K("M202", "Macro\n202", "Macro\n202"),
    K("M203", "Macro\n203", "Macro\n203"),
    K("M204", "Macro\n204", "Macro\n204"),
    K("M205", "Macro\n205", "Macro\n205"),
    K("M206", "Macro\n206", "Macro\n206"),
    K("M207", "Macro\n207", "Macro\n207"),
    K("M208", "Macro\n208", "Macro\n208"),
    K("M209", "Macro\n209", "Macro\n209"),
    K("M210", "Macro\n210", "Macro\n210"),
    K("M211", "Macro\n211", "Macro\n211"),
    K("M212", "Macro\n212", "Macro\n212"),
    K("M213", "Macro\n213", "Macro\n213"),
    K("M214", "Macro\n214", "Macro\n214"),
    K("M215", "Macro\n215", "Macro\n215"),
    K("M216", "Macro\n216", "Macro\n216"),
    K("M217", "Macro\n217", "Macro\n217"),
    K("M218", "Macro\n218", "Macro\n218"),
    K("M219", "Macro\n219", "Macro\n219"),
    K("M220", "Macro\n220", "Macro\n220"),
    K("M221", "Macro\n221", "Macro\n221"),
    K("M222", "Macro\n222", "Macro\n222"),
    K("M223", "Macro\n223", "Macro\n223"),
    K("M224", "Macro\n224", "Macro\n224"),
    K("M225", "Macro\n225", "Macro\n225"),
    K("M226", "Macro\n226", "Macro\n226"),
    K("M227", "Macro\n227", "Macro\n227"),
    K("M228", "Macro\n228", "Macro\n228"),
    K("M229", "Macro\n229", "Macro\n229"),
    K("M230", "Macro\n230", "Macro\n230"),
    K("M231", "Macro\n231", "Macro\n231"),
    K("M232", "Macro\n232", "Macro\n232"),
    K("M233", "Macro\n233", "Macro\n233"),
    K("M234", "Macro\n234", "Macro\n234"),
    K("M235", "Macro\n235", "Macro\n235"),
    K("M236", "Macro\n236", "Macro\n236"),
    K("M237", "Macro\n237", "Macro\n237"),
    K("M238", "Macro\n238", "Macro\n238"),
    K("M239", "Macro\n239", "Macro\n239"),
    K("M240", "Macro\n240", "Macro\n240"),
    K("M241", "Macro\n241", "Macro\n241"),
    K("M242", "Macro\n242", "Macro\n242"),
    K("M243", "Macro\n243", "Macro\n243"),
    K("M244", "Macro\n244", "Macro\n244"),
    K("M245", "Macro\n245", "Macro\n245"),
    K("M246", "Macro\n246", "Macro\n246"),
    K("M247", "Macro\n247", "Macro\n247"),
    K("M248", "Macro\n248", "Macro\n248"),
    K("M249", "Macro\n249", "Macro\n249"),
    K("M250", "Macro\n250", "Macro\n250"),
    K("M251", "Macro\n251", "Macro\n251"),
    K("M252", "Macro\n252", "Macro\n252"),
    K("M253", "Macro\n253", "Macro\n253"),
    K("M254", "Macro\n254", "Macro\n254"),
    K("M255", "Macro\n255", "Macro\n255")
]


KEYCODES_MACRO_BASE = [
    K("DYN_REC_START1", "Dynamic\nMacro 1\nRec", "Dynamic Macro 1 Rec Start", alias=["DM_REC1"]),
    K("DYN_REC_START2", "Dynamic\nMacro 2\nRec", "Dynamic Macro 2 Rec Start", alias=["DM_REC2"]),    
    K("DYN_MACRO_PLAY1", "Dynamic\nMacro 1\nPlay", "Dynamic Macro 1 Play", alias=["DM_PLY1"]),
    K("DYN_MACRO_PLAY2", "Dynamic\nMacro 2\nPlay", "Dynamic Macro 2 Play", alias=["DM_PLY2"]),
    K("DYN_REC_STOP", "Stop\nMacro\nRec", "Dynamic Macro Rec Stop", alias=["DM_RSTP"]),
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
    K("BPM_UP", "BPM\nUp", "Set BPM"),
    K("BPM_DOWN", "BPM\nDown", "Set BPM"),
]

KEYCODES_MIDI_PEDAL = [
    K("MI_ALLOFF", "All\nNotes\nOff", "Midi send all notes OFF"),
    K("MI_SUS", "Sustain\nPedal", "Midi Sustain"),
]

KEYCODES_MIDI_INOUT = [
    # MIDI Routing Controls - Both inputs have same 4 modes:
    # PROC (process all through QMK), THRU (forward to both outputs), CLK (process clock only), IGN (ignore)
    K("MIDI_IN_MODE_TOG", "HW MIDI\nRoute", "Toggle Hardware MIDI IN routing: PROC→THRU→CLK→IGN"),
    K("USB_MIDI_MODE_TOG", "USB MIDI\nRoute", "Toggle USB MIDI routing: PROC→THRU→CLK→IGN"),
    K("MIDI_CLOCK_SRC_TOG", "Clock\nSource", "Toggle MIDI clock source: LOCAL→USB→MIDI_IN"),

    # Override Toggles
    K("MI_CH_OVR_TOG", "Channel\nOverride", "Toggle channel override"),
    K("MI_VEL_OVR_TOG", "Velocity\nOverride", "Toggle velocity override"),
    K("MI_TRNS_OVR_TOG", "Transpose\nOverride", "Toggle transpose override"),

    # Additional MIDI Toggles
    K("MI_TRUE_SUS_TOG", "True\nSustain", "Toggle true sustain mode"),
    K("MI_CC_LOOP_TOG", "CC Loop\nRec", "Toggle CC loop recording"),
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
    K("KS_MODIFIER", "KeySplit\nModifier", "Key split modifier (hold for double-tap lock)"),
    K("TS_MODIFIER", "TripleSplit\nModifier", "Triple split modifier (hold for double-tap lock)"),
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
    K("MI_RVEL_0", "Dynamic\nRange\n0", "Set dynamic range to 0 (allows min=max velocity)"),
    K("MI_RVEL_1", "Dynamic\nRange\n1", "Set dynamic range to 1"),
    K("MI_RVEL_2", "Dynamic\nRange\n2", "Set dynamic range to 2"),
    K("MI_RVEL_3", "Dynamic\nRange\n3", "Set dynamic range to 3"),
    K("MI_RVEL_4", "Dynamic\nRange\n4", "Set dynamic range to 4"),
    K("MI_RVEL_5", "Dynamic\nRange\n5", "Set dynamic range to 5"),
    K("MI_RVEL_6", "Dynamic\nRange\n6", "Set dynamic range to 6"),
    K("MI_RVEL_7", "Dynamic\nRange\n7", "Set dynamic range to 7"),
    K("MI_RVEL_8", "Dynamic\nRange\n8", "Set dynamic range to 8"),
    K("MI_RVEL_9", "Dynamic\nRange\n9", "Set dynamic range to 9"),
    K("MI_RVEL_10", "Dynamic\nRange\n10", "Set dynamic range to 10"),
    K("MI_RVEL_11", "Dynamic\nRange\n11", "Set dynamic range to 11"),
    K("MI_RVEL_12", "Dynamic\nRange\n12", "Set dynamic range to 12"),
    K("MI_RVEL_13", "Dynamic\nRange\n13", "Set dynamic range to 13"),
    K("MI_RVEL_14", "Dynamic\nRange\n14", "Set dynamic range to 14"),
    K("MI_RVEL_15", "Dynamic\nRange\n15", "Set dynamic range to 15"),
    K("MI_RVEL_16", "Dynamic\nRange\n16", "Set dynamic range to 16"),
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
    K("OLED_2", "Smart\nChord\nRGB", "Toggle Smartchord Light mode"),
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
K("MI_INV_1", "Major 2nd", "Minor\n2nd"),
K("MI_INV_2", "Minor 2nd", "Major\n2nd"), 
K("MI_INV_3", "Minor 3rd", "Minor\n3rd"),
K("MI_INV_4", "Major 3rd", "Major\n3rd"),
K("MI_INV_5", "Perfect Fourth", "Perfect\nFourth"),
K("MI_INV_6", "Tritone", "Tritone"),
K("MI_INV_7", "Perfect 5th", "Perfect\nFifth"),
K("MI_INV_8", "Minor 6th", "Minor\n6th"),
K("MI_INV_9", "Major 6th", "Major\n6th"),
K("MI_INV_10", "Minor 7th", "Minor\n7th"),
K("MI_INV_11", "Major 7th", "Major\n7th"),
]

KEYCODES_MIDI_CHORD_1 = [
K("MI_CHORD_0", "Major", "Major"),
K("MI_CHORD_1", "m", "Minor"),
K("MI_CHORD_2", "dim", "Diminished"),
K("MI_CHORD_3", "aug", "Augmented"),
K("MI_CHORD_4", "b5", "b5"),
K("MI_CHORD_5", "sus2", "Sus2"),
K("MI_CHORD_6", "sus4", "Sus4"),
K("MI_CHORD_7", "7no3", "7 no 3"),
K("MI_CHORD_8", "maj7\nno3", "Major 7 no 3"),
K("MI_CHORD_9", "7no5", "7 no 5"),
K("MI_CHORD_10", "m7no5", "Minor 7 no 5"),
K("MI_CHORD_11", "maj7\nno5", "Major 7 no 5"),
]

KEYCODES_MIDI_CHORD_2 = [
K("MI_CHORD_12", "6", "Major 6"),
K("MI_CHORD_13", "m6", "Minor 6"), 
K("MI_CHORD_14", "add2", "Add2"),
K("MI_CHORD_15", "m(add2)", "Minor Add2"),
K("MI_CHORD_16", "add4", "Add4"),
K("MI_CHORD_17", "m(add4)", "Minor Add4"),
K("MI_CHORD_18", "7", "7"),
K("MI_CHORD_19", "Maj7", "Major 7"),
K("MI_CHORD_20", "m7", "Minor 7"),
K("MI_CHORD_21", "m7b5", "Minor 7 b5"),
K("MI_CHORD_22", "dim7", "Diminished 7"),
K("MI_CHORD_23", "minMaj7", "Minor Major 7"),
K("MI_CHORD_24", "7sus4", "7 Sus4"),
K("MI_CHORD_25", "add9", "Add9"),
K("MI_CHORD_26", "m(add9)", "Minor Add9"),
K("MI_CHORD_27", "add11", "Add11"),
K("MI_CHORD_28", "m(add11)", "Minor Add11"),
]

KEYCODES_MIDI_CHORD_3 = [
K("MI_CHORD_29", "9", "9"),
K("MI_CHORD_30", "m9", "Minor 9"),
K("MI_CHORD_31", "Maj9", "Major 9"),
K("MI_CHORD_32", "6/9", "6/9"),
K("MI_CHORD_33", "m6/9", "Minor 6/9"),
K("MI_CHORD_34", "7b9", "7 b9"),
K("MI_CHORD_35", "7(11)", "7(11)"),
K("MI_CHORD_36", "7(#11)", "7(#11)"),
K("MI_CHORD_37", "m7(11)", "Minor 7(11)"),
K("MI_CHORD_38", "maj7\n(11)", "Major 7(11)"),
K("MI_CHORD_39", "Maj7\n(#11)", "Major 7(#11)"),
K("MI_CHORD_40", "7(13)", "7(13)"),
K("MI_CHORD_41", "m7(13)", "Minor 7(13)"),
K("MI_CHORD_42", "Maj7\n(13)", "Major 7(13)"),
]

KEYCODES_MIDI_CHORD_4 = [
K("MI_CHORD_43", "11", "11"),
K("MI_CHORD_44", "m11", "Minor 11"),
K("MI_CHORD_45", "Maj11", "Major 11"),
K("MI_CHORD_46", "7(11)\n(13)", "7(11)(13)"),
K("MI_CHORD_47", "m7(11)\n(13)", "Minor 7(11)(13)"),
K("MI_CHORD_48", "maj7\n(11)(13)", "Major 7(11)(13)"),
K("MI_CHORD_49", "9(13)", "9(13)"),
K("MI_CHORD_50", "m9(13)", "Minor 9(13)"),
K("MI_CHORD_51", "maj9\n(13)", "Major 9(13)"),
K("MI_CHORD_52", "13", "13"),
K("MI_CHORD_53", "m13", "Minor 13"),
K("MI_CHORD_54", "Maj13", "Major 13"),
]

KEYCODES_MIDI_CHORD_5 = [
K("MI_CHORD_55", "7b9(11)", "7 b9(11)"),
K("MI_CHORD_56", "7sus2", "7 Sus2"),
K("MI_CHORD_57", "7#5", "7 #5"),
K("MI_CHORD_58", "7b5", "7 b5"),
K("MI_CHORD_59", "7#9", "7 #9"),
K("MI_CHORD_60", "7b5b9", "7 b5 b9"),
K("MI_CHORD_61", "7b5#9", "7 b5 #9"),
K("MI_CHORD_62", "7b9(13)", "7 b9(13)"),
K("MI_CHORD_63", "7#9(13)", "7 #9(13)"),
K("MI_CHORD_64", "7#5b9", "7 #5 b9"),
K("MI_CHORD_65", "7#5#9", "7 #5 #9"),
K("MI_CHORD_66", "7b5(11)", "7 b5(11)"),
K("MI_CHORD_67", "maj7\nsus4", "Major 7 Sus4"),
K("MI_CHORD_68", "maj7\n#5", "Major 7 #5"),
K("MI_CHORD_69", "maj7\nb5", "Major 7 b5"),
K("MI_CHORD_70", "minMaj7\n(11)", "Minor Major 7(11)"),
K("MI_CHORD_71", "(addb5)", "Add b5"),
K("MI_CHORD_72", "9#11", "9 #11"),
K("MI_CHORD_73", "9b5", "9 b5"),
K("MI_CHORD_74", "9#5", "9 #5"),
K("MI_CHORD_75", "m9b5", "Minor 9 b5"),
K("MI_CHORD_76", "m9#11", "Minor 9 #11"),
K("MI_CHORD_77", "9sus4", "9 Sus4"),
]

KEYCODES_MIDI_SCALES = [ 
K("MI_CHORD_100", "Major\nScale\n(Ionian)", "Major(Ionian)"),
K("MI_CHORD_101", "Dorian\nScale", "Dorian"),
K("MI_CHORD_102", "Phrygian\nScale", "Phrygian"),
K("MI_CHORD_103", "Lydian\nScale", "Lydian"),
K("MI_CHORD_104", "Mixolydian\nScale", "Mixolydian"),
K("MI_CHORD_105", "Minor\nScale\n(Aeolian)", "Minor(Aeolian)"),
K("MI_CHORD_106", "Locrian\nScale", "Locrian"),
K("MI_CHORD_107", "Melodic\nMinor\nScale", "Melodic Minor"),
K("MI_CHORD_108", "Lydian\nDominant\nScale", "Lydian Dominant"),
K("MI_CHORD_109", "Altered\nScale", "Altered Scale"),
K("MI_CHORD_110", "Harmonic\nMinor\nScale", "Harmonic Minor"),
K("MI_CHORD_111", "Major\nPentatonic\nScale", "Major Pentatonic"),
K("MI_CHORD_112", "Minor\nPentatonic\nScale", "Minor Pentatonic"),
K("MI_CHORD_113", "Whole\nTone\nScale", "Whole Tone"),
K("MI_CHORD_114", "Diminished\nScale", "Diminished"),
K("MI_CHORD_115", "Blues\nScale", "Blues"),
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
    K("RGB_MIDISWITCH", "MIDI\nSwitch\nAuto Light", "RGB Mode: MIDI Switch Auto Light"),
    K("RGB_KC_46", "Reactive\nLightning", "RGB Mode: Reactive Lightning"),
    K("RGB_KC_47", "Reactive\nRipple", "RGB Mode: Reactive Ripple"),
    K("RGB_KC_48", "Reactive\nFireworks", "RGB Mode: Reactive Fireworks"),
    K("RGB_KC_49", "Comet\nTrail", "RGB Mode: Comet Trail"),
    K("RGB_KC_50", "Tetris\nVertical", "RGB Mode: Tetris Vertical"),
    K("RGB_KC_51", "Tetris\nHorizontal", "RGB Mode: Tetris Horizontal"),
    K("RGB_KC_52", "Fireplace", "RGB Mode: Fireplace"),
    K("RGB_KC_53", "Pong", "RGB Mode: Pong"),
    K("RGB_KC_54", "L/R Sweep\nStatic", "RGB Mode: L/R Sweep Static"),
    K("RGB_KC_55", "L/R Sweep\nRainbow", "RGB Mode: L/R Sweep Rainbow"),
    K("RGB_KC_56", "L/R Sweep\nRandom", "RGB Mode: L/R Sweep Random"),
    K("RGB_KC_57", "Custom\nSlot 1", "RGB Mode: Custom Slot 1"),
    K("RGB_KC_58", "Custom\nSlot 2", "RGB Mode: Custom Slot 2"),
    K("RGB_KC_59", "Custom\nSlot 3", "RGB Mode: Custom Slot 3"),
    K("RGB_KC_60", "Custom\nSlot 4", "RGB Mode: Custom Slot 4"),
    K("RGB_KC_61", "Custom\nSlot 5", "RGB Mode: Custom Slot 5"),
    K("RGB_KC_62", "Custom\nSlot 6", "RGB Mode: Custom Slot 6"),
    K("RGB_KC_63", "Custom\nSlot 7", "RGB Mode: Custom Slot 7"),
    K("RGB_KC_64", "Custom\nSlot 8", "RGB Mode: Custom Slot 8"),
    K("RGB_KC_65", "Custom\nSlot 9", "RGB Mode: Custom Slot 9"),
    K("RGB_KC_66", "Custom\nSlot 10", "RGB Mode: Custom Slot 10"),
    K("RGB_KC_67", "Custom\nSlot 11", "RGB Mode: Custom Slot 11"),
    K("RGB_KC_68", "Custom\nSlot 12", "RGB Mode: Custom Slot 12"),
    K("RGB_KC_69", "Custom\nSlot 13", "RGB Mode: Custom Slot 13"),
    K("RGB_KC_70", "Custom\nSlot 14", "RGB Mode: Custom Slot 14"),
    K("RGB_KC_71", "Custom\nSlot 15", "RGB Mode: Custom Slot 15"),
    K("RGB_KC_72", "Custom\nSlot 16", "RGB Mode: Custom Slot 16"),
    K("RGB_KC_73", "Custom\nSlot 17", "RGB Mode: Custom Slot 17"),
    K("RGB_KC_74", "Custom\nSlot 18", "RGB Mode: Custom Slot 18"),
    K("RGB_KC_75", "Custom\nSlot 19", "RGB Mode: Custom Slot 19"),
    K("RGB_KC_76", "Custom\nSlot 20", "RGB Mode: Custom Slot 20"),
    K("RGB_KC_77", "Custom\nSlot 21", "RGB Mode: Custom Slot 21"),
    K("RGB_KC_78", "Custom\nSlot 22", "RGB Mode: Custom Slot 22"),
    K("RGB_KC_79", "Custom\nSlot 23", "RGB Mode: Custom Slot 23"),
    K("RGB_KC_80", "Custom\nSlot 24", "RGB Mode: Custom Slot 24"),
    K("RGB_KC_81", "Custom\nSlot 25", "RGB Mode: Custom Slot 25"),
    K("RGB_KC_82", "Custom\nSlot 26", "RGB Mode: Custom Slot 26"),
    K("RGB_KC_83", "Custom\nSlot 27", "RGB Mode: Custom Slot 27"),
    K("RGB_KC_84", "Custom\nSlot 28", "RGB Mode: Custom Slot 28"),
    K("RGB_KC_85", "Custom\nSlot 29", "RGB Mode: Custom Slot 29"),
    K("RGB_KC_86", "Custom\nSlot 30", "RGB Mode: Custom Slot 30"),
    K("RGB_KC_87", "Custom\nSlot 31", "RGB Mode: Custom Slot 31"),
    K("RGB_KC_88", "Custom\nSlot 32", "RGB Mode: Custom Slot 32"),
    K("RGB_KC_89", "Custom\nSlot 33", "RGB Mode: Custom Slot 33"),
    K("RGB_KC_90", "Custom\nSlot 34", "RGB Mode: Custom Slot 34"),
    K("RGB_KC_91", "Custom\nSlot 35", "RGB Mode: Custom Slot 35"),
    K("RGB_KC_92", "Custom\nSlot 36", "RGB Mode: Custom Slot 36"),
    K("RGB_KC_93", "Custom\nSlot 37", "RGB Mode: Custom Slot 37"),
    K("RGB_KC_94", "Custom\nSlot 38", "RGB Mode: Custom Slot 38"),
    K("RGB_KC_95", "Custom\nSlot 39", "RGB Mode: Custom Slot 39"),
    K("RGB_KC_96", "Custom\nSlot 40", "RGB Mode: Custom Slot 40"),
    K("RGB_KC_97", "Custom\nSlot 41", "RGB Mode: Custom Slot 41"),
    K("RGB_KC_98", "Custom\nSlot 42", "RGB Mode: Custom Slot 42"),
    K("RGB_KC_99", "Custom\nSlot 43", "RGB Mode: Custom Slot 43"),
    K("RGB_KC_100", "Custom\nSlot 44", "RGB Mode: Custom Slot 44"),
    K("RGB_KC_101", "Custom\nSlot 45", "RGB Mode: Custom Slot 45"),
    K("RGB_KC_102", "Custom\nSlot 46", "RGB Mode: Custom Slot 46"),
    K("RGB_KC_103", "Custom\nSlot 47", "RGB Mode: Custom Slot 47"),
    K("RGB_KC_104", "Custom\nSlot 48", "RGB Mode: Custom Slot 48"),
    K("RGB_KC_105", "Custom\nSlot 49", "RGB Mode: Custom Slot 49"),
    K("RGB_KC_106", "Random 1\nLoop", "RGB Mode: Random 1 - Loop"),
    K("RGB_KC_107", "Random 2\nLoop", "RGB Mode: Random 2 - Loop"),
    K("RGB_KC_108", "Random 3\nLoop", "RGB Mode: Random 3 - Loop"),
    K("RGB_KC_109", "Random 1\nBPM", "RGB Mode: Random 1 - BPM"),
    K("RGB_KC_110", "Random 2\nBPM", "RGB Mode: Random 2 - BPM"),
    K("RGB_KC_111", "Random 3\nBPM", "RGB Mode: Random 3 - BPM"),
    K("RGB_KC_112", "Random 1\nManual", "RGB Mode: Random 1 - Manual"),
    K("RGB_KC_113", "Random 2\nManual", "RGB Mode: Random 2 - Manual"),
    K("RGB_KC_114", "Random 3\nManual", "RGB Mode: Random 3 - Manual"),
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
# BASIC - MINOR PROGRESSIONS
KEYCODES_C_CHORDPROG_BASIC_MINOR = [
    K("C_CHORDPROG1", "A Minor\nProg\n1", "i-VII-VI\n(Am-G-F)Simple\nMinor"),
    K("C_CHORDPROG3", "A Minor\nProg\n3", "VI-VII-i\n(F-G-Am)Hopeful\nMinor"),
    K("C_CHORDPROG7", "A Minor\nProg\n7", "i-iv-VII-I\n(Am-Dm-G-C)Natural\nMinor"),
    K("C_CHORDPROG9", "A Minor\nProg\n9", "iv-III-i-VII\n(Dm-C-Am-G)Downward\nMinor"),
    K("C_CHORDPROG10", "A Minor\nProg\n10", "i-VII-v-VI\n(Am-G-Em-F)Sensitive\nMinor"),
    K("C_CHORDPROG11", "A Minor\nProg\n11", "i-v-VI-ii\n(Am-Em-F-Dm)Circular\nMinor"),
]

# BASIC - MAJOR PROGRESSIONS
KEYCODES_C_CHORDPROG_BASIC_MAJOR = [
    K("C_CHORDPROG2", "C Major\nProg\n2", "I-IV-V\n(C-F-G)Simple\nMajor"),
    K("C_CHORDPROG4", "C Major\nProg\n4", "I-vi-IV-V\n(C-Am-F-G)50s\nProgression"),
    K("C_CHORDPROG5", "C Major\nProg\n5", "I-V-vi-IV\n(C-G-Am-F)Classic\nFour-Chord"),
    K("C_CHORDPROG6", "C Major\nProg\n6", "vi-IV-I-V\n(Am-F-C-G)Axis\nProgression"),
    K("C_CHORDPROG8", "C Major\nProg\n8", "I-V-IV-IV\n(C-G-F-F)Rock\nProgression"),
    K("C_CHORDPROG12", "C Major\nProg\n12", "I-ii-vi-V\n(C-Dm-Am-G)Summer\nHit"),
    K("C_CHORDPROG13", "C Major\nProg\n13", "I-V-vi-iii\nIV-I-IV-V\n(C-G-Am-Em\nF-C-F-G)Canon\nProgression"),
]

# INTERMEDIATE - MINOR PROGRESSIONS
KEYCODES_C_CHORDPROG_INTERMEDIATE_MINOR = [
    K("C_CHORDPROG14", "A Minor\nProg\n14", "i-VII-VI-V\n(Am-G-F-E)Andalusian\nCadence"),
    K("C_CHORDPROG15", "A Minor\nProg\n15", "i-bVI-bVII-V\n(Am-F-G-E)Harmonic\nTension"),
    K("C_CHORDPROG18", "A Minor\nProg\n18", "i-bVII-VI-V\n(Am-Ab-G-F)Melancholic\nMinor"),
    K("C_CHORDPROG20", "A Minor\nProg\n20", "i-V-VI-VIm\n(Am-E-F-Fm)Darkening\nMinor"),
    K("C_CHORDPROG24", "A Minor\nProg\n24", "im7-bVImaj7\nbVII7-V7\n(Am7-Fmaj7\nG7-E7)Jazz\nMinor"),
    K("C_CHORDPROG27", "A Minor\nProg\n27", "VI-#viidim\nV7-i-VII\n(F-G#dim\nE7-Am-G)Diminished\nDominant"),
]

# INTERMEDIATE - MAJOR PROGRESSIONS
KEYCODES_C_CHORDPROG_INTERMEDIATE_MAJOR = [
    K("C_CHORDPROG16", "C Major\nProg\n16", "I-III-IV-iv\n(C-E-F-Fm)Creep\nProgression"),
    K("C_CHORDPROG17", "C Major\nProg\n17", "I-III-VII-II\n(C-E-G-D)Pumped\nKicks"),
    K("C_CHORDPROG19", "C Major\nProg\n19", "I-V-bVII-IV\n(C-G-Bb-F)Rebel\nProgression"),
    K("C_CHORDPROG21", "C Major\nProg\n21", "Isus2-IVsus2\nvi-V\n(Csus2-Fsus2\nAm-G)Ambient\nFloat"),
    K("C_CHORDPROG22", "C Major\nProg\n22", "IVsus2-Vsus4\nIsus2-vi\n(Fsus2-Gsus4\nCsus2-Am)Shoegaze\nShimmer"),
    K("C_CHORDPROG23", "C Major\nProg\n23", "ii7-V7-Imaj7\n(Dm7-G7-\nCmaj7)2-5-1\nProgression"),
    K("C_CHORDPROG25", "C Major\nProg\n25", "vi7-ii7-V7\nImaj7\n(Am7-Dm7-G7\nCmaj7)6-2-5-1\nProgression"),
    K("C_CHORDPROG26", "C Major\nProg\n26", "Imaj7-iim7\niiim7-IVadd2\n(Cmaj7-Dm7\nEm7-Fadd2)Gentle\nCity"),
]

# EXPERT - MINOR PROGRESSIONS
KEYCODES_C_CHORDPROG_EXPERT_MINOR = [
    K("C_CHORDPROG30", "A Minor\nProg\n30", "vim9-iiim9\niim9-Imaj9\n(Am9-Em9\nDm9-Cmaj9)Bring\nThe 9th"),
    K("C_CHORDPROG32", "A Minor\nProg\n32", "im9-ivaddD\nbVImaj7\nbVIIadd2\n(Am9-Dmadd9\nFmaj7-Gadd2)Modern\nMinor 9"),
    K("C_CHORDPROG33", "A Minor\nProg\n33", "im9-iim9-vm9\n(Am9-Dm9\nEm9)Lo-Fi\nNinths"),
    K("C_CHORDPROG34", "A Minor\nProg\n34", "im9-vm9\nVImaj9-im9\nVImaj9\nviim9\n(Am9-Em9\nFmaj9-Am9\nFmaj9-Gm9)Ninth\nJourney"),
    K("C_CHORDPROG37", "A Minor\nProg\n37", "im9-IVmaj7\niim7b5-V7\n(Am9-Fmaj7\nDm7b5-E7)Minor Jazz\nII-V-I"),
    K("C_CHORDPROG40", "A Minor\nProg\n40", "im9-V7b9\nVImaj9\niim9-vm7\n(Am9-E7b9\nFmaj9\nDm9-Em7)Altered\nDominant"),
]

# EXPERT - MAJOR PROGRESSIONS
KEYCODES_C_CHORDPROG_EXPERT_MAJOR = [
    K("C_CHORDPROG28", "C Major\nProg\n28", "IVmaj7-V7\niiim7-vim7\niim7-III7\nvim7\n(Fmaj7-G7\nEm7-Am7\nDm7-E7-Am7)Anime\nProgression"),
    K("C_CHORDPROG29", "C Major\nProg\n29", "IVmaj7-III7\nvim7-II7\niim7-V7\nImaj7\n(Fmaj7-E7\nAm7-D7\nDm7-G7\nCmaj7)She's\nLovely"),
    K("C_CHORDPROG31", "C Major\nProg\n31", "IVmaj7-V7\niiim9-vim7\n(Fmaj7-G7\nEm9-Am7)Neo-Pop\nTurnaround"),
    K("C_CHORDPROG35", "C Major\nProg\n35", "IVmaj7-iiim7\n#iiidim7\niim7-iim7b5\nImaj7\n(Fmaj7-Em7\nEbdim7\nDm7-Dm7b5\nCmaj7)Descending\nDiminished"),
    K("C_CHORDPROG36", "C Major\nProg\n36", "Imaj7-#idim7\niim7-#iidim7\niiim7\nbiiidim7\n(Cmaj7\nC#dim7-Dm7\nEbdim7-Em7\nEbdim7)Diminished\nBridge"),
    K("C_CHORDPROG38", "C Major\nProg\n38", "I-vi-ii\nbVII7-I\n(Cmaj7-Am7\nDm7-Bb7)Backdoor\nProgression"),
    K("C_CHORDPROG39", "C Major\nProg\n39", "Imaj7\nbIIImaj7\niim7-iiim7\n(Cmaj7\nEbmaj7\nDm7-Em7)Modal\nMixture"),
    K("C_CHORDPROG41", "C Major\nProg\n41", "Imaj9-I7\niim7-VII7b9\nV7-III7b9\nIV-IVdim7\n(Cmaj9-C7\nDm7-B7b9\nG7-E7b9\nFmaj7-Fdim7)Complex\n2-5-1-4"),
    K("C_CHORDPROG42", "C Major\nProg\n42", "Imaj7-vi7\nii7-bII7\n(Cmaj7-Am7\nDm7-Db7)Tritone\nSubstitution"),
]

# C# KEY - MINOR PROGRESSIONS
KEYCODES_C_SHARP_CHORDPROG_BASIC_MINOR = [
    K("CS_CHORDPROG1", "A# Minor\nProg\n1", "i-VII-VI\n(A#m-G#-F#)Simple\nMinor"),
    K("CS_CHORDPROG3", "A# Minor\nProg\n3", "VI-VII-i\n(F#-G#-A#m)Hopeful\nMinor"),
    K("CS_CHORDPROG7", "A# Minor\nProg\n7", "i-iv-VII-I\n(A#m-D#m-G#-C#)Natural\nMinor"),
    K("CS_CHORDPROG9", "A# Minor\nProg\n9", "iv-III-i-VII\n(D#m-C#-A#m-G#)Downward\nMinor"),
    K("CS_CHORDPROG10", "A# Minor\nProg\n10", "i-VII-v-VI\n(A#m-G#-Fm-F#)Sensitive\nMinor"),
    K("CS_CHORDPROG11", "A# Minor\nProg\n11", "i-v-VI-ii\n(A#m-Fm-F#-Cm)Circular\nMinor"),
]

# C# KEY - MAJOR PROGRESSIONS
KEYCODES_C_SHARP_CHORDPROG_BASIC_MAJOR = [
    K("CS_CHORDPROG2", "C# Major\nProg\n2", "I-IV-V\n(C#-F#-G#)Simple\nMajor"),
    K("CS_CHORDPROG4", "C# Major\nProg\n4", "I-vi-IV-V\n(C#-A#m-F#-G#)50s\nProgression"),
    K("CS_CHORDPROG5", "C# Major\nProg\n5", "I-V-vi-IV\n(C#-G#-A#m-F#)Classic\nFour-Chord"),
    K("CS_CHORDPROG6", "C# Major\nProg\n6", "vi-IV-I-V\n(A#m-F#-C#-G#)Axis\nProgression"),
    K("CS_CHORDPROG8", "C# Major\nProg\n8", "I-V-IV-IV\n(C#-G#-F#-F#)Rock\nProgression"),
    K("CS_CHORDPROG12", "C# Major\nProg\n12", "I-ii-vi-V\n(C#-D#m-A#m-G#)Summer\nHit"),
    K("CS_CHORDPROG13", "C# Major\nProg\n13", "I-V-vi-iii\nIV-I-IV-V\n(C#-G#-A#m-Fm\nF#-C#-F#-G#)Canon\nProgression"),
]

# C# KEY - INTERMEDIATE MINOR PROGRESSIONS
KEYCODES_C_SHARP_CHORDPROG_INTERMEDIATE_MINOR = [
    K("CS_CHORDPROG14", "A# Minor\nProg\n14", "i-VII-VI-V\n(A#m-G#-F#-F)Andalusian\nCadence"),
    K("CS_CHORDPROG15", "A# Minor\nProg\n15", "i-bVI-bVII-V\n(A#m-F#-G#-F)Harmonic\nTension"),
    K("CS_CHORDPROG18", "A# Minor\nProg\n18", "i-bVII-VI-V\n(A#m-G#-F#-F)Melancholic\nMinor"),
    K("CS_CHORDPROG20", "A# Minor\nProg\n20", "i-V-VI-VIm\n(A#m-F-F#-F#m)Darkening\nMinor"),
    K("CS_CHORDPROG24", "A# Minor\nProg\n24", "im7-bVImaj7\nbVII7-V7\n(A#m7-F#maj7\nG#7-F7)Jazz\nMinor"),
    K("CS_CHORDPROG27", "A# Minor\nProg\n27", "VI-#viidim\nV7-i-VII\n(F#-Adim\nF7-A#m-G#)Diminished\nDominant"),
]

# C# KEY - INTERMEDIATE MAJOR PROGRESSIONS
KEYCODES_C_SHARP_CHORDPROG_INTERMEDIATE_MAJOR = [
    K("CS_CHORDPROG16", "C# Major\nProg\n16", "I-III-IV-iv\n(C#-F-F#-F#m)Creep\nProgression"),
    K("CS_CHORDPROG17", "C# Major\nProg\n17", "I-III-VII-II\n(C#-F-C-D#)Pumped\nKicks"),
    K("CS_CHORDPROG19", "C# Major\nProg\n19", "I-V-bVII-IV\n(C#-G#-B-F#)Rebel\nProgression"),
    K("CS_CHORDPROG21", "C# Major\nProg\n21", "Isus2-IVsus2\nvi-V\n(C#sus2-F#sus2\nA#m-G#)Ambient\nFloat"),
    K("CS_CHORDPROG22", "C# Major\nProg\n22", "IVsus2-Vsus4\nIsus2-vi\n(F#sus2-G#sus4\nC#sus2-A#m)Shoegaze\nShimmer"),
    K("CS_CHORDPROG23", "C# Major\nProg\n23", "ii7-V7-Imaj7\n(D#m7-G#7-\nC#maj7)2-5-1\nProgression"),
    K("CS_CHORDPROG25", "C# Major\nProg\n25", "vi7-ii7-V7\nImaj7\n(A#m7-D#m7-G#7\nC#maj7)6-2-5-1\nProgression"),
    K("CS_CHORDPROG26", "C# Major\nProg\n26", "Imaj7-iim7\niiim7-IVadd2\n(C#maj7-D#m7\nFm7-F#add2)Gentle\nCity"),
]

# C# KEY - EXPERT MINOR PROGRESSIONS
KEYCODES_C_SHARP_CHORDPROG_EXPERT_MINOR = [
    K("CS_CHORDPROG30", "A# Minor\nProg\n30", "vim9-iiim9\niim9-Imaj9\n(A#m9-Fm9\nD#m9-C#maj9)Bring\nThe 9th"),
    K("CS_CHORDPROG32", "A# Minor\nProg\n32", "im9-ivaddD\nbVImaj7\nbVIIadd2\n(A#m9-D#madd9\nF#maj7-G#add2)Modern\nMinor 9"),
    K("CS_CHORDPROG33", "A# Minor\nProg\n33", "im9-iim9-vm9\n(A#m9-D#m9\nFm9)Lo-Fi\nNinths"),
    K("CS_CHORDPROG34", "A# Minor\nProg\n34", "im9-vm9\nVImaj9-im9\nVImaj9\nviim9\n(A#m9-Fm9\nF#maj9-A#m9\nF#maj9-G#m9)Ninth\nJourney"),
    K("CS_CHORDPROG37", "A# Minor\nProg\n37", "im9-IVmaj7\niim7b5-V7\n(A#m9-F#maj7\nD#m7b5-F7)Minor Jazz\nII-V-I"),
    K("CS_CHORDPROG40", "A# Minor\nProg\n40", "im9-V7b9\nVImaj9\niim9-vm7\n(A#m9-F7b9\nF#maj9\nD#m9-Fm7)Altered\nDominant"),
]

# C# KEY - EXPERT MAJOR PROGRESSIONS
KEYCODES_C_SHARP_CHORDPROG_EXPERT_MAJOR = [
    K("CS_CHORDPROG28", "C# Major\nProg\n28", "IVmaj7-V7\niiim7-vim7\niim7-III7\nvim7\n(F#maj7-G#7\nFm7-A#m7\nD#m7-F7-A#m7)Anime\nProgression"),
    K("CS_CHORDPROG29", "C# Major\nProg\n29", "IVmaj7-III7\nvim7-II7\niim7-V7\nImaj7\n(F#maj7-F7\nA#m7-D#7\nD#m7-G#7\nC#maj7)She's\nLovely"),
    K("CS_CHORDPROG31", "C# Major\nProg\n31", "IVmaj7-V7\niiim9-vim7\n(F#maj7-G#7\nFm9-A#m7)Neo-Pop\nTurnaround"),
    K("CS_CHORDPROG35", "C# Major\nProg\n35", "IVmaj7-iiim7\n#iiidim7\niim7-iim7b5\nImaj7\n(F#maj7-Fm7\nFdim7\nD#m7-D#m7b5\nC#maj7)Descending\nDiminished"),
    K("CS_CHORDPROG36", "C# Major\nProg\n36", "Imaj7-#idim7\niim7-#iidim7\niiim7\nbiiidim7\n(C#maj7\nDdim7-D#m7\nEdim7-Fm7\nEdim7)Diminished\nBridge"),
    K("CS_CHORDPROG38", "C# Major\nProg\n38", "I-vi-ii\nbVII7-I\n(C#maj7-A#m7\nD#m7-B7)Backdoor\nProgression"),
    K("CS_CHORDPROG39", "C# Major\nProg\n39", "Imaj7\nbIIImaj7\niim7-iiim7\n(C#maj7\nEmaj7\nD#m7-Fm7)Modal\nMixture"),
    K("CS_CHORDPROG41", "C# Major\nProg\n41", "Imaj9-I7\niim7-VII7b9\nV7-III7b9\nIV-IVdim7\n(C#maj9-C#7\nD#m7-C7b9\nG#7-F7b9\nF#maj7-F#dim7)Complex\n2-5-1-4"),
    K("CS_CHORDPROG42", "C# Major\nProg\n42", "Imaj7-vi7\nii7-bII7\n(C#maj7-A#m7\nD#m7-D7)Tritone\nSubstitution"),
]

# D KEY - MINOR PROGRESSIONS
KEYCODES_D_CHORDPROG_BASIC_MINOR = [
    K("D_CHORDPROG1", "B Minor\nProg\n1", "i-VII-VI\n(Bm-A-G)Simple\nMinor"),
    K("D_CHORDPROG3", "B Minor\nProg\n3", "VI-VII-i\n(G-A-Bm)Hopeful\nMinor"),
    K("D_CHORDPROG7", "B Minor\nProg\n7", "i-iv-VII-I\n(Bm-Em-A-D)Natural\nMinor"),
    K("D_CHORDPROG9", "B Minor\nProg\n9", "iv-III-i-VII\n(Em-D-Bm-A)Downward\nMinor"),
    K("D_CHORDPROG10", "B Minor\nProg\n10", "i-VII-v-VI\n(Bm-A-F#m-G)Sensitive\nMinor"),
    K("D_CHORDPROG11", "B Minor\nProg\n11", "i-v-VI-ii\n(Bm-F#m-G-C#m)Circular\nMinor"),
]

# D KEY - MAJOR PROGRESSIONS
KEYCODES_D_CHORDPROG_BASIC_MAJOR = [
    K("D_CHORDPROG2", "D Major\nProg\n2", "I-IV-V\n(D-G-A)Simple\nMajor"),
    K("D_CHORDPROG4", "D Major\nProg\n4", "I-vi-IV-V\n(D-Bm-G-A)50s\nProgression"),
    K("D_CHORDPROG5", "D Major\nProg\n5", "I-V-vi-IV\n(D-A-Bm-G)Classic\nFour-Chord"),
    K("D_CHORDPROG6", "D Major\nProg\n6", "vi-IV-I-V\n(Bm-G-D-A)Axis\nProgression"),
    K("D_CHORDPROG8", "D Major\nProg\n8", "I-V-IV-IV\n(D-A-G-G)Rock\nProgression"),
    K("D_CHORDPROG12", "D Major\nProg\n12", "I-ii-vi-V\n(D-Em-Bm-A)Summer\nHit"),
    K("D_CHORDPROG13", "D Major\nProg\n13", "I-V-vi-iii\nIV-I-IV-V\n(D-A-Bm-F#m\nG-D-G-A)Canon\nProgression"),
]

# D KEY - INTERMEDIATE MINOR PROGRESSIONS
KEYCODES_D_CHORDPROG_INTERMEDIATE_MINOR = [
    K("D_CHORDPROG14", "B Minor\nProg\n14", "i-VII-VI-V\n(Bm-A-G-F#)Andalusian\nCadence"),
    K("D_CHORDPROG15", "B Minor\nProg\n15", "i-bVI-bVII-V\n(Bm-G-A-F#)Harmonic\nTension"),
    K("D_CHORDPROG18", "B Minor\nProg\n18", "i-bVII-VI-V\n(Bm-A-G-F#)Melancholic\nMinor"),
    K("D_CHORDPROG20", "B Minor\nProg\n20", "i-V-VI-VIm\n(Bm-F#-G-Gm)Darkening\nMinor"),
    K("D_CHORDPROG24", "B Minor\nProg\n24", "im7-bVImaj7\nbVII7-V7\n(Bm7-Gmaj7\nA7-F#7)Jazz\nMinor"),
    K("D_CHORDPROG27", "B Minor\nProg\n27", "VI-#viidim\nV7-i-VII\n(G-A#dim\nF#7-Bm-A)Diminished\nDominant"),
]

# D KEY - INTERMEDIATE MAJOR PROGRESSIONS
KEYCODES_D_CHORDPROG_INTERMEDIATE_MAJOR = [
    K("D_CHORDPROG16", "D Major\nProg\n16", "I-III-IV-iv\n(D-F#-G-Gm)Creep\nProgression"),
    K("D_CHORDPROG17", "D Major\nProg\n17", "I-III-VII-II\n(D-F#-A-E)Pumped\nKicks"),
    K("D_CHORDPROG19", "D Major\nProg\n19", "I-V-bVII-IV\n(D-A-C-G)Rebel\nProgression"),
    K("D_CHORDPROG21", "D Major\nProg\n21", "Isus2-IVsus2\nvi-V\n(Dsus2-Gsus2\nBm-A)Ambient\nFloat"),
    K("D_CHORDPROG22", "D Major\nProg\n22", "IVsus2-Vsus4\nIsus2-vi\n(Gsus2-Asus4\nDsus2-Bm)Shoegaze\nShimmer"),
    K("D_CHORDPROG23", "D Major\nProg\n23", "ii7-V7-Imaj7\n(Em7-A7-\nDmaj7)2-5-1\nProgression"),
    K("D_CHORDPROG25", "D Major\nProg\n25", "vi7-ii7-V7\nImaj7\n(Bm7-Em7-A7\nDmaj7)6-2-5-1\nProgression"),
    K("D_CHORDPROG26", "D Major\nProg\n26", "Imaj7-iim7\niiim7-IVadd2\n(Dmaj7-Em7\nF#m7-Gadd2)Gentle\nCity"),
]

# D KEY - EXPERT MINOR PROGRESSIONS
KEYCODES_D_CHORDPROG_EXPERT_MINOR = [
    K("D_CHORDPROG30", "B Minor\nProg\n30", "vim9-iiim9\niim9-Imaj9\n(Bm9-F#m9\nEm9-Dmaj9)Bring\nThe 9th"),
    K("D_CHORDPROG32", "B Minor\nProg\n32", "im9-ivaddD\nbVImaj7\nbVIIadd2\n(Bm9-Emadd9\nGmaj7-Aadd2)Modern\nMinor 9"),
    K("D_CHORDPROG33", "B Minor\nProg\n33", "im9-iim9-vm9\n(Bm9-Em9\nF#m9)Lo-Fi\nNinths"),
    K("D_CHORDPROG34", "B Minor\nProg\n34", "im9-vm9\nVImaj9-im9\nVImaj9\nviim9\n(Bm9-F#m9\nGmaj9-Bm9\nGmaj9-Am9)Ninth\nJourney"),
    K("D_CHORDPROG37", "B Minor\nProg\n37", "im9-IVmaj7\niim7b5-V7\n(Bm9-Gmaj7\nEm7b5-F#7)Minor Jazz\nII-V-I"),
    K("D_CHORDPROG40", "B Minor\nProg\n40", "im9-V7b9\nVImaj9\niim9-vm7\n(Bm9-F#7b9\nGmaj9\nEm9-F#m7)Altered\nDominant"),
]

# D KEY - EXPERT MAJOR PROGRESSIONS
KEYCODES_D_CHORDPROG_EXPERT_MAJOR = [
    K("D_CHORDPROG28", "D Major\nProg\n28", "IVmaj7-V7\niiim7-vim7\niim7-III7\nvim7\n(Gmaj7-A7\nF#m7-Bm7\nEm7-F#7-Bm7)Anime\nProgression"),
    K("D_CHORDPROG29", "D Major\nProg\n29", "IVmaj7-III7\nvim7-II7\niim7-V7\nImaj7\n(Gmaj7-F#7\nBm7-E7\nEm7-A7\nDmaj7)She's\nLovely"),
    K("D_CHORDPROG31", "D Major\nProg\n31", "IVmaj7-V7\niiim9-vim7\n(Gmaj7-A7\nF#m9-Bm7)Neo-Pop\nTurnaround"),
    K("D_CHORDPROG35", "D Major\nProg\n35", "IVmaj7-iiim7\n#iiidim7\niim7-iim7b5\nImaj7\n(Gmaj7-F#m7\nFdim7\nEm7-Em7b5\nDmaj7)Descending\nDiminished"),
    K("D_CHORDPROG36", "D Major\nProg\n36", "Imaj7-#idim7\niim7-#iidim7\niiim7\nbiiidim7\n(Dmaj7\nD#dim7-Em7\nFdim7-F#m7\nFdim7)Diminished\nBridge"),
    K("D_CHORDPROG38", "D Major\nProg\n38", "I-vi-ii\nbVII7-I\n(Dmaj7-Bm7\nEm7-C7)Backdoor\nProgression"),
    K("D_CHORDPROG39", "D Major\nProg\n39", "Imaj7\nbIIImaj7\niim7-iiim7\n(Dmaj7\nFmaj7\nEm7-F#m7)Modal\nMixture"),
    K("D_CHORDPROG41", "D Major\nProg\n41", "Imaj9-I7\niim7-VII7b9\nV7-III7b9\nIV-IVdim7\n(Dmaj9-D7\nEm7-C#7b9\nA7-F#7b9\nGmaj7-Gdim7)Complex\n2-5-1-4"),
    K("D_CHORDPROG42", "D Major\nProg\n42", "Imaj7-vi7\nii7-bII7\n(Dmaj7-Bm7\nEm7-D#7)Tritone\nSubstitution"),
]

# Eb KEY - MINOR PROGRESSIONS
KEYCODES_E_FLAT_CHORDPROG_BASIC_MINOR = [
    K("DS_CHORDPROG1", "C Minor\nProg\n1", "i-VII-VI\n(Cm-Bb-Ab)Simple\nMinor"),
    K("DS_CHORDPROG3", "C Minor\nProg\n3", "VI-VII-i\n(Ab-Bb-Cm)Hopeful\nMinor"),
    K("DS_CHORDPROG7", "C Minor\nProg\n7", "i-iv-VII-I\n(Cm-Fm-Bb-Eb)Natural\nMinor"),
    K("DS_CHORDPROG9", "C Minor\nProg\n9", "iv-III-i-VII\n(Fm-Eb-Cm-Bb)Downward\nMinor"),
    K("DS_CHORDPROG10", "C Minor\nProg\n10", "i-VII-v-VI\n(Cm-Bb-Gm-Ab)Sensitive\nMinor"),
    K("DS_CHORDPROG11", "C Minor\nProg\n11", "i-v-VI-ii\n(Cm-Gm-Ab-Dm)Circular\nMinor"),
]

# Eb KEY - MAJOR PROGRESSIONS
KEYCODES_E_FLAT_CHORDPROG_BASIC_MAJOR = [
    K("DS_CHORDPROG2", "Eb Major\nProg\n2", "I-IV-V\n(Eb-Ab-Bb)Simple\nMajor"),
    K("DS_CHORDPROG4", "Eb Major\nProg\n4", "I-vi-IV-V\n(Eb-Cm-Ab-Bb)50s\nProgression"),
    K("DS_CHORDPROG5", "Eb Major\nProg\n5", "I-V-vi-IV\n(Eb-Bb-Cm-Ab)Classic\nFour-Chord"),
    K("DS_CHORDPROG6", "Eb Major\nProg\n6", "vi-IV-I-V\n(Cm-Ab-Eb-Bb)Axis\nProgression"),
    K("DS_CHORDPROG8", "Eb Major\nProg\n8", "I-V-IV-IV\n(Eb-Bb-Ab-Ab)Rock\nProgression"),
    K("DS_CHORDPROG12", "Eb Major\nProg\n12", "I-ii-vi-V\n(Eb-Fm-Cm-Bb)Summer\nHit"),
    K("DS_CHORDPROG13", "Eb Major\nProg\n13", "I-V-vi-iii\nIV-I-IV-V\n(Eb-Bb-Cm-Gm\nAb-Eb-Ab-Bb)Canon\nProgression"),
]

# Eb KEY - INTERMEDIATE MINOR PROGRESSIONS
KEYCODES_E_FLAT_CHORDPROG_INTERMEDIATE_MINOR = [
    K("DS_CHORDPROG14", "C Minor\nProg\n14", "i-VII-VI-V\n(Cm-Bb-Ab-G)Andalusian\nCadence"),
    K("DS_CHORDPROG15", "C Minor\nProg\n15", "i-bVI-bVII-V\n(Cm-Ab-Bb-G)Harmonic\nTension"),
    K("DS_CHORDPROG18", "C Minor\nProg\n18", "i-bVII-VI-V\n(Cm-Bb-Ab-G)Melancholic\nMinor"),
    K("DS_CHORDPROG20", "C Minor\nProg\n20", "i-V-VI-VIm\n(Cm-G-Ab-Abm)Darkening\nMinor"),
    K("DS_CHORDPROG24", "C Minor\nProg\n24", "im7-bVImaj7\nbVII7-V7\n(Cm7-Abmaj7\nBb7-G7)Jazz\nMinor"),
    K("DS_CHORDPROG27", "C Minor\nProg\n27", "VI-#viidim\nV7-i-VII\n(Ab-Bdim\nG7-Cm-Bb)Diminished\nDominant"),
]

# Eb KEY - INTERMEDIATE MAJOR PROGRESSIONS
KEYCODES_E_FLAT_CHORDPROG_INTERMEDIATE_MAJOR = [
    K("DS_CHORDPROG16", "Eb Major\nProg\n16", "I-III-IV-iv\n(Eb-G-Ab-Abm)Creep\nProgression"),
    K("DS_CHORDPROG17", "Eb Major\nProg\n17", "I-III-VII-II\n(Eb-G-Bb-F)Pumped\nKicks"),
    K("DS_CHORDPROG19", "Eb Major\nProg\n19", "I-V-bVII-IV\n(Eb-Bb-Db-Ab)Rebel\nProgression"),
    K("DS_CHORDPROG21", "Eb Major\nProg\n21", "Isus2-IVsus2\nvi-V\n(Ebsus2-Absus2\nCm-Bb)Ambient\nFloat"),
    K("DS_CHORDPROG22", "Eb Major\nProg\n22", "IVsus2-Vsus4\nIsus2-vi\n(Absus2-Bbsus4\nEbsus2-Cm)Shoegaze\nShimmer"),
    K("DS_CHORDPROG23", "Eb Major\nProg\n23", "ii7-V7-Imaj7\n(Fm7-Bb7-\nEbmaj7)2-5-1\nProgression"),
    K("DS_CHORDPROG25", "Eb Major\nProg\n25", "vi7-ii7-V7\nImaj7\n(Cm7-Fm7-Bb7\nEbmaj7)6-2-5-1\nProgression"),
    K("DS_CHORDPROG26", "Eb Major\nProg\n26", "Imaj7-iim7\niiim7-IVadd2\n(Ebmaj7-Fm7\nGm7-Abadd2)Gentle\nCity"),
]

# Eb KEY - EXPERT MINOR PROGRESSIONS
KEYCODES_E_FLAT_CHORDPROG_EXPERT_MINOR = [
    K("DS_CHORDPROG30", "C Minor\nProg\n30", "vim9-iiim9\niim9-Imaj9\n(Cm9-Gm9\nFm9-Ebmaj9)Bring\nThe 9th"),
    K("DS_CHORDPROG32", "C Minor\nProg\n32", "im9-ivaddD\nbVImaj7\nbVIIadd2\n(Cm9-Fmadd9\nAbmaj7-Bbadd2)Modern\nMinor 9"),
    K("DS_CHORDPROG33", "C Minor\nProg\n33", "im9-iim9-vm9\n(Cm9-Fm9\nGm9)Lo-Fi\nNinths"),
    K("DS_CHORDPROG34", "C Minor\nProg\n34", "im9-vm9\nVImaj9-im9\nVImaj9\nviim9\n(Cm9-Gm9\nAbmaj9-Cm9\nAbmaj9-Bbm9)Ninth\nJourney"),
    K("DS_CHORDPROG37", "C Minor\nProg\n37", "im9-IVmaj7\niim7b5-V7\n(Cm9-Abmaj7\nFm7b5-G7)Minor Jazz\nII-V-I"),
    K("DS_CHORDPROG40", "C Minor\nProg\n40", "im9-V7b9\nVImaj9\niim9-vm7\n(Cm9-G7b9\nAbmaj9\nFm9-Gm7)Altered\nDominant"),
]

# Eb KEY - EXPERT MAJOR PROGRESSIONS
KEYCODES_E_FLAT_CHORDPROG_EXPERT_MAJOR = [
    K("DS_CHORDPROG28", "Eb Major\nProg\n28", "IVmaj7-V7\niiim7-vim7\niim7-III7\nvim7\n(Abmaj7-Bb7\nGm7-Cm7\nFm7-G7-Cm7)Anime\nProgression"),
    K("DS_CHORDPROG29", "Eb Major\nProg\n29", "IVmaj7-III7\nvim7-II7\niim7-V7\nImaj7\n(Abmaj7-G7\nCm7-F7\nFm7-Bb7\nEbmaj7)She's\nLovely"),
    K("DS_CHORDPROG31", "Eb Major\nProg\n31", "IVmaj7-V7\niiim9-vim7\n(Abmaj7-Bb7\nGm9-Cm7)Neo-Pop\nTurnaround"),
    K("DS_CHORDPROG35", "Eb Major\nProg\n35", "IVmaj7-iiim7\n#iiidim7\niim7-iim7b5\nImaj7\n(Abmaj7-Gm7\nGbdim7\nFm7-Fm7b5\nEbmaj7)Descending\nDiminished"),
    K("DS_CHORDPROG36", "Eb Major\nProg\n36", "Imaj7-#idim7\niim7-#iidim7\niiim7\nbiiidim7\n(Ebmaj7\nEdim7-Fm7\nGbdim7-Gm7\nGbdim7)Diminished\nBridge"),
    K("DS_CHORDPROG38", "Eb Major\nProg\n38", "I-vi-ii\nbVII7-I\n(Ebmaj7-Cm7\nFm7-Db7)Backdoor\nProgression"),
    K("DS_CHORDPROG39", "Eb Major\nProg\n39", "Imaj7\nbIIImaj7\niim7-iiim7\n(Ebmaj7\nGbmaj7\nFm7-Gm7)Modal\nMixture"),
    K("DS_CHORDPROG41", "Eb Major\nProg\n41", "Imaj9-I7\niim7-VII7b9\nV7-III7b9\nIV-IVdim7\n(Ebmaj9-Eb7\nFm7-D7b9\nBb7-G7b9\nAbmaj7-Abdim7)Complex\n2-5-1-4"),
    K("DS_CHORDPROG42", "Eb Major\nProg\n42", "Imaj7-vi7\nii7-bII7\n(Ebmaj7-Cm7\nFm7-E7)Tritone\nSubstitution"),
]

# E KEY - MINOR PROGRESSIONS
KEYCODES_E_CHORDPROG_BASIC_MINOR = [
    K("E_CHORDPROG1", "C# Minor\nProg\n1", "i-VII-VI\n(C#m-B-A)Simple\nMinor"),
    K("E_CHORDPROG3", "C# Minor\nProg\n3", "VI-VII-i\n(A-B-C#m)Hopeful\nMinor"),
    K("E_CHORDPROG7", "C# Minor\nProg\n7", "i-iv-VII-I\n(C#m-F#m-B-E)Natural\nMinor"),
    K("E_CHORDPROG9", "C# Minor\nProg\n9", "iv-III-i-VII\n(F#m-E-C#m-B)Downward\nMinor"),
    K("E_CHORDPROG10", "C# Minor\nProg\n10", "i-VII-v-VI\n(C#m-B-G#m-A)Sensitive\nMinor"),
    K("E_CHORDPROG11", "C# Minor\nProg\n11", "i-v-VI-ii\n(C#m-G#m-A-D#m)Circular\nMinor"),
]

# E KEY - MAJOR PROGRESSIONS
KEYCODES_E_CHORDPROG_BASIC_MAJOR = [
    K("E_CHORDPROG2", "E Major\nProg\n2", "I-IV-V\n(E-A-B)Simple\nMajor"),
    K("E_CHORDPROG4", "E Major\nProg\n4", "I-vi-IV-V\n(E-C#m-A-B)50s\nProgression"),
    K("E_CHORDPROG5", "E Major\nProg\n5", "I-V-vi-IV\n(E-B-C#m-A)Classic\nFour-Chord"),
    K("E_CHORDPROG6", "E Major\nProg\n6", "vi-IV-I-V\n(C#m-A-E-B)Axis\nProgression"),
    K("E_CHORDPROG8", "E Major\nProg\n8", "I-V-IV-IV\n(E-B-A-A)Rock\nProgression"),
    K("E_CHORDPROG12", "E Major\nProg\n12", "I-ii-vi-V\n(E-F#m-C#m-B)Summer\nHit"),
    K("E_CHORDPROG13", "E Major\nProg\n13", "I-V-vi-iii\nIV-I-IV-V\n(E-B-C#m-G#m\nA-E-A-B)Canon\nProgression"),
]

# E KEY - INTERMEDIATE MINOR PROGRESSIONS
KEYCODES_E_CHORDPROG_INTERMEDIATE_MINOR = [
    K("E_CHORDPROG14", "C# Minor\nProg\n14", "i-VII-VI-V\n(C#m-B-A-G#)Andalusian\nCadence"),
    K("E_CHORDPROG15", "C# Minor\nProg\n15", "i-bVI-bVII-V\n(C#m-A-B-G#)Harmonic\nTension"),
    K("E_CHORDPROG18", "C# Minor\nProg\n18", "i-bVII-VI-V\n(C#m-B-A-G#)Melancholic\nMinor"),
    K("E_CHORDPROG20", "C# Minor\nProg\n20", "i-V-VI-VIm\n(C#m-G#-A-Am)Darkening\nMinor"),
    K("E_CHORDPROG24", "C# Minor\nProg\n24", "im7-bVImaj7\nbVII7-V7\n(C#m7-Amaj7\nB7-G#7)Jazz\nMinor"),
    K("E_CHORDPROG27", "C# Minor\nProg\n27", "VI-#viidim\nV7-i-VII\n(A-Cdim\nG#7-C#m-B)Diminished\nDominant"),
]

# E KEY - INTERMEDIATE MAJOR PROGRESSIONS
KEYCODES_E_CHORDPROG_INTERMEDIATE_MAJOR = [
    K("E_CHORDPROG16", "E Major\nProg\n16", "I-III-IV-iv\n(E-G#-A-Am)Creep\nProgression"),
    K("E_CHORDPROG17", "E Major\nProg\n17", "I-III-VII-II\n(E-G#-B-F#)Pumped\nKicks"),
    K("E_CHORDPROG19", "E Major\nProg\n19", "I-V-bVII-IV\n(E-B-D-A)Rebel\nProgression"),
    K("E_CHORDPROG21", "E Major\nProg\n21", "Isus2-IVsus2\nvi-V\n(Esus2-Asus2\nC#m-B)Ambient\nFloat"),
    K("E_CHORDPROG22", "E Major\nProg\n22", "IVsus2-Vsus4\nIsus2-vi\n(Asus2-Bsus4\nEsus2-C#m)Shoegaze\nShimmer"),
    K("E_CHORDPROG23", "E Major\nProg\n23", "ii7-V7-Imaj7\n(F#m7-B7-\nEmaj7)2-5-1\nProgression"),
    K("E_CHORDPROG25", "E Major\nProg\n25", "vi7-ii7-V7\nImaj7\n(C#m7-F#m7-B7\nEmaj7)6-2-5-1\nProgression"),
    K("E_CHORDPROG26", "E Major\nProg\n26", "Imaj7-iim7\niiim7-IVadd2\n(Emaj7-F#m7\nG#m7-Aadd2)Gentle\nCity"),
]

# E KEY - EXPERT MINOR PROGRESSIONS
KEYCODES_E_CHORDPROG_EXPERT_MINOR = [
    K("E_CHORDPROG30", "C# Minor\nProg\n30", "vim9-iiim9\niim9-Imaj9\n(C#m9-G#m9\nF#m9-Emaj9)Bring\nThe 9th"),
    K("E_CHORDPROG32", "C# Minor\nProg\n32", "im9-ivaddD\nbVImaj7\nbVIIadd2\n(C#m9-F#madd9\nAmaj7-Badd2)Modern\nMinor 9"),
    K("E_CHORDPROG33", "C# Minor\nProg\n33", "im9-iim9-vm9\n(C#m9-F#m9\nG#m9)Lo-Fi\nNinths"),
    K("E_CHORDPROG34", "C# Minor\nProg\n34", "im9-vm9\nVImaj9-im9\nVImaj9\nviim9\n(C#m9-G#m9\nAmaj9-C#m9\nAmaj9-Bm9)Ninth\nJourney"),
    K("E_CHORDPROG37", "C# Minor\nProg\n37", "im9-IVmaj7\niim7b5-V7\n(C#m9-Amaj7\nF#m7b5-G#7)Minor Jazz\nII-V-I"),
    K("E_CHORDPROG40", "C# Minor\nProg\n40", "im9-V7b9\nVImaj9\niim9-vm7\n(C#m9-G#7b9\nAmaj9\nF#m9-G#m7)Altered\nDominant"),
]

# E KEY - EXPERT MAJOR PROGRESSIONS
KEYCODES_E_CHORDPROG_EXPERT_MAJOR = [
    K("E_CHORDPROG28", "E Major\nProg\n28", "IVmaj7-V7\niiim7-vim7\niim7-III7\nvim7\n(Amaj7-B7\nG#m7-C#m7\nF#m7-G#7-C#m7)Anime\nProgression"),
    K("E_CHORDPROG29", "E Major\nProg\n29", "IVmaj7-III7\nvim7-II7\niim7-V7\nImaj7\n(Amaj7-G#7\nC#m7-F#7\nF#m7-B7\nEmaj7)She's\nLovely"),
    K("E_CHORDPROG31", "E Major\nProg\n31", "IVmaj7-V7\niiim9-vim7\n(Amaj7-B7\nG#m9-C#m7)Neo-Pop\nTurnaround"),
    K("E_CHORDPROG35", "E Major\nProg\n35", "IVmaj7-iiim7\n#iiidim7\niim7-iim7b5\nImaj7\n(Amaj7-G#m7\nGdim7\nF#m7-F#m7b5\nEmaj7)Descending\nDiminished"),
    K("E_CHORDPROG36", "E Major\nProg\n36", "Imaj7-#idim7\niim7-#iidim7\niiim7\nbiiidim7\n(Emaj7\nFdim7-F#m7\nGdim7-G#m7\nGdim7)Diminished\nBridge"),
    K("E_CHORDPROG38", "E Major\nProg\n38", "I-vi-ii\nbVII7-I\n(Emaj7-C#m7\nF#m7-D7)Backdoor\nProgression"),
    K("E_CHORDPROG39", "E Major\nProg\n39", "Imaj7\nbIIImaj7\niim7-iiim7\n(Emaj7\nGmaj7\nF#m7-G#m7)Modal\nMixture"),
    K("E_CHORDPROG41", "E Major\nProg\n41", "Imaj9-I7\niim7-VII7b9\nV7-III7b9\nIV-IVdim7\n(Emaj9-E7\nF#m7-D#7b9\nB7-G#7b9\nAmaj7-Adim7)Complex\n2-5-1-4"),
    K("E_CHORDPROG42", "E Major\nProg\n42", "Imaj7-vi7\nii7-bII7\n(Emaj7-C#m7\nF#m7-F7)Tritone\nSubstitution"),
]

# F KEY - MINOR PROGRESSIONS
KEYCODES_F_CHORDPROG_BASIC_MINOR = [
    K("F_CHORDPROG1", "D Minor\nProg\n1", "i-VII-VI\n(Dm-C-Bb)Simple\nMinor"),
    K("F_CHORDPROG3", "D Minor\nProg\n3", "VI-VII-i\n(Bb-C-Dm)Hopeful\nMinor"),
    K("F_CHORDPROG7", "D Minor\nProg\n7", "i-iv-VII-I\n(Dm-Gm-C-F)Natural\nMinor"),
    K("F_CHORDPROG9", "D Minor\nProg\n9", "iv-III-i-VII\n(Gm-F-Dm-C)Downward\nMinor"),
    K("F_CHORDPROG10", "D Minor\nProg\n10", "i-VII-v-VI\n(Dm-C-Am-Bb)Sensitive\nMinor"),
    K("F_CHORDPROG11", "D Minor\nProg\n11", "i-v-VI-ii\n(Dm-Am-Bb-Em)Circular\nMinor"),
]

# F KEY - MAJOR PROGRESSIONS
KEYCODES_F_CHORDPROG_BASIC_MAJOR = [
    K("F_CHORDPROG2", "F Major\nProg\n2", "I-IV-V\n(F-Bb-C)Simple\nMajor"),
    K("F_CHORDPROG4", "F Major\nProg\n4", "I-vi-IV-V\n(F-Dm-Bb-C)50s\nProgression"),
    K("F_CHORDPROG5", "F Major\nProg\n5", "I-V-vi-IV\n(F-C-Dm-Bb)Classic\nFour-Chord"),
    K("F_CHORDPROG6", "F Major\nProg\n6", "vi-IV-I-V\n(Dm-Bb-F-C)Axis\nProgression"),
    K("F_CHORDPROG8", "F Major\nProg\n8", "I-V-IV-IV\n(F-C-Bb-Bb)Rock\nProgression"),
    K("F_CHORDPROG12", "F Major\nProg\n12", "I-ii-vi-V\n(F-Gm-Dm-C)Summer\nHit"),
    K("F_CHORDPROG13", "F Major\nProg\n13", "I-V-vi-iii\nIV-I-IV-V\n(F-C-Dm-Am\nBb-F-Bb-C)Canon\nProgression"),
]

# F KEY - INTERMEDIATE MINOR PROGRESSIONS
KEYCODES_F_CHORDPROG_INTERMEDIATE_MINOR = [
    K("F_CHORDPROG14", "D Minor\nProg\n14", "i-VII-VI-V\n(Dm-C-Bb-A)Andalusian\nCadence"),
    K("F_CHORDPROG15", "D Minor\nProg\n15", "i-bVI-bVII-V\n(Dm-Bb-C-A)Harmonic\nTension"),
    K("F_CHORDPROG18", "D Minor\nProg\n18", "i-bVII-VI-V\n(Dm-C-Bb-A)Melancholic\nMinor"),
    K("F_CHORDPROG20", "D Minor\nProg\n20", "i-V-VI-VIm\n(Dm-A-Bb-Bbm)Darkening\nMinor"),
    K("F_CHORDPROG24", "D Minor\nProg\n24", "im7-bVImaj7\nbVII7-V7\n(Dm7-Bbmaj7\nC7-A7)Jazz\nMinor"),
    K("F_CHORDPROG27", "D Minor\nProg\n27", "VI-#viidim\nV7-i-VII\n(Bb-C#dim\nA7-Dm-C)Diminished\nDominant"),
]

# F KEY - INTERMEDIATE MAJOR PROGRESSIONS
KEYCODES_F_CHORDPROG_INTERMEDIATE_MAJOR = [
    K("F_CHORDPROG16", "F Major\nProg\n16", "I-III-IV-iv\n(F-A-Bb-Bbm)Creep\nProgression"),
    K("F_CHORDPROG17", "F Major\nProg\n17", "I-III-VII-II\n(F-A-C-G)Pumped\nKicks"),
    K("F_CHORDPROG19", "F Major\nProg\n19", "I-V-bVII-IV\n(F-C-Eb-Bb)Rebel\nProgression"),
    K("F_CHORDPROG21", "F Major\nProg\n21", "Isus2-IVsus2\nvi-V\n(Fsus2-Bbsus2\nDm-C)Ambient\nFloat"),
    K("F_CHORDPROG22", "F Major\nProg\n22", "IVsus2-Vsus4\nIsus2-vi\n(Bbsus2-Csus4\nFsus2-Dm)Shoegaze\nShimmer"),
    K("F_CHORDPROG23", "F Major\nProg\n23", "ii7-V7-Imaj7\n(Gm7-C7-\nFmaj7)2-5-1\nProgression"),
    K("F_CHORDPROG25", "F Major\nProg\n25", "vi7-ii7-V7\nImaj7\n(Dm7-Gm7-C7\nFmaj7)6-2-5-1\nProgression"),
    K("F_CHORDPROG26", "F Major\nProg\n26", "Imaj7-iim7\niiim7-IVadd2\n(Fmaj7-Gm7\nAm7-Bbadd2)Gentle\nCity"),
]

# F KEY - EXPERT MINOR PROGRESSIONS
KEYCODES_F_CHORDPROG_EXPERT_MINOR = [
    K("F_CHORDPROG30", "D Minor\nProg\n30", "vim9-iiim9\niim9-Imaj9\n(Dm9-Am9\nGm9-Fmaj9)Bring\nThe 9th"),
    K("F_CHORDPROG32", "D Minor\nProg\n32", "im9-ivaddD\nbVImaj7\nbVIIadd2\n(Dm9-Gmadd9\nBbmaj7-Cadd2)Modern\nMinor 9"),
    K("F_CHORDPROG33", "D Minor\nProg\n33", "im9-iim9-vm9\n(Dm9-Gm9\nAm9)Lo-Fi\nNinths"),
    K("F_CHORDPROG34", "D Minor\nProg\n34", "im9-vm9\nVImaj9-im9\nVImaj9\nviim9\n(Dm9-Am9\nBbmaj9-Dm9\nBbmaj9-Cm9)Ninth\nJourney"),
    K("F_CHORDPROG37", "D Minor\nProg\n37", "im9-IVmaj7\niim7b5-V7\n(Dm9-Bbmaj7\nGm7b5-A7)Minor Jazz\nII-V-I"),
    K("F_CHORDPROG40", "D Minor\nProg\n40", "im9-V7b9\nVImaj9\niim9-vm7\n(Dm9-A7b9\nBbmaj9\nGm9-Am7)Altered\nDominant"),
]

# F KEY - EXPERT MAJOR PROGRESSIONS
KEYCODES_F_CHORDPROG_EXPERT_MAJOR = [
    K("F_CHORDPROG28", "F Major\nProg\n28", "IVmaj7-V7\niiim7-vim7\niim7-III7\nvim7\n(Bbmaj7-C7\nAm7-Dm7\nGm7-A7-Dm7)Anime\nProgression"),
    K("F_CHORDPROG29", "F Major\nProg\n29", "IVmaj7-III7\nvim7-II7\niim7-V7\nImaj7\n(Bbmaj7-A7\nDm7-G7\nGm7-C7\nFmaj7)She's\nLovely"),
    K("F_CHORDPROG31", "F Major\nProg\n31", "IVmaj7-V7\niiim9-vim7\n(Bbmaj7-C7\nAm9-Dm7)Neo-Pop\nTurnaround"),
    K("F_CHORDPROG35", "F Major\nProg\n35", "IVmaj7-iiim7\n#iiidim7\niim7-iim7b5\nImaj7\n(Bbmaj7-Am7\nAbdim7\nGm7-Gm7b5\nFmaj7)Descending\nDiminished"),
    K("F_CHORDPROG36", "F Major\nProg\n36", "Imaj7-#idim7\niim7-#iidim7\niiim7\nbiiidim7\n(Fmaj7\nF#dim7-Gm7\nG#dim7-Am7\nAbdim7)Diminished\nBridge"),
    K("F_CHORDPROG38", "F Major\nProg\n38", "I-vi-ii\nbVII7-I\n(Fmaj7-Dm7\nGm7-Eb7)Backdoor\nProgression"),
    K("F_CHORDPROG39", "F Major\nProg\n39", "Imaj7\nbIIImaj7\niim7-iiim7\n(Fmaj7\nAbmaj7\nGm7-Am7)Modal\nMixture"),
    K("F_CHORDPROG41", "F Major\nProg\n41", "Imaj9-I7\niim7-VII7b9\nV7-III7b9\nIV-IVdim7\n(Fmaj9-F7\nGm7-E7b9\nC7-A7b9\nBbmaj7-Bbdim7)Complex\n2-5-1-4"),
    K("F_CHORDPROG42", "F Major\nProg\n42", "Imaj7-vi7\nii7-bII7\n(Fmaj7-Dm7\nGm7-Gb7)Tritone\nSubstitution"),
]

# F# KEY - MINOR PROGRESSIONS
KEYCODES_F_SHARP_CHORDPROG_BASIC_MINOR = [
    K("FS_CHORDPROG1", "Eb Minor\nProg\n1", "i-VII-VI\n(Ebm-Db-Cb)Simple\nMinor"),
    K("FS_CHORDPROG3", "Eb Minor\nProg\n3", "VI-VII-i\n(Cb-Db-Ebm)Hopeful\nMinor"),
    K("FS_CHORDPROG7", "Eb Minor\nProg\n7", "i-iv-VII-I\n(Ebm-Abm-Db-Gb)Natural\nMinor"),
    K("FS_CHORDPROG9", "Eb Minor\nProg\n9", "iv-III-i-VII\n(Abm-Gb-Ebm-Db)Downward\nMinor"),
    K("FS_CHORDPROG10", "Eb Minor\nProg\n10", "i-VII-v-VI\n(Ebm-Db-Bbm-Cb)Sensitive\nMinor"),
    K("FS_CHORDPROG11", "Eb Minor\nProg\n11", "i-v-VI-ii\n(Ebm-Bbm-Cb-Fm)Circular\nMinor"),
]

# F# KEY - MINOR PROGRESSIONS
KEYCODES_F_SHARP_CHORDPROG_BASIC_MINOR = [
    K("FS_CHORDPROG1", "D# Minor\nProg\n1", "i-VII-VI\n(D#m-C#-B)Simple\nMinor"),
    K("FS_CHORDPROG3", "D# Minor\nProg\n3", "VI-VII-i\n(B-C#-D#m)Hopeful\nMinor"),
    K("FS_CHORDPROG7", "D# Minor\nProg\n7", "i-iv-VII-I\n(D#m-G#m-C#-F#)Natural\nMinor"),
    K("FS_CHORDPROG9", "D# Minor\nProg\n9", "iv-III-i-VII\n(G#m-F#-D#m-C#)Downward\nMinor"),
    K("FS_CHORDPROG10", "D# Minor\nProg\n10", "i-VII-v-VI\n(D#m-C#-A#m-B)Sensitive\nMinor"),
    K("FS_CHORDPROG11", "D# Minor\nProg\n11", "i-v-VI-ii\n(D#m-A#m-B-F)Circular\nMinor"),
]

# F# KEY - MAJOR PROGRESSIONS
KEYCODES_F_SHARP_CHORDPROG_BASIC_MAJOR = [
    K("FS_CHORDPROG2", "F# Major\nProg\n2", "I-IV-V\n(F#-B-C#)Simple\nMajor"),
    K("FS_CHORDPROG4", "F# Major\nProg\n4", "I-vi-IV-V\n(F#-D#m-B-C#)50s\nProgression"),
    K("FS_CHORDPROG5", "F# Major\nProg\n5", "I-V-vi-IV\n(F#-C#-D#m-B)Classic\nFour-Chord"),
    K("FS_CHORDPROG6", "F# Major\nProg\n6", "vi-IV-I-V\n(D#m-B-F#-C#)Axis\nProgression"),
    K("FS_CHORDPROG8", "F# Major\nProg\n8", "I-V-IV-IV\n(F#-C#-B-B)Rock\nProgression"),
    K("FS_CHORDPROG12", "F# Major\nProg\n12", "I-ii-vi-V\n(F#-G#m-D#m-C#)Summer\nHit"),
    K("FS_CHORDPROG13", "F# Major\nProg\n13", "I-V-vi-iii\nIV-I-IV-V\n(F#-C#-D#m-A#m\nB-F#-B-C#)Canon\nProgression"),
]

# F# KEY - INTERMEDIATE MINOR PROGRESSIONS
KEYCODES_F_SHARP_CHORDPROG_INTERMEDIATE_MINOR = [
    K("FS_CHORDPROG14", "D# Minor\nProg\n14", "i-VII-VI-V\n(D#m-C#-B-A#)Andalusian\nCadence"),
    K("FS_CHORDPROG15", "D# Minor\nProg\n15", "i-bVI-bVII-V\n(D#m-B-C#-A#)Harmonic\nTension"),
    K("FS_CHORDPROG18", "D# Minor\nProg\n18", "i-bVII-VI-V\n(D#m-C#-B-A#)Melancholic\nMinor"),
    K("FS_CHORDPROG20", "D# Minor\nProg\n20", "i-V-VI-VIm\n(D#m-A#-B-Bm)Darkening\nMinor"),
    K("FS_CHORDPROG24", "D# Minor\nProg\n24", "im7-bVImaj7\nbVII7-V7\n(D#m7-Bmaj7\nC#7-A#7)Jazz\nMinor"),
    K("FS_CHORDPROG27", "D# Minor\nProg\n27", "VI-#viidim\nV7-i-VII\n(B-Fdim\nA#7-D#m-C#)Diminished\nDominant"),
]

# F# KEY - INTERMEDIATE MAJOR PROGRESSIONS
KEYCODES_F_SHARP_CHORDPROG_INTERMEDIATE_MAJOR = [
    K("FS_CHORDPROG16", "F# Major\nProg\n16", "I-III-IV-iv\n(F#-A#-B-Bm)Creep\nProgression"),
    K("FS_CHORDPROG17", "F# Major\nProg\n17", "I-III-VII-II\n(F#-A#-E#-G#)Pumped\nKicks"),
    K("FS_CHORDPROG19", "F# Major\nProg\n19", "I-V-bVII-IV\n(F#-C#-E-B)Rebel\nProgression"),
    K("FS_CHORDPROG21", "F# Major\nProg\n21", "Isus2-IVsus2\nvi-V\n(F#sus2-Bsus2\nD#m-C#)Ambient\nFloat"),
    K("FS_CHORDPROG22", "F# Major\nProg\n22", "IVsus2-Vsus4\nIsus2-vi\n(Bsus2-C#sus4\nF#sus2-D#m)Shoegaze\nShimmer"),
    K("FS_CHORDPROG23", "F# Major\nProg\n23", "ii7-V7-Imaj7\n(G#m7-C#7-\nF#maj7)2-5-1\nProgression"),
    K("FS_CHORDPROG25", "F# Major\nProg\n25", "vi7-ii7-V7\nImaj7\n(D#m7-G#m7-C#7\nF#maj7)6-2-5-1\nProgression"),
    K("FS_CHORDPROG26", "F# Major\nProg\n26", "Imaj7-iim7\niiim7-IVadd2\n(F#maj7-G#m7\nA#m7-Badd2)Gentle\nCity"),
]

# F# KEY - EXPERT MINOR PROGRESSIONS
KEYCODES_F_SHARP_CHORDPROG_EXPERT_MINOR = [
    K("FS_CHORDPROG30", "D# Minor\nProg\n30", "vim9-iiim9\niim9-Imaj9\n(D#m9-A#m9\nG#m9-F#maj9)Bring\nThe 9th"),
    K("FS_CHORDPROG32", "D# Minor\nProg\n32", "im9-ivaddD\nbVImaj7\nbVIIadd2\n(D#m9-G#madd9\nBmaj7-C#add2)Modern\nMinor 9"),
    K("FS_CHORDPROG33", "D# Minor\nProg\n33", "im9-iim9-vm9\n(D#m9-G#m9\nA#m9)Lo-Fi\nNinths"),
    K("FS_CHORDPROG34", "D# Minor\nProg\n34", "im9-vm9\nVImaj9-im9\nVImaj9\nviim9\n(D#m9-A#m9\nBmaj9-D#m9\nBmaj9-C#m9)Ninth\nJourney"),
    K("FS_CHORDPROG37", "D# Minor\nProg\n37", "im9-IVmaj7\niim7b5-V7\n(D#m9-Bmaj7\nG#m7b5-A#7)Minor Jazz\nII-V-I"),
    K("FS_CHORDPROG40", "D# Minor\nProg\n40", "im9-V7b9\nVImaj9\niim9-vm7\n(D#m9-A#7b9\nBmaj9\nG#m9-A#m7)Altered\nDominant"),
]

# F# KEY - EXPERT MAJOR PROGRESSIONS
KEYCODES_F_SHARP_CHORDPROG_EXPERT_MAJOR = [
    K("FS_CHORDPROG28", "F# Major\nProg\n28", "IVmaj7-V7\niiim7-vim7\niim7-III7\nvim7\n(Bmaj7-C#7\nA#m7-D#m7\nG#m7-A#7-D#m7)Anime\nProgression"),
    K("FS_CHORDPROG29", "F# Major\nProg\n29", "IVmaj7-III7\nvim7-II7\niim7-V7\nImaj7\n(Bmaj7-A#7\nD#m7-G#7\nG#m7-C#7\nF#maj7)She's\nLovely"),
    K("FS_CHORDPROG31", "F# Major\nProg\n31", "IVmaj7-V7\niiim9-vim7\n(Bmaj7-C#7\nA#m9-D#m7)Neo-Pop\nTurnaround"),
    K("FS_CHORDPROG35", "F# Major\nProg\n35", "IVmaj7-iiim7\n#iiidim7\niim7-iim7b5\nImaj7\n(Bmaj7-A#m7\nAdim7\nG#m7-G#m7b5\nF#maj7)Descending\nDiminished"),
    K("FS_CHORDPROG36", "F# Major\nProg\n36", "Imaj7-#idim7\niim7-#iidim7\niiim7\nbiiidim7\n(F#maj7\nGdim7-G#m7\nAdim7-A#m7\nAdim7)Diminished\nBridge"),
    K("FS_CHORDPROG38", "F# Major\nProg\n38", "I-vi-ii\nbVII7-I\n(F#maj7-D#m7\nG#m7-E7)Backdoor\nProgression"),
    K("FS_CHORDPROG39", "F# Major\nProg\n39", "Imaj7\nbIIImaj7\niim7-iiim7\n(F#maj7\nAmaj7\nG#m7-A#m7)Modal\nMixture"),
    K("FS_CHORDPROG41", "F# Major\nProg\n41", "Imaj9-I7\niim7-VII7b9\nV7-III7b9\nIV-IVdim7\n(F#maj9-F#7\nG#m7-F7b9\nC#7-A#7b9\nBmaj7-Bdim7)Complex\n2-5-1-4"),
    K("FS_CHORDPROG42", "F# Major\nProg\n42", "Imaj7-vi7\nii7-bII7\n(F#maj7-D#m7\nG#m7-G7)Tritone\nSubstitution"),
]

# G KEY - MINOR PROGRESSIONS
KEYCODES_G_CHORDPROG_BASIC_MINOR = [
    K("G_CHORDPROG1", "E Minor\nProg\n1", "i-VII-VI\n(Em-D-C)Simple\nMinor"),
    K("G_CHORDPROG3", "E Minor\nProg\n3", "VI-VII-i\n(C-D-Em)Hopeful\nMinor"),
    K("G_CHORDPROG7", "E Minor\nProg\n7", "i-iv-VII-I\n(Em-Am-D-G)Natural\nMinor"),
    K("G_CHORDPROG9", "E Minor\nProg\n9", "iv-III-i-VII\n(Am-G-Em-D)Downward\nMinor"),
    K("G_CHORDPROG10", "E Minor\nProg\n10", "i-VII-v-VI\n(Em-D-Bm-C)Sensitive\nMinor"),
    K("G_CHORDPROG11", "E Minor\nProg\n11", "i-v-VI-ii\n(Em-Bm-C-F#m)Circular\nMinor"),
]

# G KEY - MAJOR PROGRESSIONS
KEYCODES_G_CHORDPROG_BASIC_MAJOR = [
    K("G_CHORDPROG2", "G Major\nProg\n2", "I-IV-V\n(G-C-D)Simple\nMajor"),
    K("G_CHORDPROG4", "G Major\nProg\n4", "I-vi-IV-V\n(G-Em-C-D)50s\nProgression"),
    K("G_CHORDPROG5", "G Major\nProg\n5", "I-V-vi-IV\n(G-D-Em-C)Classic\nFour-Chord"),
    K("G_CHORDPROG6", "G Major\nProg\n6", "vi-IV-I-V\n(Em-C-G-D)Axis\nProgression"),
    K("G_CHORDPROG8", "G Major\nProg\n8", "I-V-IV-IV\n(G-D-C-C)Rock\nProgression"),
    K("G_CHORDPROG12", "G Major\nProg\n12", "I-ii-vi-V\n(G-Am-Em-D)Summer\nHit"),
    K("G_CHORDPROG13", "G Major\nProg\n13", "I-V-vi-iii\nIV-I-IV-V\n(G-D-Em-Bm\nC-G-C-D)Canon\nProgression"),
]

# G KEY - INTERMEDIATE MINOR PROGRESSIONS
KEYCODES_G_CHORDPROG_INTERMEDIATE_MINOR = [
    K("G_CHORDPROG14", "E Minor\nProg\n14", "i-VII-VI-V\n(Em-D-C-B)Andalusian\nCadence"),
    K("G_CHORDPROG15", "E Minor\nProg\n15", "i-bVI-bVII-V\n(Em-C-D-B)Harmonic\nTension"),
    K("G_CHORDPROG18", "E Minor\nProg\n18", "i-bVII-VI-V\n(Em-D-C-B)Melancholic\nMinor"),
    K("G_CHORDPROG20", "E Minor\nProg\n20", "i-V-VI-VIm\n(Em-B-C-Cm)Darkening\nMinor"),
    K("G_CHORDPROG24", "E Minor\nProg\n24", "im7-bVImaj7\nbVII7-V7\n(Em7-Cmaj7\nD7-B7)Jazz\nMinor"),
    K("G_CHORDPROG27", "E Minor\nProg\n27", "VI-#viidim\nV7-i-VII\n(C-D#dim\nB7-Em-D)Diminished\nDominant"),
]

# G KEY - INTERMEDIATE MAJOR PROGRESSIONS
KEYCODES_G_CHORDPROG_INTERMEDIATE_MAJOR = [
    K("G_CHORDPROG16", "G Major\nProg\n16", "I-III-IV-iv\n(G-B-C-Cm)Creep\nProgression"),
    K("G_CHORDPROG17", "G Major\nProg\n17", "I-III-VII-II\n(G-B-D-A)Pumped\nKicks"),
    K("G_CHORDPROG19", "G Major\nProg\n19", "I-V-bVII-IV\n(G-D-F-C)Rebel\nProgression"),
    K("G_CHORDPROG21", "G Major\nProg\n21", "Isus2-IVsus2\nvi-V\n(Gsus2-Csus2\nEm-D)Ambient\nFloat"),
    K("G_CHORDPROG22", "G Major\nProg\n22", "IVsus2-Vsus4\nIsus2-vi\n(Csus2-Dsus4\nGsus2-Em)Shoegaze\nShimmer"),
    K("G_CHORDPROG23", "G Major\nProg\n23", "ii7-V7-Imaj7\n(Am7-D7-\nGmaj7)2-5-1\nProgression"),
    K("G_CHORDPROG25", "G Major\nProg\n25", "vi7-ii7-V7\nImaj7\n(Em7-Am7-D7\nGmaj7)6-2-5-1\nProgression"),
    K("G_CHORDPROG26", "G Major\nProg\n26", "Imaj7-iim7\niiim7-IVadd2\n(Gmaj7-Am7\nBm7-Cadd2)Gentle\nCity"),
]

# G KEY - EXPERT MINOR PROGRESSIONS
KEYCODES_G_CHORDPROG_EXPERT_MINOR = [
    K("G_CHORDPROG30", "E Minor\nProg\n30", "vim9-iiim9\niim9-Imaj9\n(Em9-Bm9\nAm9-Gmaj9)Bring\nThe 9th"),
    K("G_CHORDPROG32", "E Minor\nProg\n32", "im9-ivaddD\nbVImaj7\nbVIIadd2\n(Em9-Amadd9\nCmaj7-Dadd2)Modern\nMinor 9"),
    K("G_CHORDPROG33", "E Minor\nProg\n33", "im9-iim9-vm9\n(Em9-Am9\nBm9)Lo-Fi\nNinths"),
    K("G_CHORDPROG34", "E Minor\nProg\n34", "im9-vm9\nVImaj9-im9\nVImaj9\nviim9\n(Em9-Bm9\nCmaj9-Em9\nCmaj9-Dm9)Ninth\nJourney"),
    K("G_CHORDPROG37", "E Minor\nProg\n37", "im9-IVmaj7\niim7b5-V7\n(Em9-Cmaj7\nAm7b5-B7)Minor Jazz\nII-V-I"),
    K("G_CHORDPROG40", "E Minor\nProg\n40", "im9-V7b9\nVImaj9\niim9-vm7\n(Em9-B7b9\nCmaj9\nAm9-Bm7)Altered\nDominant"),
]

# G KEY - EXPERT MAJOR PROGRESSIONS
KEYCODES_G_CHORDPROG_EXPERT_MAJOR = [
    K("G_CHORDPROG28", "G Major\nProg\n28", "IVmaj7-V7\niiim7-vim7\niim7-III7\nvim7\n(Cmaj7-D7\nBm7-Em7\nAm7-B7-Em7)Anime\nProgression"),
    K("G_CHORDPROG29", "G Major\nProg\n29", "IVmaj7-III7\nvim7-II7\niim7-V7\nImaj7\n(Cmaj7-B7\nEm7-A7\nAm7-D7\nGmaj7)She's\nLovely"),
    K("G_CHORDPROG31", "G Major\nProg\n31", "IVmaj7-V7\niiim9-vim7\n(Cmaj7-D7\nBm9-Em7)Neo-Pop\nTurnaround"),
    K("G_CHORDPROG35", "G Major\nProg\n35", "IVmaj7-iiim7\n#iiidim7\niim7-iim7b5\nImaj7\n(Cmaj7-Bm7\nA#dim7\nAm7-Am7b5\nGmaj7)Descending\nDiminished"),
    K("G_CHORDPROG36", "G Major\nProg\n36", "Imaj7-#idim7\niim7-#iidim7\niiim7\nbiiidim7\n(Gmaj7\nG#dim7-Am7\nA#dim7-Bm7\nA#dim7)Diminished\nBridge"),
    K("G_CHORDPROG38", "G Major\nProg\n38", "I-vi-ii\nbVII7-I\n(Gmaj7-Em7\nAm7-F7)Backdoor\nProgression"),
    K("G_CHORDPROG39", "G Major\nProg\n39", "Imaj7\nbIIImaj7\niim7-iiim7\n(Gmaj7\nBbmaj7\nAm7-Bm7)Modal\nMixture"),
    K("G_CHORDPROG41", "G Major\nProg\n41", "Imaj9-I7\niim7-VII7b9\nV7-III7b9\nIV-IVdim7\n(Gmaj9-G7\nAm7-F#7b9\nD7-B7b9\nCmaj7-Cdim7)Complex\n2-5-1-4"),
    K("G_CHORDPROG42", "G Major\nProg\n42", "Imaj7-vi7\nii7-bII7\n(Gmaj7-Em7\nAm7-G#7)Tritone\nSubstitution"),
]

# Ab KEY - MINOR PROGRESSIONS
KEYCODES_A_FLAT_CHORDPROG_BASIC_MINOR = [
    K("GS_CHORDPROG1", "F Minor\nProg\n1", "i-VII-VI\n(Fm-Eb-Db)Simple\nMinor"),
    K("GS_CHORDPROG3", "F Minor\nProg\n3", "VI-VII-i\n(Db-Eb-Fm)Hopeful\nMinor"),
    K("GS_CHORDPROG7", "F Minor\nProg\n7", "i-iv-VII-I\n(Fm-Bbm-Eb-Ab)Natural\nMinor"),
    K("GS_CHORDPROG9", "F Minor\nProg\n9", "iv-III-i-VII\n(Bbm-Ab-Fm-Eb)Downward\nMinor"),
    K("GS_CHORDPROG10", "F Minor\nProg\n10", "i-VII-v-VI\n(Fm-Eb-Cm-Db)Sensitive\nMinor"),
    K("GS_CHORDPROG11", "F Minor\nProg\n11", "i-v-VI-ii\n(Fm-Cm-Db-Gm)Circular\nMinor"),
]

# Ab KEY - MAJOR PROGRESSIONS
KEYCODES_A_FLAT_CHORDPROG_BASIC_MAJOR = [
    K("GS_CHORDPROG2", "Ab Major\nProg\n2", "I-IV-V\n(Ab-Db-Eb)Simple\nMajor"),
    K("GS_CHORDPROG4", "Ab Major\nProg\n4", "I-vi-IV-V\n(Ab-Fm-Db-Eb)50s\nProgression"),
    K("GS_CHORDPROG5", "Ab Major\nProg\n5", "I-V-vi-IV\n(Ab-Eb-Fm-Db)Classic\nFour-Chord"),
    K("GS_CHORDPROG6", "Ab Major\nProg\n6", "vi-IV-I-V\n(Fm-Db-Ab-Eb)Axis\nProgression"),
    K("GS_CHORDPROG8", "Ab Major\nProg\n8", "I-V-IV-IV\n(Ab-Eb-Db-Db)Rock\nProgression"),
    K("GS_CHORDPROG12", "Ab Major\nProg\n12", "I-ii-vi-V\n(Ab-Bbm-Fm-Eb)Summer\nHit"),
    K("GS_CHORDPROG13", "Ab Major\nProg\n13", "I-V-vi-iii\nIV-I-IV-V\n(Ab-Eb-Fm-Cm\nDb-Ab-Db-Eb)Canon\nProgression"),
]

# Ab KEY - INTERMEDIATE MINOR PROGRESSIONS
KEYCODES_A_FLAT_CHORDPROG_INTERMEDIATE_MINOR = [
    K("GS_CHORDPROG14", "F Minor\nProg\n14", "i-VII-VI-V\n(Fm-Eb-Db-C)Andalusian\nCadence"),
    K("GS_CHORDPROG15", "F Minor\nProg\n15", "i-bVI-bVII-V\n(Fm-Db-Eb-C)Harmonic\nTension"),
    K("GS_CHORDPROG18", "F Minor\nProg\n18", "i-bVII-VI-V\n(Fm-Eb-Db-C)Melancholic\nMinor"),
    K("GS_CHORDPROG20", "F Minor\nProg\n20", "i-V-VI-VIm\n(Fm-C-Db-Dbm)Darkening\nMinor"),
    K("GS_CHORDPROG24", "F Minor\nProg\n24", "im7-bVImaj7\nbVII7-V7\n(Fm7-Dbmaj7\nEb7-C7)Jazz\nMinor"),
    K("GS_CHORDPROG27", "F Minor\nProg\n27", "VI-#viidim\nV7-i-VII\n(Db-Edim\nC7-Fm-Eb)Diminished\nDominant"),
]

# Ab KEY - INTERMEDIATE MAJOR PROGRESSIONS
KEYCODES_A_FLAT_CHORDPROG_INTERMEDIATE_MAJOR = [
    K("GS_CHORDPROG16", "Ab Major\nProg\n16", "I-III-IV-iv\n(Ab-C-Db-Dbm)Creep\nProgression"),
    K("GS_CHORDPROG17", "Ab Major\nProg\n17", "I-III-VII-II\n(Ab-C-Eb-Bb)Pumped\nKicks"),
    K("GS_CHORDPROG19", "Ab Major\nProg\n19", "I-V-bVII-IV\n(Ab-Eb-Gb-Db)Rebel\nProgression"),
    K("GS_CHORDPROG21", "Ab Major\nProg\n21", "Isus2-IVsus2\nvi-V\n(Absus2-Dbsus2\nFm-Eb)Ambient\nFloat"),
    K("GS_CHORDPROG22", "Ab Major\nProg\n22", "IVsus2-Vsus4\nIsus2-vi\n(Dbsus2-Ebsus4\nAbsus2-Fm)Shoegaze\nShimmer"),
    K("GS_CHORDPROG23", "Ab Major\nProg\n23", "ii7-V7-Imaj7\n(Bbm7-Eb7-\nAbmaj7)2-5-1\nProgression"),
    K("GS_CHORDPROG25", "Ab Major\nProg\n25", "vi7-ii7-V7\nImaj7\n(Fm7-Bbm7-Eb7\nAbmaj7)6-2-5-1\nProgression"),
    K("GS_CHORDPROG26", "Ab Major\nProg\n26", "Imaj7-iim7\niiim7-IVadd2\n(Abmaj7-Bbm7\nCm7-Dbadd2)Gentle\nCity"),
]

# Ab KEY - EXPERT MINOR PROGRESSIONS
KEYCODES_A_FLAT_CHORDPROG_EXPERT_MINOR = [
    K("GS_CHORDPROG30", "F Minor\nProg\n30", "vim9-iiim9\niim9-Imaj9\n(Fm9-Cm9\nBbm9-Abmaj9)Bring\nThe 9th"),
    K("GS_CHORDPROG32", "F Minor\nProg\n32", "im9-ivaddD\nbVImaj7\nbVIIadd2\n(Fm9-Bbmadd9\nDbmaj7-Ebadd2)Modern\nMinor 9"),
    K("GS_CHORDPROG33", "F Minor\nProg\n33", "im9-iim9-vm9\n(Fm9-Bbm9\nCm9)Lo-Fi\nNinths"),
    K("GS_CHORDPROG34", "F Minor\nProg\n34", "im9-vm9\nVImaj9-im9\nVImaj9\nviim9\n(Fm9-Cm9\nDbmaj9-Fm9\nDbmaj9-Ebm9)Ninth\nJourney"),
    K("GS_CHORDPROG37", "F Minor\nProg\n37", "im9-IVmaj7\niim7b5-V7\n(Fm9-Dbmaj7\nBbm7b5-C7)Minor Jazz\nII-V-I"),
    K("GS_CHORDPROG40", "F Minor\nProg\n40", "im9-V7b9\nVImaj9\niim9-vm7\n(Fm9-C7b9\nDbmaj9\nBbm9-Cm7)Altered\nDominant"),
]

# Ab KEY - EXPERT MAJOR PROGRESSIONS
KEYCODES_A_FLAT_CHORDPROG_EXPERT_MAJOR = [
    K("GS_CHORDPROG28", "Ab Major\nProg\n28", "IVmaj7-V7\niiim7-vim7\niim7-III7\nvim7\n(Dbmaj7-Eb7\nCm7-Fm7\nBbm7-C7-Fm7)Anime\nProgression"),
    K("GS_CHORDPROG29", "Ab Major\nProg\n29", "IVmaj7-III7\nvim7-II7\niim7-V7\nImaj7\n(Dbmaj7-C7\nFm7-Bb7\nBbm7-Eb7\nAbmaj7)She's\nLovely"),
    K("GS_CHORDPROG31", "Ab Major\nProg\n31", "IVmaj7-V7\niiim9-vim7\n(Dbmaj7-Eb7\nCm9-Fm7)Neo-Pop\nTurnaround"),
    K("GS_CHORDPROG35", "Ab Major\nProg\n35", "IVmaj7-iiim7\n#iiidim7\niim7-iim7b5\nImaj7\n(Dbmaj7-Cm7\nBdim7\nBbm7-Bbm7b5\nAbmaj7)Descending\nDiminished"),
    K("GS_CHORDPROG36", "Ab Major\nProg\n36", "Imaj7-#idim7\niim7-#iidim7\niiim7\nbiiidim7\n(Abmaj7\nAdim7-Bbm7\nBdim7-Cm7\nCbdim7)Diminished\nBridge"),
    K("GS_CHORDPROG38", "Ab Major\nProg\n38", "I-vi-ii\nbVII7-I\n(Abmaj7-Fm7\nBbm7-Gb7)Backdoor\nProgression"),
    K("GS_CHORDPROG39", "Ab Major\nProg\n39", "Imaj7\nbIIImaj7\niim7-iiim7\n(Abmaj7\nCbmaj7\nBbm7-Cm7)Modal\nMixture"),
    K("GS_CHORDPROG41", "Ab Major\nProg\n41", "Imaj9-I7\niim7-VII7b9\nV7-III7b9\nIV-IVdim7\n(Abmaj9-Ab7\nBbm7-G7b9\nEb7-C7b9\nDbmaj7-Dbdim7)Complex\n2-5-1-4"),
    K("GS_CHORDPROG42", "Ab Major\nProg\n42", "Imaj7-vi7\nii7-bII7\n(Abmaj7-Fm7\nBbm7-A7)Tritone\nSubstitution"),
]

# A KEY - MINOR PROGRESSIONS
KEYCODES_A_CHORDPROG_BASIC_MINOR = [
    K("A_CHORDPROG1", "F# Minor\nProg\n1", "i-VII-VI\n(F#m-E-D)Simple\nMinor"),
    K("A_CHORDPROG3", "F# Minor\nProg\n3", "VI-VII-i\n(D-E-F#m)Hopeful\nMinor"),
    K("A_CHORDPROG7", "F# Minor\nProg\n7", "i-iv-VII-I\n(F#m-Bm-E-A)Natural\nMinor"),
    K("A_CHORDPROG9", "F# Minor\nProg\n9", "iv-III-i-VII\n(Bm-A-F#m-E)Downward\nMinor"),
    K("A_CHORDPROG10", "F# Minor\nProg\n10", "i-VII-v-VI\n(F#m-E-C#m-D)Sensitive\nMinor"),
    K("A_CHORDPROG11", "F# Minor\nProg\n11", "i-v-VI-ii\n(F#m-C#m-D-G#m)Circular\nMinor"),
]

# A KEY - MAJOR PROGRESSIONS
KEYCODES_A_CHORDPROG_BASIC_MAJOR = [
    K("A_CHORDPROG2", "A Major\nProg\n2", "I-IV-V\n(A-D-E)Simple\nMajor"),
    K("A_CHORDPROG4", "A Major\nProg\n4", "I-vi-IV-V\n(A-F#m-D-E)50s\nProgression"),
    K("A_CHORDPROG5", "A Major\nProg\n5", "I-V-vi-IV\n(A-E-F#m-D)Classic\nFour-Chord"),
    K("A_CHORDPROG6", "A Major\nProg\n6", "vi-IV-I-V\n(F#m-D-A-E)Axis\nProgression"),
    K("A_CHORDPROG8", "A Major\nProg\n8", "I-V-IV-IV\n(A-E-D-D)Rock\nProgression"),
    K("A_CHORDPROG12", "A Major\nProg\n12", "I-ii-vi-V\n(A-Bm-F#m-E)Summer\nHit"),
    K("A_CHORDPROG13", "A Major\nProg\n13", "I-V-vi-iii\nIV-I-IV-V\n(A-E-F#m-C#m\nD-A-D-E)Canon\nProgression"),
]

# A KEY - INTERMEDIATE MINOR PROGRESSIONS
KEYCODES_A_CHORDPROG_INTERMEDIATE_MINOR = [
    K("A_CHORDPROG14", "F# Minor\nProg\n14", "i-VII-VI-V\n(F#m-E-D-C#)Andalusian\nCadence"),
    K("A_CHORDPROG15", "F# Minor\nProg\n15", "i-bVI-bVII-V\n(F#m-D-E-C#)Harmonic\nTension"),
    K("A_CHORDPROG18", "F# Minor\nProg\n18", "i-bVII-VI-V\n(F#m-E-D-C#)Melancholic\nMinor"),
    K("A_CHORDPROG20", "F# Minor\nProg\n20", "i-V-VI-VIm\n(F#m-C#-D-Dm)Darkening\nMinor"),
    K("A_CHORDPROG24", "F# Minor\nProg\n24", "im7-bVImaj7\nbVII7-V7\n(F#m7-Dmaj7\nE7-C#7)Jazz\nMinor"),
    K("A_CHORDPROG27", "F# Minor\nProg\n27", "VI-#viidim\nV7-i-VII\n(D-Fdim\nC#7-F#m-E)Diminished\nDominant"),
]

# A KEY - INTERMEDIATE MAJOR PROGRESSIONS
KEYCODES_A_CHORDPROG_INTERMEDIATE_MAJOR = [
    K("A_CHORDPROG16", "A Major\nProg\n16", "I-III-IV-iv\n(A-C#-D-Dm)Creep\nProgression"),
    K("A_CHORDPROG17", "A Major\nProg\n17", "I-III-VII-II\n(A-C#-E-B)Pumped\nKicks"),
    K("A_CHORDPROG19", "A Major\nProg\n19", "I-V-bVII-IV\n(A-E-G-D)Rebel\nProgression"),
    K("A_CHORDPROG21", "A Major\nProg\n21", "Isus2-IVsus2\nvi-V\n(Asus2-Dsus2\nF#m-E)Ambient\nFloat"),
    K("A_CHORDPROG22", "A Major\nProg\n22", "IVsus2-Vsus4\nIsus2-vi\n(Dsus2-Esus4\nAsus2-F#m)Shoegaze\nShimmer"),
    K("A_CHORDPROG23", "A Major\nProg\n23", "ii7-V7-Imaj7\n(Bm7-E7-\nAmaj7)2-5-1\nProgression"),
    K("A_CHORDPROG25", "A Major\nProg\n25", "vi7-ii7-V7\nImaj7\n(F#m7-Bm7-E7\nAmaj7)6-2-5-1\nProgression"),
    K("A_CHORDPROG26", "A Major\nProg\n26", "Imaj7-iim7\niiim7-IVadd2\n(Amaj7-Bm7\nC#m7-Dadd2)Gentle\nCity"),
]

# A KEY - EXPERT MINOR PROGRESSIONS
KEYCODES_A_CHORDPROG_EXPERT_MINOR = [
    K("A_CHORDPROG30", "F# Minor\nProg\n30", "vim9-iiim9\niim9-Imaj9\n(F#m9-C#m9\nBm9-Amaj9)Bring\nThe 9th"),
    K("A_CHORDPROG32", "F# Minor\nProg\n32", "im9-ivaddD\nbVImaj7\nbVIIadd2\n(F#m9-Bmadd9\nDmaj7-Eadd2)Modern\nMinor 9"),
    K("A_CHORDPROG33", "F# Minor\nProg\n33", "im9-iim9-vm9\n(F#m9-Bm9\nC#m9)Lo-Fi\nNinths"),
    K("A_CHORDPROG34", "F# Minor\nProg\n34", "im9-vm9\nVImaj9-im9\nVImaj9\nviim9\n(F#m9-C#m9\nDmaj9-F#m9\nDmaj9-Em9)Ninth\nJourney"),
    K("A_CHORDPROG37", "F# Minor\nProg\n37", "im9-IVmaj7\niim7b5-V7\n(F#m9-Dmaj7\nBm7b5-C#7)Minor Jazz\nII-V-I"),
    K("A_CHORDPROG40", "F# Minor\nProg\n40", "im9-V7b9\nVImaj9\niim9-vm7\n(F#m9-C#7b9\nDmaj9\nBm9-C#m7)Altered\nDominant"),
]

# A KEY - EXPERT MAJOR PROGRESSIONS
KEYCODES_A_CHORDPROG_EXPERT_MAJOR = [
    K("A_CHORDPROG28", "A Major\nProg\n28", "IVmaj7-V7\niiim7-vim7\niim7-III7\nvim7\n(Dmaj7-E7\nC#m7-F#m7\nBm7-C#7-F#m7)Anime\nProgression"),
    K("A_CHORDPROG29", "A Major\nProg\n29", "IVmaj7-III7\nvim7-II7\niim7-V7\nImaj7\n(Dmaj7-C#7\nF#m7-B7\nBm7-E7\nAmaj7)She's\nLovely"),
    K("A_CHORDPROG31", "A Major\nProg\n31", "IVmaj7-V7\niiim9-vim7\n(Dmaj7-E7\nC#m9-F#m7)Neo-Pop\nTurnaround"),
    K("A_CHORDPROG35", "A Major\nProg\n35", "IVmaj7-iiim7\n#iiidim7\niim7-iim7b5\nImaj7\n(Dmaj7-C#m7\nCdim7\nBm7-Bm7b5\nAmaj7)Descending\nDiminished"),
    K("A_CHORDPROG36", "A Major\nProg\n36", "Imaj7-#idim7\niim7-#iidim7\niiim7\nbiiidim7\n(Amaj7\nA#dim7-Bm7\nCdim7-C#m7\nCdim7)Diminished\nBridge"),
    K("A_CHORDPROG38", "A Major\nProg\n38", "I-vi-ii\nbVII7-I\n(Amaj7-F#m7\nBm7-G7)Backdoor\nProgression"),
    K("A_CHORDPROG39", "A Major\nProg\n39", "Imaj7\nbIIImaj7\niim7-iiim7\n(Amaj7\nCmaj7\nBm7-C#m7)Modal\nMixture"),
    K("A_CHORDPROG41", "A Major\nProg\n41", "Imaj9-I7\niim7-VII7b9\nV7-III7b9\nIV-IVdim7\n(Amaj9-A7\nBm7-G#7b9\nE7-C#7b9\nDmaj7-Ddim7)Complex\n2-5-1-4"),
    K("A_CHORDPROG42", "A Major\nProg\n42", "Imaj7-vi7\nii7-bII7\n(Amaj7-F#m7\nBm7-A#7)Tritone\nSubstitution"),
]

# Bb KEY - MINOR PROGRESSIONS
KEYCODES_B_FLAT_CHORDPROG_BASIC_MINOR = [
    K("AS_CHORDPROG1", "G Minor\nProg\n1", "i-VII-VI\n(Gm-F-Eb)Simple\nMinor"),
    K("AS_CHORDPROG3", "G Minor\nProg\n3", "VI-VII-i\n(Eb-F-Gm)Hopeful\nMinor"),
    K("AS_CHORDPROG7", "G Minor\nProg\n7", "i-iv-VII-I\n(Gm-Cm-F-Bb)Natural\nMinor"),
    K("AS_CHORDPROG9", "G Minor\nProg\n9", "iv-III-i-VII\n(Cm-Bb-Gm-F)Downward\nMinor"),
    K("AS_CHORDPROG10", "G Minor\nProg\n10", "i-VII-v-VI\n(Gm-F-Dm-Eb)Sensitive\nMinor"),
    K("AS_CHORDPROG11", "G Minor\nProg\n11", "i-v-VI-ii\n(Gm-Dm-Eb-Am)Circular\nMinor"),
]

# Bb KEY - MAJOR PROGRESSIONS
KEYCODES_B_FLAT_CHORDPROG_BASIC_MAJOR = [
    K("AS_CHORDPROG2", "Bb Major\nProg\n2", "I-IV-V\n(Bb-Eb-F)Simple\nMajor"),
    K("AS_CHORDPROG4", "Bb Major\nProg\n4", "I-vi-IV-V\n(Bb-Gm-Eb-F)50s\nProgression"),
    K("AS_CHORDPROG5", "Bb Major\nProg\n5", "I-V-vi-IV\n(Bb-F-Gm-Eb)Classic\nFour-Chord"),
    K("AS_CHORDPROG6", "Bb Major\nProg\n6", "vi-IV-I-V\n(Gm-Eb-Bb-F)Axis\nProgression"),
    K("AS_CHORDPROG8", "Bb Major\nProg\n8", "I-V-IV-IV\n(Bb-F-Eb-Eb)Rock\nProgression"),
    K("AS_CHORDPROG12", "Bb Major\nProg\n12", "I-ii-vi-V\n(Bb-Cm-Gm-F)Summer\nHit"),
    K("AS_CHORDPROG13", "Bb Major\nProg\n13", "I-V-vi-iii\nIV-I-IV-V\n(Bb-F-Gm-Dm\nEb-Bb-Eb-F)Canon\nProgression"),
]

# Bb KEY - INTERMEDIATE MINOR PROGRESSIONS
KEYCODES_B_FLAT_CHORDPROG_INTERMEDIATE_MINOR = [
    K("AS_CHORDPROG14", "G Minor\nProg\n14", "i-VII-VI-V\n(Gm-F-Eb-D)Andalusian\nCadence"),
    K("AS_CHORDPROG15", "G Minor\nProg\n15", "i-bVI-bVII-V\n(Gm-Eb-F-D)Harmonic\nTension"),
    K("AS_CHORDPROG18", "G Minor\nProg\n18", "i-bVII-VI-V\n(Gm-F-Eb-D)Melancholic\nMinor"),
    K("AS_CHORDPROG20", "G Minor\nProg\n20", "i-V-VI-VIm\n(Gm-D-Eb-Ebm)Darkening\nMinor"),
    K("AS_CHORDPROG24", "G Minor\nProg\n24", "im7-bVImaj7\nbVII7-V7\n(Gm7-Ebmaj7\nF7-D7)Jazz\nMinor"),
    K("AS_CHORDPROG27", "G Minor\nProg\n27", "VI-#viidim\nV7-i-VII\n(Eb-F#dim\nD7-Gm-F)Diminished\nDominant"),
]

# Bb KEY - INTERMEDIATE MAJOR PROGRESSIONS
KEYCODES_B_FLAT_CHORDPROG_INTERMEDIATE_MAJOR = [
    K("AS_CHORDPROG16", "Bb Major\nProg\n16", "I-III-IV-iv\n(Bb-D-Eb-Ebm)Creep\nProgression"),
    K("AS_CHORDPROG17", "Bb Major\nProg\n17", "I-III-VII-II\n(Bb-D-F-C)Pumped\nKicks"),
    K("AS_CHORDPROG19", "Bb Major\nProg\n19", "I-V-bVII-IV\n(Bb-F-Ab-Eb)Rebel\nProgression"),
    K("AS_CHORDPROG21", "Bb Major\nProg\n21", "Isus2-IVsus2\nvi-V\n(Bbsus2-Ebsus2\nGm-F)Ambient\nFloat"),
    K("AS_CHORDPROG22", "Bb Major\nProg\n22", "IVsus2-Vsus4\nIsus2-vi\n(Ebsus2-Fsus4\nBbsus2-Gm)Shoegaze\nShimmer"),
    K("AS_CHORDPROG23", "Bb Major\nProg\n23", "ii7-V7-Imaj7\n(Cm7-F7-\nBbmaj7)2-5-1\nProgression"),
    K("AS_CHORDPROG25", "Bb Major\nProg\n25", "vi7-ii7-V7\nImaj7\n(Gm7-Cm7-F7\nBbmaj7)6-2-5-1\nProgression"),
    K("AS_CHORDPROG26", "Bb Major\nProg\n26", "Imaj7-iim7\niiim7-IVadd2\n(Bbmaj7-Cm7\nDm7-Ebadd2)Gentle\nCity"),
]

# Bb KEY - EXPERT MINOR PROGRESSIONS
KEYCODES_B_FLAT_CHORDPROG_EXPERT_MINOR = [
    K("AS_CHORDPROG30", "G Minor\nProg\n30", "vim9-iiim9\niim9-Imaj9\n(Gm9-Dm9\nCm9-Bbmaj9)Bring\nThe 9th"),
    K("AS_CHORDPROG32", "G Minor\nProg\n32", "im9-ivaddD\nbVImaj7\nbVIIadd2\n(Gm9-Cmadd9\nEbmaj7-Fadd2)Modern\nMinor 9"),
    K("AS_CHORDPROG33", "G Minor\nProg\n33", "im9-iim9-vm9\n(Gm9-Cm9\nDm9)Lo-Fi\nNinths"),
    K("AS_CHORDPROG34", "G Minor\nProg\n34", "im9-vm9\nVImaj9-im9\nVImaj9\nviim9\n(Gm9-Dm9\nEbmaj9-Gm9\nEbmaj9-Fm9)Ninth\nJourney"),
    K("AS_CHORDPROG37", "G Minor\nProg\n37", "im9-IVmaj7\niim7b5-V7\n(Gm9-Ebmaj7\nCm7b5-D7)Minor Jazz\nII-V-I"),
    K("AS_CHORDPROG40", "G Minor\nProg\n40", "im9-V7b9\nVImaj9\niim9-vm7\n(Gm9-D7b9\nEbmaj9\nCm9-Dm7)Altered\nDominant"),
]

# Bb KEY - EXPERT MAJOR PROGRESSIONS
KEYCODES_B_FLAT_CHORDPROG_EXPERT_MAJOR = [
    K("AS_CHORDPROG28", "Bb Major\nProg\n28", "IVmaj7-V7\niiim7-vim7\niim7-III7\nvim7\n(Ebmaj7-F7\nDm7-Gm7\nCm7-D7-Gm7)Anime\nProgression"),
    K("AS_CHORDPROG29", "Bb Major\nProg\n29", "IVmaj7-III7\nvim7-II7\niim7-V7\nImaj7\n(Ebmaj7-D7\nGm7-C7\nCm7-F7\nBbmaj7)She's\nLovely"),
    K("AS_CHORDPROG31", "Bb Major\nProg\n31", "IVmaj7-V7\niiim9-vim7\n(Ebmaj7-F7\nDm9-Gm7)Neo-Pop\nTurnaround"),
    K("AS_CHORDPROG35", "Bb Major\nProg\n35", "IVmaj7-iiim7\n#iiidim7\niim7-iim7b5\nImaj7\n(Ebmaj7-Dm7\nDbdim7\nCm7-Cm7b5\nBbmaj7)Descending\nDiminished"),
    K("AS_CHORDPROG36", "Bb Major\nProg\n36", "Imaj7-#idim7\niim7-#iidim7\niiim7\nbiiidim7\n(Bbmaj7\nBdim7-Cm7\nDbdim7-Dm7\nDbdim7)Diminished\nBridge"),
    K("AS_CHORDPROG38", "Bb Major\nProg\n38", "I-vi-ii\nbVII7-I\n(Bbmaj7-Gm7\nCm7-Ab7)Backdoor\nProgression"),
    K("AS_CHORDPROG39", "Bb Major\nProg\n39", "Imaj7\nbIIImaj7\niim7-iiim7\n(Bbmaj7\nDbmaj7\nCm7-Dm7)Modal\nMixture"),
    K("AS_CHORDPROG41", "Bb Major\nProg\n41", "Imaj9-I7\niim7-VII7b9\nV7-III7b9\nIV-IVdim7\n(Bbmaj9-Bb7\nCm7-A7b9\nF7-D7b9\nEbmaj7-Ebdim7)Complex\n2-5-1-4"),
    K("AS_CHORDPROG42", "Bb Major\nProg\n42", "Imaj7-vi7\nii7-bII7\n(Bbmaj7-Gm7\nCm7-Cb7)Tritone\nSubstitution"),
]

# B KEY - MINOR PROGRESSIONS
KEYCODES_B_CHORDPROG_BASIC_MINOR = [
    K("B_CHORDPROG1", "G# Minor\nProg\n1", "i-VII-VI\n(G#m-F#-E)Simple\nMinor"),
    K("B_CHORDPROG3", "G# Minor\nProg\n3", "VI-VII-i\n(E-F#-G#m)Hopeful\nMinor"),
    K("B_CHORDPROG7", "G# Minor\nProg\n7", "i-iv-VII-I\n(G#m-C#m-F#-B)Natural\nMinor"),
    K("B_CHORDPROG9", "G# Minor\nProg\n9", "iv-III-i-VII\n(C#m-B-G#m-F#)Downward\nMinor"),
    K("B_CHORDPROG10", "G# Minor\nProg\n10", "i-VII-v-VI\n(G#m-F#-D#m-E)Sensitive\nMinor"),
    K("B_CHORDPROG11", "G# Minor\nProg\n11", "i-v-VI-ii\n(G#m-D#m-E-A#m)Circular\nMinor"),
]

# B KEY - MAJOR PROGRESSIONS
KEYCODES_B_CHORDPROG_BASIC_MAJOR = [
    K("B_CHORDPROG2", "B Major\nProg\n2", "I-IV-V\n(B-E-F#)Simple\nMajor"),
    K("B_CHORDPROG4", "B Major\nProg\n4", "I-vi-IV-V\n(B-G#m-E-F#)50s\nProgression"),
    K("B_CHORDPROG5", "B Major\nProg\n5", "I-V-vi-IV\n(B-F#-G#m-E)Classic\nFour-Chord"),
    K("B_CHORDPROG6", "B Major\nProg\n6", "vi-IV-I-V\n(G#m-E-B-F#)Axis\nProgression"),
    K("B_CHORDPROG8", "B Major\nProg\n8", "I-V-IV-IV\n(B-F#-E-E)Rock\nProgression"),
    K("B_CHORDPROG12", "B Major\nProg\n12", "I-ii-vi-V\n(B-C#m-G#m-F#)Summer\nHit"),
    K("B_CHORDPROG13", "B Major\nProg\n13", "I-V-vi-iii\nIV-I-IV-V\n(B-F#-G#m-D#m\nE-B-E-F#)Canon\nProgression"),
]

# B KEY - INTERMEDIATE MINOR PROGRESSIONS
KEYCODES_B_CHORDPROG_INTERMEDIATE_MINOR = [
    K("B_CHORDPROG14", "G# Minor\nProg\n14", "i-VII-VI-V\n(G#m-F#-E-D#)Andalusian\nCadence"),
    K("B_CHORDPROG15", "G# Minor\nProg\n15", "i-bVI-bVII-V\n(G#m-E-F#-D#)Harmonic\nTension"),
    K("B_CHORDPROG18", "G# Minor\nProg\n18", "i-bVII-VI-V\n(G#m-F#-E-D#)Melancholic\nMinor"),
    K("B_CHORDPROG20", "G# Minor\nProg\n20", "i-V-VI-VIm\n(G#m-D#-E-Em)Darkening\nMinor"),
    K("B_CHORDPROG24", "G# Minor\nProg\n24", "im7-bVImaj7\nbVII7-V7\n(G#m7-Emaj7\nF#7-D#7)Jazz\nMinor"),
    K("B_CHORDPROG27", "G# Minor\nProg\n27", "VI-#viidim\nV7-i-VII\n(E-Gdim\nD#7-G#m-F#)Diminished\nDominant"),
]

# B KEY - INTERMEDIATE MAJOR PROGRESSIONS
KEYCODES_B_CHORDPROG_INTERMEDIATE_MAJOR = [
    K("B_CHORDPROG16", "B Major\nProg\n16", "I-III-IV-iv\n(B-D#-E-Em)Creep\nProgression"),
    K("B_CHORDPROG17", "B Major\nProg\n17", "I-III-VII-II\n(B-D#-F#-C#)Pumped\nKicks"),
    K("B_CHORDPROG19", "B Major\nProg\n19", "I-V-bVII-IV\n(B-F#-A-E)Rebel\nProgression"),
    K("B_CHORDPROG21", "B Major\nProg\n21", "Isus2-IVsus2\nvi-V\n(Bsus2-Esus2\nG#m-F#)Ambient\nFloat"),
    K("B_CHORDPROG22", "B Major\nProg\n22", "IVsus2-Vsus4\nIsus2-vi\n(Esus2-F#sus4\nBsus2-G#m)Shoegaze\nShimmer"),
    K("B_CHORDPROG23", "B Major\nProg\n23", "ii7-V7-Imaj7\n(C#m7-F#7-\nBmaj7)2-5-1\nProgression"),
    K("B_CHORDPROG25", "B Major\nProg\n25", "vi7-ii7-V7\nImaj7\n(G#m7-C#m7-F#7\nBmaj7)6-2-5-1\nProgression"),
    K("B_CHORDPROG26", "B Major\nProg\n26", "Imaj7-iim7\niiim7-IVadd2\n(Bmaj7-C#m7\nD#m7-Eadd2)Gentle\nCity"),
]

# B KEY - EXPERT MINOR PROGRESSIONS
KEYCODES_B_CHORDPROG_EXPERT_MINOR = [
    K("B_CHORDPROG30", "G# Minor\nProg\n30", "vim9-iiim9\niim9-Imaj9\n(G#m9-D#m9\nC#m9-Bmaj9)Bring\nThe 9th"),
    K("B_CHORDPROG32", "G# Minor\nProg\n32", "im9-ivaddD\nbVImaj7\nbVIIadd2\n(G#m9-C#madd9\nEmaj7-F#add2)Modern\nMinor 9"),
    K("B_CHORDPROG33", "G# Minor\nProg\n33", "im9-iim9-vm9\n(G#m9-C#m9\nD#m9)Lo-Fi\nNinths"),
    K("B_CHORDPROG34", "G# Minor\nProg\n34", "im9-vm9\nVImaj9-im9\nVImaj9\nviim9\n(G#m9-D#m9\nEmaj9-G#m9\nEmaj9-F#m9)Ninth\nJourney"),
    K("B_CHORDPROG37", "G# Minor\nProg\n37", "im9-IVmaj7\niim7b5-V7\n(G#m9-Emaj7\nC#m7b5-D#7)Minor Jazz\nII-V-I"),
    K("B_CHORDPROG40", "G# Minor\nProg\n40", "im9-V7b9\nVImaj9\niim9-vm7\n(G#m9-D#7b9\nEmaj9\nC#m9-D#m7)Altered\nDominant"),
]

# B KEY - EXPERT MAJOR PROGRESSIONS
KEYCODES_B_CHORDPROG_EXPERT_MAJOR = [
    K("B_CHORDPROG28", "B Major\nProg\n28", "IVmaj7-V7\niiim7-vim7\niim7-III7\nvim7\n(Emaj7-F#7\nD#m7-G#m7\nC#m7-D#7-G#m7)Anime\nProgression"),
    K("B_CHORDPROG29", "B Major\nProg\n29", "IVmaj7-III7\nvim7-II7\niim7-V7\nImaj7\n(Emaj7-D#7\nG#m7-C#7\nC#m7-F#7\nBmaj7)She's\nLovely"),
    K("B_CHORDPROG31", "B Major\nProg\n31", "IVmaj7-V7\niiim9-vim7\n(Emaj7-F#7\nD#m9-G#m7)Neo-Pop\nTurnaround"),
    K("B_CHORDPROG35", "B Major\nProg\n35", "IVmaj7-iiim7\n#iiidim7\niim7-iim7b5\nImaj7\n(Emaj7-D#m7\nDdim7\nC#m7-C#m7b5\nBmaj7)Descending\nDiminished"),
    K("B_CHORDPROG36", "B Major\nProg\n36", "Imaj7-#idim7\niim7-#iidim7\niiim7\nbiiidim7\n(Bmaj7\nCdim7-C#m7\nDdim7-D#m7\nDdim7)Diminished\nBridge"),
    K("B_CHORDPROG38", "B Major\nProg\n38", "I-vi-ii\nbVII7-I\n(Bmaj7-G#m7\nC#m7-A7)Backdoor\nProgression"),
    K("B_CHORDPROG39", "B Major\nProg\n39", "Imaj7\nbIIImaj7\niim7-iiim7\n(Bmaj7\nDmaj7\nC#m7-D#m7)Modal\nMixture"),
    K("B_CHORDPROG41", "B Major\nProg\n41", "Imaj9-I7\niim7-VII7b9\nV7-III7b9\nIV-IVdim7\n(Bmaj9-B7\nC#m7-A#7b9\nF#7-D#7b9\nEmaj7-Edim7)Complex\n2-5-1-4"),
    K("B_CHORDPROG42", "B Major\nProg\n42", "Imaj7-vi7\nii7-bII7\n(Bmaj7-G#m7\nC#m7-C7)Tritone\nSubstitution"),
]

# VOICINGS AND OCTAVE CONTROLS
KEYCODES_CHORD_PROG_CONTROLS = [
    K("PROG_VOICING_BASIC", "Voicing\nStyle\n1", "Use basic chord voicings for progressions"),
    K("PROG_VOICING_ADVANCED", "Voicing\nStyle\n2", "Use advanced chord voicings for progressions"),
    K("PROG_VOICING_DESCENDING", "Voicing\nStyle\n3", "Use descending voice leading for progressions"),
    K("PROG_VOICING_ASCENDING", "Voicing\nStyle\n4", "Use ascending voice leading for progressions"),
    K("PROG_VOICING_RANDOM", "Voicing\nStyle\n5", "Use ascending voice leading for progressions"),
    K("PROG_OCTAVE_UP", "Octave\nUp", "Raise progression octave"),
    K("PROG_OCTAVE_DOWN", "Octave\nDown", "Lower progression octave"),
    K("PROG_OCTAVE_RESET", "Octave\nReset", "Reset progression octave to default"),
    K("MI_TAP", "Set\nBPM", "Set BPM"),
    K("BPM_UP", "BPM\nUp", "Set BPM"),
    K("BPM_DOWN", "BPM\nDown", "Set BPM"),
]

KEYCODES_LOOP_BUTTONS = [
    # Main macro keys
    K("DM_MACRO_1", "Loop\n1", "Main loop/macro key 1"),
    K("DM_MACRO_2", "Loop\n2", "Main loop/macro key 2"),
    K("DM_MACRO_3", "Loop\n3", "Main loop/macro key 3"),
    K("DM_MACRO_4", "Loop\n4", "Main loop/macro key 4"),
    
    # Core control buttons
    K("DM_MUTE", "Mute\nButton", "Global mute button"),
    K("DM_OVERDUB", "Overdub\nButton", "Overdub recording button"),
    K("DM_UNSYNC", "Sync\nMode", "Toggle sync mode"),
    K("DM_SAMPLE", "Sample\nMode", "Toggle sample mode"),
    K("DM_EDIT_MOD", "Global\nEdit", "Global edit modifier button"),
    K("DM_PLAY_PAUSE", "Play\nPause", "Global play/pause toggle"),

    # Loop modifier keys
    K("DM_LOOP_MOD_1", "Loop 1\nModifier", "Loop modifier 1 (hold + loop for alt function)"),
    K("DM_LOOP_MOD_2", "Loop 2\nModifier", "Loop modifier 2 (hold + loop for alt function)"),
    K("DM_LOOP_MOD_3", "Loop 3\nModifier", "Loop modifier 3 (hold + loop for alt function)"),
    K("DM_LOOP_MOD_4", "Loop 4\nModifier", "Loop modifier 4 (hold + loop for alt function)"),
    
    # Dedicated mute keys
    K("DM_MUTE_1", "Mute\nLoop 1", "Dedicated mute for loop 1"),
    K("DM_MUTE_2", "Mute\nLoop 2", "Dedicated mute for loop 2"),
    K("DM_MUTE_3", "Mute\nLoop 3", "Dedicated mute for loop 3"),
    K("DM_MUTE_4", "Mute\nLoop 4", "Dedicated mute for loop 4"),
    
    # Octave doubler controls
    K("DM_OCT_1", "Octave\nDouble\nLoop 1", "Octave doubler toggle for loop 1"),
    K("DM_OCT_2", "Octave\nDouble\nLoop 2", "Octave doubler toggle for loop 2"),
    K("DM_OCT_3", "Octave\nDouble\nLoop 3", "Octave doubler toggle for loop 3"),
    K("DM_OCT_4", "Octave\nDouble\nLoop 4", "Octave doubler toggle for loop 4"),
    K("DM_OCT_MOD", "Octave\nDouble\nModifier", "Octave doubler modifier button"),
    
    # Speed controls
    K("DM_SPEED_MOD", "Speed\nModifier", "Speed modifier button (hold + loop)"),
    K("DM_SLOW_MOD", "Slow\nModifier", "Slow modifier button (hold + loop)"),
    K("DM_SPEED_1", "Speed\nLoop 1", "Individual speed toggle for loop 1"),
    K("DM_SPEED_2", "Speed\nLoop 2", "Individual speed toggle for loop 2"),
    K("DM_SPEED_3", "Speed\nLoop 3", "Individual speed toggle for loop 3"),
    K("DM_SPEED_4", "Speed\nLoop 4", "Individual speed toggle for loop 4"),
    K("DM_SPEED_ALL", "Speed\nAll\nLoops", "Speed up all macros"),
    K("DM_SLOW_1", "Slow\nLoop 1", "Individual slow toggle for loop 1"),
    K("DM_SLOW_2", "Slow\nLoop 2", "Individual slow toggle for loop 2"),
    K("DM_SLOW_3", "Slow\nLoop 3", "Individual slow toggle for loop 3"),
    K("DM_SLOW_4", "Slow\nLoop 4", "Individual slow toggle for loop 4"),
    K("DM_SLOW_ALL", "Slow\nAll\nLoops", "Slow up all macros"),
    K("DM_RESET_SPEED", "Reset\nSpeed", "Reset all speeds and BPM to original"),
    
    # Navigation controls
    K("DM_NAV_BWD_1S", "Nav\n◀ 1s", "Navigate backward 1 second"),
    K("DM_NAV_FWD_1S", "Nav\n1s ▶", "Navigate forward 1 second"),
    K("DM_NAV_BWD_5S", "Nav\n◀ 5s", "Navigate backward 5 seconds"),
    K("DM_NAV_FWD_5S", "Nav\n5s ▶", "Navigate forward 5 seconds"),
    
    # Fractional navigation
    K("DM_SKIP_0_8", "Skip\n0/8", "Skip to start (0/8)"),
    K("DM_SKIP_1_8", "Skip\n1/8", "Skip to 1/8 position"),
    K("DM_SKIP_2_8", "Skip\n2/8", "Skip to 2/8 position"),
    K("DM_SKIP_3_8", "Skip\n3/8", "Skip to 3/8 position"),
    K("DM_SKIP_4_8", "Skip\n4/8", "Skip to middle (4/8)"),
    K("DM_SKIP_5_8", "Skip\n5/8", "Skip to 5/8 position"),
    K("DM_SKIP_6_8", "Skip\n6/8", "Skip to 6/8 position"),
    K("DM_SKIP_7_8", "Skip\n7/8", "Skip to 7/8 position"),
    
    # Save and copy operations
    K("DM_COPY", "Copy\nLoop", "Copy loop operation"),
    K("DM_SAVE_1", "Save\nLoop 1", "Save loop 1 to file"),
    K("DM_SAVE_2", "Save\nLoop 2", "Save loop 2 to file"),
    K("DM_SAVE_3", "Save\nLoop 3", "Save loop 3 to file"),
    K("DM_SAVE_4", "Save\nLoop 4", "Save loop 4 to file"),
    K("DM_SAVE_ALL", "Save\nAll", "Save all loops to file"),
        
    # Advanced overdub operations
    K("DM_ADVANCED_OVERDUB", "Advanced\nOverdub", "Advanced overdub operation"),

    # Overdub operations
    K("DM_OVERDUB_1", "Overdub\nLoop 1", "Overdub loop 1"),
    K("DM_OVERDUB_2", "Overdub\nLoop 2", "Overdub loop 2"),
    K("DM_OVERDUB_3", "Overdub\nLoop 3", "Overdub loop 3"),
    K("DM_OVERDUB_4", "Overdub\nLoop 4", "Overdub loop 4"),

    # Overdub mute operations
    K("DM_OVERDUB_MUTE_1", "Overdub\nMute 1", "Overdub mute loop 1"),
    K("DM_OVERDUB_MUTE_2", "Overdub\nMute 2", "Overdub mute loop 2"),
    K("DM_OVERDUB_MUTE_3", "Overdub\nMute 3", "Overdub mute loop 3"),
    K("DM_OVERDUB_MUTE_4", "Overdub\nMute 4", "Overdub mute loop 4"),

    # Loop advanced controls
    K("LOOP_QUANTIZE", "Loop\nQuantize", "Quantize loop timing"),
    K("LOOP_BPM_DOUBLE", "Loop\nBPM x2", "Double loop BPM"),
]

# Gaming Controller Keycodes
KEYCODES_GAMING = [
    # Toggle gaming mode
    K("GAMING_MODE", "Gaming\nMode", "Toggle gaming mode (auto-maps WASD to left stick + arrows to D-pad)"),

    # Digital Buttons (Face buttons)
    K("XBOX_A", "Button\n1", "Button 1 (Button 0)"),
    K("XBOX_B", "Button\n2", "Button 2 (Button 1)"),
    K("XBOX_X", "Button\n3", "Button 3 (Button 2)"),
    K("XBOX_Y", "Button\n4", "Button 4 (Button 3)"),

    # Shoulder Buttons
    K("XBOX_LB", "LB", "Left bumper (Button 4)"),
    K("XBOX_RB", "RB", "Right bumper (Button 5)"),

    # Center Buttons
    K("XBOX_BACK", "Back", "Back/Select (Button 6)"),
    K("XBOX_START", "Start", "Start (Button 7)"),

    # Stick Click Buttons
    K("XBOX_L3", "L3", "Left stick click (Button 8)"),
    K("XBOX_R3", "R3", "Right stick click (Button 9)"),

    # Left Analog Stick (Hall Effect)
    K("LS_UP", "LS ↑", "Left stick up (Axis 1 negative)"),
    K("LS_DOWN", "LS ↓", "Left stick down (Axis 1 positive)"),
    K("LS_LEFT", "LS ←", "Left stick left (Axis 0 negative)"),
    K("LS_RIGHT", "LS →", "Left stick right (Axis 0 positive)"),

    # Right Analog Stick (Hall Effect)
    K("RS_UP", "RS ↑", "Right stick up (Axis 3 negative)"),
    K("RS_DOWN", "RS ↓", "Right stick down (Axis 3 positive)"),
    K("RS_LEFT", "RS ←", "Right stick left (Axis 2 negative)"),
    K("RS_RIGHT", "RS →", "Right stick right (Axis 2 positive)"),

    # Analog Triggers (Hall Effect)
    K("LT", "LT", "Left trigger (Axis 4, 0-127 based on press depth)"),
    K("RT", "RT", "Right trigger (Axis 5, 0-127 based on press depth)"),

    # D-pad (Digital directional pad)
    K("DPAD_UP", "D-pad ↑", "D-pad Up (Button 12)"),
    K("DPAD_DOWN", "D-pad ↓", "D-pad Down (Button 13)"),
    K("DPAD_LEFT", "D-pad ←", "D-pad Left (Button 14)"),
    K("DPAD_RIGHT", "D-pad →", "D-pad Right (Button 15)"),
]


KEYCODES_ARPEGGIATOR = [
    # Control keycodes
    K("ARP_PLAY", "Play\nArp", "Arpeggiator play/stop toggle"),
    K("ARP_NEXT_PRESET", "Next\nPreset", "Load next arpeggiator preset"),
    K("ARP_PREV_PRESET", "Prev\nPreset", "Load previous arpeggiator preset"),
    K("ARP_SYNC_MODE", "Sync\nMode", "Toggle arpeggiator sync mode"),
    K("ARP_GATE_RESET", "Gate\nReset", "Reset gate to preset default"),
    K("ARP_RESET_OVERRIDES", "Reset\nOverrides", "Reset all arpeggiator overrides"),

    # Gate up controls (1-10%)
    K("ARP_GATE_1_UP", "Gate\n+1%", "Increase arpeggiator gate (+1%)"),
    K("ARP_GATE_2_UP", "Gate\n+2%", "Increase arpeggiator gate (+2%)"),
    K("ARP_GATE_3_UP", "Gate\n+3%", "Increase arpeggiator gate (+3%)"),
    K("ARP_GATE_4_UP", "Gate\n+4%", "Increase arpeggiator gate (+4%)"),
    K("ARP_GATE_5_UP", "Gate\n+5%", "Increase arpeggiator gate (+5%)"),
    K("ARP_GATE_6_UP", "Gate\n+6%", "Increase arpeggiator gate (+6%)"),
    K("ARP_GATE_7_UP", "Gate\n+7%", "Increase arpeggiator gate (+7%)"),
    K("ARP_GATE_8_UP", "Gate\n+8%", "Increase arpeggiator gate (+8%)"),
    K("ARP_GATE_9_UP", "Gate\n+9%", "Increase arpeggiator gate (+9%)"),
    K("ARP_GATE_10_UP", "Gate\n+10%", "Increase arpeggiator gate (+10%)"),

    # Gate down controls (1-10%)
    K("ARP_GATE_1_DOWN", "Gate\n-1%", "Decrease arpeggiator gate (-1%)"),
    K("ARP_GATE_2_DOWN", "Gate\n-2%", "Decrease arpeggiator gate (-2%)"),
    K("ARP_GATE_3_DOWN", "Gate\n-3%", "Decrease arpeggiator gate (-3%)"),
    K("ARP_GATE_4_DOWN", "Gate\n-4%", "Decrease arpeggiator gate (-4%)"),
    K("ARP_GATE_5_DOWN", "Gate\n-5%", "Decrease arpeggiator gate (-5%)"),
    K("ARP_GATE_6_DOWN", "Gate\n-6%", "Decrease arpeggiator gate (-6%)"),
    K("ARP_GATE_7_DOWN", "Gate\n-7%", "Decrease arpeggiator gate (-7%)"),
    K("ARP_GATE_8_DOWN", "Gate\n-8%", "Decrease arpeggiator gate (-8%)"),
    K("ARP_GATE_9_DOWN", "Gate\n-9%", "Decrease arpeggiator gate (-9%)"),
    K("ARP_GATE_10_DOWN", "Gate\n-10%", "Decrease arpeggiator gate (-10%)"),

    # Rate overrides
    K("ARP_RATE_QUARTER", "Quarter\nNotes", "Arpeggiator rate: quarter notes"),
    K("ARP_RATE_QUARTER_DOT", "Quarter\nDotted", "Arpeggiator rate: dotted quarter"),
    K("ARP_RATE_QUARTER_TRIP", "Quarter\nTriplet", "Arpeggiator rate: triplet quarter"),
    K("ARP_RATE_EIGHTH", "Eighth\nNotes", "Arpeggiator rate: eighth notes"),
    K("ARP_RATE_EIGHTH_DOT", "Eighth\nDotted", "Arpeggiator rate: dotted eighth"),
    K("ARP_RATE_EIGHTH_TRIP", "Eighth\nTriplet", "Arpeggiator rate: triplet eighth"),
    K("ARP_RATE_SIXTEENTH", "16th\nNotes", "Arpeggiator rate: sixteenth notes"),
    K("ARP_RATE_SIXTEENTH_DOT", "16th\nDotted", "Arpeggiator rate: dotted sixteenth"),
    K("ARP_RATE_SIXTEENTH_TRIP", "16th\nTriplet", "Arpeggiator rate: triplet sixteenth"),
    K("ARP_RATE_RESET", "Rate\nReset", "Reset to preset's default rate"),

    # NEW: Rate cycling
    K("ARP_RATE_UP", "Rate\nUp", "Cycle to next arpeggiator rate"),
    K("ARP_RATE_DOWN", "Rate\nDown", "Cycle to previous arpeggiator rate"),

    # NEW: Static gate values
    K("ARP_SET_GATE_10", "Gate\n10%", "Set arpeggiator gate to 10%"),
    K("ARP_SET_GATE_20", "Gate\n20%", "Set arpeggiator gate to 20%"),
    K("ARP_SET_GATE_30", "Gate\n30%", "Set arpeggiator gate to 30%"),
    K("ARP_SET_GATE_40", "Gate\n40%", "Set arpeggiator gate to 40%"),
    K("ARP_SET_GATE_50", "Gate\n50%", "Set arpeggiator gate to 50%"),
    K("ARP_SET_GATE_60", "Gate\n60%", "Set arpeggiator gate to 60%"),
    K("ARP_SET_GATE_70", "Gate\n70%", "Set arpeggiator gate to 70%"),
    K("ARP_SET_GATE_80", "Gate\n80%", "Set arpeggiator gate to 80%"),
    K("ARP_SET_GATE_90", "Gate\n90%", "Set arpeggiator gate to 90%"),
    K("ARP_SET_GATE_100", "Gate\n100%", "Set arpeggiator gate to 100%"),

    # Modes
    K("ARP_MODE_SINGLE", "Single\nNote", "Arpeggiator mode: single note"),
    K("ARP_MODE_CHORD_BASIC", "Chord\nBasic", "Arpeggiator mode: chord basic"),
    K("ARP_MODE_CHORD_ADVANCED", "Chord\nAdvanced", "Arpeggiator mode: chord advanced"),
]

# Generate preset selection keycodes (48 factory + 20 user = 68 total)
KEYCODES_ARPEGGIATOR_PRESETS = []
# Factory presets 0-47
for x in range(48):
    KEYCODES_ARPEGGIATOR_PRESETS.append(
        K("ARP_PRESET_{}".format(x), "Arp\nPreset\n{}".format(x), "Load arpeggiator preset {}".format(x))
    )
# User presets 48-67 (displayed as User 1-20)
for x in range(48, 68):
    user_num = x - 47
    KEYCODES_ARPEGGIATOR_PRESETS.append(
        K("ARP_PRESET_{}".format(x), "Arp\nUser\n{}".format(user_num), "Load arpeggiator user preset {}".format(user_num))
    )

KEYCODES_STEP_SEQUENCER = [
    # Control keycodes
    K("SEQ_PLAY", "Play\nSeq", "Step sequencer play"),
    K("SEQ_STOP_ALL", "Stop\nAll Seq", "Stop all step sequencers"),
    K("SEQ_NEXT_PRESET", "Next\nPreset", "Load next sequencer preset"),
    K("SEQ_PREV_PRESET", "Prev\nPreset", "Load previous sequencer preset"),
    K("SEQ_SYNC_MODE", "Sync\nMode", "Toggle sequencer sync mode"),
    K("SEQ_GATE_RESET", "Gate\nReset", "Reset gate to preset default"),
    K("SEQ_RESET_OVERRIDES", "Reset\nOverrides", "Reset all sequencer overrides"),

    # Gate up controls (1-10%)
    K("SEQ_GATE_1_UP", "Gate\n+1%", "Increase sequencer gate (+1%)"),
    K("SEQ_GATE_2_UP", "Gate\n+2%", "Increase sequencer gate (+2%)"),
    K("SEQ_GATE_3_UP", "Gate\n+3%", "Increase sequencer gate (+3%)"),
    K("SEQ_GATE_4_UP", "Gate\n+4%", "Increase sequencer gate (+4%)"),
    K("SEQ_GATE_5_UP", "Gate\n+5%", "Increase sequencer gate (+5%)"),
    K("SEQ_GATE_6_UP", "Gate\n+6%", "Increase sequencer gate (+6%)"),
    K("SEQ_GATE_7_UP", "Gate\n+7%", "Increase sequencer gate (+7%)"),
    K("SEQ_GATE_8_UP", "Gate\n+8%", "Increase sequencer gate (+8%)"),
    K("SEQ_GATE_9_UP", "Gate\n+9%", "Increase sequencer gate (+9%)"),
    K("SEQ_GATE_10_UP", "Gate\n+10%", "Increase sequencer gate (+10%)"),

    # Gate down controls (1-10%)
    K("SEQ_GATE_1_DOWN", "Gate\n-1%", "Decrease sequencer gate (-1%)"),
    K("SEQ_GATE_2_DOWN", "Gate\n-2%", "Decrease sequencer gate (-2%)"),
    K("SEQ_GATE_3_DOWN", "Gate\n-3%", "Decrease sequencer gate (-3%)"),
    K("SEQ_GATE_4_DOWN", "Gate\n-4%", "Decrease sequencer gate (-4%)"),
    K("SEQ_GATE_5_DOWN", "Gate\n-5%", "Decrease sequencer gate (-5%)"),
    K("SEQ_GATE_6_DOWN", "Gate\n-6%", "Decrease sequencer gate (-6%)"),
    K("SEQ_GATE_7_DOWN", "Gate\n-7%", "Decrease sequencer gate (-7%)"),
    K("SEQ_GATE_8_DOWN", "Gate\n-8%", "Decrease sequencer gate (-8%)"),
    K("SEQ_GATE_9_DOWN", "Gate\n-9%", "Decrease sequencer gate (-9%)"),
    K("SEQ_GATE_10_DOWN", "Gate\n-10%", "Decrease sequencer gate (-10%)"),

    # Rate overrides
    K("SEQ_RATE_QUARTER", "Quarter\nNotes", "Sequencer rate: quarter notes"),
    K("SEQ_RATE_QUARTER_DOT", "Quarter\nDotted", "Sequencer rate: dotted quarter"),
    K("SEQ_RATE_QUARTER_TRIP", "Quarter\nTriplet", "Sequencer rate: triplet quarter"),
    K("SEQ_RATE_EIGHTH", "Eighth\nNotes", "Sequencer rate: eighth notes"),
    K("SEQ_RATE_EIGHTH_DOT", "Eighth\nDotted", "Sequencer rate: dotted eighth"),
    K("SEQ_RATE_EIGHTH_TRIP", "Eighth\nTriplet", "Sequencer rate: triplet eighth"),
    K("SEQ_RATE_SIXTEENTH", "16th\nNotes", "Sequencer rate: sixteenth notes"),
    K("SEQ_RATE_SIXTEENTH_DOT", "16th\nDotted", "Sequencer rate: dotted sixteenth"),
    K("SEQ_RATE_SIXTEENTH_TRIP", "16th\nTriplet", "Sequencer rate: triplet sixteenth"),
    K("SEQ_RATE_RESET", "Rate\nReset", "Reset to preset's default rate"),

    # NEW: Rate cycling
    K("SEQ_RATE_UP", "Rate\nUp", "Cycle to next sequencer rate"),
    K("SEQ_RATE_DOWN", "Rate\nDown", "Cycle to previous sequencer rate"),

    # NEW: Static gate values
    K("STEP_SET_GATE_10", "Gate\n10%", "Set sequencer gate to 10%"),
    K("STEP_SET_GATE_20", "Gate\n20%", "Set sequencer gate to 20%"),
    K("STEP_SET_GATE_30", "Gate\n30%", "Set sequencer gate to 30%"),
    K("STEP_SET_GATE_40", "Gate\n40%", "Set sequencer gate to 40%"),
    K("STEP_SET_GATE_50", "Gate\n50%", "Set sequencer gate to 50%"),
    K("STEP_SET_GATE_60", "Gate\n60%", "Set sequencer gate to 60%"),
    K("STEP_SET_GATE_70", "Gate\n70%", "Set sequencer gate to 70%"),
    K("STEP_SET_GATE_80", "Gate\n80%", "Set sequencer gate to 80%"),
    K("STEP_SET_GATE_90", "Gate\n90%", "Set sequencer gate to 90%"),
    K("STEP_SET_GATE_100", "Gate\n100%", "Set sequencer gate to 100%"),

    # NEW: Sequencer modifiers
    K("SEQ_MOD_1", "Seq 1\nModifier", "Step Sequencer 1 Modifier"),
    K("SEQ_MOD_2", "Seq 2\nModifier", "Step Sequencer 2 Modifier"),
    K("SEQ_MOD_3", "Seq 3\nModifier", "Step Sequencer 3 Modifier"),
    K("SEQ_MOD_4", "Seq 4\nModifier", "Step Sequencer 4 Modifier"),
    K("SEQ_MOD_5", "Seq 5\nModifier", "Step Sequencer 5 Modifier"),
    K("SEQ_MOD_6", "Seq 6\nModifier", "Step Sequencer 6 Modifier"),
    K("SEQ_MOD_7", "Seq 7\nModifier", "Step Sequencer 7 Modifier"),
    K("SEQ_MOD_8", "Seq 8\nModifier", "Step Sequencer 8 Modifier"),
]

# Generate preset selection keycodes (48 factory + 20 user = 68 total)
KEYCODES_STEP_SEQUENCER_PRESETS = []
# Factory presets 0-47
for x in range(48):
    KEYCODES_STEP_SEQUENCER_PRESETS.append(
        K("SEQ_PRESET_{}".format(x), "Seq\nPreset\n{}".format(x), "Load sequencer preset {}".format(x))
    )
# User presets 48-67 (displayed as User 1-20)
for x in range(48, 68):
    user_num = x - 47
    KEYCODES_STEP_SEQUENCER_PRESETS.append(
        K("SEQ_PRESET_{}".format(x), "Seq\nUser\n{}".format(user_num), "Load sequencer user preset {}".format(user_num))
    )

# DKS (Dynamic Keystroke) slot keycodes (50 slots)
KEYCODES_DKS = []
for x in range(50):
    KEYCODES_DKS.append(
        K("DKS_{:02d}".format(x), "Dynamic\nKeystroke\n{}".format(x), "Dynamic Keystroke slot {} - multi-action analog key".format(x))
    )

# Toggle key slot keycodes (100 slots)
KEYCODES_TOGGLE = []
for x in range(100):
    KEYCODES_TOGGLE.append(
        K("TGL_{:02d}".format(x), "Toggle\n{}".format(x), "Toggle key slot {} - toggle keycode held/released".format(x))
    )

# =============================================================================
# DAW (Digital Audio Workstation) Shortcut Keycodes
# =============================================================================
# These keycodes send keyboard shortcuts commonly used in popular DAWs.
# Using LGUI (Windows key) as Command modifier since Windows keyboards map GUI to Cmd on Mac.

# -----------------------------------------------------------------------------
# ABLETON LIVE Shortcuts (0xDA00-0xDA3F)
# -----------------------------------------------------------------------------
KEYCODES_DAW_ABLETON = [
    # Transport Controls
    K("ABL_PLAY", "Play", "Ableton: Play/Pause (Space)"),
    K("ABL_STOP", "Stop", "Ableton: Stop (Space when playing)"),
    K("ABL_RECORD", "Record", "Ableton: Record (F9)"),
    K("ABL_LOOP", "Loop", "Ableton: Toggle Loop (Cmd/Ctrl+L)"),
    K("ABL_REWIND", "Rewind", "Ableton: Go to Start (Home)"),
    K("ABL_METRONOME", "Metro", "Ableton: Toggle Metronome (Cmd/Ctrl+U)"),
    K("ABL_TAP_TEMPO", "Tap\nTempo", "Ableton: Tap Tempo"),
    K("ABL_FOLLOW", "Follow", "Ableton: Follow Playhead (Cmd/Ctrl+Shift+F)"),

    # Editing
    K("ABL_UNDO", "Undo", "Ableton: Undo (Cmd/Ctrl+Z)"),
    K("ABL_REDO", "Redo", "Ableton: Redo (Cmd/Ctrl+Shift+Z)"),
    K("ABL_CUT", "Cut", "Ableton: Cut (Cmd/Ctrl+X)"),
    K("ABL_COPY", "Copy", "Ableton: Copy (Cmd/Ctrl+C)"),
    K("ABL_PASTE", "Paste", "Ableton: Paste (Cmd/Ctrl+V)"),
    K("ABL_DUPLICATE", "Dupe", "Ableton: Duplicate (Cmd/Ctrl+D)"),
    K("ABL_DELETE", "Delete", "Ableton: Delete (Backspace)"),
    K("ABL_SPLIT", "Split", "Ableton: Split Clip (Cmd/Ctrl+E)"),
    K("ABL_QUANTIZE", "Quant", "Ableton: Quantize (Cmd/Ctrl+U)"),
    K("ABL_CONSOLIDATE", "Consol", "Ableton: Consolidate (Cmd/Ctrl+J)"),

    # Track Controls
    K("ABL_SOLO", "Solo", "Ableton: Solo Track (S)"),
    K("ABL_MUTE", "Mute", "Ableton: Mute/Activate Track (0)"),
    K("ABL_ARM", "Arm", "Ableton: Arm Track (C)"),
    K("ABL_TRACK_UP", "Track\nUp", "Ableton: Select Previous Track (Up)"),
    K("ABL_TRACK_DOWN", "Track\nDown", "Ableton: Select Next Track (Down)"),
    K("ABL_NEW_AUDIO", "New\nAudio", "Ableton: Insert Audio Track (Cmd/Ctrl+T)"),
    K("ABL_NEW_MIDI", "New\nMIDI", "Ableton: Insert MIDI Track (Cmd/Ctrl+Shift+T)"),
    K("ABL_GROUP", "Group", "Ableton: Group Tracks (Cmd/Ctrl+G)"),

    # Navigation & Zoom
    K("ABL_ZOOM_IN", "Zoom\nIn", "Ableton: Zoom In (+)"),
    K("ABL_ZOOM_OUT", "Zoom\nOut", "Ableton: Zoom Out (-)"),
    K("ABL_ZOOM_FIT", "Zoom\nFit", "Ableton: Zoom to Fit (Z)"),
    K("ABL_PREV_MARKER", "Prev\nMarker", "Ableton: Previous Locator"),
    K("ABL_NEXT_MARKER", "Next\nMarker", "Ableton: Next Locator"),
    K("ABL_ADD_MARKER", "Add\nMarker", "Ableton: Add Locator"),

    # Views
    K("ABL_SESSION", "Session\nView", "Ableton: Toggle Session/Arrangement (Tab)"),
    K("ABL_BROWSER", "Browser", "Ableton: Toggle Browser (Cmd/Ctrl+Alt+B)"),
    K("ABL_DETAIL", "Detail", "Ableton: Toggle Detail View (Cmd/Ctrl+Alt+L)"),
    K("ABL_MIXER", "Mixer", "Ableton: Toggle Mixer (Cmd/Ctrl+Alt+M)"),
    K("ABL_SENDS", "Sends", "Ableton: Toggle Sends (Cmd/Ctrl+Alt+S)"),

    # Automation
    K("ABL_AUTO_ARM", "Auto\nArm", "Ableton: Toggle Automation Arm (A)"),
    K("ABL_AUTO_MODE", "Auto\nMode", "Ableton: Cycle Automation Mode"),

    # Tempo
    K("ABL_BPM_UP", "BPM\nUp", "Ableton: Increase Tempo"),
    K("ABL_BPM_DOWN", "BPM\nDown", "Ableton: Decrease Tempo"),

    # Additional
    K("ABL_SAVE", "Save", "Ableton: Save (Cmd/Ctrl+S)"),
    K("ABL_CAPTURE", "Capture\nMIDI", "Ableton: Capture MIDI (Cmd/Ctrl+Shift+C)"),
]

# -----------------------------------------------------------------------------
# FL STUDIO Shortcuts (0xDB00-0xDB3F)
# -----------------------------------------------------------------------------
KEYCODES_DAW_FL = [
    # Transport Controls
    K("FL_PLAY", "Play", "FL Studio: Play/Pause (Space)"),
    K("FL_STOP", "Stop", "FL Studio: Stop (Space)"),
    K("FL_RECORD", "Record", "FL Studio: Record (R)"),
    K("FL_LOOP", "Loop", "FL Studio: Toggle Pattern/Song Mode (L)"),
    K("FL_REWIND", "Rewind", "FL Studio: Go to Start (Home)"),
    K("FL_METRONOME", "Metro", "FL Studio: Toggle Metronome (Ctrl+M)"),
    K("FL_TAP_TEMPO", "Tap\nTempo", "FL Studio: Tap Tempo"),
    K("FL_PAT_MODE", "Pattern\nMode", "FL Studio: Pattern Mode (P)"),

    # Editing
    K("FL_UNDO", "Undo", "FL Studio: Undo (Ctrl+Z)"),
    K("FL_REDO", "Redo", "FL Studio: Redo (Ctrl+Y)"),
    K("FL_CUT", "Cut", "FL Studio: Cut (Ctrl+X)"),
    K("FL_COPY", "Copy", "FL Studio: Copy (Ctrl+C)"),
    K("FL_PASTE", "Paste", "FL Studio: Paste (Ctrl+V)"),
    K("FL_DUPLICATE", "Dupe", "FL Studio: Duplicate (Ctrl+B)"),
    K("FL_DELETE", "Delete", "FL Studio: Delete (Delete)"),
    K("FL_SPLIT", "Split", "FL Studio: Split at Cursor (C)"),
    K("FL_QUANTIZE", "Quant", "FL Studio: Quantize (Ctrl+Q)"),
    K("FL_QUICK_QUANT", "Quick\nQuant", "FL Studio: Quick Quantize (Shift+Q)"),

    # Track/Channel Controls
    K("FL_SOLO", "Solo", "FL Studio: Solo Channel (Ctrl+Click)"),
    K("FL_MUTE", "Mute", "FL Studio: Mute Channel"),
    K("FL_TRACK_UP", "Track\nUp", "FL Studio: Select Previous Track (Up)"),
    K("FL_TRACK_DOWN", "Track\nDown", "FL Studio: Select Next Track (Down)"),
    K("FL_NEW_PATTERN", "New\nPattern", "FL Studio: New Pattern (Ctrl+Shift+P)"),
    K("FL_CLONE_PAT", "Clone\nPattern", "FL Studio: Clone Pattern"),
    K("FL_ADD_CHANNEL", "Add\nChannel", "FL Studio: Add Channel"),
    K("FL_CHANNEL_UP", "Chan\nUp", "FL Studio: Select Previous Channel"),
    K("FL_CHANNEL_DOWN", "Chan\nDown", "FL Studio: Select Next Channel"),

    # Navigation & Zoom
    K("FL_ZOOM_IN", "Zoom\nIn", "FL Studio: Zoom In (Page Up)"),
    K("FL_ZOOM_OUT", "Zoom\nOut", "FL Studio: Zoom Out (Page Down)"),
    K("FL_ZOOM_FIT", "Zoom\nFit", "FL Studio: Zoom to Fit (Shift+0)"),
    K("FL_PREV_MARKER", "Prev\nMarker", "FL Studio: Previous Marker"),
    K("FL_NEXT_MARKER", "Next\nMarker", "FL Studio: Next Marker"),
    K("FL_ADD_MARKER", "Add\nMarker", "FL Studio: Add Time Marker (Ctrl+T)"),

    # Views
    K("FL_PLAYLIST", "Playlist", "FL Studio: Toggle Playlist (F5)"),
    K("FL_PIANO_ROLL", "Piano\nRoll", "FL Studio: Toggle Piano Roll (F7)"),
    K("FL_MIXER", "Mixer", "FL Studio: Toggle Mixer (F9)"),
    K("FL_BROWSER", "Browser", "FL Studio: Toggle Browser (F8)"),
    K("FL_CHANNEL_RACK", "Channel\nRack", "FL Studio: Toggle Channel Rack (F6)"),

    # Automation
    K("FL_AUTO_CLIP", "Auto\nClip", "FL Studio: Create Automation Clip"),
    K("FL_LINK_CTRL", "Link\nCtrl", "FL Studio: Link to Controller"),

    # Tempo
    K("FL_BPM_UP", "BPM\nUp", "FL Studio: Increase Tempo (+)"),
    K("FL_BPM_DOWN", "BPM\nDown", "FL Studio: Decrease Tempo (-)"),

    # Additional
    K("FL_SAVE", "Save", "FL Studio: Save (Ctrl+S)"),
    K("FL_EXPORT", "Export", "FL Studio: Export (Ctrl+R)"),
]

# -----------------------------------------------------------------------------
# LOGIC PRO Shortcuts (0xDC00-0xDC3F)
# -----------------------------------------------------------------------------
KEYCODES_DAW_LOGIC = [
    # Transport Controls
    K("LOG_PLAY", "Play", "Logic: Play/Pause (Space)"),
    K("LOG_STOP", "Stop", "Logic: Stop (0 or Space)"),
    K("LOG_RECORD", "Record", "Logic: Record (R or *)"),
    K("LOG_LOOP", "Loop", "Logic: Toggle Cycle (C)"),
    K("LOG_REWIND", "Rewind", "Logic: Go to Start (Return)"),
    K("LOG_METRONOME", "Metro", "Logic: Toggle Metronome (K)"),
    K("LOG_TAP_TEMPO", "Tap\nTempo", "Logic: Tap Tempo"),
    K("LOG_COUNT_IN", "Count\nIn", "Logic: Toggle Count-In"),

    # Editing
    K("LOG_UNDO", "Undo", "Logic: Undo (Cmd+Z)"),
    K("LOG_REDO", "Redo", "Logic: Redo (Cmd+Shift+Z)"),
    K("LOG_CUT", "Cut", "Logic: Cut (Cmd+X)"),
    K("LOG_COPY", "Copy", "Logic: Copy (Cmd+C)"),
    K("LOG_PASTE", "Paste", "Logic: Paste (Cmd+V)"),
    K("LOG_DUPLICATE", "Dupe", "Logic: Duplicate (Cmd+D)"),
    K("LOG_DELETE", "Delete", "Logic: Delete (Backspace)"),
    K("LOG_SPLIT", "Split", "Logic: Split at Playhead (Cmd+T)"),
    K("LOG_QUANTIZE", "Quant", "Logic: Quantize (Q)"),
    K("LOG_JOIN", "Join", "Logic: Join Regions (Cmd+J)"),

    # Track Controls
    K("LOG_SOLO", "Solo", "Logic: Solo Track (S)"),
    K("LOG_MUTE", "Mute", "Logic: Mute Track (M)"),
    K("LOG_ARM", "Arm", "Logic: Record Enable (R)"),
    K("LOG_TRACK_UP", "Track\nUp", "Logic: Select Previous Track (Up)"),
    K("LOG_TRACK_DOWN", "Track\nDown", "Logic: Select Next Track (Down)"),
    K("LOG_NEW_AUDIO", "New\nAudio", "Logic: New Audio Track (Opt+Cmd+A)"),
    K("LOG_NEW_SOFTWARE", "New\nInstr", "Logic: New Software Instrument (Opt+Cmd+S)"),
    K("LOG_NEW_DRUMMER", "New\nDrummer", "Logic: New Drummer Track (Opt+Cmd+D)"),

    # Navigation & Zoom
    K("LOG_ZOOM_IN", "Zoom\nIn", "Logic: Zoom In (Cmd+Arrow Right)"),
    K("LOG_ZOOM_OUT", "Zoom\nOut", "Logic: Zoom Out (Cmd+Arrow Left)"),
    K("LOG_ZOOM_FIT", "Zoom\nFit", "Logic: Zoom to Fit Selection (Z)"),
    K("LOG_PREV_MARKER", "Prev\nMarker", "Logic: Go to Previous Marker (,)"),
    K("LOG_NEXT_MARKER", "Next\nMarker", "Logic: Go to Next Marker (.)"),
    K("LOG_ADD_MARKER", "Add\nMarker", "Logic: Create Marker (Opt+')"),

    # Views
    K("LOG_PIANO_ROLL", "Piano\nRoll", "Logic: Toggle Piano Roll (P)"),
    K("LOG_MIXER", "Mixer", "Logic: Toggle Mixer (X)"),
    K("LOG_SMART_CTRL", "Smart\nCtrl", "Logic: Toggle Smart Controls (B)"),
    K("LOG_LIBRARY", "Library", "Logic: Toggle Library (Y)"),
    K("LOG_LOOPS", "Loops", "Logic: Toggle Loop Browser (O)"),

    # Automation
    K("LOG_AUTO_READ", "Auto\nRead", "Logic: Automation Read"),
    K("LOG_AUTO_TOUCH", "Auto\nTouch", "Logic: Automation Touch"),
    K("LOG_AUTO_LATCH", "Auto\nLatch", "Logic: Automation Latch"),
    K("LOG_AUTO_WRITE", "Auto\nWrite", "Logic: Automation Write"),
    K("LOG_AUTO_TOGGLE", "Auto\nToggle", "Logic: Toggle Automation (A)"),

    # Tempo
    K("LOG_BPM_UP", "BPM\nUp", "Logic: Increase Tempo"),
    K("LOG_BPM_DOWN", "BPM\nDown", "Logic: Decrease Tempo"),

    # Additional
    K("LOG_SAVE", "Save", "Logic: Save (Cmd+S)"),
    K("LOG_BOUNCE", "Bounce", "Logic: Bounce Project (Cmd+B)"),
]

# -----------------------------------------------------------------------------
# PRO TOOLS Shortcuts (0xDD00-0xDD3F)
# -----------------------------------------------------------------------------
KEYCODES_DAW_PROTOOLS = [
    # Transport Controls
    K("PT_PLAY", "Play", "Pro Tools: Play (Space)"),
    K("PT_STOP", "Stop", "Pro Tools: Stop (. numpad or Space)"),
    K("PT_RECORD", "Record", "Pro Tools: Record (F12 or Cmd+Space)"),
    K("PT_LOOP", "Loop", "Pro Tools: Toggle Loop Playback (Cmd/Ctrl+Shift+L)"),
    K("PT_REWIND", "Rewind", "Pro Tools: Return to Zero (Enter numpad)"),
    K("PT_METRONOME", "Metro", "Pro Tools: Toggle Click (7 numpad)"),
    K("PT_TAP_TEMPO", "Tap\nTempo", "Pro Tools: Tap Tempo"),
    K("PT_COUNT_IN", "Count\nIn", "Pro Tools: Toggle Count-Off (8 numpad)"),

    # Editing
    K("PT_UNDO", "Undo", "Pro Tools: Undo (Cmd/Ctrl+Z)"),
    K("PT_REDO", "Redo", "Pro Tools: Redo (Cmd/Ctrl+Shift+Z)"),
    K("PT_CUT", "Cut", "Pro Tools: Cut (Cmd/Ctrl+X)"),
    K("PT_COPY", "Copy", "Pro Tools: Copy (Cmd/Ctrl+C)"),
    K("PT_PASTE", "Paste", "Pro Tools: Paste (Cmd/Ctrl+V)"),
    K("PT_DUPLICATE", "Dupe", "Pro Tools: Duplicate (Cmd/Ctrl+D)"),
    K("PT_DELETE", "Delete", "Pro Tools: Clear (Delete)"),
    K("PT_SEPARATE", "Separate", "Pro Tools: Separate Region (Cmd/Ctrl+E or B)"),
    K("PT_HEAL", "Heal", "Pro Tools: Heal Separation (Cmd/Ctrl+H)"),
    K("PT_CONSOLIDATE", "Consol", "Pro Tools: Consolidate (Opt/Alt+Shift+3)"),

    # Track Controls
    K("PT_SOLO", "Solo", "Pro Tools: Solo Track (S)"),
    K("PT_MUTE", "Mute", "Pro Tools: Mute Track (M)"),
    K("PT_ARM", "Arm", "Pro Tools: Record Arm (Shift+R)"),
    K("PT_TRACK_UP", "Track\nUp", "Pro Tools: Select Previous Track (Up/;)"),
    K("PT_TRACK_DOWN", "Track\nDown", "Pro Tools: Select Next Track (Down/P)"),
    K("PT_NEW_TRACK", "New\nTrack", "Pro Tools: New Track (Cmd/Ctrl+Shift+N)"),
    K("PT_GROUP", "Group", "Pro Tools: Create Group (Cmd/Ctrl+G)"),
    K("PT_INPUT_MON", "Input\nMon", "Pro Tools: Toggle Input Monitor"),

    # Navigation & Zoom
    K("PT_ZOOM_IN", "Zoom\nIn", "Pro Tools: Zoom In (Cmd/Ctrl+])"),
    K("PT_ZOOM_OUT", "Zoom\nOut", "Pro Tools: Zoom Out (Cmd/Ctrl+[)"),
    K("PT_ZOOM_FIT", "Zoom\nFit", "Pro Tools: Zoom to Fit (Opt/Alt+A)"),
    K("PT_PREV_MARKER", "Prev\nMarker", "Pro Tools: Previous Memory Location (.)"),
    K("PT_NEXT_MARKER", "Next\nMarker", "Pro Tools: Next Memory Location (.)"),
    K("PT_ADD_MARKER", "Add\nMarker", "Pro Tools: Create Memory Location (Enter)"),

    # Views
    K("PT_MIX_WIN", "Mix\nWindow", "Pro Tools: Toggle Mix Window (Cmd/Ctrl+=)"),
    K("PT_EDIT_WIN", "Edit\nWindow", "Pro Tools: Toggle Edit Window (Cmd/Ctrl+=)"),
    K("PT_TRANSPORT", "Transport", "Pro Tools: Toggle Transport (Cmd/Ctrl+1 numpad)"),
    K("PT_MIDI_EDIT", "MIDI\nEdit", "Pro Tools: Open MIDI Editor"),
    K("PT_BROWSER", "Browser", "Pro Tools: Toggle Workspace Browser"),

    # Automation
    K("PT_AUTO_READ", "Auto\nRead", "Pro Tools: Automation Read"),
    K("PT_AUTO_WRITE", "Auto\nWrite", "Pro Tools: Automation Write"),
    K("PT_AUTO_TOUCH", "Auto\nTouch", "Pro Tools: Automation Touch"),
    K("PT_AUTO_LATCH", "Auto\nLatch", "Pro Tools: Automation Latch"),
    K("PT_AUTO_OFF", "Auto\nOff", "Pro Tools: Automation Off"),

    # Tempo
    K("PT_BPM_UP", "BPM\nUp", "Pro Tools: Increase Tempo"),
    K("PT_BPM_DOWN", "BPM\nDown", "Pro Tools: Decrease Tempo"),

    # Additional
    K("PT_SAVE", "Save", "Pro Tools: Save (Cmd/Ctrl+S)"),
    K("PT_BOUNCE", "Bounce", "Pro Tools: Bounce to Disk (Cmd/Ctrl+Opt/Alt+B)"),
]

# -----------------------------------------------------------------------------
# GARAGEBAND Shortcuts (0xDE00-0xDE3F)
# -----------------------------------------------------------------------------
KEYCODES_DAW_GARAGEBAND = [
    # Transport Controls
    K("GB_PLAY", "Play", "GarageBand: Play/Pause (Space)"),
    K("GB_STOP", "Stop", "GarageBand: Stop (Space)"),
    K("GB_RECORD", "Record", "GarageBand: Record (R)"),
    K("GB_LOOP", "Loop", "GarageBand: Toggle Cycle (C)"),
    K("GB_REWIND", "Rewind", "GarageBand: Go to Beginning (Return)"),
    K("GB_METRONOME", "Metro", "GarageBand: Toggle Metronome (K)"),
    K("GB_COUNT_IN", "Count\nIn", "GarageBand: Toggle Count-In (Shift+K)"),

    # Editing
    K("GB_UNDO", "Undo", "GarageBand: Undo (Cmd+Z)"),
    K("GB_REDO", "Redo", "GarageBand: Redo (Cmd+Shift+Z)"),
    K("GB_CUT", "Cut", "GarageBand: Cut (Cmd+X)"),
    K("GB_COPY", "Copy", "GarageBand: Copy (Cmd+C)"),
    K("GB_PASTE", "Paste", "GarageBand: Paste (Cmd+V)"),
    K("GB_DUPLICATE", "Dupe", "GarageBand: Duplicate (Cmd+D)"),
    K("GB_DELETE", "Delete", "GarageBand: Delete (Backspace)"),
    K("GB_SPLIT", "Split", "GarageBand: Split at Playhead (Cmd+T)"),
    K("GB_JOIN", "Join", "GarageBand: Join Regions (Cmd+J)"),

    # Track Controls
    K("GB_SOLO", "Solo", "GarageBand: Solo Track (S)"),
    K("GB_MUTE", "Mute", "GarageBand: Mute Track (M)"),
    K("GB_ARM", "Arm", "GarageBand: Record Enable"),
    K("GB_TRACK_UP", "Track\nUp", "GarageBand: Select Previous Track (Up)"),
    K("GB_TRACK_DOWN", "Track\nDown", "GarageBand: Select Next Track (Down)"),
    K("GB_NEW_TRACK", "New\nTrack", "GarageBand: New Track (Opt+Cmd+N)"),
    K("GB_DUPLICATE_TRK", "Dupe\nTrack", "GarageBand: Duplicate Track (Cmd+D)"),

    # Navigation & Zoom
    K("GB_ZOOM_IN", "Zoom\nIn", "GarageBand: Zoom In (Cmd++)"),
    K("GB_ZOOM_OUT", "Zoom\nOut", "GarageBand: Zoom Out (Cmd+-)"),
    K("GB_ZOOM_FIT", "Zoom\nFit", "GarageBand: Zoom to Fit (Shift+Z)"),

    # Views
    K("GB_SMART_CTRL", "Smart\nCtrl", "GarageBand: Toggle Smart Controls (B)"),
    K("GB_LIBRARY", "Library", "GarageBand: Toggle Library (Y)"),
    K("GB_LOOPS", "Loops", "GarageBand: Toggle Loop Browser (O)"),
    K("GB_EDITOR", "Editor", "GarageBand: Toggle Editor (E)"),
    K("GB_NOTE_PAD", "Note\nPad", "GarageBand: Toggle Note Pad (Cmd+Opt+P)"),

    # Tempo
    K("GB_BPM_UP", "BPM\nUp", "GarageBand: Increase Tempo"),
    K("GB_BPM_DOWN", "BPM\nDown", "GarageBand: Decrease Tempo"),

    # Additional
    K("GB_SAVE", "Save", "GarageBand: Save (Cmd+S)"),
    K("GB_SHARE", "Share", "GarageBand: Share Song to Music"),
    K("GB_MUSICAL_TYPING", "Musical\nTyping", "GarageBand: Toggle Musical Typing (Cmd+K)"),
]

KEYCODES_HIDDEN = []
for x in range(256):
    KEYCODES_HIDDEN.append(K("TD({})".format(x), "Tap/\nHold\n{}".format(x)))

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
                              "Fixed\nVelocity\n{}".format(x),
                              "Fixed Velocity {}".format(x)))
                              
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

# HE Velocity Curve keycodes
KEYCODES_HE_VELOCITY_CURVE = [
    K("HE_CURVE_SOFTEST", "HE Curve\nSoftest", "HE Velocity Curve Softest"),
    K("HE_CURVE_SOFT", "HE Curve\nSoft", "HE Velocity Curve Soft"),
    K("HE_CURVE_MEDIUM", "HE Curve\nMedium", "HE Velocity Curve Medium"),
    K("HE_CURVE_HARD", "HE Curve\nHard", "HE Velocity Curve Hard"),
    K("HE_CURVE_HARDEST", "HE Curve\nHardest", "HE Velocity Curve Hardest"),
]

# HE Velocity Range keycodes (min/max pairs where min ≤ max)
# Generates 8,128 keycodes total (127×128/2 triangular number)
KEYCODES_HE_VELOCITY_RANGE = []

for min_val in range(1, 128):  # 1 to 127
    for max_val in range(min_val, 128):  # min to 127 (includes min == max for fixed velocity)
        KEYCODES_HE_VELOCITY_RANGE.append(K("HE_VEL_RANGE_{}_{}".format(min_val, max_val),
                                  "VEL\n{}\n{}".format(min_val, max_val),
                                  "HE Velocity Range {}-{}".format(min_val, max_val)))

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
                    KEYCODES_HE_VELOCITY_CURVE+KEYCODES_HE_VELOCITY_RANGE+
                    KEYCODES_ARPEGGIATOR+KEYCODES_ARPEGGIATOR_PRESETS+KEYCODES_STEP_SEQUENCER+KEYCODES_STEP_SEQUENCER_PRESETS+KEYCODES_DKS+KEYCODES_TOGGLE+
                    KEYCODES_C_CHORDPROG_BASIC_MINOR + KEYCODES_C_CHORDPROG_BASIC_MAJOR + KEYCODES_C_CHORDPROG_INTERMEDIATE_MINOR + KEYCODES_C_CHORDPROG_INTERMEDIATE_MAJOR + KEYCODES_C_CHORDPROG_EXPERT_MINOR + KEYCODES_C_CHORDPROG_EXPERT_MAJOR +
                    KEYCODES_C_SHARP_CHORDPROG_BASIC_MINOR + KEYCODES_C_SHARP_CHORDPROG_BASIC_MAJOR + KEYCODES_C_SHARP_CHORDPROG_INTERMEDIATE_MINOR + KEYCODES_C_SHARP_CHORDPROG_INTERMEDIATE_MAJOR + KEYCODES_C_SHARP_CHORDPROG_EXPERT_MINOR + KEYCODES_C_SHARP_CHORDPROG_EXPERT_MAJOR +
                    KEYCODES_D_CHORDPROG_BASIC_MINOR + KEYCODES_D_CHORDPROG_BASIC_MAJOR + KEYCODES_D_CHORDPROG_INTERMEDIATE_MINOR + KEYCODES_D_CHORDPROG_INTERMEDIATE_MAJOR + KEYCODES_D_CHORDPROG_EXPERT_MINOR + KEYCODES_D_CHORDPROG_EXPERT_MAJOR +
                    KEYCODES_E_FLAT_CHORDPROG_BASIC_MINOR + KEYCODES_E_FLAT_CHORDPROG_BASIC_MAJOR + KEYCODES_E_FLAT_CHORDPROG_INTERMEDIATE_MINOR + KEYCODES_E_FLAT_CHORDPROG_INTERMEDIATE_MAJOR + KEYCODES_E_FLAT_CHORDPROG_EXPERT_MINOR + KEYCODES_E_FLAT_CHORDPROG_EXPERT_MAJOR +
                    KEYCODES_E_CHORDPROG_BASIC_MINOR + KEYCODES_E_CHORDPROG_BASIC_MAJOR + KEYCODES_E_CHORDPROG_INTERMEDIATE_MINOR + KEYCODES_E_CHORDPROG_INTERMEDIATE_MAJOR + KEYCODES_E_CHORDPROG_EXPERT_MINOR + KEYCODES_E_CHORDPROG_EXPERT_MAJOR +
                    KEYCODES_F_CHORDPROG_BASIC_MINOR + KEYCODES_F_CHORDPROG_BASIC_MAJOR + KEYCODES_F_CHORDPROG_INTERMEDIATE_MINOR + KEYCODES_F_CHORDPROG_INTERMEDIATE_MAJOR + KEYCODES_F_CHORDPROG_EXPERT_MINOR + KEYCODES_F_CHORDPROG_EXPERT_MAJOR + KEYCODES_LOOP_BUTTONS + KEYCODES_GAMING +
                    KEYCODES_F_SHARP_CHORDPROG_BASIC_MINOR + KEYCODES_F_SHARP_CHORDPROG_BASIC_MAJOR + KEYCODES_F_SHARP_CHORDPROG_INTERMEDIATE_MINOR + KEYCODES_F_SHARP_CHORDPROG_INTERMEDIATE_MAJOR + KEYCODES_F_SHARP_CHORDPROG_EXPERT_MINOR + KEYCODES_F_SHARP_CHORDPROG_EXPERT_MAJOR +
                    KEYCODES_G_CHORDPROG_BASIC_MINOR + KEYCODES_G_CHORDPROG_BASIC_MAJOR + KEYCODES_G_CHORDPROG_INTERMEDIATE_MINOR + KEYCODES_G_CHORDPROG_INTERMEDIATE_MAJOR + KEYCODES_G_CHORDPROG_EXPERT_MINOR + KEYCODES_G_CHORDPROG_EXPERT_MAJOR + KEYCODES_A_FLAT_CHORDPROG_BASIC_MINOR + KEYCODES_A_FLAT_CHORDPROG_BASIC_MAJOR + KEYCODES_A_FLAT_CHORDPROG_INTERMEDIATE_MINOR + KEYCODES_A_FLAT_CHORDPROG_INTERMEDIATE_MAJOR + KEYCODES_A_FLAT_CHORDPROG_EXPERT_MINOR + KEYCODES_A_FLAT_CHORDPROG_EXPERT_MAJOR + KEYCODES_A_CHORDPROG_BASIC_MINOR + KEYCODES_A_CHORDPROG_BASIC_MAJOR + KEYCODES_A_CHORDPROG_INTERMEDIATE_MINOR + KEYCODES_A_CHORDPROG_INTERMEDIATE_MAJOR + KEYCODES_A_CHORDPROG_EXPERT_MINOR + KEYCODES_A_CHORDPROG_EXPERT_MAJOR + KEYCODES_B_FLAT_CHORDPROG_BASIC_MINOR + KEYCODES_B_FLAT_CHORDPROG_BASIC_MAJOR + KEYCODES_B_FLAT_CHORDPROG_INTERMEDIATE_MINOR + KEYCODES_B_FLAT_CHORDPROG_INTERMEDIATE_MAJOR + KEYCODES_B_FLAT_CHORDPROG_EXPERT_MINOR + KEYCODES_B_FLAT_CHORDPROG_EXPERT_MAJOR + KEYCODES_B_CHORDPROG_BASIC_MINOR + KEYCODES_B_CHORDPROG_BASIC_MAJOR + KEYCODES_B_CHORDPROG_INTERMEDIATE_MINOR + KEYCODES_B_CHORDPROG_INTERMEDIATE_MAJOR + KEYCODES_B_CHORDPROG_EXPERT_MINOR + KEYCODES_B_CHORDPROG_EXPERT_MAJOR +
                    KEYCODES_MIDI_INVERSION+KEYCODES_MIDI_SCALES+KEYCODES_MIDI_OCTAVE+KEYCODES_MIDI_KEY+KEYCODES_Program_Change_UPDOWN+KEYCODES_MIDI_BANK_LSB+KEYCODES_MIDI_BANK_MSB+KEYCODES_MIDI_PEDAL+KEYCODES_MIDI_ADVANCED+KEYCODES_MIDI_INOUT+KEYCODES_MIDI_SPLIT_BUTTONS+KEYCODES_BASIC + KEYCODES_SHIFTED + KEYCODES_CHORD_PROG_CONTROLS +
                    KEYCODES_DAW_ABLETON + KEYCODES_DAW_FL + KEYCODES_DAW_LOGIC + KEYCODES_DAW_PROTOOLS + KEYCODES_DAW_GARAGEBAND)
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
        qmk_id = "M{}".format(x)
        label = "Macro\n{}".format(x)
        KEYCODES_MACRO.append(Keycode(qmk_id, label))


    KEYCODES_TAP_DANCE.clear()
    for x in range(keyboard.tap_dance_count):
        qmk_id = "TD({})".format(x)
        label = "Tap/\nHold\n{}".format(x)
        KEYCODES_TAP_DANCE.append(Keycode(qmk_id, label, "Tap dance keycode"))

    # Check if custom keycodes are defined in keyboard, and if so add them to user keycodes
    if keyboard.custom_keycodes is not None and len(keyboard.custom_keycodes) > 0:
        create_custom_user_keycodes(keyboard.custom_keycodes)
    else:
        create_user_keycodes()

    create_midi_keycodes(keyboard.midi)

    recreate_keycodes()


recreate_keycodes()
