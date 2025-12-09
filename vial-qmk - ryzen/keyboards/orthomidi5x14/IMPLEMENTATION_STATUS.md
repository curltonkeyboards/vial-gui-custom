# Arpeggiator/Sequencer Lazy-Loading Implementation Status

## Completed ✅

### 1. Keycode Definitions (orthomidi5x14.h)
- Added all arpeggiator keycodes (0xCD00-0xCD7F)
- Added all step sequencer keycodes (0xCD80-0xCDFF)
- Includes control, transport, rate overrides, modes, and preset selection

### 2. RAM Storage Refactor (arpeggiator.c + orthomidi5x14.h)
- Replaced `arp_preset_t arp_presets[64]` (25KB) with:
  - `arp_preset_t arp_active_preset` (1 slot, ~392 bytes)
  - `arp_preset_t seq_active_presets[4]` (4 slots, ~1.5KB)
- Updated `arp_state_t` to include `loaded_preset_id` tracking
- Created `seq_state_t` structure for 4 sequencer slots

### 3. Lazy-Loading Functions (arpeggiator.c)
- `arp_load_preset_into_slot()` - Load arp preset on-demand
- `seq_load_preset_into_slot()` - Load seq preset into specific slot
- `seq_find_available_slot()` - Find free sequencer slot
- `arp_load_factory_preset()` - Stub in arpeggiator.c

### 4. Factory Preset Loader (arp_factory_presets.c)
- Created separate file with all factory presets (0-7, 32-35)
- Switch-based loading for efficient on-demand initialization
- **NOTE:** Needs to be added to build system (rules.mk or SRC)

### 5. EEPROM Functions Updated
- `arp_load_preset_from_eeprom(preset_id, dest)` - Now uses destination pointer
- Removed dependency on global preset array

## Still TODO ⚠️

### 1. Update Core Functions (arpeggiator.c)
**Critical - These reference old `arp_presets[preset_id]` array:**

- `arp_start(preset_id)` - Must call `arp_load_preset_into_slot()` before starting
- `arp_update()` - Must use `&arp_active_preset` instead of `&arp_presets[id]`
- Add new `seq_start(preset_id)`, `seq_stop()`, `seq_update()` functions

###  2. Implement Helper Functions
- `arp_next_preset()`, `arp_prev_preset()` - Navigate & lazy-load
- `seq_next_preset()`, `seq_prev_preset()` - Navigate & lazy-load
- `arp_set_rate_override()`, `seq_set_rate_override()`
- `arp_reset_overrides()`, `seq_reset_overrides()`
- `seq_toggle_sync_mode()`, `seq_set_master_gate()`

### 3. Keycode Handlers (orthomidi5x14.c - process_record_user)
Add handling for ALL new keycodes:
- ARP_PLAY, ARP_NEXT_PRESET, ARP_PREV_PRESET, etc.
- ARP_RATE_* keycodes (pattern rate overrides)
- ARP_MODE_* keycodes
- ARP_PRESET_BASE + 0-63 (direct preset selection)
- SEQ_* equivalents for all above

### 4. Build System
- Add `arp_factory_presets.c` to `SRC` in rules.mk or keyboard-level build files

### 5. Remove Obsolete Functions
- Delete `arp_load_all_user_presets()` (no longer load all at init)
- Update `arp_copy_preset()` to work with lazy-loading
- Update `arp_save_preset_to_eeprom()` if it references old array

## Critical Next Steps

1. **Update arp_start():**
   ```c
   void arp_start(uint8_t preset_id) {
       // Lazy-load preset into active slot
       if (!arp_load_preset_into_slot(preset_id)) {
           return;  // Load failed
       }

       arp_state.current_preset_id = preset_id;
       arp_state.active = true;
       // ... rest of logic using &arp_active_preset
   }
   ```

2. **Update arp_update():**
   ```c
   void arp_update(void) {
       if (!arp_state.active) return;

       // Use active preset instead of array
       arp_preset_t *preset = &arp_active_preset;

       // ... rest of logic
   }
   ```

3. **Add keycode handling in process_record_user()**

4. **Test compilation and fix linker errors**

## Files Modified
- `orthomidi5x14.h` - Keycodes, structures, function declarations
- `arpeggiator.c` - RAM storage, lazy-loading functions, init
- `arp_factory_presets.c` - NEW FILE with factory presets

## RAM Savings
- **Before:** 64 presets × 392 bytes = 25,088 bytes (~25KB)
- **After:** 5 presets × 392 bytes = 1,960 bytes (~2KB)
- **Saved:** ~23KB of RAM ✅
