# SPDX-License-Identifier: GPL-2.0-or-later
"""
DKS (Dynamic Keystroke) Protocol Handler

Provides communication between the GUI and firmware for DKS configuration.
DKS allows up to 8 actions per key (4 press + 4 release) with customizable
actuation points and behaviors.
"""

import struct
from typing import Optional, Dict, List, Tuple

# DKS HID Command Codes (0xE5-0xEA)
HID_CMD_DKS_GET_SLOT = 0xE5        # Get DKS slot configuration (32 bytes)
HID_CMD_DKS_SET_ACTION = 0xE6      # Set a single DKS action
HID_CMD_DKS_SAVE_EEPROM = 0xE7     # Save all DKS configs to EEPROM
HID_CMD_DKS_LOAD_EEPROM = 0xE8     # Load all DKS configs from EEPROM
HID_CMD_DKS_RESET_SLOT = 0xE9      # Reset a slot to defaults
HID_CMD_DKS_RESET_ALL = 0xEA       # Reset all slots to defaults

# DKS Constants
DKS_NUM_SLOTS = 50                  # Number of DKS slots (DKS_00 - DKS_49)
DKS_ACTIONS_PER_STAGE = 4           # 4 press + 4 release
DKS_SLOT_SIZE = 32                  # Bytes per slot

# Behavior Types
DKS_BEHAVIOR_TAP = 0                # Press + immediate release
DKS_BEHAVIOR_PRESS = 1              # Press and hold
DKS_BEHAVIOR_RELEASE = 2            # Release only


class DKSAction:
    """Represents a single DKS action (press or release)"""

    def __init__(self, keycode=0, actuation=60, behavior=DKS_BEHAVIOR_TAP):
        self.keycode = keycode          # Keycode to send (0 = disabled)
        self.actuation = actuation      # Actuation point (0-100 = 0-2.5mm)
        self.behavior = behavior        # TAP/PRESS/RELEASE

    def is_enabled(self):
        """Check if this action is enabled (has a valid keycode)"""
        return self.keycode != 0

    def to_dict(self):
        """Convert to dictionary for GUI"""
        return {
            'keycode': self.keycode,
            'actuation': self.actuation,
            'behavior': self.behavior
        }

    @staticmethod
    def from_dict(data):
        """Create from dictionary"""
        return DKSAction(
            keycode=data.get('keycode', 0),
            actuation=data.get('actuation', 60),
            behavior=data.get('behavior', DKS_BEHAVIOR_TAP)
        )


