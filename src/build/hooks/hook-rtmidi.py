# PyInstaller hook for rtmidi
# Ensures the binary extension and all backends are included

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('rtmidi')

# Ensure the rtmidi C extension is included
hiddenimports += ['_rtmidi', 'rtmidi._rtmidi']
