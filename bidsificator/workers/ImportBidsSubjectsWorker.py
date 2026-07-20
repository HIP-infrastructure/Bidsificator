import logging
import multiprocessing as mp

from PyQt6.QtCore import QThread, pyqtSignal

from .BidsSubjectsProcess import processBidsSubjects
from .import_processor import PROGRESS_DONE, PROGRESS_ERROR

logger = logging.getLogger(__name__)


class ImportBidsSubjectsWorker(QThread):
    update_progressbar_signal = pyqtSignal(int)
    finished = pyqtSignal()
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

            progress = parent_conn.recv()
            if progress == PROGRESS_DONE:
                break
            elif progress <= PROGRESS_ERROR:
                failed = True
                logger.error("Import process reported an error")
                self.error.emit("Error while processing subjects (see log for details)")
                break
            else:
                self.update_progressbar_signal.emit(progress)

        process.join()
        if not failed:
            self.finished.emit()
