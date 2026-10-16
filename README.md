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
6. Use the Export buttons to save the run as an Excel workbook (.xlsx), HDF5, or mzML. The drop-down
   beside them selects **raw + processed (default)**, raw only, or processed only. Raw = as acquired,
   never modified. The Excel workbook has **Raw**, **Processed**, **Peaks**, and **Settings** sheets; HDF5 stores
   labelled `raw_intensity` and `intensity` datasets in one file; mzML writes separate
   `<name>_raw.mzML` and `<name>_processed.mzML` files (importing either restores both). Every export
   also records the **instrument/ion metadata** and the **processing and peak-detection settings**
   (positive mode, baseline subtraction + window, normalization + scale, peak min height/prominence,
   noise window, software version): Excel `Settings` sheet, HDF5 `processing` / `instrument_metadata`
   groups (plus `processing_json`), mzML `userParam`s. Importing restores them into the GUI. Tick
   **Overlay raw** above the plot to compare the raw trace with the processed one. To verify
   original data is preserved through export/import, run
   `$env:PYTHONPATH='.'; .venv\Scripts\python.exe scripts\verify_raw_roundtrip.py`.
7. Use **Import...** to load a previously saved Excel, HDF5, mzML (or legacy CSV) file for review —
   this replaces the current in-memory run.

See [AGENTS.md](AGENTS.md) for architecture details relevant to future development.
