"""Order-independent subject lookup-table application.

Regression: loading the lookup table AFTER clicking Parse left the already-parsed
subjects un-anonymized — ``set_lookup_table`` stored the mapping but never
re-applied it to loaded subjects, so the display (and the eventual ``sub-<id>``)
stayed on the original folder names. The mapping is now re-applied in place
(``SubjectDataModel.reapply_subject_mapping``) so order does not matter and
per-subject file edits are preserved. The formatting is shared with crawl-time
mapping via ``DataCrawlerService.format_mapped_subject``.
"""

from bidsificator.models.SubjectDataModel import SubjectDataModel
from bidsificator.services.DataCrawlerService import DataCrawlerService


class TestFormatMappedSubject:
    def test_no_mapping_keeps_original(self):
        assert DataCrawlerService.format_mapped_subject("PAT_1", None) == ("PAT_1", "PAT_1")
        assert DataCrawlerService.format_mapped_subject("PAT_1", {}) == ("PAT_1", "PAT_1")

    def test_missing_key_keeps_original(self):
        assert DataCrawlerService.format_mapped_subject("PAT_1", {"OTHER": "X"}) == ("PAT_1", "PAT_1")

    def test_custom_alphanumeric(self):
        assert DataCrawlerService.format_mapped_subject(
            "PAT_1", {"PAT_1": "CHUV001"}
        ) == ("CHUV001", "PAT_1 [CHUV001]")

    def test_numeric_seven_digits_split(self):
        mapped, display = DataCrawlerService.format_mapped_subject("PAT_1", {"PAT_1": "0010123"})
        assert mapped == "0010123"
        assert display == "PAT_1 [001-0123]"


class TestReapplySubjectMapping:
    def _model(self):
        m = SubjectDataModel()
        m.load_from_legacy_format([
            {
                "subject_id": "LYON_A",
                "original_subject_id": "LYON_A",
                "display_name": "LYON_A",
                "files": [{"file_path": "/a.nii", "modality": "T1w (anat)"}],
            },
            {
                "subject_id": "LYON_B",
                "original_subject_id": "LYON_B",
                "display_name": "LYON_B",
                "files": [],
            },
        ])
        return m

    def test_reapply_maps_ids_and_display_and_keeps_files(self):
        m = self._model()
        m.reapply_subject_mapping({"LYON_A": "CHUV001", "LYON_B": "CHUV002"})
        assert m.get_subject_ids() == ["CHUV001", "CHUV002"]
        assert m.get_display_names() == ["LYON_A [CHUV001]", "LYON_B [CHUV002]"]
        # File edits are preserved (in-place re-map, no re-crawl).
        assert m.subjects[0].files == [{"file_path": "/a.nii", "modality": "T1w (anat)"}]

    def test_reapply_empty_reverts_to_original(self):
        m = self._model()
        m.reapply_subject_mapping({"LYON_A": "CHUV001", "LYON_B": "CHUV002"})
        m.reapply_subject_mapping({})  # clear the lookup table
        assert m.get_subject_ids() == ["LYON_A", "LYON_B"]
        assert m.get_display_names() == ["LYON_A", "LYON_B"]

    def test_reapply_is_idempotent_and_partial(self):
        m = self._model()
        # Only one subject mapped; the other keeps its original name.
        m.reapply_subject_mapping({"LYON_A": "CHUV001"})
        m.reapply_subject_mapping({"LYON_A": "CHUV001"})  # again — must not double-map
        assert m.get_subject_ids() == ["CHUV001", "LYON_B"]
        assert m.get_display_names() == ["LYON_A [CHUV001]", "LYON_B"]
