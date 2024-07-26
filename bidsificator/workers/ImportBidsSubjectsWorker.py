import multiprocessing as mp

from PyQt6.QtCore import pyqtSignal, QThread

from .BidsSubjectsProcess import processBidsSubjects

class ImportBidsSubjectsWorker(QThread):
    update_progressbar_signal = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, dataset_path: str, subject_list: str):
        super().__init__()
        self.dataset_path = dataset_path
        self.subject_list = subject_list
        self.anatomical_modalities = {"T1w (anat)", "T2w (anat)", "T1rho (anat)", "T2* (anat)", "FLAIR (anat)", "CT (anat)"}

    def run(self):
        parent_conn, child_conn = mp.Pipe()
        process = mp.Process(target=processBidsSubjects, args=(child_conn, self.dataset_path, self.subject_list, self.anatomical_modalities))
        process.start()

        while True:
            progress = parent_conn.recv()  # Wait for progress update
            if progress == 101:  # Check for completion
                break
            elif progress < 0:  # Check for error
                print("Error in processing files")
                break
            else:
                self.update_progressbar_signal.emit(progress)

        process.join()  # Ensure the process has completed

        self.finished.emit()
