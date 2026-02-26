# Task: Implement Quick Build Parameter Setup & Encoder Hijacking

## What To Build

### 1. Quick Build Parameter Setup Phase (BEFORE note recording)

Currently when `ARP_QUICK_BUILD` or `SEQ_QUICK_BUILD_N` keycodes are pressed, it goes straight into note recording mode. Instead, add a **parameter wizard** first:

1. **Press quick build button** → Show **Mode selector** on OLED
2. **Encoder 0 rotation** scrolls through available modes
3. **Either encoder 0 click OR the same quick build button** confirms selection
4. Show **Speed/Rate selector** → same encoder interaction → confirm
5. Show **Gate length selector** → same encoder interaction → confirm
6. **Then** enter note recording mode (existing behavior)

Display each parameter on the OLED using the existing large font system (`oled_write_str_2x()`, `render_big_number()` style).

### 2. Encoder 0 Hijacking During Quick Build

- **Only encoder 0** is hijacked during quick build. Encoder 1 keeps normal behavior.
- Encoder 0 hardware: Click=B14, Rotation=C14/C13, matrix position (5,0) for click
- Encoder 1 hardware: Click=B15, Rotation=C15/B4, matrix position (5,1) for click
- During **parameter setup**: enc0 rotation = scroll parameter values, enc0 click = confirm
- During **note recording**: enc0 click = momentary chord mode (see below)
- Encoder 0 must **NOT** send its normal keycode actions while quick build is active

The encoder click is currently handled in `matrix_scan_user()` in `orthomidi5x14.c` (~line 17265+):
```c
// Handle encoder 0 click button (PB14) - matrix position (5, 0)
static bool encoder0_click_prev_state = true;
bool encoder0_click_state = readPin(B14);
if (encoder0_click_state != encoder0_click_prev_state) {
    action_exec(MAKE_KEYEVENT(5, 0, !encoder0_click_state));
    encoder0_click_prev_state = encoder0_click_state;
}
```

Encoder rotation is handled in `encoder_update_user()` (also in `orthomidi5x14.c`). Both need to be intercepted when `quick_build_is_active()` returns true.

### 3. Encoder Click Momentary Chord Mode (during recording)

During note recording phase:
- **Hold** encoder 0 click = all notes pressed go to the **same step** (chord grouping, like sustain pedal)
- **Release** encoder 0 click = advance to next step
- This works **in addition to** the existing sustain pedal chord grouping

### 4. Arpeggiator/Sequencer Velocity Through Curve

Currently arp/seq playback sends raw velocity (0-127) directly, bypassing velocity curves. Change this so:
- Take the preset velocity (1-127) as-is
- Run it through the **same velocity curve and vel min/max system** that normal MIDI key presses use
- Do NOT double or rescale the value first — just use 1-127 as input to the curve
- Look at how `process_midi.c` applies velocity curves to understand the integration point

## Key Files To Read

| File | What's There |
|------|-------------|
| `keyboards/orthomidi5x14/arpeggiator.c` | `quick_build_*` functions, `arp_update()`, `seq_update()`, note-sending code (`midi_send_noteon_arp` or similar) |
| `keyboards/orthomidi5x14/orthomidi5x14.c` | `matrix_scan_user()` (encoder click handling ~line 17265+), `encoder_update_user()` (encoder rotation), `oled_task_user()` (~line 17237), `render_big_number()` (~line 17191), large font system (`oled_write_str_2x` ~line 16591) |
| `keyboards/orthomidi5x14/orthomidi5x14.h` | `quick_build_state` struct, keycodes (`ARP_QUICK_BUILD`=0xEF0D, `SEQ_QUICK_BUILD_1-8`=0xEF0E-0xEF15), `arp_mode_t` enum, `arp_state_t`/`seq_state_t` structs |
| `quantum/process_keycode/process_midi.c` (or similar) | How velocity curves are applied to normal MIDI key presses — this is the pattern to replicate for arp/seq |

## Hardware Reference

- **OLED**: 128x128 SH1107, I2C on B6/B7. 21 columns x 16 rows in 6x8 font. Large font = 12x16px (2x scaled).
- **Encoder 0**: Click=B14, Rotation=C14/C13, matrix pos (5,0)
- **Encoder 1**: Click=B15, Rotation=C15/B4, matrix pos (5,1)
- **Footswitch**: A9, matrix pos (5,2)

## Implementation Notes

- The `quick_build_state` struct will need new fields for the setup phase (e.g. `setup_phase`, `setup_param_index`, `setup_value`)
- Add a new `quick_build_setup_phase_t` enum: `QB_SETUP_MODE`, `QB_SETUP_SPEED`, `QB_SETUP_GATE`, `QB_SETUP_DONE`
- The OLED rendering in `oled_task_user()` already checks `quick_build_is_active()` and calls `render_big_number()` — extend this to show the parameter setup screens when in setup phase
- For encoder hijacking: guard the `action_exec(MAKE_KEYEVENT(5, 0, ...))` call and the `encoder_update_user()` index 0 case with `if (!quick_build_is_active())`
- Firmware compiles with `-Werror` — all warnings are errors. Watch for unused variables and snprintf truncation in `buf[22]`.
