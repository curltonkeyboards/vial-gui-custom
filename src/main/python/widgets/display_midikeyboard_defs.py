# SPDX-License-Identifier: GPL-2.0-or-later
midi_layout = r"""
[
    # First row: Black keys from the first 3 octaves (C# to A#)
    ["MI_Cs", {"x": 1}, "MI_Ds", {"x": 1}, "MI_Fs", {"x": 1}, "MI_Gs", {"x": 1}, "MI_As",
     {"x": 1.5}, "MI_Cs_1", {"x": 1}, "MI_Ds_1", {"x": 1}, "MI_Fs_1", {"x": 1}, "MI_Gs_1", {"x": 1}, "MI_As_1",
     {"x": 1.5}, "MI_Cs_2", {"x": 1}, "MI_Ds_2", {"x": 1}, "MI_Fs_2", {"x": 1}, "MI_Gs_2", {"x": 1}, "MI_As_2"],
    
    # Second row: White keys from the first 3 octaves (C to B)
    [{"y": 0.25}, "MI_C", "MI_D", "MI_E", "MI_F", "MI_G", "MI_A", "MI_B",
     {"x": 0.5}, "MI_C_1", "MI_D_1", "MI_E_1", "MI_F_1", "MI_G_1", "MI_A_1", "MI_B_1",
     {"x": 0.5}, "MI_C_2", "MI_D_2", "MI_E_2", "MI_F_2", "MI_G_2", "MI_A_2", "MI_B_2"],
    
    # Third row: Black keys from the highest 3 octaves (C# to A#)
    ["MI_Cs_3", {"x": 1}, "MI_Ds_3", {"x": 1}, "MI_Fs_3", {"x": 1}, "MI_Gs_3", {"x": 1}, "MI_As_3",
     {"x": 1.5}, "MI_Cs_4", {"x": 1}, "MI_Ds_4", {"x": 1}, "MI_Fs_4", {"x": 1}, "MI_Gs_4", {"x": 1}, "MI_As_4",
     {"x": 1.5}, "MI_Cs_5", {"x": 1}, "MI_Ds_5", {"x": 1}, "MI_Fs_5", {"x": 1}, "MI_Gs_5", {"x": 1}, "MI_As_5"],
    
    # Fourth row: White keys from the highest 3 octaves (C to B)
    [{"y": 0.25}, "MI_C_3", "MI_D_3", "MI_E_3", "MI_F_3", "MI_G_3", "MI_A_3", "MI_B_3",
     {"x": 0.5}, "MI_C_4", "MI_D_4", "MI_E_4", "MI_F_4", "MI_G_4", "MI_A_4", "MI_B_4",
     {"x": 0.5}, "MI_C_5", "MI_D_5", "MI_E_5", "MI_F_5", "MI_G_5", "MI_A_5", "MI_B_5"]
]
"""