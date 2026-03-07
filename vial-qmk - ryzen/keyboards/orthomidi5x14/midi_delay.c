// midi_delay.c - MIDI Delay Effect System
// Repeats note-on/note-off events with configurable timing, decay, channel, and transpose

#include QMK_KEYBOARD_H
#include "midi_delay.h"
#include "orthomidi5x14.h"
#include "process_midi.h"
#include "midi/qmk_midi.h"
#include "midi/midi.h"
#include "raw_hid.h"
#include "eeprom.h"
#include <string.h>

// =============================================================================
// FACTORY PRESETS (const in flash - zero RAM cost)
// =============================================================================
// Layout: 5 rates x 3 timings x 3 decays = 45, then 3 pitch delay variants = 48 total
// Rates: 0=1/1, 1=1/2, 2=1/4, 3=1/8, 4=1/16
// Timings: 0=Straight, 2=Dotted, 1=Triplet
// Decays: 38% (Short), 20% (Med), 11% (Long)

#define FACTORY_PRESET(rv, tm, dp) \
    { .rate_mode = 0, .note_value = (rv), .timing_mode = (tm), .decay_percent = (dp), \
      .fixed_delay_ms = 500, .max_repeats = 0, .channel = 0, .transpose_semi = 0, \
      .transpose_mode = 0, .max_active_notes = 0, .channel_count = 1, \
      .channel2 = 0, .channel3 = 0, .channel4 = 0, .reserved = {0} }

#define PITCH_PRESET(rv) \
    { .rate_mode = 0, .note_value = (rv), .timing_mode = 0, .decay_percent = 21, \
      .fixed_delay_ms = 500, .max_repeats = 2, .channel = 0, .transpose_semi = 12, \
      .transpose_mode = 1, .max_active_notes = 0, .channel_count = 1, \
      .channel2 = 0, .channel3 = 0, .channel4 = 0, .reserved = {0} }

const delay_slot_config_t delay_factory_presets[DELAY_FACTORY_COUNT] = {
    // ---- 1/1 Whole note (rate 0) ----
    // Note, Dotted, Triplet x Short, Med, Long
    FACTORY_PRESET(0, 0, 38), FACTORY_PRESET(0, 0, 20), FACTORY_PRESET(0, 0, 11),  // 1/1 Note
    FACTORY_PRESET(0, 2, 38), FACTORY_PRESET(0, 2, 20), FACTORY_PRESET(0, 2, 11),  // 1/1 Dotted
    FACTORY_PRESET(0, 1, 38), FACTORY_PRESET(0, 1, 20), FACTORY_PRESET(0, 1, 11),  // 1/1 Triplet

    // ---- 1/2 Half note (rate 1) ----
    FACTORY_PRESET(1, 0, 38), FACTORY_PRESET(1, 0, 20), FACTORY_PRESET(1, 0, 11),  // 1/2 Note
    FACTORY_PRESET(1, 2, 38), FACTORY_PRESET(1, 2, 20), FACTORY_PRESET(1, 2, 11),  // 1/2 Dotted
    FACTORY_PRESET(1, 1, 38), FACTORY_PRESET(1, 1, 20), FACTORY_PRESET(1, 1, 11),  // 1/2 Triplet

    // ---- 1/4 Quarter note (rate 2) ----
    FACTORY_PRESET(2, 0, 38), FACTORY_PRESET(2, 0, 20), FACTORY_PRESET(2, 0, 11),  // 1/4 Note
    FACTORY_PRESET(2, 2, 38), FACTORY_PRESET(2, 2, 20), FACTORY_PRESET(2, 2, 11),  // 1/4 Dotted
    FACTORY_PRESET(2, 1, 38), FACTORY_PRESET(2, 1, 20), FACTORY_PRESET(2, 1, 11),  // 1/4 Triplet

    // ---- 1/8 Eighth note (rate 3) ----
    FACTORY_PRESET(3, 0, 38), FACTORY_PRESET(3, 0, 20), FACTORY_PRESET(3, 0, 11),  // 1/8 Note
    FACTORY_PRESET(3, 2, 38), FACTORY_PRESET(3, 2, 20), FACTORY_PRESET(3, 2, 11),  // 1/8 Dotted
    FACTORY_PRESET(3, 1, 38), FACTORY_PRESET(3, 1, 20), FACTORY_PRESET(3, 1, 11),  // 1/8 Triplet

    // ---- 1/16 Sixteenth note (rate 4) ----
    FACTORY_PRESET(4, 0, 38), FACTORY_PRESET(4, 0, 20), FACTORY_PRESET(4, 0, 11),  // 1/16 Note
    FACTORY_PRESET(4, 2, 38), FACTORY_PRESET(4, 2, 20), FACTORY_PRESET(4, 2, 11),  // 1/16 Dotted
    FACTORY_PRESET(4, 1, 38), FACTORY_PRESET(4, 1, 20), FACTORY_PRESET(4, 1, 11),  // 1/16 Triplet

    // ---- Pitch delay variants: +12 cumulative, 2 repeats, 21% decay ----
    PITCH_PRESET(2),   // Slot 45: 1/4 Note Pitch Delay
    PITCH_PRESET(3),   // Slot 46: 1/8 Note Pitch Delay
    PITCH_PRESET(4),   // Slot 47: 1/16 Note Pitch Delay
};

