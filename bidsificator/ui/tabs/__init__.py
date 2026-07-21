"""Per-tab UI widgets for MainWindow (per-tab `.ui` split complete, 9d).

Each tab of the main QTabWidget is a self-contained ``QWidget`` subclass built
from its own ``.ui``, owning its widgets and behaviour and receiving its
dependencies by injection. ``MainWindow`` is a thin host that constructs these
and inserts them into the (otherwise empty) tab widget at runtime.

- ``ParticipantsTab`` — subject creation and the subject table
  (``PatientTableWidget``). Built from ``forms/ParticipantsTab.ui``. Exposes
  ``subject_updated`` (re-emitted from the table), ``subject_controller`` (for the
  host's file-tree rename/delete ops), and ``refresh_table(path)``. The file-tree
  browser itself is left-pane chrome and lives on ``MainWindow``, not here.
- ``ImportFilesTab`` — the per-file metadata form, the file list, the subject
  dropdown, modality/session/task handling, and file import. Built from
  ``forms/ImportFilesTab.ui``. Exposes ``refresh_subject_dropdown()``.
- ``ImportSubjectsTab`` — subject parsing, the subject list + embedded
  ``FileEditor`` sync, the lookup table, and batch import. Built from
  ``forms/ImportSubjectsTab.ui``.

Each tab wires its own controller signals and renders its own dialogs (parented
to the tab); status-bar updates go through the injected ``StatusBarManager``.
"""
