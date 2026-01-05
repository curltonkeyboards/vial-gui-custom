# Deadzone Configuration for Normal and MIDI Keys - Implementation Plan

## Executive Summary

Currently, deadzone configuration (deadzone_top and deadzone_bottom) is only available when per-key actuation mode is enabled. This plan outlines the changes needed to enable deadzone configuration for normal and MIDI keys even when per-key actuation is disabled, using the layer-wide actuation system.

---

## Current Architecture

### Firmware (vial-qmk-ryzen)

**Per-Key Actuation Structure** (`per_key_actuation_t` - 8 bytes):
```c
typedef struct {
    uint8_t actuation;              // 0-100 (0-2.5mm)
    uint8_t deadzone_top;           // 0-100 (0-2.5mm) ✓ HAS DEADZONES
    uint8_t deadzone_bottom;        // 0-100 (0-2.5mm) ✓ HAS DEADZONES
    uint8_t velocity_curve;
    uint8_t flags;
    uint8_t rapidfire_press_sens;
    uint8_t rapidfire_release_sens;
    int8_t rapidfire_velocity_mod;
} per_key_actuation_t;
```

**Layer Actuation Structure** (`layer_actuation_t` - 5 bytes):
```c
typedef struct {
    uint8_t normal_actuation;       // 0-100 (0-2.5mm)
    uint8_t midi_actuation;         // 0-100 (0-2.5mm)
    uint8_t velocity_mode;
    uint8_t velocity_speed_scale;
    uint8_t flags;
    // ✗ NO DEADZONES - This is what we need to add!
} layer_actuation_t;
```

**Storage**:
- Per-Key Data: EEPROM address 67000, size 6,720 bytes (12 layers × 70 keys × 8 bytes)
- Layer Actuation: EEPROM address 74000, size 60 bytes (12 layers × 5 bytes)

**Deadzone Application**:
- Currently only applied when per-key mode is enabled
- Uses `is_in_deadzone()` function in `matrix.c:431-444`
- Applied during rapid trigger logic and key press processing

### GUI (vial-gui-custom)

**Protocol Commands**:
- `HID_CMD_SET_LAYER_ACTUATION = 0xCA` - Set layer settings (5 bytes)
- `HID_CMD_GET_LAYER_ACTUATION = 0xCB` - Get layer settings (5 bytes)
- No deadzone fields in current packet format

**UI Components**:
- Layer-wide actuation settings only show: normal_actuation, midi_actuation, velocity settings
- No deadzone sliders for layer-wide mode
- Deadzone UI only visible/functional in per-key mode

---

## Proposed Changes

### Phase 1: Firmware Data Structure Changes

#### 1.1 Update `layer_actuation_t` Structure

**File**: `vial-qmk-ryzen/quantum/process_keycode/process_midi.h`

**Current** (5 bytes):
```c
typedef struct {
    uint8_t normal_actuation;
    uint8_t midi_actuation;
    uint8_t velocity_mode;
    uint8_t velocity_speed_scale;
    uint8_t flags;
} layer_actuation_t;
```

**Proposed** (9 bytes):
```c
typedef struct {
    uint8_t normal_actuation;       // 0-100 (0-2.5mm)
    uint8_t midi_actuation;         // 0-100 (0-2.5mm)
    uint8_t velocity_mode;          // 0=Fixed, 1=Peak, 2=Speed, 3=Speed+Peak
    uint8_t velocity_speed_scale;   // 1-20
    uint8_t flags;                  // Bit 2: use_fixed_velocity
    uint8_t normal_deadzone_top;    // 0-100 (0-2.5mm) ← NEW
    uint8_t normal_deadzone_bottom; // 0-100 (0-2.5mm) ← NEW
    uint8_t midi_deadzone_top;      // 0-100 (0-2.5mm) ← NEW
    uint8_t midi_deadzone_bottom;   // 0-100 (0-2.5mm) ← NEW
} layer_actuation_t;
```

**Impact**: Structure grows from 5 → 9 bytes per layer

#### 1.2 Update EEPROM Storage

**File**: `vial-qmk-ryzen/quantum/process_keycode/process_dynamic_macro.h`

