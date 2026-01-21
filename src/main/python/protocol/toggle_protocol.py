# SPDX-License-Identifier: GPL-2.0-or-later
"""
Toggle Keys Protocol Handler

Provides toggle key functionality where pressing a key toggles between
holding and releasing a target keycode. This is implemented as keybinds
(TGL_00 - TGL_99) that can be assigned to any physical key.

Each toggle slot contains:
- target_keycode: The keycode to toggle (held until toggled again)
- state: Current state (0 = released, 1 = held) - runtime only

Usage:
1. Configure a toggle slot with a target keycode via GUI
2. Assign TGL_XX keycode to a physical key in keymap
3. Pressing the key toggles the target keycode held/released state
"""

import struct
from typing import Optional, List

# Toggle HID Command Codes (0xF5-0xF9)
HID_CMD_TOGGLE_GET_SLOT = 0xF5        # Get toggle slot configuration
HID_CMD_TOGGLE_SET_SLOT = 0xF6        # Set toggle slot configuration
HID_CMD_TOGGLE_SAVE_EEPROM = 0xF7     # Save all slots to EEPROM
HID_CMD_TOGGLE_LOAD_EEPROM = 0xF8     # Load all slots from EEPROM
HID_CMD_TOGGLE_RESET_ALL = 0xF9       # Reset all slots to defaults

# Toggle Constants
TOGGLE_NUM_SLOTS = 100                 # Number of toggle slots (TGL_00 - TGL_99)
TOGGLE_SLOT_SIZE = 4                   # Bytes per slot in firmware

# Toggle Keycode Range
TOGGLE_KEY_BASE = 0xEE00               # TGL_00
TOGGLE_KEY_MAX = 0xEE63                # TGL_99 (0xEE00 + 99)


def is_toggle_keycode(keycode: int) -> bool:
    """Check if a keycode is a toggle keycode (TGL_XX)"""
    return TOGGLE_KEY_BASE <= keycode <= TOGGLE_KEY_MAX


def toggle_keycode_to_slot(keycode: int) -> int:
    """Convert a toggle keycode to its slot number"""
    return keycode - TOGGLE_KEY_BASE


def slot_to_toggle_keycode(slot: int) -> int:
    """Convert a slot number to its toggle keycode"""
    return TOGGLE_KEY_BASE + slot


class ToggleSlot:
    """Represents a toggle slot configuration"""

    def __init__(self, target_keycode: int = 0):
        """Initialize a toggle slot

        Args:
            target_keycode: The keycode to toggle (0 = disabled/empty)
        """
        self.target_keycode = target_keycode

    def is_enabled(self) -> bool:
        """Check if this slot is configured (has a target keycode)"""
        return self.target_keycode != 0

    def to_bytes(self) -> bytes:
        """Pack slot into firmware format (4 bytes)

        Format:
        - bytes 0-1: target_keycode (uint16_t)
        - bytes 2-3: reserved (for future use, e.g., options/flags)
        """
        data = bytearray(TOGGLE_SLOT_SIZE)
        struct.pack_into('<H', data, 0, self.target_keycode)
        # bytes 2-3 reserved, already 0
        return bytes(data)

    @staticmethod
    def from_bytes(data: bytes) -> 'ToggleSlot':
        """Unpack slot from firmware format"""
        if len(data) < TOGGLE_SLOT_SIZE:
            raise ValueError(f"Toggle slot data must be {TOGGLE_SLOT_SIZE} bytes")

        slot = ToggleSlot()
        slot.target_keycode = struct.unpack_from('<H', data, 0)[0]
        return slot

    def to_dict(self) -> dict:
        """Convert to dictionary for GUI"""
        return {
            'target_keycode': self.target_keycode
        }

    @staticmethod
    def from_dict(data: dict) -> 'ToggleSlot':
        """Create from dictionary"""
        return ToggleSlot(
            target_keycode=data.get('target_keycode', 0)
        )


