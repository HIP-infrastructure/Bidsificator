"""Completion-state selection and the "completed with errors" dialog for imports.

Split out of the tabs so the state selection and report formatting are pure,
importable, and unit-testable without constructing a window; only
:class:`ImportCompletionDialog` touches Qt widgets. Shared by the Import Files and
Import Subjects tabs (UR-GUI-009, REQ-GUI-075-078).

The input everywhere is the plain ``summary`` dict the controllers emit inside
``import_completed`` (``ImportSummary.to_dict()``): ``imported`` / ``failed`` /
``skipped`` / ``total`` counts, ``subjects_created``, an ``items`` list of
``{path, subject, status, reason}``, and a ``warnings`` list of strings.
"""

import logging
from enum import Enum

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
)

logger = logging.getLogger(__name__)


class CompletionState(Enum):
    """How an import finished, for the completion UX (green / amber / red)."""

    SUCCESS = "success"                 # everything imported, no problems
    PARTIAL = "completed-with-errors"   # some imported AND some failed/skipped
    ERROR = "error"                     # the run completed but nothing imported


def select_completion_state(summary: dict) -> CompletionState:
    """Pick the completion state from an import summary dict (pure).

    - ``SUCCESS``: no failures, skips, or warnings.
    - ``PARTIAL``: at least one item imported *and* at least one problem.
    - ``ERROR``: the run completed but nothing was imported.

    This covers only the *completion* path. A hard abort (dead subprocess) is
    reported via the controller's error signal, not here, and its red state must
    not claim "nothing was imported" (files may already be on disk).
    """
    imported = summary.get("imported", 0)
    problems = _problem_count(summary)
    if problems == 0:
        return CompletionState.SUCCESS
    if imported <= 0:
        return CompletionState.ERROR
    return CompletionState.PARTIAL


def _problem_count(summary: dict) -> int:
    return summary.get("failed", 0) + summary.get("skipped", 0) + len(summary.get("warnings") or [])


def _plural(count: int, singular: str) -> str:
    return f"{count} {singular}" if count == 1 else f"{count} {singular}s"


def headline(summary: dict, item_noun: str) -> str:
    """One-line human summary, e.g. ``Imported 7 of 10 files — 2 failed, 1 skipped.`` (pure)."""
    imported = summary.get("imported", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)
    total = summary.get("total", imported + failed + skipped)
    line = f"Imported {imported} of {_plural(total, item_noun)}."
    problems = []
    if failed:
        problems.append(f"{failed} failed")
    if skipped:
        problems.append(f"{skipped} skipped")
    if problems:
        line += " — " + ", ".join(problems) + "."
    return line


def _describe(item: dict) -> str:
    """Render one outcome item as a single line: location — reason."""
    path = item.get("path")
    subject = item.get("subject")
    reason = item.get("reason") or ""
    if path and subject:
        head = f"{path}  (subject {subject})"
    elif path:
        head = path
    elif subject:
        head = f"subject {subject}"
    else:
        head = "(item)"
    return f"{head} — {reason}" if reason else head


def build_report_text(summary: dict, item_noun: str, header: str | None = None) -> str:
    """Full multi-line report of failed/skipped items + warnings, for Copy/Save (pure).

    UTF-8 friendly (accented CHUV filenames are realistic); the full untruncated
    reason of every item is preserved here even though the on-screen list elides.
    """
    items = summary.get("items", [])
    failed = [it for it in items if it.get("status") == "failed"]
    skipped = [it for it in items if it.get("status") == "skipped"]
    warnings = summary.get("warnings") or []

    lines = [header or headline(summary, item_noun), ""]
    if failed:
        lines.append(f"Failed ({len(failed)}):")
        lines.extend(f"  - {_describe(it)}" for it in failed)
        lines.append("")
    if skipped:
        lines.append(f"Skipped ({len(skipped)}):")
        lines.extend(f"  - {_describe(it)}" for it in skipped)
        lines.append("")
    if warnings:
        lines.append(f"Warnings ({len(warnings)}):")
        lines.extend(f"  - {w}" for w in warnings)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


class ImportCompletionDialog(QDialog):
    """Modal shown after a partial or empty import.

    Header + one-line summary, a scrollable list of the failed/skipped items and
    warnings (each row elided to one line, full text in the tooltip and in the
    export), and Copy-details / Save… actions. Long batches scroll rather than
    grow the dialog.
    """

    def __init__(self, parent, state: CompletionState, summary: dict,
                 item_noun: str, header: str | None = None):
        super().__init__(parent)
        self._report = build_report_text(summary, item_noun, header)

        titles = {
            CompletionState.PARTIAL: "Import completed with errors",
            CompletionState.ERROR: "Import failed",
            CompletionState.SUCCESS: "Import complete",
        }
        self.setWindowTitle(titles.get(state, "Import complete"))
        self.resize(560, 420)

        layout = QVBoxLayout(self)
        head = QLabel(header or headline(summary, item_noun))
        head.setWordWrap(True)
        layout.addWidget(head)

        self._list = QListWidget()
        self._list.setTextElideMode(Qt.TextElideMode.ElideRight)  # single-line truncation
        self._list.setWordWrap(False)
        for it in summary.get("items", []):
            status = it.get("status")
            if status in ("failed", "skipped"):
                text = f"[{status}] {_describe(it)}"
                row = QListWidgetItem(text)
                row.setToolTip(text)  # full text on hover; the row elides
                self._list.addItem(row)
        for warning in summary.get("warnings") or []:
            row = QListWidgetItem(f"[warning] {warning}")
            row.setToolTip(warning)
            self._list.addItem(row)
        layout.addWidget(self._list, 1)

        buttons = QDialogButtonBox()
        copy_btn = buttons.addButton("Copy details", QDialogButtonBox.ButtonRole.ActionRole)
        save_btn = buttons.addButton("Save…", QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Close)
        copy_btn.clicked.connect(self._copy_details)
        save_btn.clicked.connect(self._save_report)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _copy_details(self) -> None:
        QApplication.clipboard().setText(self._report)

    def _save_report(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save import report", "import_report.txt",
            "Text files (*.txt);;All files (*)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._report)
        except OSError as e:
            logger.warning("Could not save import report to %s: %s", path, e)
            QMessageBox.warning(self, "Save Failed", f"Could not save the report:\n{e}")
