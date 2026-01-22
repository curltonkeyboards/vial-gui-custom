MIDI_ENABLE = yes
MIDI_SERIAL_ENABLE = yes
SERIAL_DRIVER = usart
RAW_ENABLE = yes
OLED_ENABLE = yes
OLED_DRIVER = SSD1306
OLED_TRANSPORT = i2c

BOOTMAGIC_ENABLE = yes      # Enable Bootmagic Lite
MOUSEKEY_ENABLE = yes       # Mouse keys
EXTRAKEY_ENABLE = yes       # Audio control and System control
CONSOLE_ENABLE = no         # Console for debug
COMMAND_ENABLE = no         # Commands for debug and configuration
NKRO_ENABLE = yes           # Enable USB N-key Rollover
BACKLIGHT_ENABLE = no       # Enable keyboard backlight functionality
RGBLIGHT_ENABLE = no        # Enable keyboard RGB underglow
AUDIO_ENABLE = no           # Audio output
ENCODER_ENABLE = yes        # Enable Encoder
KEYLOGGER_ENABLE      = yes
WPM_ENABLE = yes
JOYSTICK_ENABLE = yes       # Enable joystick/gaming controller support

HID_DEBUG_LAYER_RGB = yes
HID_DEBUG_PER_KEY_RGB = yes
ORTHOMIDI_CUSTOM_HID_ENABLE = yes

# Convert custom flags to C defines
ifeq ($(ORTHOMIDI_CUSTOM_HID_ENABLE), yes)
    OPT_DEFS += -DORTHOMIDI_CUSTOM_HID_ENABLE
endif

KEYBOARD_SHARED_EP = yes

EEPROM_DRIVER = i2c

#EEPROM_DRIVER = wear_leveling
#WEAR_LEVELING_DRIVER = embedded_flash

DYNAMIC_MACRO_ENABLE = yes
RGB_MATRIX_ENABLE = yes
RGB_MATRIX_DRIVER = WS2812
RGB_MATRIX_CUSTOM_USER = yes

#CUSTOM_MATRIX = lite
#SRC += matrix.c

# Arpeggiator system
SRC += arpeggiator.c
SRC += arpeggiator_hid.c
SRC += arp_factory_presets.c

# DKS (Dynamic Keystroke) system
SRC += quantum/process_keycode/process_dks.c