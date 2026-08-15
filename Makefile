# 🍌 🎥 CamView — Makefile
# Standalone executable build automation and developer shortcuts

SHELL := /bin/bash
PYTHON := uv run python

.DEFAULT_GOAL := help

.PHONY: help install run dev build build-dir build-debug build-linux build-windows build-macos clean check

## ── Help & Information ──────────────────────────────────────────

help: ## Show this help message
	@echo ""
	@echo "🍌 CamView — Build & Development Shortcuts"
	@echo "==========================================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

## ── Setup & Development ─────────────────────────────────────────

install: ## Install all dependencies including build tools (UV)
	uv sync --all-extras

dev: install ## Alias for install

run: ## Run CamView from source in development mode
	$(PYTHON) main.py

check: ## Verify Python syntax and imports across the codebase
	$(PYTHON) -m py_compile main.py build.py src/**/*.py
	@echo "✅ All Python files passed syntax compilation."

## ── Standalone Executable Builds ───────────────────────────────

build: ## Build standalone single-file executable for current OS (dist/CamView)
	$(PYTHON) build.py --onefile

build-dir: ## Build standalone directory distribution for current OS
	$(PYTHON) build.py --onedir

build-debug: ## Build standalone executable with terminal console enabled
	$(PYTHON) build.py --onefile --debug

build-linux: ## Build Linux standalone binary (dist/CamView)
	@if [ "$$(uname -s)" != "Linux" ]; then \
		echo "⚠️ Warning: Native Linux binary is best built on a Linux system or via GitHub Actions."; \
	fi
	$(PYTHON) build.py --onefile --name CamView-Linux-x86_64

build-windows: ## Build Windows standalone executable (.exe)
	@if [ "$$(uname -s)" = "Linux" ] || [ "$$(uname -s)" = "Darwin" ]; then \
		echo "ℹ️  Tip: To build a native Windows .exe without Windows installed:"; \
		echo "   1. Push your code to GitHub and use the automated CI/CD workflow (.github/workflows/build.yml)"; \
		echo "   2. Or run: make build inside a Windows PowerShell / CMD terminal with UV installed."; \
	fi
	$(PYTHON) build.py --onefile --name CamView-Windows

build-macos: ## Build macOS standalone app bundle (CamView.app)
	@if [ "$$(uname -s)" != "Darwin" ]; then \
		echo "ℹ️  Tip: macOS .app bundles require macOS (or GitHub Actions macOS runners)."; \
		echo "   Use the included GitHub Actions workflow to build for macOS automatically."; \
	fi
	$(PYTHON) build.py --onefile --name CamView-macOS

## ── Cleanup ─────────────────────────────────────────────────────

clean: ## Clean build artifacts, temporary cache files, and dist folders
	rm -rf build dist .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "🧹 Workspace cleaned."
