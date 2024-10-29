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
  #  K("OLED_1", "Hold\nLayer\n1", "Momentarily turn on layer when pressed"),
  #  K("OLED_1", "Hold\nLayer\n2", "Momentarily turn on layer when pressed"),
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
    K("M1", "Macro 0", "Macro 1"),
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
    K("M127", "Macro 127", "Macro 127")
]


KEYCODES_MACRO_BASE = [
    K("DYN_REC_START1", "DM1\nRec", "Dynamic Macro 1 Rec Start", alias=["DM_REC1"]),
    K("DYN_REC_START2", "DM2\nRec", "Dynamic Macro 2 Rec Start", alias=["DM_REC2"]),    
    K("DYN_MACRO_PLAY1", "DM1\nPlay", "Dynamic Macro 1 Play", alias=["DM_PLY1"]),
    K("DYN_MACRO_PLAY2", "DM2\nPlay", "Dynamic Macro 2 Play", alias=["DM_PLY2"]),
    K("DYN_REC_STOP", "DM Rec\nStop", "Dynamic Macro Rec Stop", alias=["DM_RSTP"]),
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

KEYCODES_MIDI_ADVANCED = [
    K("MI_TRNSU", "Transpose\n▲", "Midi increase transposition"), 
    K("MI_OCTU", "Octave\n▲", "Midi move up an octave"),  
    K("MI_VELOCITY_UP", "Velocity\n▲", "Midi increase velocity"),  
    K("MI_CHU", "Channel\n▲", "Midi increase channel"),   
    K("MI_BENDU", "Pitch\nBend ▲", "Midi bend pitch up"),   
    K("MI_MODSU", "Mod\nSpeed ▲", "Midi increase modulation speed"), 
    K("MI_PROG_UP", "Program\n▲", "Program up")  ,  
    K("MI_BANK_UP", "Bank\n▲", "Bank up"),
    K("MI_ALLOFF", "All\nNotes\nOff", "Midi send all notes OFF"),    
    K("MI_PORT", "Portmento", "Midi Portmento"),
    K("MI_SOST", "Sostenuto", "Midi Sostenuto"),
    K("MI_LEG", "Legato", "Midi Legato"),         
    K("MI_TRNSD", "Transpose\n▼", "Midi decrease transposition"),  
    K("MI_OCTD", "Octave\n▼", "Midi move down an octave"),
    K("MI_VELOCITY_DOWN", "Velocity\n▼", "Midi decrease velocity"), 
    K("MI_CHD", "Channel\n▼", "Midi decrease channel"),
    K("MI_BENDD", "Pitch\nBend ▼", "Midi bend pitch down"),
    K("MI_MODSD", "Mod\nSpeed ▼", "Midi decrease modulation speed"), 
    K("MI_PROG_DWN", "Program\n▼", "Program down"),
    K("MI_BANK_DWN", "Bank\n▼", "Bank down"),
    K("MI_MOD", "Modulation", "Midi Modulation"),
    K("MI_SUS", "Sustain\nPedal", "Midi Sustain"),
    K("MI_SOFT", "Soft\nSPedal", "Midi Soft Pedal"),
    K("OLED_1", "Screen\nKeyboard\nShift", "Momentarily turn on layer when pressed"),
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

KEYCODES_CC_STEPSIZE = [
    K("CC_STEPSIZE_1", "CC\nUp/Down\nx1", "SET CC Up/Down TO X1"),
    K("CC_STEPSIZE_2", "CC\nUp/Down\nx2", "SET CC Up/Down TO X2"),
    K("CC_STEPSIZE_3", "CC\nUp/Down\nx3", "SET CC Up/Down TO X3"),
    K("CC_STEPSIZE_4", "CC\nUp/Down\nx4", "SET CC Up/Down TO X4"),
    K("CC_STEPSIZE_5", "CC\nUp/Down\nx5", "SET CC Up/Down TO X5"),
    K("CC_STEPSIZE_6", "CC\nUp/Down\nx6", "SET CC Up/Down TO X6"),
    K("CC_STEPSIZE_7", "CC\nUp/Down\nx7", "SET CC Up/Down TO X7"),
    K("CC_STEPSIZE_8", "CC\nUp/Down\nx8", "SET CC Up/Down TO X8"),
    K("CC_STEPSIZE_9", "CC\nUp/Down\nx9", "SET CC Up/Down TO X9"),
    K("CC_STEPSIZE_10", "CC\nUp/Down\nx10", "SET CC Up/Down TO X10"),
]

KEYCODES_VELOCITY_STEPSIZE = [
    K("MI_VELOCITY_STEPSIZE_1", "Velocity\nUp/Down\nx1", "SET Velocity Up/Down x1"),
    K("MI_VELOCITY_STEPSIZE_2", "Velocity\nUp/Down\nx2", "SET Velocity Up/Down TO x2"),
    K("MI_VELOCITY_STEPSIZE_3", "Velocity\nUp/Down\nx3", "SET Velocity Up/Down TO x3"),
    K("MI_VELOCITY_STEPSIZE_4", "Velocity\nUp/Down\nx4", "SET Velocity Up/Down TO x4"),
    K("MI_VELOCITY_STEPSIZE_5", "Velocity\nUp/Down\nx5", "SET Velocity Up/Down TO x5"),
    K("MI_VELOCITY_STEPSIZE_6", "Velocity\nUp/Down\nx6", "SET Velocity Up/Down TO x6"),
    K("MI_VELOCITY_STEPSIZE_7", "Velocity\nUp/Down\nx7", "SET Velocity Up/Down TO x7"),
    K("MI_VELOCITY_STEPSIZE_8", "Velocity\nUp/Down\nx8", "SET Velocity Up/Down TO x8"),
    K("MI_VELOCITY_STEPSIZE_9", "Velocity\nUp/Down\nx9", "SET Velocity Up/Down TO x9"),
    K("MI_VELOCITY_STEPSIZE_10", "Velocity\nUp/Down\nx10", "SET Velocity Up/Down TO x10"),
]

KEYCODES_MIDI_SMARTCHORDBUTTONS = [
    K("SMARTCHORD_DOWN", "Smart\nChord\n▼", "QuickChord Down"),
    K("MI_CHORD_99", "Smart\nChord", "Press QuickChord"),
    K("SMARTCHORD_UP", "Smart\nChord\n▲", "QuickChord Up"),
    K("COLORBLIND_TOGGLE", "Colorblind\nMode\nOn/Off", "Colorblind"),
    K("SMARTCHORDCOLOR_TOGGLE", "Smart\nchord\nRGB", "Smartchord LEDs Toggle"),
    K("OLED_1", "Screen\nKeyboard\nShift", "Momentarily turn on layer when pressed"),
    
]

KEYCODES_MIDI_CHANNEL_HOLD = [
    K("MI_CHANNEL_HOLD_1", "HOLD\nChannel\n1", "Hold for MIDI channel 1, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_2", "HOLD\nChannel\n2", "Hold for MIDI channel 2, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_3", "HOLD\nChannel\n3", "Hold for MIDI channel 3, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_4", "HOLD\nChannel\n4", "Hold for MIDI channel 4, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_5", "HOLD\nChannel\n5", "Hold for MIDI channel 5, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_6", "HOLD\nChannel\n6", "Hold for MIDI channel 6, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_7", "HOLD\nChannel\n7", "Hold for MIDI channel 7, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_8", "HOLD\nChannel\n8", "Hold for MIDI channel 8, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_9", "HOLD\nChannel\n9", "Hold for MIDI channel 9, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_10", "HOLD\nChannel\n10", "Hold for MIDI channel 10, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_11", "HOLD\nChannel\n11", "Hold for MIDI channel 11, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_12", "HOLD\nChannel\n12", "Hold for MIDI channel 12, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_13", "HOLD\nChannel\n13", "Hold for MIDI channel 13, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_14", "HOLD\nChannel\n14", "Hold for MIDI channel 14, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_15", "HOLD\nChannel\n15", "Hold for MIDI channel 15, release for default MIDI channel"),
    K("MI_CHANNEL_HOLD_16", "HOLD\nChannel\n16", "Hold for MIDI channel 16, release for default MIDI channel"),
]

KEYCODES_MIDI_CHANNEL_OS = [
    K("MI_CHANNEL_OS_1", "Next Key\nChannel\n1", "Temporary switch to MIDI channel 1"),
    K("MI_CHANNEL_OS_2", "Next Key\nChannel\n2", "Temporary switch to MIDI channel 2"),
    K("MI_CHANNEL_OS_3", "Next Key\nChannel\n3", "Temporary switch to MIDI channel 3"),
    K("MI_CHANNEL_OS_4", "Next Key\nChannel\n4", "Temporary switch to MIDI channel 4"),
    K("MI_CHANNEL_OS_5", "Next Key\nChannel\n5", "Temporary switch to MIDI channel 5"),
    K("MI_CHANNEL_OS_6", "Next Key\nChannel\n6", "Temporary switch to MIDI channel 6"),
    K("MI_CHANNEL_OS_7", "Next Key\nChannel\n7", "Temporary switch to MIDI channel 7"),
    K("MI_CHANNEL_OS_8", "Next Key\nChannel\n8", "Temporary switch to MIDI channel 8"),
    K("MI_CHANNEL_OS_9", "Next Key\nChannel\n9", "Temporary switch to MIDI channel 9"),
    K("MI_CHANNEL_OS_10", "Next Key\nChannel\n10", "Temporary switch to MIDI channel 10"),
    K("MI_CHANNEL_OS_11", "Next Key\nChannel\n11", "Temporary switch to MIDI channel 11"),
    K("MI_CHANNEL_OS_12", "Next Key\nChannel\n12", "Temporary switch to MIDI channel 12"),
    K("MI_CHANNEL_OS_13", "Next Key\nChannel\n13", "Temporary switch to MIDI channel 13"),
    K("MI_CHANNEL_OS_14", "Next Key\nChannel\n14", "Temporary switch to MIDI channel 14"),
    K("MI_CHANNEL_OS_15", "Next Key\nChannel\n15", "Temporary switch to MIDI channel 15"),
    K("MI_CHANNEL_OS_16", "Next Key\nChannel\n16", "Temporary switch to MIDI channel 16"),
]


KEYCODES_MIDI_CHORD_1 = [
K("MI_CHORD_0", "Major", "Major Chord"),
K("MI_CHORD_1", "Minor", "Minor Chord"),
K("MI_CHORD_2", "Dim\n/\n°", "Diminished Chord"),
K("MI_CHORD_128", "Aug\n/\n+", "Aug Chord"),
K("MI_CHORD_3", "b5", "b5 Chord"),
K("MI_CHORD_4", "Sus2", "Sus2 Chord"),
K("MI_CHORD_5", "Sus4", "Sus4 Chord"),
K("MI_CHORD_32", "Maj7\nno5", "Maj7no5 Chord"),
K("MI_CHORD_33", "min7\nno5", "Min7no5 Chord"),
K("MI_CHORD_34", "7\nno5", "7no5 Chord"),
]

KEYCODES_MIDI_CHORD_2 = [
K("MI_CHORD_17", "Add2", "Add2 Chord"),
K("MI_CHORD_18", "min\nAdd2", "mAdd2 Chord"),
K("MI_CHORD_19", "Add4", "Add4 Chord"),
K("MI_CHORD_20", "min\nAdd4", "mAdd4 Chord"),
K("MI_CHORD_6", "Major\n6", "Major 6 Chord"),
K("MI_CHORD_7", "Minor\n6", "Minor 6 Chord"),
K("MI_CHORD_8", "Maj7", "Maj7 Chord"),
K("MI_CHORD_9", "min7", "min7 Chord"),
K("MI_CHORD_10", "7\nChord", "7 Chord"),
K("MI_CHORD_11", "Dim7\n/\nb7b5", "Dim7 Chord"),
K("MI_CHORD_12", "HalfDim7\n/\nm7b5", "Half Dim7 Chord"),
K("MI_CHORD_35", "Add9", "Add9 Chord"),
K("MI_CHORD_36", "min\nAdd9", "minAdd9 Chord"),
K("MI_CHORD_43", "Add11", "Add11 Chord"),
K("MI_CHORD_44", "min\nAdd11", "minAdd11 Chord"),
]

KEYCODES_MIDI_CHORD_3 = [
K("MI_CHORD_21", "6/9", "6/9 Chord"),
K("MI_CHORD_22", "Minor\n6/9", "Minor 6/9 Chord"),
K("MI_CHORD_14", "Maj9", "Maj9 Chord"),
K("MI_CHORD_15", "min9", "min9 Chord"),
K("MI_CHORD_16", "9\nChord", "9 Chord"),
K("MI_CHORD_37", "Dim9\n/\nb7b5(9)", "Dim9 Chord"),
K("MI_CHORD_38", "HalfDim9\n/\nm7b5(9)", "Half Dim9 Chord"),
K("MI_CHORD_39", "Aug9", "Aug9 Chord"),
K("MI_CHORD_40", "Maj11", "Maj11 Chord"),
K("MI_CHORD_41", "min11", "min11 Chord"),
K("MI_CHORD_42", "11\nChord", "11 Chord"),
]

KEYCODES_MIDI_CHORD_4 = [
K("MI_CHORD_23", "MinMaj7", "MinMaj7 Chord"),
K("MI_CHORD_24", "Maj7\nSus4", "Maj7sus4 Chord"),
K("MI_CHORD_25", "7\nSus4", "7sus4 Chord"),
K("MI_CHORD_26", "Maj7\nSus2", "Maj7sus2 Chord"),
K("MI_CHORD_27", "7\nSus2", "7sus2 Chord"),
K("MI_CHORD_28", "Maj7\n#5", "Maj7#5 Chord"),
K("MI_CHORD_29", "min7\n#5", "Min7#5 Chord"),
K("MI_CHORD_13", "Aug7\n/\n7#5", "Aug7 Chord"),
K("MI_CHORD_30", "Maj7\nb5", "Maj7b5 Chord"),
K("MI_CHORD_31", "7\nb5", "7b5 Chord"),
K("MI_CHORD_45", "Maj7\nAdd11", "Maj7Add11 Chord"),
K("MI_CHORD_46", "min7\nAdd11", "min7Add11 Chord"),
K("MI_CHORD_47", "7\nAdd11", "7Add11 Chord"),
K("MI_CHORD_50", "Maj7\n#11", "Maj7#11 Chord"),
K("MI_CHORD_51", "min7\n#11", "min7#11 Chord"),
K("MI_CHORD_52", "7\n#11", "7#11 Chord"),
K("MI_CHORD_48", "Dim11\n/\nb7b5(9/11)", "Dim11 Chord"),
K("MI_CHORD_49", "HalfDim11\n/\nm7b5(9/11)", "HalfDim11 Chord"),
]

KEYCODES_MIDI_SCALES = [ 
K("MI_CHORD_110", "Major Pentatonic", "Pentatonic"),
K("MI_CHORD_111", "Minor Pentatonic", "Minor Pentatonic"),
K("MI_CHORD_100", "Major Scale / Ionian", "Ionian/Major Scale"),
K("MI_CHORD_105", "Minor Scale / Aeolian", "Aeolian Scale"),
K("MI_CHORD_101", "Dorian", "Dorian Scale"),
K("MI_CHORD_102", "Phrygian", "Phrygian Scale"),
K("MI_CHORD_103", "Lydian", "Lydian Scale"),
K("MI_CHORD_104", "Mixolydian", "Mixolydian Scale"),
K("MI_CHORD_106", "Locrian", "Locrian Scale"),
K("MI_CHORD_107", "Harmonic Minor", "Harmonic Minor"),
K("MI_CHORD_108", "Melodic Minor", "Melodic Minor"),
K("MI_CHORD_109", "Whole Step Scale", "Whole Step Scale"),
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
                    KEYCODES_BOOT + KEYCODES_MODIFIERS + KEYCODES_QUANTUM + KEYCODES_BACKLIGHT + KEYCODES_MEDIA + KEYCODES_OLED + KEYCODES_CLEAR + KEYCODES_RGB_KC_COLOR +
                    KEYCODES_TAP_DANCE + KEYCODES_MACRO + KEYCODES_MACRO_BASE + KEYCODES_USER + KEYCODES_HIDDEN + KEYCODES_MIDI+ KEYCODES_MIDI_CHANNEL_OS + KEYCODES_MIDI_CHANNEL_HOLD + KEYCODES_RGB_KC_CUSTOM +
                    KEYCODES_MIDI_CC_FIXED+KEYCODES_MIDI_CC+KEYCODES_MIDI_CC_DOWN+KEYCODES_MIDI_CC_UP+KEYCODES_MIDI_BANK+KEYCODES_Program_Change+KEYCODES_MIDI_SMARTCHORDBUTTONS+KEYCODES_VELOCITY_STEPSIZE+
                    KEYCODES_MIDI_VELOCITY+KEYCODES_CC_STEPSIZE+KEYCODES_MIDI_CHANNEL+KEYCODES_MIDI_UPDOWN+KEYCODES_MIDI_CHORD_1+KEYCODES_MIDI_CHORD_2+KEYCODES_MIDI_CHORD_3+KEYCODES_MIDI_CHORD_4+
                    KEYCODES_MIDI_INVERSION+KEYCODES_MIDI_SCALES+KEYCODES_MIDI_OCTAVE+KEYCODES_MIDI_KEY+KEYCODES_Program_Change_UPDOWN+KEYCODES_MIDI_BANK_LSB+KEYCODES_MIDI_BANK_MSB+KEYCODES_MIDI_PEDAL+KEYCODES_MIDI_ADVANCED)
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
