import logging
import multiprocessing as mp

from PyQt6.QtCore import QThread, pyqtSignal

from .BidsSubjectsProcess import processBidsSubjects
from .import_processor import ImportSummary, MessageKind, classify_message

logger = logging.getLogger(__name__)


class ImportBidsSubjectsWorker(QThread):
    update_progressbar_signal = pyqtSignal(int)
    # Carries the ImportSummary from the finished import. Named distinctly (not
    # `finished`) so it does not shadow QThread.finished.
    import_finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, dataset_path: str, subject_list: str, overwrite_existing: bool = False, task: str = "Rest"):
        super().__init__()
        self.dataset_path = dataset_path
        self.subject_list = subject_list
        self.overwrite_existing = overwrite_existing
        self.task = task

    def run(self):
        parent_conn, child_conn = mp.Pipe()
        process = mp.Process(
            target=processBidsSubjects,
            args=(child_conn, self.dataset_path, self.subject_list,
                  self.overwrite_existing, self.task),
        )
        process.start()

        failed = False
        summary = ImportSummary()
        while True:
            # Poll with a timeout instead of a blocking recv(): a child that dies
            # without writing (crash, OOM kill) would otherwise hang the GUI forever.
            if not parent_conn.poll(timeout=5):
                if not process.is_alive():
                    failed = True
                    logger.error("Import process terminated unexpectedly")
                    self.error.emit("Import process terminated unexpectedly")
                    break
                continue  # still working, keep waiting

            message = parent_conn.recv()
            # Classify by type BEFORE any ordering comparison: a non-int terminal
            # message would otherwise raise TypeError here and hang the UI.
            kind = classify_message(message)
            if kind is MessageKind.SUMMARY:
                summary = message
                break
            elif kind is MessageKind.DONE:
                break  # legacy bare completion sentinel: empty summary
            elif kind is MessageKind.ERROR:
                failed = True
                logger.error("Import process reported an error")
                self.error.emit("Error while processing subjects (see log for details)")
                break
            elif kind is MessageKind.PROGRESS:
                self.update_progressbar_signal.emit(message)
            else:  # MessageKind.UNKNOWN
                failed = True
                logger.error("Import process sent an unrecognized message: %r", message)
                self.error.emit("Import process sent an unrecognized message (see log for details)")
                break

        process.join()
        if not failed:
            self.import_finished.emit(summary)
