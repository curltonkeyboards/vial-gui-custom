# PyInstaller hook for mido
# Ensures all backends and submodules are included

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all mido submodules
hiddenimports = collect_submodules('mido')

# Collect any data files
datas = collect_data_files('mido')

# Explicitly include backends
hiddenimports += [
    'mido.backends',
    'mido.backends.rtmidi',
    'mido.backends.portmidi',
    'mido.backends.pygame',
    'mido.backends.amidi',
]