// =============================================================================
// GLOBAL STATE
// =============================================================================

delay_system_t delay_system;

// Track original note-on times for duration mirroring
// Maps (channel, note) -> timestamp of most recent note-on
typedef struct {
    uint8_t  channel;
    uint8_t  note;
    uint32_t time;
    bool     in_use;
} note_on_tracker_t;

#define MAX_NOTE_ON_TRACKING 32
static note_on_tracker_t note_on_times[MAX_NOTE_ON_TRACKING];

// =============================================================================
// CONFIG ACCESSOR
// =============================================================================

const delay_slot_config_t* midi_delay_get_config(uint8_t slot_id) {
    if (slot_id < DELAY_FACTORY_COUNT) {
        return &delay_factory_presets[slot_id];
    }
    uint8_t user_idx = slot_id - DELAY_FACTORY_COUNT;
    if (user_idx < DELAY_USER_SLOT_COUNT) {
        return &delay_system.user_configs[user_idx];
    }
    return NULL;
}

// =============================================================================
// TIMING CALCULATION
// =============================================================================

// Compute delay interval in ms for a given slot config
// Replicates the arpeggiator's compute_step_time_offset() logic for BPM-synced mode
static uint32_t compute_delay_interval(const delay_slot_config_t *cfg) {
    if (cfg->rate_mode == 1) {
        // Fixed ms mode
        return cfg->fixed_delay_ms;
    }

    // BPM-synced mode
    extern uint32_t current_bpm;
    uint32_t bpm = (current_bpm == 0) ? 12000000 : current_bpm;  // Default 120.00 BPM

    // Note value multiplier (how many 16ths per step)
    uint8_t multiplier = 1;
    switch (cfg->note_value) {
        case 0: multiplier = 16; break; // 1/1 Whole note
        case 1: multiplier = 8; break;  // 1/2 Half note
        case 2: multiplier = 4; break;  // 1/4 Quarter note
        case 3: multiplier = 2; break;  // 1/8 Eighth note
        case 4:                          // 1/16 Sixteenth note
        default: multiplier = 1; break;
    }

    // Timing mode numerator/denominator
    uint8_t timing_num = 1, timing_den = 1;
    if (cfg->timing_mode & TIMING_MODE_TRIPLET) {
        timing_num = 2; timing_den = 3;  // 2/3 duration
    } else if (cfg->timing_mode & TIMING_MODE_DOTTED) {
        timing_num = 3; timing_den = 2;  // 3/2 duration
    }

    // 64-bit calculation: (1 * 6,000,000,000 * multiplier * timing_num) / (4 * bpm * timing_den)
    uint64_t numerator = (uint64_t)6000000000ULL * multiplier * timing_num;
    uint64_t denominator = (uint64_t)4 * bpm * timing_den;

    return (uint32_t)(numerator / denominator);
}

// =============================================================================
// NOTE-ON TIME TRACKING (for duration mirroring)
// =============================================================================

