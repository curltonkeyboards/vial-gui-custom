# PyInstaller hook for mido (compatible with PyInstaller 3.4+)
# Ensures all backends and submodules are included

try:
    from PyInstaller.utils.hooks import collect_submodules, collect_data_files

    # Collect all mido submodules
    hiddenimports = collect_submodules('mido')

    # Collect any data files
    try:
        datas = collect_data_files('mido')
    except:
        datas = []

except ImportError:
    # Fallback for older PyInstaller versions
    hiddenimports = [
        'mido',
        'mido.backends',
        'mido.backends.rtmidi',
        'mido.backends.portmidi',
        'mido.backends.pygame',
        'mido.backends.amidi',
        'mido.messages',
        'mido.ports',
        'mido.parser',
        'mido.midifiles',
    ]
    datas = []