class DKSSlot:
    """Represents a complete DKS slot configuration"""

    def __init__(self):
        self.press_actions = [DKSAction() for _ in range(DKS_ACTIONS_PER_STAGE)]
        self.release_actions = [DKSAction() for _ in range(DKS_ACTIONS_PER_STAGE)]

    def to_bytes(self):
        """Pack slot into 32-byte firmware format"""
        data = bytearray(DKS_SLOT_SIZE)
        offset = 0

        # Press keycodes (8 bytes)
        for action in self.press_actions:
            struct.pack_into('<H', data, offset, action.keycode)
            offset += 2

        # Press actuation points (4 bytes)
        for action in self.press_actions:
            data[offset] = action.actuation
            offset += 1

        # Release keycodes (8 bytes)
        for action in self.release_actions:
            struct.pack_into('<H', data, offset, action.keycode)
            offset += 2

        # Release actuation points (4 bytes)
        for action in self.release_actions:
            data[offset] = action.actuation
            offset += 1

        # Behaviors (2 bytes, bit-packed)
        behaviors = 0
        for i, action in enumerate(self.press_actions):
            behaviors |= (action.behavior & 0x03) << (i * 2)
        for i, action in enumerate(self.release_actions):
            behaviors |= (action.behavior & 0x03) << ((i + 4) * 2)

        struct.pack_into('<H', data, offset, behaviors)

        return bytes(data)

    @staticmethod
    def from_bytes(data):
        """Unpack slot from 32-byte firmware format"""
        if len(data) < DKS_SLOT_SIZE:
            raise ValueError(f"DKS slot data must be {DKS_SLOT_SIZE} bytes, got {len(data)}")

        slot = DKSSlot()
        offset = 0

        # Press keycodes (8 bytes)
        for i in range(DKS_ACTIONS_PER_STAGE):
            slot.press_actions[i].keycode = struct.unpack_from('<H', data, offset)[0]
            offset += 2

        # Press actuation points (4 bytes)
        for i in range(DKS_ACTIONS_PER_STAGE):
            slot.press_actions[i].actuation = data[offset]
            offset += 1

        # Release keycodes (8 bytes)
        for i in range(DKS_ACTIONS_PER_STAGE):
            slot.release_actions[i].keycode = struct.unpack_from('<H', data, offset)[0]
            offset += 2

        # Release actuation points (4 bytes)
        for i in range(DKS_ACTIONS_PER_STAGE):
            slot.release_actions[i].actuation = data[offset]
            offset += 1

        # Behaviors (2 bytes, bit-packed)
        behaviors = struct.unpack_from('<H', data, offset)[0]
        for i in range(DKS_ACTIONS_PER_STAGE):
            slot.press_actions[i].behavior = (behaviors >> (i * 2)) & 0x03
        for i in range(DKS_ACTIONS_PER_STAGE):
            slot.release_actions[i].behavior = (behaviors >> ((i + 4) * 2)) & 0x03

        return slot

    def to_dict(self):
        """Convert to dictionary for GUI"""
        return {
            'press': [action.to_dict() for action in self.press_actions],
            'release': [action.to_dict() for action in self.release_actions]
        }

    @staticmethod
    def from_dict(data):
        """Create from dictionary"""
        slot = DKSSlot()
        if 'press' in data:
            slot.press_actions = [DKSAction.from_dict(a) for a in data['press']]
        if 'release' in data:
            slot.release_actions = [DKSAction.from_dict(a) for a in data['release']]
        return slot