**Current**:
```c
#define LAYER_ACTUATION_EEPROM_ADDR 74000
#define LAYER_ACTUATION_SIZE (12 * 5)  // 60 bytes
```

**Proposed**:
```c
#define LAYER_ACTUATION_EEPROM_ADDR 74000
#define LAYER_ACTUATION_SIZE (12 * 9)  // 108 bytes (was 60)
```

**Impact**: EEPROM usage increases by 48 bytes (60 → 108)

#### 1.3 Update Default Values

**File**: `vial-qmk-ryzen/quantum/process_keycode/process_midi.h`

Add new defaults:
```c
#define DEFAULT_NORMAL_DEADZONE_TOP 4      // 0.1mm
#define DEFAULT_NORMAL_DEADZONE_BOTTOM 4   // 0.1mm
#define DEFAULT_MIDI_DEADZONE_TOP 4        // 0.1mm
#define DEFAULT_MIDI_DEADZONE_BOTTOM 4     // 0.1mm
```

#### 1.4 Update Initialization Functions

**File**: `vial-qmk-ryzen/keyboards/orthomidi5x14/orthomidi5x14.c`

**Function**: `reset_layer_actuations()` (around line 3100)

Add initialization for new fields:
```c
void reset_layer_actuations(void) {
    for (int i = 0; i < 12; i++) {
        layer_actuations[i].normal_actuation = DEFAULT_ACTUATION_VALUE;
        layer_actuations[i].midi_actuation = DEFAULT_ACTUATION_VALUE;
        layer_actuations[i].velocity_mode = 0;
        layer_actuations[i].velocity_speed_scale = 4;
        layer_actuations[i].flags = 0;
        // NEW FIELDS ↓
        layer_actuations[i].normal_deadzone_top = DEFAULT_NORMAL_DEADZONE_TOP;
        layer_actuations[i].normal_deadzone_bottom = DEFAULT_NORMAL_DEADZONE_BOTTOM;
        layer_actuations[i].midi_deadzone_top = DEFAULT_MIDI_DEADZONE_TOP;
        layer_actuations[i].midi_deadzone_bottom = DEFAULT_MIDI_DEADZONE_BOTTOM;
    }
    save_layer_actuations();
}
```

### Phase 2: Firmware Protocol Updates

#### 2.1 Update Protocol Packet Size

**File**: `vial-qmk-ryzen/quantum/vial.c`

**Current Packet** (SET_LAYER_ACTUATION - 0xCA):
```
[layer, normal_act, midi_act, vel_mode, vel_scale, flags]  // 6 bytes
```

**Proposed Packet**:
```
[layer, normal_act, midi_act, vel_mode, vel_scale, flags,
 normal_dz_top, normal_dz_bottom, midi_dz_top, midi_dz_bottom]  // 10 bytes
```

#### 2.2 Update HID Command Handlers

**File**: `vial-qmk-ryzen/keyboards/orthomidi5x14/orthomidi5x14.c`

**Function**: `handler_set_layer_actuation()` (around line 3250)

**Current**:
```c
static void handler_set_layer_actuation(uint8_t *data, uint8_t length) {
    if (length < 6) return;

    uint8_t layer = data[0];
    if (layer >= 12) return;

    layer_actuations[layer].normal_actuation = data[1];
    layer_actuations[layer].midi_actuation = data[2];
    layer_actuations[layer].velocity_mode = data[3];
    layer_actuations[layer].velocity_speed_scale = data[4];
    layer_actuations[layer].flags = data[5];

    save_layer_actuations();
}
```

**Proposed**:
```c
static void handler_set_layer_actuation(uint8_t *data, uint8_t length) {
    if (length < 10) return;  // Was 6, now 10

    uint8_t layer = data[0];
    if (layer >= 12) return;

    layer_actuations[layer].normal_actuation = data[1];
    layer_actuations[layer].midi_actuation = data[2];
    layer_actuations[layer].velocity_mode = data[3];
    layer_actuations[layer].velocity_speed_scale = data[4];
    layer_actuations[layer].flags = data[5];
    // NEW FIELDS ↓
    layer_actuations[layer].normal_deadzone_top = data[6];
    layer_actuations[layer].normal_deadzone_bottom = data[7];
    layer_actuations[layer].midi_deadzone_top = data[8];
    layer_actuations[layer].midi_deadzone_bottom = data[9];

    save_layer_actuations();
}
```