static void track_note_on_time(uint8_t channel, uint8_t note, uint32_t time) {
    // Find existing or empty slot
    int8_t empty = -1;
    for (uint8_t i = 0; i < MAX_NOTE_ON_TRACKING; i++) {
        if (note_on_times[i].in_use &&
            note_on_times[i].channel == channel &&
            note_on_times[i].note == note) {
            note_on_times[i].time = time;
            return;
        }
        if (!note_on_times[i].in_use && empty < 0) {
            empty = i;
        }
    }
    if (empty >= 0) {
        note_on_times[empty].channel = channel;
        note_on_times[empty].note = note;
        note_on_times[empty].time = time;
        note_on_times[empty].in_use = true;
    }
}

static uint32_t get_note_on_time(uint8_t channel, uint8_t note) {
    for (uint8_t i = 0; i < MAX_NOTE_ON_TRACKING; i++) {
        if (note_on_times[i].in_use &&
            note_on_times[i].channel == channel &&
            note_on_times[i].note == note) {
            return note_on_times[i].time;
        }
    }
    return 0;  // Not found
}

static void remove_note_on_time(uint8_t channel, uint8_t note) {
    for (uint8_t i = 0; i < MAX_NOTE_ON_TRACKING; i++) {
        if (note_on_times[i].in_use &&
            note_on_times[i].channel == channel &&
            note_on_times[i].note == note) {
            note_on_times[i].in_use = false;
            return;
        }
    }
}

// =============================================================================
// QUEUE MANAGEMENT
// =============================================================================

static bool queue_add(delay_event_t *event) {
    if (delay_system.queue_count >= DELAY_MAX_PENDING) {
        return false;  // Queue full
    }
    memcpy(&delay_system.queue[delay_system.queue_count], event, sizeof(delay_event_t));
    delay_system.queue_count++;
    return true;
}

static void queue_remove(uint8_t index) {
    if (index >= delay_system.queue_count) return;
    // Shift remaining events down
    for (uint8_t i = index; i < delay_system.queue_count - 1; i++) {
        memcpy(&delay_system.queue[i], &delay_system.queue[i + 1], sizeof(delay_event_t));
    }
    delay_system.queue_count--;
}

// =============================================================================
// INITIALIZATION & PERSISTENCE
// =============================================================================

void midi_delay_init(void) {
    memset(&delay_system, 0, sizeof(delay_system_t));

    // Set defaults for user slots
    for (uint8_t i = 0; i < DELAY_USER_SLOT_COUNT; i++) {
        delay_system.user_configs[i].rate_mode = 0;
        delay_system.user_configs[i].note_value = 3;
        delay_system.user_configs[i].timing_mode = 0;
        delay_system.user_configs[i].decay_percent = 50;
        delay_system.user_configs[i].fixed_delay_ms = 500;
        delay_system.user_configs[i].max_repeats = 3;
        delay_system.user_configs[i].channel = 0;
        delay_system.user_configs[i].transpose_semi = 0;
        delay_system.user_configs[i].transpose_mode = 0;
        delay_system.user_configs[i].max_active_notes = 0;
        delay_system.user_configs[i].channel_count = 1;
        delay_system.user_configs[i].channel2 = 0;
        delay_system.user_configs[i].channel3 = 0;
        delay_system.user_configs[i].channel4 = 0;
    }

    memset(note_on_times, 0, sizeof(note_on_times));

    // Load user slots from EEPROM (factory presets are const in flash)
    midi_delay_load();
}

void midi_delay_save(void) {
    // Write magic
    uint16_t magic = DELAY_EEPROM_MAGIC;
    eeprom_write_block(&magic, (void *)(DELAY_EEPROM_ADDR), 2);

    // Write only user slot configs
    eeprom_write_block(delay_system.user_configs,
                       (void *)(DELAY_EEPROM_ADDR + 2),
                       sizeof(delay_slot_config_t) * DELAY_USER_SLOT_COUNT);

    dprintf("midi_delay: saved %d user slots to EEPROM\n", DELAY_USER_SLOT_COUNT);
}

void midi_delay_load(void) {
    // Check magic
    uint16_t magic = 0;
    eeprom_read_block(&magic, (void *)(DELAY_EEPROM_ADDR), 2);

    if (magic != DELAY_EEPROM_MAGIC) {
        dprintf("midi_delay: no valid EEPROM data (magic=0x%04X), using defaults\n", magic);
        return;
    }

    // Load user slots from EEPROM
    eeprom_read_block(delay_system.user_configs,
                      (void *)(DELAY_EEPROM_ADDR + 2),
                      sizeof(delay_slot_config_t) * DELAY_USER_SLOT_COUNT);

    dprintf("midi_delay: loaded %d user slots from EEPROM\n", DELAY_USER_SLOT_COUNT);
}

