# PyInstaller hook for rtmidi (compatible with PyInstaller 3.4+)
# Ensures the binary extension is included

import os
import sys

hiddenimports = ['_rtmidi']
binaries = []
datas = []

# Manually find and include the rtmidi binary extension
try:
    import rtmidi
    rtmidi_path = os.path.dirname(rtmidi.__file__)

    # Find the binary extension file (_rtmidi.so or _rtmidi.pyd)
    for filename in os.listdir(rtmidi_path):
        if filename.startswith('_rtmidi') and (filename.endswith('.so') or filename.endswith('.pyd')):
            src_path = os.path.join(rtmidi_path, filename)
            # Include in the rtmidi package directory
            binaries.append((src_path, 'rtmidi'))
            print(f"[hook-rtmidi] Including binary: {filename}")

    # Include Python files
    for filename in os.listdir(rtmidi_path):
        if filename.endswith('.py'):
            src_path = os.path.join(rtmidi_path, filename)
            datas.append((src_path, 'rtmidi'))

except Exception as e:
    print(f"[hook-rtmidi] Warning: Could not collect rtmidi files: {e}")
    # Fallback - at minimum try to import
    hiddenimports = ['_rtmidi', 'rtmidi']