**Function**: `handler_get_layer_actuation()` (around line 3260)

**Current**:
```c
static void handler_get_layer_actuation(uint8_t *data, uint8_t length) {
    if (length < 1) return;

    uint8_t layer = data[0];
    if (layer >= 12) return;

    uint8_t response[6];
    response[0] = layer;
    response[1] = layer_actuations[layer].normal_actuation;
    response[2] = layer_actuations[layer].midi_actuation;
    response[3] = layer_actuations[layer].velocity_mode;
    response[4] = layer_actuations[layer].velocity_speed_scale;
    response[5] = layer_actuations[layer].flags;

    raw_hid_send(response, 6);
}
```

**Proposed**:
```c
static void handler_get_layer_actuation(uint8_t *data, uint8_t length) {
    if (length < 1) return;

    uint8_t layer = data[0];
    if (layer >= 12) return;

    uint8_t response[10];  // Was 6, now 10
    response[0] = layer;
    response[1] = layer_actuations[layer].normal_actuation;
    response[2] = layer_actuations[layer].midi_actuation;
    response[3] = layer_actuations[layer].velocity_mode;
    response[4] = layer_actuations[layer].velocity_speed_scale;
    response[5] = layer_actuations[layer].flags;
    // NEW FIELDS ↓
    response[6] = layer_actuations[layer].normal_deadzone_top;
    response[7] = layer_actuations[layer].normal_deadzone_bottom;
    response[8] = layer_actuations[layer].midi_deadzone_top;
    response[9] = layer_actuations[layer].midi_deadzone_bottom;

    raw_hid_send(response, 10);
}
```

**Function**: `handler_get_all_layer_actuations()` (around line 3275)

Update to return 9 bytes per layer instead of 5:
```c
static void handler_get_all_layer_actuations(void) {
    uint8_t response[108];  // Was 60, now 108 (12 layers × 9 bytes)

    for (int i = 0; i < 12; i++) {
        int offset = i * 9;  // Was i * 5
        response[offset + 0] = layer_actuations[i].normal_actuation;
        response[offset + 1] = layer_actuations[i].midi_actuation;
        response[offset + 2] = layer_actuations[i].velocity_mode;
        response[offset + 3] = layer_actuations[i].velocity_speed_scale;
        response[offset + 4] = layer_actuations[i].flags;
        // NEW FIELDS ↓
        response[offset + 5] = layer_actuations[i].normal_deadzone_top;
        response[offset + 6] = layer_actuations[i].normal_deadzone_bottom;
        response[offset + 7] = layer_actuations[i].midi_deadzone_top;
        response[offset + 8] = layer_actuations[i].midi_deadzone_bottom;
    }

    raw_hid_send(response, 108);
}
```

### Phase 3: Firmware Deadzone Application Logic

#### 3.1 Apply Deadzones to Layer-Wide Keys

**File**: `vial-qmk-ryzen/quantum/matrix.c`

**Current**: Deadzones only applied when per-key mode enabled

**Function**: Key press processing (around line 481-561)

**Proposed Change**: Add deadzone check for layer-wide mode

```c
// Around line 500-510 in process_analog_key()
bool in_deadzone = false;
uint8_t deadzone_top = 0;
uint8_t deadzone_bottom = 0;

if (per_key_mode_enabled && settings != NULL) {
    // Per-key deadzones (existing code)
    deadzone_top = settings->deadzone_top;
    deadzone_bottom = settings->deadzone_bottom;
    in_deadzone = is_in_deadzone(travel, deadzone_top, deadzone_bottom);
} else {
    // Layer-wide deadzones (NEW CODE)
    uint8_t current_layer = get_highest_layer(layer_state);
    if (current_layer >= 12) current_layer = 0;

    // Determine if this is a MIDI key or normal key
    bool is_midi_key = (keycode >= MI_C && keycode <= MI_B_5);

    if (is_midi_key) {
        deadzone_top = layer_actuations[current_layer].midi_deadzone_top;
        deadzone_bottom = layer_actuations[current_layer].midi_deadzone_bottom;
    } else {
        deadzone_top = layer_actuations[current_layer].normal_deadzone_top;
        deadzone_bottom = layer_actuations[current_layer].normal_deadzone_bottom;
    }

    in_deadzone = is_in_deadzone(travel, deadzone_top, deadzone_bottom);
}

// Rest of rapid trigger logic uses `in_deadzone` variable
```