void midi_delay_reset(void) {
    midi_delay_clear_queue();

    // Deactivate all slots
    for (uint8_t i = 0; i < DELAY_TOTAL_SLOT_COUNT; i++) {
        delay_system.runtime[i].active = false;
    }

    // Reset user slots to defaults
    for (uint8_t i = 0; i < DELAY_USER_SLOT_COUNT; i++) {
        delay_system.user_configs[i].rate_mode = 0;
        delay_system.user_configs[i].note_value = 3;
        delay_system.user_configs[i].timing_mode = 0;
        delay_system.user_configs[i].decay_percent = 50;
        delay_system.user_configs[i].fixed_delay_ms = 500;
        delay_system.user_configs[i].max_repeats = 3;
        delay_system.user_configs[i].channel = 0;
        delay_system.user_configs[i].transpose_semi = 0;
        delay_system.user_configs[i].transpose_mode = 0;
        delay_system.user_configs[i].max_active_notes = 0;
        delay_system.user_configs[i].channel_count = 1;
        memset(delay_system.user_configs[i].reserved, 0, sizeof(delay_system.user_configs[i].reserved));
    }

    midi_delay_save();
    dprintf("midi_delay: reset all user slots to defaults\n");
}

// =============================================================================
// CORE ENGINE
// =============================================================================

void midi_delay_tick(void) {
    if (delay_system.queue_count == 0) return;

    uint32_t now = timer_read32();

    // Process events - iterate backwards so removal doesn't skip entries
    for (int8_t i = delay_system.queue_count - 1; i >= 0; i--) {
        delay_event_t *evt = &delay_system.queue[i];

        // Check if 32-bit timer wrapped (handle with simple comparison)
        if ((int32_t)(now - evt->fire_time) >= 0) {
            // Time to fire this event
            if (evt->is_note_off) {
                // Only send note-off if the corresponding note-on was actually sent
                if (evt->note_on_sent) {
                    midi_send_noteoff_delay(evt->channel, evt->note, 0);
                    dprintf("midi_delay: note-off ch:%d note:%d\n", evt->channel, evt->note);
                }
            } else {
                // Note-on
                if (evt->velocity > 0) {
                    midi_send_noteon_delay(evt->channel, evt->note, evt->velocity);
                    evt->note_on_sent = 1;
                    dprintf("midi_delay: note-on ch:%d note:%d vel:%d\n",
                            evt->channel, evt->note, evt->velocity);

                    // Mark matching note-off events as having their note-on sent
                    for (uint8_t j = 0; j < delay_system.queue_count; j++) {
                        delay_event_t *off = &delay_system.queue[j];
                        if (off->is_note_off &&
                            off->channel == evt->channel &&
                            off->note == evt->note &&
                            off->slot_id == evt->slot_id &&
                            !off->note_on_sent) {
                            off->note_on_sent = 1;
                            break;  // Match first corresponding note-off
                        }
                    }
                }
            }

            queue_remove(i);
        }
    }
}

