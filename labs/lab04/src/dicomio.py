"""Reading files off an archive without trusting any of it.

Written for you. Nothing in this file is a stub.

The one idea here: a folder of DICOM files is not a tidy data structure. Some
of the files are not DICOM, some are truncated, some are missing the tags you
were going to index on, and the folder names mean whatever the person doing the
migration felt like that afternoon. Every function below assumes that and
returns something usable instead of raising.
"""

import os

import pydicom
from pydicom.multival import MultiValue


def walk(root):
    """Every file under root, in a stable order, folders included.

    Sorted so that two students comparing output are comparing the same thing.
    """
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            out.append(os.path.join(dirpath, name))
    return out


def read_header(path):
    """Read the metadata of one file.

    Returns (dataset, None) on success and (None, reason) on failure. It never
    raises, because the point of Part A is that you find out how many files
    fail and why, not that your loop stops at the first one.

    Pixel data is not read. That is deliberate and it is also a trap: a file
    whose pixels are corrupt reads perfectly well here. See read_pixels.
    """
    try:
        ds = pydicom.dcmread(path, stop_before_pixels=True)
        return ds, None
    except pydicom.errors.InvalidDicomError:
        return None, "not DICOM"
    except Exception as exc:                      # noqa: BLE001
        return None, "%s: %s" % (type(exc).__name__, exc)


def read_pixels(path):
    """Read one file including its pixel data.

    Returns (dataset, None) or (None, reason). A dataset that has no PixelData
    at all, a structured report for instance, comes back as a success with
    ds.get("PixelData") of None. That is not an error and must not be counted
    as one.
    """
    try:
        ds = pydicom.dcmread(path)
        if "PixelData" in ds:
            _ = ds.pixel_array                    # force the decode to happen here
        return ds, None
    except pydicom.errors.InvalidDicomError:
        return None, "not DICOM"
    except Exception as exc:                      # noqa: BLE001
        return None, "%s: %s" % (type(exc).__name__, exc)


def tag(ds, name, default=None):
    """Read one tag and give back something you can put in a table.

    DICOM string types come back as pydicom wrapper objects, numbers come back
    as DSfloat and IS, and anything with a VM above one comes back as a
    MultiValue. A dataframe built straight out of those is miserable to work
    with, so everything here is flattened to str, float, int, tuple or None.

    An absent tag and an empty tag both give the default. In DICOM those two
    are different things (type 2 attributes are present and empty on purpose)
    and for the inventory the difference does not help.
    """
    if ds is None or name not in ds:
        return default
    value = ds.get(name)
    if value is None or value == "":
        return default
    if isinstance(value, MultiValue):
        return tuple(_scalar(v) for v in value)
    return _scalar(value)


def _scalar(v):
    try:
        import pydicom.valuerep as vr
        if isinstance(v, vr.DSfloat):
            return float(v)
        if isinstance(v, vr.IS):
            return int(v)
        if isinstance(v, vr.PersonName):
            return str(v)
    except Exception:                             # noqa: BLE001
        pass
    if isinstance(v, (int, float)):
        return v
    return str(v)


def relname(path, root):
    """The path as you would write it in a report: relative, forward slashes."""
    return os.path.relpath(path, root).replace(os.sep, "/")
