# AGENTS.md — IMS Control (agent-facing architecture reference)

This file orients an AI coding agent (or new contributor) making future changes to this
repository. It describes intent, module boundaries, and conventions — read this before
modifying acquisition, DAQ, or processing code.

## Purpose

Control software for a drift-tube ion mobility spectrometer (IMS) built around an
NI USB-6351 (or similar NI-DAQmx X-Series) DAQ. Operators (often undergraduate students)
configure an experiment, run it, watch live/past spectra and a full-run heatmap, review
auto-picked peaks with derived parameters, and export data.

## Architecture overview

```
main.py                        entry point, launches MainWindow
ims_control/
  daq/                         hardware abstraction — swap backends without touching acquisition/GUI code
    base.py                    DAQBackend ABC: configure(), acquire_one(), close()
    ni_daq.py                  real NI-DAQmx backend (nidaqmx); optional import, raises RuntimeError if unavailable
    simulator.py                SimulatedDAQBackend — synthetic Gaussian-peak traces, no hardware required
    power_supply.py             PowerSupplyBackend ABC + NIPowerSupplyBackend/SimulatedPowerSupplyBackend —
                                 IMS cell / Ionization AO setpoints (0-10 V) and shared enable+LED DO pair
  acquisition/
    experiment.py               ExperimentConfig dataclass (per-run params) + SystemParameters dataclass
                                 (DAQ channels, power-supply channels/scaling — edited rarely, via a dialog)
    controller.py                AcquisitionWorker(QThread) — runs the iterate/average acquisition loop, start/stop/pause
  models/
    data_store.py                DataStore/IterationRecord — in-memory results (raw spectra + picked peaks) for one run
  processing/
    baseline.py                  noise-window mean/std (SNR denominator), default = last 10 ms of trace
    peak_picking.py               scipy find_peaks/peak_widths wrapper; computes FWHM, resolving power, SNR, K0, CCS
  io/
    csv_io.py / hdf5_io.py / mzml_io.py   export (and for HDF5, import) of a DataStore
    settings_io.py                save/load operator defaults (ExperimentConfig + SystemParameters +
                                   simulator flag + kV setpoints) as JSON at ~/.ims_control/defaults.json
  gui/
    control_panel.py             experiment parameter form, power-supply kV controls + on/off toggle,
                                  "System Parameters..." and "Save Current as Defaults" buttons, Start/Stop/Pause
    system_parameters_dialog.py  modal dialog for DAQ channel assignments + power-supply channels/max kV
    plot_panel.py                 X/Y line plot, selector for "current (live)" vs any past iteration
    heatmap_panel.py               2D colormap of all iterations (ImageItem + HistogramLUTItem, "spectrum" preset)
    peak_table.py                  table of picked-peak parameters for the selected iteration
    main_window.py                 wires everything together; owns the DataStore, AcquisitionWorker, and
                                    PowerSupplyBackend; sets the window background green/red for power off/on
tests/                           pytest suite — uses SimulatedDAQBackend exclusively (no hardware needed)
```

## Key design decisions (do not silently change these)

- **DAQBackend is the only hardware boundary.** Acquisition, GUI, and processing code
  must never import `nidaqmx` directly — only `ims_control/daq/ni_daq.py` does, and that
  import is wrapped in `try/except ImportError` so the app still launches (simulator-only)
  on machines without the NI-DAQmx driver installed.
- **Gate pulse timing**: the ion gate pulse is generated as a free-running, continuous
  pulse train on a DAQ counter-output (CO) channel at the experiment repetition rate
  (`exp_length_ms`); the AI task uses that pulse's internal output terminal as a
  *retriggerable* digital-edge start trigger, so it auto-rearms after each replicate.
  Both tasks are started once in `configure()`; `acquire_one()` only reads -- it must
  never call `task.start()`/`task.stop()` per replicate, since NI-DAQmx task
  start/stop over USB adds tens of ms of overhead per call and will inflate the pulse
  period well beyond `exp_length_ms` if done every replicate.
  Sample rate is always derived as `num_points / (exp_length_ms / 1000)` — never hardcode it.
- **One "iteration"** = `averages` replicate acquisitions, averaged together in software
  (accumulate then divide) before being emitted to the GUI/data store. Iterations are the
  unit shown in the heatmap and iteration selector.
- **AcquisitionWorker runs on a QThread**, never on the GUI thread. Stop is cooperative —
  checked between replicate acquisitions via `QThread.requestInterruption()` (mid-replicate
  is not interruptible). Pause blocks between replicates via a mutex-guarded flag, polled
  with short sleeps.