void midi_delay_schedule_note_on(uint8_t channel, uint8_t note, uint8_t velocity) {
    uint32_t now = timer_read32();

    // Track this note-on time for duration mirroring
    track_note_on_time(channel, note, now);

    // Check each active slot (factory + user)
    for (uint8_t s = 0; s < DELAY_TOTAL_SLOT_COUNT; s++) {
        if (!delay_system.runtime[s].active) continue;

        const delay_slot_config_t *cfg = midi_delay_get_config(s);
        if (!cfg) continue;

        // Max active notes: limit how many distinct notes can have pending delays in this slot
        if (cfg->max_active_notes > 0) {
            // Step 1: Always cancel existing delays for the SAME note (re-trigger resets delay)
            for (int8_t i = delay_system.queue_count - 1; i >= 0; i--) {
                delay_event_t *evt = &delay_system.queue[i];
                if (evt->slot_id == s && evt->original_note == note) {
                    if (!evt->is_note_off && evt->note_on_sent) {
                        midi_send_noteoff_delay(evt->channel, evt->note, 0);
                    }
                    queue_remove(i);
                }
            }

            // Step 2: Count distinct OTHER notes still pending in this slot
            uint8_t distinct_notes[128];
            uint8_t distinct_count = 0;
            memset(distinct_notes, 0, sizeof(distinct_notes));

            for (uint8_t i = 0; i < delay_system.queue_count; i++) {
                delay_event_t *evt = &delay_system.queue[i];
                if (evt->slot_id == s && !distinct_notes[evt->original_note]) {
                    distinct_notes[evt->original_note] = 1;
                    distinct_count++;
                }
            }

            // Step 3: Evict oldest notes until we have room for the new one
            while (distinct_count >= cfg->max_active_notes) {
                // Find the oldest pending note in this slot (by earliest fire_time)
                uint8_t oldest_note = 0;
                uint32_t oldest_time = UINT32_MAX;
                bool found = false;

                for (uint8_t i = 0; i < delay_system.queue_count; i++) {
                    delay_event_t *evt = &delay_system.queue[i];
                    if (evt->slot_id == s && !evt->is_note_off) {
                        if (!found || (int32_t)(evt->fire_time - oldest_time) < 0) {
                            oldest_time = evt->fire_time;
                            oldest_note = evt->original_note;
                            found = true;
                        }
                    }
                }

                if (!found) break;

                // Remove all events for this oldest note and send note-offs
                for (int8_t i = delay_system.queue_count - 1; i >= 0; i--) {
                    delay_event_t *evt = &delay_system.queue[i];
                    if (evt->slot_id == s && evt->original_note == oldest_note) {
                        if (!evt->is_note_off && evt->note_on_sent) {
                            midi_send_noteoff_delay(evt->channel, evt->note, 0);
                        }
                        queue_remove(i);
                    }
                }
                distinct_count--;
            }
        }

        uint32_t interval = compute_delay_interval(cfg);

        if (interval == 0) continue;  // Safety

        uint8_t max_rep = cfg->max_repeats;
        if (max_rep == 0) max_rep = 255;  // 0 = unlimited (until decay kills it)

        for (uint8_t r = 1; r <= max_rep; r++) {
            // Calculate decayed velocity
            // velocity_out = original - (original * decay% * repeat_num / 100)
            int16_t vel = (int16_t)velocity - ((int16_t)velocity * cfg->decay_percent * r / 100);
            if (vel <= 0) break;  // No more audible repeats
            if (vel > 127) vel = 127;

            // Calculate transposed note
            int16_t transposed;
            if (cfg->transpose_mode == 1) {
                // Cumulative: each repeat adds another offset
                transposed = (int16_t)note + (int16_t)cfg->transpose_semi * r;
            } else {
                // Fixed: all repeats use same offset
                transposed = (int16_t)note + (int16_t)cfg->transpose_semi;
            }

            // Skip if out of MIDI range
            if (transposed < 0 || transposed > 127) continue;

            // Determine channel (multi-channel mode cycles through channels per repeat)
            uint8_t ch;
            if (cfg->channel == 0) {
                ch = channel;  // Same as original
            } else if (cfg->channel_count >= 2) {
                // Multi-channel: build channel list and cycle through it
                uint8_t ch_list[4];
                uint8_t ch_count = cfg->channel_count;
                if (ch_count > 4) ch_count = 4;
                ch_list[0] = cfg->channel - 1;
                ch_list[1] = (ch_count >= 2 && cfg->channel2 > 0) ? (cfg->channel2 - 1) : ch_list[0];
                ch_list[2] = (ch_count >= 3 && cfg->channel3 > 0) ? (cfg->channel3 - 1) : ch_list[0];
                ch_list[3] = (ch_count >= 4 && cfg->channel4 > 0) ? (cfg->channel4 - 1) : ch_list[0];
                ch = ch_list[(r - 1) % ch_count];
            } else {
                ch = cfg->channel - 1;  // Single different channel
            }

            // Schedule the note-on event
            delay_event_t evt = {0};
            evt.fire_time = now + interval * r;
            evt.note_on_time = now;
            evt.channel = ch;
            evt.note = (uint8_t)transposed;
            evt.velocity = (uint8_t)vel;
            evt.is_note_off = 0;
            evt.original_note = note;
            evt.original_channel = channel;
            evt.note_on_sent = 0;
            evt.slot_id = s;

            if (!queue_add(&evt)) {
                dprintf("midi_delay: queue full, dropping event\n");
                return;  // Queue full, stop scheduling entirely
            }
        }
    }
}