**Key Detection Logic**: Need to determine if key is MIDI or normal
- Check keycode range for MIDI keys: `MI_C` (0x6000) to `MI_B_5` (0x607B)
- Alternative: Add flag to key structure or use keymap lookup

### Phase 4: GUI Protocol Layer Updates

#### 4.1 Update Protocol Communication

**File**: `vial-gui-custom/src/main/python/protocol/keyboard_comm.py`

**Function**: `set_layer_actuation()` (around line 1209)

**Current**:
```python
def set_layer_actuation(self, layer, normal_act, midi_act, vel_mode, vel_scale, flags):
    data = bytearray([
        layer,
        normal_act,
        midi_act,
        vel_mode,
        vel_scale,
        flags
    ])
    packet = self._create_hid_packet(HID_CMD_SET_LAYER_ACTUATION, 0, data)
    response = self.usb_send(self.dev, packet, retries=20)
    return response and len(response) > 5 and response[5] == 0x01
```

**Proposed**:
```python
def set_layer_actuation(self, layer, normal_act, midi_act, vel_mode, vel_scale, flags,
                        normal_dz_top=4, normal_dz_bottom=4,
                        midi_dz_top=4, midi_dz_bottom=4):
    data = bytearray([
        layer,
        normal_act,
        midi_act,
        vel_mode,
        vel_scale,
        flags,
        normal_dz_top,      # NEW
        normal_dz_bottom,   # NEW
        midi_dz_top,        # NEW
        midi_dz_bottom      # NEW
    ])
    packet = self._create_hid_packet(HID_CMD_SET_LAYER_ACTUATION, 0, data)
    response = self.usb_send(self.dev, packet, retries=20)
    return response and len(response) > 5 and response[5] == 0x01
```

**Function**: `get_layer_actuation()` (around line 1224)

**Current**:
```python
def get_layer_actuation(self, layer):
    data = bytearray([layer])
    packet = self._create_hid_packet(HID_CMD_GET_LAYER_ACTUATION, 0, data)
    response = self.usb_send(self.dev, packet, retries=20)

    if response and len(response) >= 11:  # Was 11, check actual response
        return {
            'normal_actuation': response[6],
            'midi_actuation': response[7],
            'velocity_mode': response[8],
            'velocity_speed_scale': response[9],
            'flags': response[10]
        }
    return None
```

**Proposed**:
```python
def get_layer_actuation(self, layer):
    data = bytearray([layer])
    packet = self._create_hid_packet(HID_CMD_GET_LAYER_ACTUATION, 0, data)
    response = self.usb_send(self.dev, packet, retries=20)

    if response and len(response) >= 15:  # Was 11, now 15 (header + 10 bytes)
        return {
            'normal_actuation': response[6],
            'midi_actuation': response[7],
            'velocity_mode': response[8],
            'velocity_speed_scale': response[9],
            'flags': response[10],
            'normal_deadzone_top': response[11],      # NEW
            'normal_deadzone_bottom': response[12],   # NEW
            'midi_deadzone_top': response[13],        # NEW
            'midi_deadzone_bottom': response[14]      # NEW
        }
    return None
```

**Function**: `get_all_layer_actuations()` (around line 1239)

