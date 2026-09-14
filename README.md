# IMS Control 2026 (Simple)

Control software for a drift-tube ion mobility spectrometer using an NI USB-6351 DAQ.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

NI-DAQmx driver + the `nidaqmx` package are required only to run against real hardware.
Without them, the app still launches and runs fully in simulator mode.

## Run

```powershell
.venv\Scripts\python.exe main.py
```

Check "Use simulated DAQ (no hardware)" in the DAQ Configuration panel to try the app
without an instrument connected.

## Run tests

```powershell
.venv\Scripts\python.exe -m pytest tests -q
```

## Usage

1. Set experiment parameters (pulse width, experiment length, data points, averages,
   iterations) and DAQ device/channel names in the left panel.
2. Enter instrument metadata (drift length/voltage, pressure, temperature, gas) and,
   optionally, the analyte's ion m/z and charge to enable CCS calculation.
3. Click **Start**. Use **Pause**/**Resume** and **Stop** as needed.
4. Use the iteration selector above the line plot to view the live iteration or any
   past iteration; the heatmap shows all iterations at once.
5. The peak table updates for whichever iteration is selected.
6. Use the Export buttons to save the run as CSV, HDF5, or mzML.
7. Use **Import...** to load a previously saved CSV, HDF5, or mzML file for review —
   this replaces the current in-memory run.

See [AGENTS.md](AGENTS.md) for architecture details relevant to future development.