void midi_delay_schedule_note_off(uint8_t channel, uint8_t note) {
    uint32_t now = timer_read32();

    // Get the original note-on time for duration mirroring
    uint32_t original_on_time = get_note_on_time(channel, note);
    uint32_t held_duration = (original_on_time > 0) ? (now - original_on_time) : 100;  // Fallback 100ms

    // Remove the note-on tracking entry
    remove_note_on_time(channel, note);

    // For each pending note-on event matching this original note,
    // schedule a corresponding note-off after the same held duration
    for (uint8_t i = 0; i < delay_system.queue_count; i++) {
        delay_event_t *on_evt = &delay_system.queue[i];

        if (on_evt->is_note_off) continue;
        if (on_evt->original_note != note) continue;
        if (on_evt->original_channel != channel) continue;

        // Schedule note-off at: note-on fire time + held duration
        delay_event_t off_evt = {0};
        off_evt.fire_time = on_evt->fire_time + held_duration;
        off_evt.note_on_time = on_evt->note_on_time;
        off_evt.channel = on_evt->channel;
        off_evt.note = on_evt->note;
        off_evt.velocity = 0;
        off_evt.is_note_off = 1;
        off_evt.original_note = note;
        off_evt.original_channel = channel;
        off_evt.note_on_sent = 0;  // Will be set when the note-on fires
        off_evt.slot_id = on_evt->slot_id;

        queue_add(&off_evt);
    }

    // Also handle note-on events that have ALREADY fired (their note is still sounding)
    // These won't be in the queue anymore, so check all active slots
    for (uint8_t s = 0; s < DELAY_TOTAL_SLOT_COUNT; s++) {
        if (!delay_system.runtime[s].active) continue;

        const delay_slot_config_t *cfg = midi_delay_get_config(s);
        if (!cfg) continue;

        uint32_t interval = compute_delay_interval(cfg);
        if (interval == 0) continue;

        uint8_t max_rep = cfg->max_repeats;
        if (max_rep == 0) max_rep = 255;

        for (uint8_t r = 1; r <= max_rep; r++) {
            uint32_t on_fire_time = original_on_time + interval * r;

            // Check if this note-on already fired (fire_time has passed)
            if ((int32_t)(now - on_fire_time) < 0) break;  // Not yet fired, handled above

            // This note-on already fired. Check if velocity was > 0
            int16_t vel = (int16_t)127 - ((int16_t)127 * cfg->decay_percent * r / 100);
            if (vel <= 0) break;

            int16_t transposed;
            if (cfg->transpose_mode == 1) {
                transposed = (int16_t)note + (int16_t)cfg->transpose_semi * r;
            } else {
                transposed = (int16_t)note + (int16_t)cfg->transpose_semi;
            }
            if (transposed < 0 || transposed > 127) continue;

            uint8_t ch = (cfg->channel == 0) ? channel : (cfg->channel - 1);

            // Check if there's already a note-off queued for this note
            bool already_queued = false;
            for (uint8_t j = 0; j < delay_system.queue_count; j++) {
                if (delay_system.queue[j].is_note_off &&
                    delay_system.queue[j].channel == ch &&
                    delay_system.queue[j].note == (uint8_t)transposed &&
                    delay_system.queue[j].slot_id == s) {
                    already_queued = true;
                    break;
                }
            }

            if (!already_queued) {
                delay_event_t off_evt = {0};
                off_evt.fire_time = now + held_duration;
                off_evt.channel = ch;
                off_evt.note = (uint8_t)transposed;
                off_evt.velocity = 0;
                off_evt.is_note_off = 1;
                off_evt.original_note = note;
                off_evt.original_channel = channel;
                off_evt.note_on_sent = 1;  // Note-on was already sent
                off_evt.slot_id = s;
                queue_add(&off_evt);
            }
        }
    }
}