Update to parse 9 bytes per layer instead of 5:
```python
def get_all_layer_actuations(self):
    packet = self._create_hid_packet(HID_CMD_GET_ALL_LAYER_ACTUATIONS, 0, bytearray())
    response = self.usb_send(self.dev, packet, retries=20)

    if response and len(response) >= 114:  # Was 66, now 114 (header 6 + data 108)
        layers = []
        for i in range(12):
            offset = 6 + (i * 9)  # Was i * 5, now i * 9
            layers.append({
                'normal_actuation': response[offset + 0],
                'midi_actuation': response[offset + 1],
                'velocity_mode': response[offset + 2],
                'velocity_speed_scale': response[offset + 3],
                'flags': response[offset + 4],
                'normal_deadzone_top': response[offset + 5],      # NEW
                'normal_deadzone_bottom': response[offset + 6],   # NEW
                'midi_deadzone_top': response[offset + 7],        # NEW
                'midi_deadzone_bottom': response[offset + 8]      # NEW
            })
        return layers
    return None
```

### Phase 5: GUI UI Updates

#### 5.1 Add Layer-Wide Deadzone UI Controls

**File**: `vial-gui-custom/src/main/python/editor/trigger_settings.py`

**Location**: Layer-wide settings section (around line 200-300)

**Current UI**: Only shows actuation sliders for normal and MIDI

**Proposed Addition**:

1. **Add Normal Key Deadzone Sliders**:
   - Label: "Normal Key Deadzones"
   - TriggerSlider widget (same as per-key mode)
   - Handlers: `on_normal_deadzone_top_changed()`, `on_normal_deadzone_bottom_changed()`

2. **Add MIDI Key Deadzone Sliders**:
   - Label: "MIDI Key Deadzones"
   - TriggerSlider widget (same as per-key mode)
   - Handlers: `on_midi_deadzone_top_changed()`, `on_midi_deadzone_bottom_changed()`

**Example Code**:
```python
# Around line 250-350 in create_layer_wide_settings()

# Normal Key Deadzones (NEW)
normal_dz_label = QLabel("Normal Key Deadzones")
self.normal_dz_slider = TriggerSlider()
self.normal_dz_slider.set_deadzone_top(4)
self.normal_dz_slider.set_deadzone_bottom(4)
self.normal_dz_slider.deadzoneTopChanged.connect(self.on_normal_deadzone_top_changed)
self.normal_dz_slider.deadzoneBottomChanged.connect(self.on_normal_deadzone_bottom_changed)

# MIDI Key Deadzones (NEW)
midi_dz_label = QLabel("MIDI Key Deadzones")
self.midi_dz_slider = TriggerSlider()
self.midi_dz_slider.set_deadzone_top(4)
self.midi_dz_slider.set_deadzone_bottom(4)
self.midi_dz_slider.deadzoneTopChanged.connect(self.on_midi_deadzone_top_changed)
self.midi_dz_slider.deadzoneBottomChanged.connect(self.on_midi_deadzone_bottom_changed)
```

#### 5.2 Add Handler Functions

**File**: `vial-gui-custom/src/main/python/editor/trigger_settings.py`

**New Functions** (around line 1100-1200):

```python
def on_normal_deadzone_top_changed(self, value):
    """Handle normal key deadzone top slider change"""
    if self.rebuilding:
        return

    current_layer = self.current_layer
    settings = self.layer_wide_settings[current_layer]
    settings['normal_deadzone_top'] = value

    # Send to device
    self.send_layer_actuation_to_device(current_layer)

    # Update visualization
    self.update_layer_visualizer()

def on_normal_deadzone_bottom_changed(self, value):
    """Handle normal key deadzone bottom slider change"""
    if self.rebuilding:
        return

    current_layer = self.current_layer
    settings = self.layer_wide_settings[current_layer]
    settings['normal_deadzone_bottom'] = value

    # Send to device
    self.send_layer_actuation_to_device(current_layer)

    # Update visualization
    self.update_layer_visualizer()

def on_midi_deadzone_top_changed(self, value):
    """Handle MIDI key deadzone top slider change"""
    if self.rebuilding:
        return

    current_layer = self.current_layer
    settings = self.layer_wide_settings[current_layer]
    settings['midi_deadzone_top'] = value

    # Send to device
    self.send_layer_actuation_to_device(current_layer)

    # Update visualization
    self.update_layer_visualizer()

def on_midi_deadzone_bottom_changed(self, value):
    """Handle MIDI key deadzone bottom slider change"""
    if self.rebuilding:
        return

    current_layer = self.current_layer
    settings = self.layer_wide_settings[current_layer]
    settings['midi_deadzone_bottom'] = value

    # Send to device
    self.send_layer_actuation_to_device(current_layer)

    # Update visualization
    self.update_layer_visualizer()

def send_layer_actuation_to_device(self, layer):
    """Send complete layer actuation settings including deadzones"""
    settings = self.layer_wide_settings[layer]

    self.device.keyboard.set_layer_actuation(
        layer=layer,
        normal_act=settings['normal_actuation'],
        midi_act=settings['midi_actuation'],
        vel_mode=settings['velocity_mode'],
        vel_scale=settings['velocity_speed_scale'],
        flags=settings['flags'],
        normal_dz_top=settings['normal_deadzone_top'],
        normal_dz_bottom=settings['normal_deadzone_bottom'],
        midi_dz_top=settings['midi_deadzone_top'],
        midi_dz_bottom=settings['midi_deadzone_bottom']
    )
```

