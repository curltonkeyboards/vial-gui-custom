###  MIDIswitch app is a vial-gui fork with additional functionality

With respect to the original work of the various contributors in creating Vial, this version has been modified by MidiSwitch and is not officially connected to or endorsed by the Vial team.

Vial is an open-source cross-platform (Windows, Linux and Mac) GUI and a QMK fork for configuring your keyboard in real time.


![](https://i.imgur.com/jad9FjY.png)


---


#### Releases

Visit https://www.MIDIswitch.com for the latest releases

Please visit [get.vial.today](https://get.vial.today/) to get started with Vial, the software which SwitchStation is based on

#### Development

**Python 3.6-3.9 is REQUIRED** (3.9 recommended). Python 3.10+ will NOT work due to old dependencies.

**For Windows users:** See [WINDOWS_SETUP.md](WINDOWS_SETUP.md) for detailed setup instructions and troubleshooting.

Install dependencies (Linux/Mac):

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Install dependencies (Windows - Git Bash):

```
python -m venv venv
source venv/Scripts/activate
pip install -r requirements-windows.txt
```

To launch the application afterwards:

```
source venv/bin/activate  # Linux/Mac
# OR
source venv/Scripts/activate  # Windows Git Bash
fbs run
```
