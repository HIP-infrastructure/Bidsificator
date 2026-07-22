"""Tests for the import completion UX helpers (UR-GUI-009 ticket 3).

Covers the pure state selection and report formatting, the amber status-bar
state, and the completed-with-errors dialog. Follows the house offscreen-Qt
pattern (module-scoped QApplication).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication, QStatusBar

from bidsificator.ui.import_completion import (
    CompletionState,
    ImportCompletionDialog,
    build_report_text,
    headline,
    select_completion_state,
)
from bidsificator.ui.StatusBarManager import StatusBarManager


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _summary(imported=0, failed=0, skipped=0, warnings=None, items=None, subjects_created=0):
    """Build a summary dict shaped like ImportSummary.to_dict()."""
    warnings = warnings or []
    if items is None:
        items = []
        items += [
            {"path": f"f{i}.trc", "subject": "01", "status": "imported", "reason": None}
            for i in range(imported)
        ]
        items += [
            {"path": f"bad{i}.trc", "subject": "01", "status": "failed", "reason": "boom"}
            for i in range(failed)
        ]
        items += [
            {"path": f"sk{i}.trc", "subject": "01", "status": "skipped", "reason": "missing"}
            for i in range(skipped)
        ]
    return {
        "imported": imported,
        "failed": failed,
        "skipped": skipped,
        "total": imported + failed + skipped,
        "subjects_created": subjects_created,
        "items": items,
        "warnings": warnings,
    }


class TestSelectCompletionState:
    def test_all_imported_is_success(self):
        assert select_completion_state(_summary(imported=3)) is CompletionState.SUCCESS

    def test_some_failed_is_partial(self):
        assert select_completion_state(_summary(imported=2, failed=1)) is CompletionState.PARTIAL

    def test_some_skipped_is_partial(self):
        assert select_completion_state(_summary(imported=2, skipped=1)) is CompletionState.PARTIAL

    def test_warnings_only_is_partial_when_something_imported(self):
        summary = _summary(imported=1, warnings=["contact labeling file missing"])
        assert select_completion_state(summary) is CompletionState.PARTIAL

    def test_nothing_imported_is_error(self):
        assert select_completion_state(_summary(imported=0, skipped=2)) is CompletionState.ERROR
        assert select_completion_state(_summary(imported=0, failed=2)) is CompletionState.ERROR


class TestHeadline:
    def test_singular(self):
        assert headline(_summary(imported=1), "file") == "Imported 1 of 1 file."

    def test_counts_and_problems(self):
        line = headline(_summary(imported=7, failed=2, skipped=1), "file")
        assert "Imported 7 of 10 files." in line
        assert "2 failed" in line
        assert "1 skipped" in line


class TestReportText:
    def test_lists_failed_skipped_and_warnings(self):
        summary = _summary(imported=1, failed=1, skipped=1, warnings=["contact labeling file missing"])
        text = build_report_text(summary, "file")
        assert "Failed (1):" in text
        assert "Skipped (1):" in text
        assert "Warnings (1):" in text
        assert "boom" in text
        assert "missing" in text
        assert "contact labeling file missing" in text

    def test_preserves_accented_text_utf8(self):
        summary = {
            "imported": 0, "failed": 1, "skipped": 0, "total": 1, "subjects_created": 0,
            "items": [{"path": "éEG_privé.trc", "subject": "01", "status": "failed", "reason": "conversion échouée"}],
            "warnings": [],
        }
        text = build_report_text(summary, "file")
        assert "éEG_privé.trc" in text
        assert "conversion échouée" in text


class TestStatusBarWarning:
    def test_show_warning_is_amber_with_icon(self, qapp):
        bar = QStatusBar()
        StatusBarManager(bar).show_warning("Import finished with 3 problems")
        assert "FF9800" in bar.styleSheet()
        assert StatusBarManager.ICON_WARNING in bar.currentMessage()
        assert "3 problems" in bar.currentMessage()


class TestCompletionDialog:
    def test_lists_only_problems_and_copies_report(self, qapp):
        summary = _summary(imported=1, failed=1, skipped=1, warnings=["contact file"])
        dlg = ImportCompletionDialog(None, CompletionState.PARTIAL, summary, "file")
        try:
            # 1 failed + 1 skipped + 1 warning; the imported item is not listed.
            assert dlg._list.count() == 3
            dlg._copy_details()
            clip = QApplication.clipboard().text()
            assert "Failed (1):" in clip
            assert "boom" in clip
        finally:
            dlg.deleteLater()
