"""bgchange: replace the background of a person/product photo with a solid colour.

The package is a pipeline: one folder per step, numbered in the order a photo
goes through them, so each one can be read, tested and swapped on its own:

    s1_load_photo/       open the photo safely (EXIF rotation, colour modes, alpha)
    s2_read_color/       "#FF0066" -> Color(255, 0, 102)
    s3_ai_models/        the 5 AI models; each one only predicts the mask
    s4_shadow/           (later) keep the subject's shadow
    s5_new_background/   clean the edges, mix photo + colour with the mask, save

    benchmark/           not part of the pipeline: tests which model is best

The command (scripts/change_background.py) and, later, the web API are thin
wrappers around these steps, so both always produce identical results.
"""

__version__ = "0.1.0"
