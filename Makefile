.DEFAULT_GOAL := help

# Hand-authored .ui files whose generated _ui.py is kept in sync here. Add each
# per-tab widget as it is split out of MainWindow.ui (9d): ImportSubjects +
# ImportFiles done, Participants to follow.
UI_FILES := \
	bidsificator/forms/MainWindow_ui.py \
	bidsificator/forms/ImportFilesTab_ui.py \
	bidsificator/forms/ImportSubjectsTab_ui.py

build-ui: $(UI_FILES) ## Build the UI (main window + per-tab widgets)

run: ## Run the Bidsificator
	bidsificator

.PHONY: design
design: ## Run the Qt designer on all forms
	qt6-tools designer bidsificator/forms/*.ui

%_ui.py: %.ui
	pyuic6 -o "$@" "$^"

.PHONY: test
test: ## Run the test suite
	poetry run pytest tests/ -v

.PHONY: lint
lint: ## Run ruff checks (active after PR 5)
	poetry run ruff check bidsificator tests

.PHONY: help
help:  ## Show the help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