- **Peak parameters** (`ims_control/processing/peak_picking.py`):
  - FWHM via `scipy.signal.peak_widths(rel_height=0.5)`.
  - Resolving power = drift time / FWHM.
  - SNR = peak height / baseline std, where baseline std comes from a noise window
    (default: last 10 ms of the trace — same convention as the sibling
    IMSDataAnalysis2026 repo).
  - K0 (reduced mobility): `K0 = (L^2 / (V * t_d)) * (P/760) * (273.15/T)`.
  - CCS (Mason-Schamp): requires ion m/z + charge (operator-entered per run); returns
    `None` when `ion_mz <= 0` so the GUI/exports can show "CCS unavailable" rather than a
    bogus number. Ion neutral mass is approximated as `m/z * charge` (electron mass ignored).
  - Buffer gas masses are looked up from `GAS_MASSES_AMU` in `peak_picking.py` — add new
    gases there, keyed by uppercase symbol, matching the `ControlPanel` gas combo box entries.
  - Changing any K0/CCS metadata field (drift length/voltage, P, T, gas, ion m/z/charge) emits
    `ControlPanel.metadata_changed`; `MainWindow._on_metadata_changed` updates `store.config`
    in place and recomputes peaks for **every** stored iteration, live or idle, so displayed
    parameters always reflect the current fields rather than the values at Start time.
- **mzML export is intentionally minimal** — hand-rolled (no `psims` dependency), one
  `<spectrum>` per averaged iteration, drift time (ms) written into the m/z array slot and
  detector signal into the intensity array slot. Not indexed mzML; not validated against
  the full PSI-MS CV. If a downstream tool needs stricter schema compliance, revisit with
  a real mzML library rather than extending the hand-rolled writer indefinitely.
- **DAQ channel names are always user-configurable** (GUI text fields in `ControlPanel`),
  never hardcoded constants — different instruments/rewiring should not require code changes.
- **Power supplies (IMS cell / Ionization)**: `ims_control/daq/power_supply.py` defines
  `PowerSupplyBackend` (simulated + real NI-DAQmx). Operator kV setpoints are scaled to
  0-10 V analog outputs via `kv_to_volts(kv, max_kv)`; `max_kv` for each supply lives in
  `SystemParameters`, edited via the System Parameters dialog. A single "Power" toggle in
  `ControlPanel` drives both supplies together through **one** shared DO line
  (`SystemParameters.power_do_channel`) that both enables the supplies and drives the
  external indicator LED (`PowerSupplyBackend.set_enabled`) — do not split this into
  separate enable/LED channels or separate buttons.
  The Ionization control is a **bias on top of** the IMS cell output (e.g. IMS cell at
  10 kV + Ionization bias at 3 kV means the ionization supply's true output is 13 kV).
  Software computes this sum explicitly: `MainWindow` adds the IMS cell kV to the operator's
  bias setpoint before calling `PowerSupplyBackend.set_ionization_output_kv()`, which then
  scales the combined total to 0-10 V — the ionization AO channel always represents the
  supply's absolute output, never the bias alone. Do not revert to writing the bias value
  directly to the ionization AO channel.
  The power-supply hardware backend is selected by its own `power_simulator_checkbox` in
  `ControlPanel`, deliberately **independent** of the acquisition `simulator_checkbox` —
  do not reuse the acquisition simulator flag for power, or real hardware never gets
  the DO/AO writes even when the operator thinks they've enabled "real mode".
  `ControlPanel.set_power_indicator()` colors only the Power toggle button itself
  (green = off, red = on) — the window background is intentionally left neutral.
  `MainWindow` warns (not blocks) if the operator starts a run with power off.
  Unlike the AI/CO acquisition tasks, AO/DO writes for the power supplies are infrequent
  (spinbox changes, one toggle click) so `NIPowerSupplyBackend` opens/closes a short-lived
  `nidaqmx.Task()` per write rather than keeping persistent armed tasks.
- **Saved defaults** (`ims_control/io/settings_io.py`): "Save Current as Defaults" persists the
  current `ExperimentConfig`, `SystemParameters`, simulator-mode flag, and kV setpoints to
  `~/.ims_control/defaults.json`; `MainWindow` loads this at startup if present. Loading defaults
  must never itself write to hardware or enable power — kV spinboxes are populated with
  `blockSignals` so restoring a saved setpoint doesn't trigger an AO write before the operator
  explicitly interacts with power controls.

## Working with hardware

The agent cannot execute code against a physical USB-6351. `NIDAQBackend` should be
reviewed carefully for correctness (channel naming, trigger routing, timing config) but
verified experimentally by the human operator on the real instrument. Prefer adding/
extending simulator-based tests over ones that assume real hardware is present.

## Adding a new derived peak parameter

1. Add the computation to `ims_control/processing/peak_picking.py` (either inline in
   `pick_peaks` or as a standalone function it calls).
2. Add the field to `PeakResult`.
3. Add a column to `_COLUMNS` in `ims_control/gui/peak_table.py`.
4. Add the field name to `fieldnames` in `ims_control/io/csv_io.py::export_peaks_csv`.
5. Add/extend a unit test in `tests/test_peak_picking.py` with a known expected value.

## Running tests

```
& ".venv/Scripts/python.exe" -m pytest tests -q
```

All tests use `SimulatedDAQBackend` — no NI-DAQmx driver or hardware is required to run
the suite or to develop most of the application.
