# Arpeggiator/Sequencer Lazy-Loading Implementation - Summary

## Overview
Successfully implemented a lazy-loading preset system for the arpeggiator and step sequencer, reducing RAM usage from ~25KB to ~2KB (92% reduction).

## Key Changes

### 1. RAM Storage Refactor
**File: orthomidi5x14.h, arpeggiator.c**

**Before:**
```c
extern arp_preset_t arp_presets[64];  // 25KB RAM
```

**After:**
```c
extern arp_preset_t arp_active_preset;                 // 1 slot (~392 bytes)
extern arp_preset_t seq_active_presets[MAX_SEQ_SLOTS]; // 4 slots (~1.5KB)
extern seq_state_t seq_state[MAX_SEQ_SLOTS];
```

### 2. Lazy-Loading Functions
**File: arpeggiator.c**

- `arp_load_preset_into_slot(preset_id)` - Load arp preset on-demand
- `seq_load_preset_into_slot(preset_id, slot)` - Load seq preset into specific slot
- `seq_find_available_slot()` - Find free sequencer slot
- Added `loaded_preset_id` tracking to prevent redundant loads

### 3. Factory Preset System
**File: arp_factory_presets.c (NEW)**

- Created separate file with switch-based factory preset loader
- Presets 0-7: Arpeggiator factory presets
- Presets 32-35: Step sequencer factory presets
- Added to build system in rules.mk

### 4. Updated Core Functions
**File: arpeggiator.c**

- `arp_start()` - Now lazy-loads presets before starting
- `arp_update()` - Uses `&arp_active_preset` instead of array lookup
- `seq_start()` - NEW: Start sequencer with lazy-loading
- `seq_update()` - NEW: Update all 4 sequencer slots
- `seq_stop_all()` - NEW: Stop all sequencers

### 5. Helper Functions Implemented
**File: arpeggiator.c**

- `arp_next_preset()`, `arp_prev_preset()` - Navigate & lazy-load
- `seq_next_preset()`, `seq_prev_preset()` - Navigate & lazy-load
- `arp_set_rate_override()`, `seq_set_rate_override()`
- `arp_reset_overrides()`, `seq_reset_overrides()`
- `seq_toggle_sync_mode()`, `seq_set_master_gate()`

### 6. Keycode Definitions
**File: orthomidi5x14.h**

Added comprehensive keycode ranges:
- **Arpeggiator:** 0xCD00-0xCD7F (128 keycodes)
  - Control: ARP_PLAY, ARP_NEXT_PRESET, ARP_PREV_PRESET, etc.
  - Rate overrides: ARP_RATE_QUARTER, ARP_RATE_EIGHTH, etc.
  - Modes: ARP_MODE_SINGLE, ARP_MODE_CHORD_BASIC, ARP_MODE_CHORD_ADVANCED
  - Direct selection: ARP_PRESET_BASE + 0-63

- **Step Sequencer:** 0xCD80-0xCDFF (128 keycodes)
  - Control: SEQ_PLAY, SEQ_STOP_ALL, SEQ_NEXT_PRESET, etc.
  - Rate overrides: SEQ_RATE_QUARTER, SEQ_RATE_EIGHTH, etc.
  - Direct selection: SEQ_PRESET_BASE + 0-63

### 7. Keycode Handlers
**File: orthomidi5x14.c**

Added comprehensive handlers for all 256 new keycodes in `process_record_user()`, including:
- Transport controls (play/stop)
- Preset navigation (next/prev)
- Rate overrides with switch statements
- Mode selection
- Direct preset selection (0-63)
- Gate and sync controls

### 8. HID Interface Updates
**File: arpeggiator_hid.c**

- Added `hid_edit_preset` - Temporary buffer for HID preset editing
- Updated `ARP_CMD_GET_PRESET` - Lazy-loads preset into edit buffer
- Updated `ARP_CMD_SET_PRESET` - Modifies edit buffer
- Updated `ARP_CMD_SAVE_PRESET` - Saves from edit buffer to EEPROM
- Updated `ARP_CMD_SET_NOTE` - Modifies notes in edit buffer
- Updated `ARP_CMD_SET_NOTES_CHUNK` - Bulk note editing in buffer