class ProtocolToggle:
    """Toggle protocol handler - manages communication with firmware"""

    def __init__(self, keyboard):
        """Initialize Toggle protocol

        Args:
            keyboard: Keyboard communication object
        """
        self.keyboard = keyboard
        self.slots_cache = {}  # Cache of loaded slots

    def get_slot(self, slot_num: int) -> Optional[ToggleSlot]:
        """Get toggle slot configuration from keyboard

        Args:
            slot_num: Slot number (0-99)

        Returns:
            ToggleSlot object or None on error
        """
        if slot_num < 0 or slot_num >= TOGGLE_NUM_SLOTS:
            return None

        try:
            packet = self.keyboard._create_hid_packet(HID_CMD_TOGGLE_GET_SLOT, 0, [slot_num])
            response = self.keyboard.usb_send(self.keyboard.dev, packet, retries=3)

            if not response or len(response) < (5 + TOGGLE_SLOT_SIZE):
                return None

            # Check status byte (firmware puts it at index 4)
            if response[4] != 0:
                return None

            # Extract slot data (firmware puts it at index 5)
            slot_data = response[5:5 + TOGGLE_SLOT_SIZE]
            slot = ToggleSlot.from_bytes(slot_data)

            # Cache it
            self.slots_cache[slot_num] = slot

            return slot

        except Exception as e:
            print(f"Toggle: Error getting slot {slot_num}: {e}")
            return None

    def set_slot(self, slot_num: int, slot: ToggleSlot) -> bool:
        """Set toggle slot configuration

        Args:
            slot_num: Slot number (0-99)
            slot: ToggleSlot configuration

        Returns:
            True if successful
        """
        if slot_num < 0 or slot_num >= TOGGLE_NUM_SLOTS:
            return False

        try:
            # Packet: [slot_num] + slot_data (4 bytes)
            data = bytearray([slot_num]) + bytearray(slot.to_bytes())

            packet = self.keyboard._create_hid_packet(HID_CMD_TOGGLE_SET_SLOT, 0, data)
            response = self.keyboard.usb_send(self.keyboard.dev, packet, retries=3)

            success = response and len(response) > 4 and response[4] == 0

            # Update cache
            if success:
                self.slots_cache[slot_num] = slot

            return success

        except Exception as e:
            print(f"Toggle: Error setting slot {slot_num}: {e}")
            return False

    def save_to_eeprom(self) -> bool:
        """Save all toggle configurations to EEPROM

        Returns:
            True if successful
        """
        try:
            packet = self.keyboard._create_hid_packet(HID_CMD_TOGGLE_SAVE_EEPROM, 0, None)
            response = self.keyboard.usb_send(self.keyboard.dev, packet, retries=3)
            return response and len(response) > 4 and response[4] == 0
        except Exception as e:
            print(f"Toggle: Error saving to EEPROM: {e}")
            return False

    def load_from_eeprom(self) -> bool:
        """Load all toggle configurations from EEPROM

        Returns:
            True if successful
        """
        try:
            packet = self.keyboard._create_hid_packet(HID_CMD_TOGGLE_LOAD_EEPROM, 0, None)
            response = self.keyboard.usb_send(self.keyboard.dev, packet, retries=3)

            success = response and len(response) > 4 and response[4] == 0

            if success:
                self.slots_cache.clear()

            return success
        except Exception as e:
            print(f"Toggle: Error loading from EEPROM: {e}")
            return False

    def reset_all_slots(self) -> bool:
        """Reset all toggle slots to defaults

        Returns:
            True if successful
        """
        try:
            packet = self.keyboard._create_hid_packet(HID_CMD_TOGGLE_RESET_ALL, 0, None)
            response = self.keyboard.usb_send(self.keyboard.dev, packet, retries=3)

            success = response and len(response) > 4 and response[4] == 0

            if success:
                self.slots_cache.clear()

            return success
        except Exception as e:
            print(f"Toggle: Error resetting slots: {e}")
            return False

    def clear_cache(self):
        """Clear the slots cache"""
        self.slots_cache.clear()

    def get_all_slots(self) -> List[ToggleSlot]:
        """Load all slots from keyboard

        Returns:
            List of all ToggleSlot objects
        """
        slots = []
        for i in range(TOGGLE_NUM_SLOTS):
            slot = self.get_slot(i)
            if slot:
                slots.append(slot)
            else:
                slots.append(ToggleSlot())  # Default empty slot
        return slots

    def get_configured_slots(self) -> List[tuple]:
        """Get list of configured (non-empty) slots

        Returns:
            List of (slot_num, ToggleSlot) tuples for enabled slots
        """
        configured = []
        for slot_num, slot in self.slots_cache.items():
            if slot.is_enabled():
                configured.append((slot_num, slot))
        return configured