#### 5.3 Update Layer-Wide Settings Cache

**File**: `vial-gui-custom/src/main/python/editor/trigger_settings.py`

**Location**: Initialization and loading functions (around line 47-100)

**Current Cache Structure**:
```python
self.layer_wide_settings[layer] = {
    'normal_actuation': 60,
    'midi_actuation': 60,
    'velocity_mode': 0,
    'velocity_speed_scale': 4,
    'flags': 0
}
```

**Proposed Cache Structure**:
```python
self.layer_wide_settings[layer] = {
    'normal_actuation': 60,
    'midi_actuation': 60,
    'velocity_mode': 0,
    'velocity_speed_scale': 4,
    'flags': 0,
    'normal_deadzone_top': 4,      # NEW - default 0.1mm
    'normal_deadzone_bottom': 4,   # NEW - default 0.1mm
    'midi_deadzone_top': 4,        # NEW - default 0.1mm
    'midi_deadzone_bottom': 4      # NEW - default 0.1mm
}
```

#### 5.4 Update Visualization

**File**: `vial-gui-custom/src/main/python/editor/trigger_settings.py`

**Function**: `update_layer_visualizer()` (new function)

Add visualization update for layer-wide deadzones:
```python
def update_layer_visualizer(self):
    """Update the vertical travel bar for layer-wide settings"""
    if not hasattr(self, 'layer_visualizer'):
        return

    current_layer = self.current_layer
    settings = self.layer_wide_settings[current_layer]

    # Update for normal keys (can show both normal and MIDI side-by-side)
    self.layer_visualizer.update_deadzones(
        deadzone_top=settings['normal_deadzone_top'],
        deadzone_bottom=settings['normal_deadzone_bottom'],
        actuation=settings['normal_actuation']
    )
```

---

## Implementation Checklist

### Firmware Changes (vial-qmk-ryzen)

- [ ] **Data Structures**
  - [ ] Expand `layer_actuation_t` from 5 to 9 bytes
  - [ ] Add 4 new deadzone fields (normal_dz_top/bottom, midi_dz_top/bottom)
  - [ ] Add default value constants

- [ ] **EEPROM**
  - [ ] Update `LAYER_ACTUATION_SIZE` from 60 to 108 bytes
  - [ ] Update save/load functions for expanded structure
  - [ ] Update reset function to initialize new fields

- [ ] **Protocol Handlers**
  - [ ] Update `handler_set_layer_actuation()` to read 10 bytes (was 6)
  - [ ] Update `handler_get_layer_actuation()` to send 10 bytes (was 6)
  - [ ] Update `handler_get_all_layer_actuations()` to send 108 bytes (was 60)

- [ ] **Matrix Scanning**
  - [ ] Add layer-wide deadzone application logic
  - [ ] Determine MIDI vs normal key type
  - [ ] Apply appropriate deadzones based on key type
  - [ ] Integrate with existing `is_in_deadzone()` function