### 9. EEPROM Function Updates
**File: arpeggiator.c**

- `arp_save_preset_to_eeprom()` - Changed signature to accept source pointer
- `arp_load_preset_from_eeprom()` - Already used destination pointer
- `arp_clear_preset()` - Uses temporary preset structure
- `arp_copy_preset()` - Lazy-loads source preset before copying
- `arp_load_all_user_presets()` - Marked as obsolete (no longer needed)

### 10. Enum Naming Fix
**File: orthomidi5x14.h, arpeggiator.c, orthomidi5x14.c**

**Problem:** Naming conflict between keycodes and enum values

**Solution:** Renamed enum values to use `ARPMODE_` prefix:
- `ARP_MODE_SINGLE_NOTE` → `ARPMODE_SINGLE_NOTE` (enum value)
- `ARP_MODE_CHORD_BASIC` → `ARPMODE_CHORD_BASIC` (enum value)
- `ARP_MODE_CHORD_ADVANCED` → `ARPMODE_CHORD_ADVANCED` (enum value)

Keycodes retain original names:
- `ARP_MODE_SINGLE` (0xCD20)
- `ARP_MODE_CHORD_BASIC` (0xCD21)
- `ARP_MODE_CHORD_ADVANCED` (0xCD22)

## Build System Changes
**File: rules.mk**

Added:
```makefile
SRC += arp_factory_presets.c
```

## Technical Details

### Preset Loading Flow
1. User presses preset selection key
2. `arp_start(preset_id)` called
3. Check if `loaded_preset_id == preset_id` (skip if already loaded)
4. Call `arp_load_preset_into_slot(preset_id)`
5. Load from EEPROM (user presets 48-63) or factory data (0-47)
6. Update `loaded_preset_id` to track what's in RAM
7. Begin playback using `&arp_active_preset`

### Multi-Slot Sequencer
- Up to 4 simultaneous sequencers supported
- Each slot has independent state: `seq_state[0-3]`
- `seq_find_available_slot()` returns first free slot
- `seq_update()` loops through all active slots

### HID Editing Workflow
1. GUI calls `ARP_CMD_GET_PRESET` - loads preset into `hid_edit_preset`
2. GUI calls `ARP_CMD_SET_PRESET` / `ARP_CMD_SET_NOTE` - modifies buffer
3. GUI calls `ARP_CMD_SAVE_PRESET` - writes buffer to EEPROM

## RAM Savings
- **Before:** 64 presets × 392 bytes = 25,088 bytes (~25KB)
- **After:** 5 presets × 392 bytes = 1,960 bytes (~2KB)
- **Saved:** ~23KB of RAM (92% reduction)

## Files Modified
1. `orthomidi5x14.h` - Keycodes, structures, function declarations, enum fixes
2. `arpeggiator.c` - RAM storage, lazy-loading, core functions, helper functions
3. `arpeggiator_hid.c` - HID edit buffer and handlers
4. `orthomidi5x14.c` - Keycode handlers
5. `rules.mk` - Build system
6. `arp_factory_presets.c` - NEW: Factory preset definitions

## Files Created
- `arp_factory_presets.c` - Factory preset loader
- `IMPLEMENTATION_STATUS.md` - Implementation roadmap (from previous session)
- `LAZY_LOADING_SUMMARY.md` - This file

## Testing Status
- Code structure complete
- All references to old `arp_presets[]` array replaced
- Enum naming conflicts resolved
- Build system updated
- Ready for compilation testing

## Next Steps (for user)
1. Compile firmware: `make orthomidi5x14:vial`
2. Test preset loading and switching
3. Verify multi-slot sequencer behavior
4. Test HID interface with VIAL GUI
5. Verify EEPROM save/load for user presets
