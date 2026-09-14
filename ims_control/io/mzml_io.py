"""Minimal hand-rolled mzML writer for IMS drift-time spectra.

Not a full-featured mzML implementation (no indexed mzML, no compression, no CV
validation against the full PSI-MS ontology) -- just enough structurally valid
mzML to be readable by common tools. Each averaged iteration becomes one
<spectrum>, with drift time (ms) written into the m/z array slot and detector
intensity into the intensity array slot.
"""

from __future__ import annotations

import base64
import struct
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement, parse

import numpy as np

from ims_control.acquisition.experiment import ExperimentConfig
from ims_control.models.data_store import DataStore

_NO_COMPRESSION = ("MS:1000576", "no compression")
_FLOAT64 = ("MS:1000523", "64-bit float")
_MZ_ARRAY = ("MS:1000514", "m/z array")
_INTENSITY_ARRAY = ("MS:1000515", "intensity array")
_MS_LEVEL = ("MS:1000511", "ms level")
_CENTROID = ("MS:1000127", "centroid spectrum")


def _cv_param(parent: Element, accession: str, name: str, value: str | None = None) -> None:
    attrs = {"cvRef": "MS", "accession": accession, "name": name}
    if value is not None:
        attrs["value"] = value
    SubElement(parent, "cvParam", attrs)


def _binary_data_array(parent: Element, values, array_type: tuple[str, str]) -> None:
    encoded = base64.b64encode(struct.pack(f"<{len(values)}d", *values)).decode("ascii")
    bda = SubElement(
        parent, "binaryDataArray", {"encodedLength": str(len(encoded))}
    )
    _cv_param(bda, *_FLOAT64)
    _cv_param(bda, *_NO_COMPRESSION)
    _cv_param(bda, *array_type)
    binary = SubElement(bda, "binary")
    binary.text = encoded


def export_mzml(store: DataStore, path: str | Path) -> None:
    mzml = Element("mzML", {"xmlns": "http://psi.hupo.org/ms/mzml", "version": "1.1.0"})

    cv_list = SubElement(mzml, "cvList", {"count": "1"})
    SubElement(
        cv_list,
        "cv",
        {"id": "MS", "fullName": "Proteomics Standards Initiative Mass Spectrometry Ontology",
         "URI": "https://raw.githubusercontent.com/HUPO-PSI/psi-ms-CV/master/psi-ms.obo"},
    )

    file_desc = SubElement(mzml, "fileDescription")
    file_content = SubElement(file_desc, "fileContent")
    _cv_param(file_content, *_CENTROID)

    run = SubElement(mzml, "run", {"id": "ims_run"})
    spectrum_list = SubElement(run, "spectrumList", {"count": str(len(store.iterations))})

    time_ms = store.time_axis_ms
    for rec in store.iterations:
        spectrum = SubElement(
            spectrum_list,
            "spectrum",
            {
                "id": f"scan={rec.index}",
                "index": str(rec.index),
                "defaultArrayLength": str(len(rec.intensity)),
            },
        )
        _cv_param(spectrum, _MS_LEVEL[0], _MS_LEVEL[1], value="1")
        _cv_param(spectrum, *_CENTROID)

        binary_data_array_list = SubElement(
            spectrum, "binaryDataArrayList", {"count": "2"}
        )
        _binary_data_array(binary_data_array_list, list(time_ms), _MZ_ARRAY)
        _binary_data_array(binary_data_array_list, list(rec.intensity), _INTENSITY_ARRAY)

    ElementTree(mzml).write(path, xml_declaration=True, encoding="UTF-8")


def _local_tag(element: Element) -> str:
    """Strip the `{namespace}` prefix ElementTree adds when a default xmlns is declared."""
    return element.tag.rsplit("}", 1)[-1]


def _decode_binary_data_array(bda: Element) -> tuple[str, list[float]]:
    array_type = None
    for cv_param in bda:
        if _local_tag(cv_param) == "cvParam" and cv_param.get("accession") in (
            _MZ_ARRAY[0],
            _INTENSITY_ARRAY[0],
        ):
            array_type = cv_param.get("accession")
    binary_text = next(child.text for child in bda if _local_tag(child) == "binary")
    raw = base64.b64decode(binary_text or "")
    values = list(struct.unpack(f"<{len(raw) // 8}d", raw))
    return array_type, values


def import_mzml(path: str | Path) -> DataStore:
    """Rebuild a DataStore from an mzML file written by `export_mzml`. Instrument/ion
    metadata is not stored in mzML, so the resulting ExperimentConfig uses default
    metadata values -- edit the metadata fields in the GUI afterward to get correct
    K0/CCS on any recomputation. No peak data is stored in mzML either."""
    root = parse(path).getroot()
    spectra = [el for el in root.iter() if _local_tag(el) == "spectrum"]

    time_ms: list[float] | None = None
    intensities: list[tuple[int, list[float]]] = []
    for spectrum in spectra:
        index = int(spectrum.get("index", "0"))
        binary_data_array_list = next(
            child for child in spectrum if _local_tag(child) == "binaryDataArrayList"
        )
        mz_values = intensity_values = None
        for bda in binary_data_array_list:
            array_type, values = _decode_binary_data_array(bda)
            if array_type == _MZ_ARRAY[0]:
                mz_values = values
            elif array_type == _INTENSITY_ARRAY[0]:
                intensity_values = values
        if time_ms is None:
            time_ms = mz_values
        intensities.append((index, intensity_values))

    if time_ms is None:
        raise ValueError(f"No spectra found in mzML file: {path}")

    num_points = len(time_ms)
    # DataStore.time_axis_ms = arange(num_points)/sample_rate*1000 with sample_rate =
    # num_points/(exp_length_ms/1000), i.e. dt = exp_length_ms/num_points -- so recover
    # exp_length_ms from the sample spacing, not from (last - first) time.
    dt_ms = float(time_ms[1] - time_ms[0]) if num_points > 1 else 1.0
    exp_length_ms = dt_ms * num_points
    config = ExperimentConfig(exp_length_ms=exp_length_ms, num_points=num_points)
    store = DataStore(config)
    for index, values in intensities:
        store.add_iteration(index, np.array(values))
    return store