- [ ] **Testing**
  - [ ] Verify EEPROM persistence
  - [ ] Test normal key deadzones
  - [ ] Test MIDI key deadzones
  - [ ] Test per-layer vs global layer settings
  - [ ] Verify backward compatibility (old EEPROM data)

### GUI Changes (vial-gui-custom)

- [ ] **Protocol Layer**
  - [ ] Update `set_layer_actuation()` signature (add 4 deadzone params)
  - [ ] Update `get_layer_actuation()` response parsing (10 bytes)
  - [ ] Update `get_all_layer_actuations()` response parsing (108 bytes)

- [ ] **UI Components**
  - [ ] Add normal key deadzone sliders to layer-wide settings
  - [ ] Add MIDI key deadzone sliders to layer-wide settings
  - [ ] Add labels and layout for new controls
  - [ ] Add visual separation between normal and MIDI settings

- [ ] **Event Handlers**
  - [ ] Implement `on_normal_deadzone_top_changed()`
  - [ ] Implement `on_normal_deadzone_bottom_changed()`
  - [ ] Implement `on_midi_deadzone_top_changed()`
  - [ ] Implement `on_midi_deadzone_bottom_changed()`
  - [ ] Implement `send_layer_actuation_to_device()`

- [ ] **Data Management**
  - [ ] Update `layer_wide_settings` cache structure (add 4 fields)
  - [ ] Update loading functions to read new fields
  - [ ] Update reset functions to initialize new fields
  - [ ] Handle backward compatibility (devices without new fields)

- [ ] **Visualization**
  - [ ] Create `update_layer_visualizer()` function
  - [ ] Update vertical travel bar for layer-wide deadzones
  - [ ] Show separate visualizations for normal vs MIDI (optional)

- [ ] **Testing**
  - [ ] Test UI layout and responsiveness
  - [ ] Test value changes propagate to device
  - [ ] Test loading values from device
  - [ ] Test layer switching updates UI correctly
  - [ ] Test reset to defaults

---

## Key Design Decisions & Questions

### 1. Separate Deadzones for Normal vs MIDI Keys

**Decision**: Add 4 separate deadzone fields:
- `normal_deadzone_top` / `normal_deadzone_bottom`
- `midi_deadzone_top` / `midi_deadzone_bottom`

**Rationale**:
- MIDI keys may need different deadzone tuning than normal keys
- MIDI velocity is more sensitive to travel distance
- Follows existing pattern of separate `normal_actuation` and `midi_actuation`

**Alternative**: Single shared deadzone for both key types
- **Pros**: Simpler structure (7 bytes instead of 9)
- **Cons**: Less flexibility, harder to tune for different key types

**Question for User**: Do you prefer separate deadzones for normal vs MIDI, or a single shared deadzone?

### 2. MIDI Key Detection Method

**Options**:

**A. Keycode Range Check** (Recommended)
```c
bool is_midi_key = (keycode >= MI_C && keycode <= MI_B_5);
```
- **Pros**: Simple, fast, no extra storage
- **Cons**: Assumes contiguous keycode range

**B. Keymap Lookup**
```c
uint16_t keycode = keymap_key_to_keycode(layer, (keypos_t){.row=row, .col=col});
bool is_midi_key = (keycode >= MI_C && keycode <= MI_B_5);
```
- **Pros**: Accurate, respects layer configuration
- **Cons**: Requires layer parameter, slightly slower

**C. Flag in Key Structure**
- **Pros**: Very fast lookup
- **Cons**: Requires additional storage, complexity

**Question for User**: How should we determine if a key is MIDI vs normal? Keycode range check should work fine.

### 3. UI Layout

**Option A: Vertical Stack** (Recommended)
```
┌─────────────────────────────┐
│ Normal Key Settings         │
│  ├─ Actuation Slider        │
│  └─ Deadzone Slider         │
│                             │
│ MIDI Key Settings           │
│  ├─ Actuation Slider        │
│  └─ Deadzone Slider         │
└─────────────────────────────┘
```

**Option B: Side-by-Side**
```
┌────────────────┬────────────────┐
│ Normal Keys    │ MIDI Keys      │
│  ├─ Actuation  │  ├─ Actuation  │
│  └─ Deadzones  │  └─ Deadzones  │
└────────────────┴────────────────┘
```

