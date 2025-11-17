# PyInstaller hook for rtmidi package
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

# Collect the binary extension
binaries = collect_dynamic_libs('rtmidi')

# Collect data files
datas = collect_data_files('rtmidi', include_py_files=True)

# Hidden imports
hiddenimports = ['_rtmidi', 'rtmidi._rtmidi']
