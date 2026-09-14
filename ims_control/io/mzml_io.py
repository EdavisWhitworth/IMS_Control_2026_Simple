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
from xml.etree.ElementTree import Element, ElementTree, SubElement

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
