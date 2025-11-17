"""
Custom freeze script for fbs
This modifies the PyInstaller build to include MIDI libraries
"""

def freeze(application_context, output_directory):
    """
    Called by fbs during the freeze process
    Modify PyInstaller settings to include MIDI libraries
    """
    import os
    from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

    # Get the hooks directory
    hooks_dir = os.path.join(application_context.project_dir, 'src', 'build', 'hooks')

    # Ensure hooks directory exists
    if not os.path.exists(hooks_dir):
        print(f"Warning: hooks directory not found at {hooks_dir}")

    # Additional hidden imports for MIDI libraries
    hidden_imports = [
        'mido',
        'mido.backends',
        'mido.backends.rtmidi',
        'mido.messages',
        'mido.ports',
        'rtmidi',
        '_rtmidi',
    ]

    print(f"[freeze.py] Adding hidden imports for MIDI libraries: {hidden_imports}")
    print(f"[freeze.py] Using hooks directory: {hooks_dir}")

    # Return configuration for fbs to use
    return {
        'hiddenimports': hidden_imports,
        'hookspath': [hooks_dir],
    }
