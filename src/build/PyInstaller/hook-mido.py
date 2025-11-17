# PyInstaller hook for mido package
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all mido submodules including backends
hiddenimports = collect_submodules('mido')

# Collect data files
datas = collect_data_files('mido', include_py_files=True)
