# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Fixed
- **Windows path handling**: `shlex.split` now uses non-POSIX mode on Windows to properly preserve backslashes in file paths
- **f-string backslash escaping**: Extracted Windows example paths into dedicated variables, avoiding backslash issues in f-strings (Python < 3.12 limitation)

### Added
- **Chat template file browser**: Added "Browse..." button for chat template file parameter with Jinja/text file filter
- **Flexible file filters**: Refactored `_browse_file` helper to accept custom file type filters

### Changed
- Added `.idea/` to `.gitignore` (PyCharm IDE config)

## [0.1.0] - 2026-04-03

### Added
- macOS Apple Silicon support
- Platform-specific setup instructions in README

### Changed
- Updated README with cross-platform documentation