class ProtocolDKS:
    """DKS protocol handler - manages communication with firmware"""

    def __init__(self, keyboard):
        """Initialize DKS protocol

        Args:
            keyboard: Keyboard communication object with usb_send and _create_hid_packet methods
        """
        self.keyboard = keyboard
        self.slots_cache = {}  # Cache of loaded slots

    def get_slot(self, slot_num: int) -> Optional[DKSSlot]:
        """Get DKS slot configuration from keyboard

        Args:
            slot_num: Slot number (0-49)

        Returns:
            DKSSlot object or None on error
        """
        if slot_num < 0 or slot_num >= DKS_NUM_SLOTS:
            return None

        try:
            # Create HID packet with slot number
            packet = self.keyboard._create_hid_packet(HID_CMD_DKS_GET_SLOT, 0, [slot_num])
            response = self.keyboard.usb_send(self.keyboard.dev, packet, retries=20)

            if not response or len(response) < (6 + DKS_SLOT_SIZE):
                return None

            # Check status byte (response[5])
            if response[5] != 0:  # 0 = success
                return None

            # Extract 32-byte slot data (starts at response[6])
            slot_data = response[6:6 + DKS_SLOT_SIZE]
            slot = DKSSlot.from_bytes(slot_data)

            # Cache it
            self.slots_cache[slot_num] = slot

            return slot

        except Exception as e:
            print(f"DKS: Error getting slot {slot_num}: {e}")
            return None

    def set_action(self, slot_num: int, is_press: bool, action_index: int,
                   keycode: int, actuation: int, behavior: int) -> bool:
        """Set a single DKS action

        Args:
            slot_num: Slot number (0-49)
            is_press: True for press action, False for release
            action_index: Action index (0-3)
            keycode: Keycode to send
            actuation: Actuation point (0-100)
            behavior: Behavior type (TAP/PRESS/RELEASE)

        Returns:
            True if successful
        """
        if slot_num < 0 or slot_num >= DKS_NUM_SLOTS:
            return False
        if action_index < 0 or action_index >= DKS_ACTIONS_PER_STAGE:
            return False

        try:
            # Packet format: [slot_num] [is_press] [action_index] [keycode_low] [keycode_high] [actuation] [behavior]
            data = bytearray([
                slot_num,
                1 if is_press else 0,
                action_index,
                keycode & 0xFF,
                (keycode >> 8) & 0xFF,
                actuation,
                behavior
            ])

            packet = self.keyboard._create_hid_packet(HID_CMD_DKS_SET_ACTION, 0, data)
            response = self.keyboard.usb_send(self.keyboard.dev, packet, retries=20)

            success = response and len(response) > 5 and response[5] == 0

            # Update cache if successful
            if success and slot_num in self.slots_cache:
                slot = self.slots_cache[slot_num]
                if is_press:
                    slot.press_actions[action_index].keycode = keycode
                    slot.press_actions[action_index].actuation = actuation
                    slot.press_actions[action_index].behavior = behavior
                else:
                    slot.release_actions[action_index].keycode = keycode
                    slot.release_actions[action_index].actuation = actuation
                    slot.release_actions[action_index].behavior = behavior

            return success

        except Exception as e:
            print(f"DKS: Error setting action: {e}")
            return False

    def save_to_eeprom(self) -> bool:
        """Save all DKS configurations to EEPROM

        Returns:
            True if successful
        """
        try:
            packet = self.keyboard._create_hid_packet(HID_CMD_DKS_SAVE_EEPROM, 0, None)
            response = self.keyboard.usb_send(self.keyboard.dev, packet, retries=20)
            return response and len(response) > 5 and response[5] == 0
        except Exception as e:
            print(f"DKS: Error saving to EEPROM: {e}")
            return False

    def load_from_eeprom(self) -> bool:
        """Load all DKS configurations from EEPROM

        Returns:
            True if successful
        """
        try:
            packet = self.keyboard._create_hid_packet(HID_CMD_DKS_LOAD_EEPROM, 0, None)
            response = self.keyboard.usb_send(self.keyboard.dev, packet, retries=20)

            success = response and len(response) > 5 and response[5] == 0

            # Clear cache on successful load
            if success:
                self.slots_cache.clear()

            return success
        except Exception as e:
            print(f"DKS: Error loading from EEPROM: {e}")
            return False

    def reset_slot(self, slot_num: int) -> bool:
        """Reset a DKS slot to defaults

        Args:
            slot_num: Slot number (0-49)

        Returns:
            True if successful
        """
        if slot_num < 0 or slot_num >= DKS_NUM_SLOTS:
            return False

        try:
            packet = self.keyboard._create_hid_packet(HID_CMD_DKS_RESET_SLOT, 0, [slot_num])
            response = self.keyboard.usb_send(self.keyboard.dev, packet, retries=20)

            success = response and len(response) > 5 and response[5] == 0

            # Clear from cache
            if success and slot_num in self.slots_cache:
                del self.slots_cache[slot_num]

            return success
        except Exception as e:
            print(f"DKS: Error resetting slot: {e}")
            return False

    def reset_all_slots(self) -> bool:
        """Reset all DKS slots to defaults

        Returns:
            True if successful
        """
        try:
            packet = self.keyboard._create_hid_packet(HID_CMD_DKS_RESET_ALL, 0, None)
            response = self.keyboard.usb_send(self.keyboard.dev, packet, retries=20)

            success = response and len(response) > 5 and response[5] == 0

            # Clear cache
            if success:
                self.slots_cache.clear()

            return success
        except Exception as e:
            print(f"DKS: Error resetting all slots: {e}")
            return False

    def clear_cache(self):
        """Clear the slots cache"""
        self.slots_cache.clear()
