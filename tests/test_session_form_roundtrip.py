"""Regression tests for the import form session round-trip.

Bug: loading a session-less file into the import form displayed 'ses-post'
instead of an empty session. The form save on import start (or on file
selection / session combobox repopulation) then wrote session='post' back onto
the currently selected file only, sending files[0] to ses-post/ with acq-01
while its siblings stayed session-less as acq-02/03.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication, QComboBox

from bidsificator.ui.MainWindow import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _SessionComboHolder:
    """Minimal stand-in for MainWindow exposing only SessionComboBox."""

    def __init__(self):
        self.SessionComboBox = QComboBox()
        self.SessionComboBox.setEditable(True)
        self.SessionComboBox.addItems(["ses-post", "ses-pre"])


def _display_session(file_session):
    """Mirrors MainWindow._load_import_file_into_form session display."""
    return "ses-" + file_session if file_session else ""


def _save_session(displayed_text):
    """Mirrors MainWindow.save_current_form_to_data session parsing."""
    return displayed_text.removeprefix("ses-") if displayed_text else ""


class TestSetSessionComboboxText:
    def test_empty_text_clears_selection(self, qapp):
        holder = _SessionComboHolder()
        MainWindow._set_session_combobox_text(holder, "")
        assert holder.SessionComboBox.currentText() == ""

    def test_known_session_selects_item(self, qapp):
        holder = _SessionComboHolder()
        MainWindow._set_session_combobox_text(holder, "ses-pre")
        assert holder.SessionComboBox.currentIndex() == 1
        assert holder.SessionComboBox.currentText() == "ses-pre"

    def test_custom_session_shown_even_if_not_an_item(self, qapp):
        holder = _SessionComboHolder()
        MainWindow._set_session_combobox_text(holder, "ses-01")
        assert holder.SessionComboBox.currentText() == "ses-01"


class TestComboboxRepopulationWithPlaceholder:
    """Documents why update_subject_details needs an explicit setCurrentIndex(0).

    A QComboBox with placeholderText set does not auto-select the first item
    after addItems() — it stays at index -1 so the placeholder can show. The
    session combobox gets a placeholder in _setup_session_combobox, so without
    the explicit default the dropdown starts blank on dataset load and newly
    added files silently become session-less instead of defaulting to ses-post.
    """

    def _session_combo(self):
        combo = QComboBox()
        combo.setEditable(True)
        combo.setPlaceholderText("Type session name (e.g., baseline, month6, 01)")
        return combo

    def test_additems_with_placeholder_leaves_combo_blank(self, qapp):
        combo = self._session_combo()
        combo.addItems(["ses-post", "ses-pre"])
        assert combo.currentIndex() == -1
        assert combo.currentText() == ""

    def test_explicit_default_selects_ses_post(self, qapp):
        combo = self._session_combo()
        combo.addItems(["ses-post", "ses-pre"])
        combo.setCurrentIndex(0)
        assert combo.currentText() == "ses-post"


class TestSessionRoundTrip:
    def test_empty_session_round_trips_unchanged(self):
        """Session-less files must stay session-less through display + save."""
        files = [
            {"file_name": "a.trc", "session": "", "acquisition": "01"},
            {"file_name": "b.trc", "session": "", "acquisition": "02"},
            {"file_name": "c.trc", "session": "", "acquisition": "03"},
        ]

        # Import click: form save writes the displayed session onto files[0]
        files[0]["session"] = _save_session(_display_session(files[0]["session"]))

        assert [f["session"] for f in files] == ["", "", ""]

    def test_named_sessions_round_trip_unchanged(self):
        assert _save_session(_display_session("post")) == "post"
        assert _save_session(_display_session("01")) == "01"