// =============================================================================
// SLOT CONTROL
// =============================================================================

void midi_delay_toggle_slot(uint8_t slot_id) {
    if (slot_id >= DELAY_TOTAL_SLOT_COUNT) return;
    delay_system.runtime[slot_id].active = !delay_system.runtime[slot_id].active;
    dprintf("midi_delay: slot %d %s%s\n", slot_id + 1,
            delay_system.runtime[slot_id].active ? "ON" : "OFF",
            slot_id < DELAY_FACTORY_COUNT ? " (factory)" : "");
}

bool midi_delay_slot_active(uint8_t slot_id) {
    if (slot_id >= DELAY_TOTAL_SLOT_COUNT) return false;
    return delay_system.runtime[slot_id].active;
}

void midi_delay_clear_queue(void) {
    // Send note-offs for any pending note-ons that already fired
    for (uint8_t i = 0; i < delay_system.queue_count; i++) {
        delay_event_t *evt = &delay_system.queue[i];
        if (evt->is_note_off && evt->note_on_sent) {
            // Send immediate note-off
            midi_send_noteoff(&midi_device, evt->channel, evt->note, 0);
        }
    }
    delay_system.queue_count = 0;
    memset(note_on_times, 0, sizeof(note_on_times));
    dprintf("midi_delay: queue cleared\n");
}

// =============================================================================
// QUERY HELPERS
// =============================================================================

bool midi_delay_any_bpm_synced_active(void) {
    for (uint8_t s = 0; s < DELAY_TOTAL_SLOT_COUNT; s++) {
        if (delay_system.runtime[s].active) {
            const delay_slot_config_t *cfg = midi_delay_get_config(s);
            if (cfg && cfg->rate_mode == 0) {
                return true;
            }
        }
    }
    return false;
}

// =============================================================================
// HID HANDLERS
// =============================================================================

void midi_delay_hid_get_slot(uint8_t slot_id, uint8_t *response) {
    // response format: [status, 16 bytes config]
    // Unified slot index: 0-47 = factory (from flash), 48-97 = user (from RAM)
    const delay_slot_config_t *cfg = midi_delay_get_config(slot_id);
    if (!cfg) {
        response[0] = 0x00;  // Error
        return;
    }

    response[0] = 0x01;  // Success
    memcpy(&response[1], cfg, DELAY_CONFIG_SIZE);
}

void midi_delay_hid_set_slot(uint8_t slot_id, const uint8_t *data) {
    // Factory presets (0-47) are read-only in flash
    if (slot_id < DELAY_FACTORY_COUNT) {
        dprintf("midi_delay: slot %d is a factory preset, ignoring HID write\n", slot_id + 1);
        return;
    }
    uint8_t user_idx = slot_id - DELAY_FACTORY_COUNT;
    if (user_idx >= DELAY_USER_SLOT_COUNT) return;

    memcpy(&delay_system.user_configs[user_idx], data, DELAY_CONFIG_SIZE);
    dprintf("midi_delay: user slot %d config updated via HID\n", user_idx + 1);
}

void midi_delay_hid_get_bulk(uint8_t start, uint8_t count, uint8_t *data, uint8_t length) {
    // Bulk read: send multiple slots in chunked packets
    // Unified index: 0-47 factory, 48-97 user

    uint8_t end = start + count;
    if (end > DELAY_TOTAL_SLOT_COUNT) end = DELAY_TOTAL_SLOT_COUNT;

    for (uint8_t s = start; s < end; s++) {
        uint8_t response[32] = {0};

        response[0] = 0x7D;  // HID_MANUFACTURER_ID
        response[1] = 0x00;  // HID_SUB_ID
        response[2] = 0x4D;  // HID_DEVICE_ID
        response[3] = 0xD8;  // HID_CMD_DELAY_GET_BULK

        response[4] = 0x01;  // Success
        response[5] = s;     // Unified slot index
        response[6] = (s < DELAY_FACTORY_COUNT) ? 0x01 : 0x00;  // is_factory flag

        const delay_slot_config_t *cfg = midi_delay_get_config(s);
        if (cfg) {
            memcpy(&response[7], cfg, DELAY_CONFIG_SIZE);
        }

        raw_hid_send(response, 32);
    }
}
