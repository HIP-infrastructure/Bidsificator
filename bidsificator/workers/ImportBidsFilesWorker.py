import multiprocessing as mp
from PyQt6.QtCore import pyqtSignal, QThread
from workers.BidsFilesProcss import processBidsFiles

class ImportBidsFilesWorker(QThread):
    update_progressbar_signal = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, dataset_path, subject_name, file_list):
        super().__init__()
        self.dataset_path = dataset_path
        self.subject_name = subject_name
        self.file_list = file_list
        self.anatomical_modalities = {"T1w (anat)", "T2w (anat)", "T1rho (anat)", "T2rho (anat)", "FLAIR (anat)"}

    def run(self):
        parent_conn, child_conn = mp.Pipe()
        process = mp.Process(target=processBidsFiles, args=(child_conn, self.dataset_path, self.subject_name, self.file_list, self.anatomical_modalities))
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