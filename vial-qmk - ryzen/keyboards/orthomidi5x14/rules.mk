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


KEYBOARD_SHARED_EP = yes

EEPROM_DRIVER = i2c

#EEPROM_DRIVER = wear_leveling
#WEAR_LEVELING_DRIVER = embedded_flash

DYNAMIC_MACRO_ENABLE = yes
RGB_MATRIX_ENABLE = yes
RGB_MATRIX_DRIVER = WS2812
RGB_MATRIX_CUSTOM_USER = yes

CUSTOM_MATRIX = lite
SRC += matrix.c