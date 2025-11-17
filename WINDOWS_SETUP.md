# Windows Development Setup Guide

This guide will help you set up the Vial GUI development environment on Windows.

## Prerequisites

1. **Python Installation**
   - **CRITICAL:** You must use **Python 3.8 or 3.9**. Python 3.10+ will NOT work!
   - Download Python 3.9.13 from [python.org](https://www.python.org/downloads/) (recommended)
   - **Important:** During installation, check "Add Python to PATH"
   - Restart your terminal after installation
   - **Note:** If you have Python 3.10+ installed, you can install 3.9 alongside it and use `py -3.9` to access it

2. **Visual C++ Build Tools** (Required for compiling hidapi)
   - Download and install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   - Select "Desktop development with C++" workload
   - This is required for the `hidapi` dependency

## Setup Steps

### 1. Verify Python Installation

Open Git Bash or PowerShell and run:

```bash
python --version
# or
py --version

# If you have multiple Python versions, list them:
py -0

# To check a specific version:
py -3.9 --version
```

You should see Python 3.8 or 3.9. **If you see 3.10 or higher, you need to install Python 3.9.**

### 2. Create Virtual Environment

```bash
# Navigate to project directory
cd ~/Documents/vial-gui-custom-[your-branch-name]

# Create virtual environment with Python 3.9 specifically
# If you have multiple Python versions installed:
py -3.9 -m venv venv

# If Python 3.9 is your default Python:
python -m venv venv

# Activate virtual environment
# For Git Bash:
source venv/Scripts/activate

# For PowerShell:
.\venv\Scripts\Activate.ps1

# For CMD:
venv\Scripts\activate.bat

# Verify you're using the correct Python version:
python --version  # Should show 3.9.x
```

### 3. Install Dependencies (WITH CYTHON FIX)

The `hidapi` dependency requires Cython, but the pinned alpha version is no longer available. Here's the workaround:

```bash
# Make sure venv is activated
source venv/Scripts/activate

# Install compatible Cython version first
pip install "Cython>=0.29.32,<3.0"

# Install remaining dependencies (skip hidapi for now)
pip install altgraph==0.17
pip install fbs==0.9.0
pip install future==0.18.2
pip install keyboard==0.13.5
pip install macholib==1.14
pip install pefile==2019.4.18
pip install PyInstaller==3.4
pip install PyQt5==5.9.2
pip install sip==4.19.8
pip install pywin32==303
pip install certifi

# Download and install simpleeval
pip install https://github.com/danthedeckie/simpleeval/archive/41c99b8e224a7a0ae0ac59c773598fe79a4470db.zip

# Finally, try installing hidapi (may need build tools)
pip install git+https://github.com/vial-kb/cython-hidapi@88d8983b3dc65b9ef84238abe3f46004b0ef2fd0
```

**Alternative:** If the above still fails, you can try installing a pre-built hidapi wheel:

```bash
pip install hidapi
```

### 4. Run the Application

```bash
# Activate virtual environment if not already active
source venv/Scripts/activate

# Run the app
fbs run

# If fbs is not found, try:
python -m fbs run
```

## Troubleshooting

### Wrong Python version (3.10+)
- This project requires Python 3.8 or 3.9 maximum
- Python 3.10+ is not compatible with the old dependencies
- Install Python 3.9 from python.org
- Use `py -3.9 -m venv venv` to create venv with correct version

### Python not found
- Make sure Python is added to PATH during installation
- Restart your terminal after installing Python
- Try `py` instead of `python`
- Use `py -0` to list all installed Python versions

### Permission errors
- Run Git Bash or PowerShell as Administrator
- Disable antivirus temporarily if it blocks Python

### hidapi build fails
- Install Microsoft C++ Build Tools (see Prerequisites)
- Alternatively, use pre-built `hidapi` package: `pip install hidapi`

### fbs not found after installation
- Make sure virtual environment is activated
- Try `python -m fbs run` instead of `fbs run`

### PyQt5 issues
- If you get Qt platform plugin errors, try:
  ```bash
  pip uninstall PyQt5
  pip install PyQt5==5.15.9
  ```

## Quick Reference

```bash
# Activate environment
source venv/Scripts/activate  # Git Bash
.\venv\Scripts\Activate.ps1   # PowerShell

# Run application
fbs run

# Deactivate environment
deactivate
```

## Additional Notes

- **This project REQUIRES Python 3.6-3.9** (3.9 recommended for Windows)
- **Python 3.10+ will NOT work** due to incompatible old dependencies
- The `fbs` (fman build system) requires PyQt5 5.9.2 by default
- Some dependencies may require Visual C++ Build Tools to compile
- If you encounter Cython or hidapi errors, it's likely a Python version issue

## Getting Help

If you continue to have issues:
1. Check that all prerequisites are installed
2. Verify Python version compatibility
3. Ensure virtual environment is activated
4. Review error messages for missing dependencies
