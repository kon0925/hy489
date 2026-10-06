"""The identifiers header editing does not reach.

ONE STUB IN THIS FILE: blank_region. Everything else is written for you.

Week 8 said it and Lab 4 found it: one object in this archive has the
patient's name drawn into the pixel data. Every attribute in profile.py can be
removed, the file can be checked by a conformance tool, and the name is still
legible to anybody who opens the image.

PS3.15 has an option for this, the Clean Pixel Data Option, code 113101 in
CID 7050. The option says the identifying information has been removed from
the pixels. It does not say how, because there is no how that works in
general. What exists is:

  a fixed region, blanked, when the layout of the modality is known and stable
  OCR, which finds most text and misses some
  not releasing the object at all

The third one is the only one with no false negatives, and it is a real
answer. An archive that drops every secondary capture loses screen grabs and
keeps the primary acquisitions, which for most research questions costs
nothing.
"""

import numpy as np


def blank_region(arr, box, fill=0):
    """STUB 5. Remove a rectangle of pixels.

    arr is the pixel array as read, box is (row0, row1, col0, col1) with the
    end points included, and fill is what goes in. Returns a new array of the
    same dtype and shape. Do not modify arr in place: Part C compares the two.

    Yours to decide:

      the fill value      0 is black on MONOCHROME2 and white on MONOCHROME1.
                          A constant rectangle is visibly a redaction, which
                          is honest and tells the next reader that something
                          was there. Filling with the surrounding background
                          hides the redaction and hides that the object was
                          ever annotated.

      the margin          the detector finds the pixels that are lit. Glyph
                          antialiasing, a drop shadow or a second line of text
                          below the threshold are not lit. Decide how much
                          beyond the box to take and say why.

      what else to blank  the box found in this archive is one band at the top
                          of one image. Blanking a band is not the same as
                          certifying the image.

    The dtype matters. These are uint8 here and int16 elsewhere, and writing a
    float array back into PixelData produces a file that reads as noise.
    """
    raise NotImplementedError("Lab 5, Part B, task 3")


# ---------------------------------------------------------------------------
# written for you
# ---------------------------------------------------------------------------

def declares_burned_in(ds):
    """What the header claims about its own pixels.

    BurnedInAnnotation (0028,0301) is YES, NO, or absent. Absent is the common
    case and it means nothing at all: most scanners never write the tag. An
    archive that trusts this attribute to find its annotated images will find
    the ones that were honest.
    """
    value = ds.get("BurnedInAnnotation", None)
    return None if value is None else str(value).strip().upper()


def find_annotation_band(arr, saturation=0.995, min_run=4, min_pixels=8,
                         margin=2):
    """Find a horizontal band of saturated pixels, or None.

    Returns (row0, row1, col0, col1), end points included, with margin added
    on every side and clipped to the image.

    How it works: text burned into an image by a console is drawn at or near
    the maximum value of the pixel range, because it has to stay legible under
    any window. So count, per row, how many pixels sit above saturation of the
    observed range. Rows of text have many, rows of anatomy have few or none.
    Take the longest run of rows above min_pixels, require it to be at least
    min_run rows tall, and take the column extent of the saturated pixels
    inside it.

    What this does not do. It finds one band. It finds text that saturates and
    not text drawn in mid-grey. It has no idea whether the text is a name, a
    date, a laterality marker or the scanner's own logo, and blanking the
    laterality marker off an image destroys clinical information. It is the
    cheap version of a problem whose expensive version is OCR and whose honest
    version is not releasing the object.
    """
    a = np.asarray(arr)
    if a.ndim != 2:
        return None
    lo, hi = float(a.min()), float(a.max())
    if hi <= lo:
        return None
    threshold = lo + (hi - lo) * saturation
    hot = a >= threshold
    per_row = hot.sum(axis=1)

    best, run_start = None, None
    for i, n in enumerate(list(per_row) + [0]):
        if n >= min_pixels and run_start is None:
            run_start = i
        elif n < min_pixels and run_start is not None:
            length = i - run_start
            if best is None or length > best[1] - best[0]:
                best = (run_start, i)
            run_start = None
    if best is None or (best[1] - best[0]) < min_run:
        return None

    r0, r1 = best[0], best[1] - 1
    cols = np.nonzero(hot[r0:r1 + 1].any(axis=0))[0]
    if cols.size == 0:
        return None
    c0, c1 = int(cols.min()), int(cols.max())

    r0 = max(0, r0 - margin)
    c0 = max(0, c0 - margin)
    r1 = min(a.shape[0] - 1, r1 + margin)
    c1 = min(a.shape[1] - 1, c1 + margin)
    return (r0, r1, c0, c1)


def band_report(arr, box):
    """One line about what was found, for the notebook and the report."""
    if box is None:
        return "no saturated band found"
    r0, r1, c0, c1 = box
    a = np.asarray(arr)
    patch = a[r0:r1 + 1, c0:c1 + 1]
    return ("rows %d-%d, columns %d-%d, %d pixels, %.1f%% of the image, "
            "%d of them at the maximum value %g"
            % (r0, r1, c0, c1, patch.size, 100.0 * patch.size / a.size,
               int((patch >= a.max()).sum()), float(a.max())))


def write_pixels(ds, arr):
    """Put an array back into a dataset, keeping the encoding it had.

    PixelData is bytes and the bytes are interpreted through BitsAllocated,
    PixelRepresentation, Rows and Columns. Change the array's dtype and the
    file still parses and shows noise, which is the failure that looks like a
    corrupt disk and is not.
    """
    signed = int(ds.get("PixelRepresentation", 0)) == 1
    bits = int(ds.get("BitsAllocated", 16))
    if bits == 8:
        dtype = np.int8 if signed else np.uint8
    else:
        dtype = np.int16 if signed else np.uint16
    data = np.asarray(arr).astype(dtype)
    if data.shape != (int(ds.Rows), int(ds.Columns)):
        raise ValueError("array is %s and the header says %sx%s"
                         % (data.shape, ds.Rows, ds.Columns))
    ds.PixelData = data.tobytes()
    return ds
