# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- TableField and TableQuestion support in dataset creation workflow (#114)
  - New `table` field type available in field type dropdown
  - New `table` question type with dynamic column management (add/remove/edit columns)
  - Validation requiring at least one column for table questions
  - i18n translations for en, de, es, ja
