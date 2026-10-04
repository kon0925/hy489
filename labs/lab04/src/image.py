"""Stored values, real values, and what you put on a screen.

TWO STUBS IN THIS FILE: to_real_values and to_display.

Three different numbers live in a DICOM image and confusing them is the most
common imaging bug there is:

  the stored value     what is in PixelData. An integer. Means nothing on its
                       own: 24 is not a quantity of anything.
  the real value       stored * RescaleSlope + RescaleIntercept. For CT this is
                       Hounsfield units, where water is 0 and air is -1000 by
                       definition, and those two anchors are what make a CT
                       number comparable between a scanner in Heraklion and one
                       in Helsinki.
  the displayed value  the real value put through a window and, if the image is
                       MONOCHROME1, inverted. Has no units. Exists only to be
                       looked at. Never measure anything on it.
"""

import numpy as np


def to_real_values(ds):
    """STUB 5. The pixel array in real units.

    stored * RescaleSlope + RescaleIntercept, as float.

    Both tags are optional. The standard says an absent slope is 1 and an
    absent intercept is 0, so the arithmetic always works and is sometimes
    silently wrong. That is exactly what one series in this archive does, and
    Part B asks you to find it by measuring air rather than by reading tags.

    Do not clip, do not rescale to 0-255, do not touch the photometric
    interpretation. This function returns physics, not a picture.
    """
    raise NotImplementedError("Lab 4, Part B, task 1")


def to_display(ds, center=None, width=None):
    """STUB 6. The same image as something you can look at, 0.0 to 1.0.

    Four steps, in this order:

      1. real values, from to_real_values
      2. if center and width were not given, take WindowCenter and WindowWidth
         from the header, and if those are absent too, use the 1st and 99th
         percentile of the image itself
      3. window: everything at or below center - width/2 becomes 0.0,
         everything at or above center + width/2 becomes 1.0, linear between
      4. if PhotometricInterpretation is MONOCHROME1, invert: 1.0 - result

    WindowCenter and WindowWidth can both have VM greater than 1, because a
    series can ship several suggested presets. dicomio.tag gives you a tuple
    in that case; take the first.
    """
    raise NotImplementedError("Lab 4, Part B, task 2")


# ---------------------------------------------------------------------------
# written for you
# ---------------------------------------------------------------------------

def window(arr, center, width):
    """Linear window, to 0.0-1.0. Width below 1 is treated as 1."""
    width = max(float(width), 1.0)
    low = float(center) - width / 2.0
    return np.clip((np.asarray(arr, dtype=float) - low) / width, 0.0, 1.0)


def roi_mean(arr, cy, cx, r):
    """Mean of a circular region of interest, centre (cy, cx), radius r pixels.

    A measurement, so it belongs on real values and not on a display image.
    """
    arr = np.asarray(arr, dtype=float)
    yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]]
    mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    if not mask.any():
        return float("nan")
    return float(arr[mask].mean())


def corner_mean(arr, size=12):
    """Mean of the four corners.

    On a CT this is the air around the patient and it should read about
    -1000 HU. It is the cheapest check there is that a rescale was applied
    correctly, it needs no tags at all, and it is the one Part B uses to catch
    the series whose intercept is missing.
    """
    arr = np.asarray(arr, dtype=float)
    s = size
    patches = [arr[:s, :s], arr[:s, -s:], arr[-s:, :s], arr[-s:, -s:]]
    return float(np.mean([p.mean() for p in patches]))


def mm_per_pixel(ds, tag):
    """(row mm, column mm) or None if the series does not say.

    None is an answer. It means every distance you report from this image is
    in pixels, and a pixel is not a unit anybody can act on.
    """
    ps = tag(ds, "PixelSpacing")
    if ps is None:
        return None
    if isinstance(ps, (tuple, list)):
        return (float(ps[0]), float(ps[1]))
    return (float(ps), float(ps))


def distance_mm(ds, p0, p1, tag):
    """Distance between two (row, column) points, in millimetres, or None.

    Returns None rather than guessing 1.0 mm. A measurement that quietly
    assumes square millimetre pixels is worse than no measurement, because it
    arrives in a report looking like a number somebody checked.
    """
    spacing = mm_per_pixel(ds, tag)
    if spacing is None:
        return None
    dr = (p1[0] - p0[0]) * spacing[0]
    dc = (p1[1] - p0[1]) * spacing[1]
    return float(np.hypot(dr, dc))


HU_REFERENCE = [
    ("air", -1000, "by definition"),
    ("lung", -850, "-950 to -700, inflated"),
    ("fat", -90, "-120 to -60"),
    ("water", 0, "by definition"),
    ("soft tissue", 40, "20 to 60"),
    ("blood, clotted", 70, "50 to 90"),
    ("cancellous bone", 300, "100 to 500"),
    ("cortical bone", 1500, "500 to 2000"),
]


def hu_table():
    print("%-18s %8s   %s" % ("tissue", "HU", "usual range"))
    for name, value, note in HU_REFERENCE:
        print("%-18s %8d   %s" % (name, value, note))
    print()
    print("Air and water are fixed points, not measurements. A scanner that "
          "reads water as 12 HU is out of calibration, and that is what the "
          "daily QA phantom is for.")