**Question for User**: Which layout do you prefer for the layer-wide settings UI?

### 4. Backward Compatibility

**Challenge**: Old firmware won't send new deadzone fields

**Solution**: GUI should:
1. Try to read 10-byte response
2. If response is 6 bytes (old format), default deadzones to 4
3. Only send 10-byte SET commands if device supports it (version check)

**Question for User**: Do we need to support old firmware, or can we require firmware update?

### 5. Value Range

**Current**: Per-key deadzones use 0-100 range (0-2.5mm)

**Proposed**: Layer-wide deadzones use same 0-100 range for consistency

**Alternative**: Limit to 0-20 (0-0.5mm) like the UI slider
- **Pros**: Prevents extreme values, matches slider range
- **Cons**: Inconsistent with per-key storage format

**Question for User**: Should layer-wide deadzones use full 0-100 range or restricted 0-20 range?

---

## Migration Path

### For Existing Users

1. **Firmware Flash**: Users must flash updated firmware
2. **EEPROM Reset**: Recommended to run `RESET_LAYER_ACTUATIONS` command
   - This ensures new deadzone fields are initialized
   - Alternative: Firmware auto-detects old format and migrates on boot
3. **GUI Update**: Update GUI to version with deadzone support
4. **Configuration**: Set layer-wide deadzones as desired

### EEPROM Migration Strategy (Optional)

**Auto-Migration on Boot**:
```c
void check_and_migrate_layer_actuations(void) {
    // Check if EEPROM has old 5-byte format
    // Read magic byte or version number
    // If old format:
    //   - Load 5 bytes per layer
    //   - Add default deadzone values (4, 4, 4, 4)
    //   - Save 9 bytes per layer
    //   - Update version marker
}
```

**Question for User**: Do you want auto-migration, or is it acceptable to require manual reset?

---

## Testing Strategy

### Firmware Tests

1. **EEPROM Persistence**
   - Set deadzones via HID
   - Power cycle keyboard
   - Verify values persist

2. **Deadzone Application**
   - Set deadzone_top to 20 (0.5mm)
   - Verify keys don't trigger in top deadzone region
   - Set deadzone_bottom to 20 (0.5mm)
   - Verify keys don't trigger in bottom deadzone region

3. **Normal vs MIDI**
   - Set different deadzones for normal vs MIDI
   - Press normal key → verify normal deadzones apply
   - Press MIDI key → verify MIDI deadzones apply

4. **Layer Switching**
   - Configure different deadzones per layer
   - Switch layers
   - Verify correct deadzones apply per layer

### GUI Tests

1. **UI Rendering**
   - Open trigger settings
   - Verify 4 deadzone sliders appear
   - Verify labels are correct

2. **Value Propagation**
   - Adjust slider
   - Verify value sent to device
   - Read back from device
   - Verify slider shows correct value

3. **Layer Switching**
   - Set different values on layer 0 and layer 1
   - Switch layers in GUI
   - Verify UI updates to show correct values

4. **Visualization**
   - Set deadzone values
   - Verify visual travel bar shows correct deadzone regions

---

## Estimated Impact

### Memory Impact (Firmware)
- **EEPROM**: +48 bytes (60 → 108)
- **RAM**: +48 bytes (global `layer_actuations` array)
- **Flash**: ~200-300 bytes (new logic + handlers)

**Total**: Minimal impact, well within available space

### Performance Impact
- **Matrix Scan**: +1 conditional check per key press (negligible)
- **HID Communication**: +4 bytes per packet (negligible)

### Development Time Estimate
- **Firmware Changes**: 2-3 hours
- **GUI Changes**: 3-4 hours
- **Testing**: 2-3 hours
- **Total**: 7-10 hours

---

## Next Steps

1. **Review this plan** and answer the design questions above
2. **Approve architecture** (or suggest changes)
3. **Begin implementation** starting with firmware data structures
4. **Iterate** with testing and refinement

Please review and let me know:
- Which design options you prefer
- Any additional requirements or constraints
- Whether to proceed with implementation
