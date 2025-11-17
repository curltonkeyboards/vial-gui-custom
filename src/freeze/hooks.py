"""
Custom freeze hooks for including MIDI libraries in the standalone build
"""

def get_hidden_imports():
    """Return list of hidden imports to include in the frozen application"""
    return [
        'mido',
        'mido.backends',
        'mido.backends.rtmidi',
        'mido.backends.portmidi',
        'mido.backends.amidi',
        'mido.backends.pygame',
        'rtmidi',
        '_rtmidi',
    ]

def get_binaries():
    """Return list of binary files to include"""
    import os
    import sys
    binaries = []

    # Find rtmidi binary extension
    try:
        import rtmidi
        rtmidi_path = os.path.dirname(rtmidi.__file__)
        # Look for the _rtmidi.so or _rtmidi.pyd file
        for filename in os.listdir(rtmidi_path):
            if filename.startswith('_rtmidi') and (filename.endswith('.so') or filename.endswith('.pyd')):
                src = os.path.join(rtmidi_path, filename)
                dst = os.path.join('rtmidi', filename)
                binaries.append((src, 'rtmidi'))
                print(f"Including binary: {src} -> {dst}")
    except ImportError:
        print("Warning: rtmidi not found, MIDI functionality will not be available")

    return binaries

def get_datas():
    """Return list of data files to include"""
    datas = []

    # Include any mido data files
    try:
        import mido
        import os
        mido_path = os.path.dirname(mido.__file__)
        # Include all .py files in mido package
        for root, dirs, files in os.walk(mido_path):
            for file in files:
                if file.endswith('.py'):
                    src = os.path.join(root, file)
                    rel_path = os.path.relpath(root, os.path.dirname(mido_path))
                    datas.append((src, rel_path))
    except ImportError:
        print("Warning: mido not found")

    return datas
