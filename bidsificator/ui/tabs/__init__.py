"""Per-tab UI mixins for MainWindow.

MainWindow's per-tab logic is split into three mixins — one per tab of the main
QTabWidget — so each tab's slots and helpers live in their own file instead of a
single 1400-line window class:

- `ParticipantsTabMixin` — the Participants tab: subject creation, the file-tree
  view and its context-menu operations (validate / rename / delete).
- `ImportFilesTabMixin` — the Import Files tab: the per-file metadata form, the
  file list, modality/session handling, and file import.
- `ImportSubjectsTabMixin` — the Import Subjects tab: subject parsing, the
  subject list + embedded FileEditor sync, the lookup table, and batch import.

These are mixins rather than standalone objects on purpose: `self` is the live
`MainWindow`, so the slot bodies (and their dialog parents) are unchanged and
the Qt signal wiring in MainWindow keeps working as-is. They rely on the widgets
built by `Ui_MainWindow.setupUi` and on the controllers/state created in
`MainWindow.__init__`, and are only ever mixed into `MainWindow`. The eventual
per-tab QWidget split (regenerating the `.ui`) supersedes this arrangement.
"""
