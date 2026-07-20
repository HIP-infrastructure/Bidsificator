"""Shared constants for the worker → GUI progress pipe.

Both import workers (the ``QThread`` side) and their subprocess processors
exchange integers over a ``multiprocessing`` pipe. Ordinary values are 0–100
progress percentages; these name the two sentinels that are not.
"""

PROGRESS_DONE = 101   # processor finished successfully
PROGRESS_ERROR = -1   # processor hit an unrecoverable error and bailed out
