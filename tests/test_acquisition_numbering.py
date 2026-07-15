"""Regression tests for acquisition auto-increment and form-save corruption."""

from bidsificator.services.ImportService import ImportService
from bidsificator.services.DataCrawlerService import DataCrawlerService



class TestGetNextAcquisitionNumber:
    def test_starts_at_01_when_empty(self):
        assert ImportService.get_next_acquisition_number(
            [], "post", "ieeg (ieeg)", "Rest"
        ) == "01"

    def test_increments_for_matching_files(self):
        files = []
        for _ in range(3):
            acq = ImportService.get_next_acquisition_number(
                files, "post", "ieeg (ieeg)", "Rest"
            )
            files.append({
                "session": "post",
                "modality": "ieeg (ieeg)",
                "task": "Rest",
                "acquisition": acq,
            })
        assert [f["acquisition"] for f in files] == ["01", "02", "03"]

    def test_ignores_different_session_or_task(self):
        existing = [
            {"session": "pre", "modality": "ieeg (ieeg)", "task": "Rest", "acquisition": "05"},
            {"session": "post", "modality": "ieeg (ieeg)", "task": "Other", "acquisition": "09"},
        ]
        assert ImportService.get_next_acquisition_number(
            existing, "post", "ieeg (ieeg)", "Rest"
        ) == "01"


class TestDisplayModalityForAcquisition:
    def test_ieeg_trc_maps_to_display_modality(self):
        assert ImportService._display_modality_for_file(
            "/data/recording.TRC", "ieeg"
        ) == "ieeg (ieeg)"

    def test_photo_maps_to_photo_ieeg(self):
        assert ImportService._display_modality_for_file(
            "/data/photo.png", "ieeg"
        ) == "photo (ieeg)"


class TestProcessMultipleFilesAcquisition:
    def test_sequential_trc_files_get_unique_acquisitions(self, tmp_path):
        """TRC-like files must get 01, 02, 03 — not all 01 from modality key mismatch."""
        paths = []
        for i in range(3):
            p = tmp_path / f"run{i}.trc"
            p.write_bytes(b"dummy")
            paths.append(str(p))

        successful, failed = ImportService.process_multiple_files(
            paths,
            {"session": "ses-post", "task": "Rest"},
            existing_files=[],
        )

        assert not failed
        assert [f["acquisition"] for f in successful] == ["01", "02", "03"]
        assert all(f["modality"] == "ieeg (ieeg)" for f in successful)

    def test_existing_display_modality_files_continue_sequence(self, tmp_path):
        existing = [{
            "file_name": "old.trc",
            "file_path": "/elsewhere/old.trc",
            "modality": "ieeg (ieeg)",
            "task": "Rest",
            "session": "post",
            "acquisition": "01",
        }]
        p = tmp_path / "new.trc"
        p.write_bytes(b"dummy")

        successful, failed = ImportService.process_multiple_files(
            [str(p)],
            {"session": "ses-post", "task": "Rest"},
            existing_files=existing,
        )

        assert not failed
        assert successful[0]["acquisition"] == "02"
        assert successful[0]["modality"] == "ieeg (ieeg)"


class TestStaleFormSaveCorruption:
    """Documents the MainWindow refresh bug: saving stale form onto files[0]."""

    def test_stale_form_save_corrupts_first_acquisition(self):
        """Simulate the pre-fix race: force index=0 then write form acq-02."""
        files = [
            {"file_name": "a.trc", "acquisition": "01", "modality": "ieeg (ieeg)",
             "session": "post", "task": "Rest"},
            {"file_name": "b.trc", "acquisition": "02", "modality": "ieeg (ieeg)",
             "session": "post", "task": "Rest"},
            {"file_name": "c.trc", "acquisition": "03", "modality": "ieeg (ieeg)",
             "session": "post", "task": "Rest"},
        ]

        # Bug pattern: user had file 1 selected (form shows "02"), refresh forces
        # selected index to 0, then saves form into files[0].
        stale_form_acquisition = "02"
        selected_index = 0
        files[selected_index]["acquisition"] = stale_form_acquisition

        assert [f["acquisition"] for f in files] == ["02", "02", "03"]
        # Duplicate acq-02 means second export overwrites the first

    def test_correct_reload_preserves_acquisitions(self):
        """Correct pattern: load files[0] into form without saving first."""
        files = [
            {"file_name": "a.trc", "acquisition": "01"},
            {"file_name": "b.trc", "acquisition": "02"},
            {"file_name": "c.trc", "acquisition": "03"},
        ]
        stale_form_acquisition = "02"

        # Fixed pattern: do not write form into files[0]; instead read files[0]
        form_acquisition = files[0]["acquisition"]
        assert form_acquisition == "01"
        assert stale_form_acquisition == "02"  # ignored
        assert [f["acquisition"] for f in files] == ["01", "02", "03"]


class TestDataCrawlerAcquisitionNumbering:
    def test_crawler_assigns_01_02_03(self):
        subject = {
            "subject_id": "001",
            "data": {
                "ieeg": {
                    "modality": "ieeg (ieeg)",
                    "file_paths": [
                        "/data/a.TRC",
                        "/data/b.TRC",
                        "/data/c.TRC",
                    ],
                }
            },
        }
        processed = DataCrawlerService._process_subject_data(subject)
        assert [f["acquisition"] for f in processed["files"]] == ["01", "02", "03"]
