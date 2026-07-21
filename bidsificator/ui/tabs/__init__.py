"""Per-tab UI for MainWindow — mid-migration to standalone QWidgets (9d).

Each tab of the main QTabWidget lives in its own file here. The split is being
converted, one tab per PR, from *mixins into `MainWindow`* to *self-contained
`QWidget` subclasses* built from their own `.ui` and receiving their
dependencies by injection:

- `ImportFilesTab` (QWidget, 9d.2 — DONE): the per-file metadata form, the file
  list, modality/session/subject handling, and file import. Built from
  `forms/ImportFilesTab.ui`. Exposes `refresh_subject_dropdown()` for the host to
  call when the dataset's subject list changes.
- `ImportSubjectsTab` (QWidget, 9d.1 — DONE): subject parsing, the subject list
  + embedded FileEditor sync, the lookup table, and batch import. Built from
  `forms/ImportSubjectsTab.ui`; owns its widgets, behaviour, and controller
  signal wiring; MainWindow inserts it into the tab widget at runtime.
- `ParticipantsTabMixin` (mixin — pending 9d.3): the Participants tab: subject
  creation, the file-tree view and its context-menu operations.

The remaining mixins are transitional: `self` is the live `MainWindow`, so their
slot bodies (and dialog parents) are unchanged and rely on the widgets built by
`Ui_MainWindow.setupUi` and the state created in `MainWindow.__init__`. They are
retired as each tab becomes a QWidget.
"""
