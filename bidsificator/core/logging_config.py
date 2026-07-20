"""Central logging configuration for the application.

Call :func:`setup_logging` once from each entry point (the GUI ``main``, the API
``main``, and each worker subprocess). Modules elsewhere should just do
``logger = logging.getLogger(__name__)`` and log against that — they must not
configure handlers themselves.
"""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger for the current process.

    Safe to call from worker subprocesses: ``multiprocessing`` starts a fresh
    interpreter per process, so each configures its own root logger. ``force``
    replaces any handlers a dependency may have installed at import time so our
    format and level win.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )
