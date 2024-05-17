.DEFAULT_GOAL := help

build-ui: bidsificator/forms/MainWindow_ui.py ## Build the UI

run: ## Run the Bidsificator
	bidsificator

.PHONY: design
design: ## Run the Qt designer
	qt6-tools designer bidsificator/forms/MainWindow.ui

bidsificator/forms/MainWindow_ui.py: bidsificator/forms/MainWindow.ui
	pyuic6 -o "$@" "$^"

.PHONY: help
help:  ## Show the help
		@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
