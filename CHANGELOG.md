# Changelog

## Unreleased

Highlights:
* Added: support for asynchronous handles.
* Added: escaping of the header and body (protocol).
* Changed: minimal Python version is Python 3.12.
* Changed: body checksum is always included (protocol).
* Changed: body checksum is now calculated over header and payload (protocol).
* Fixed: preamble is now read as string of bytes.
* Improved: CLI is more interactive.
* Improved: consistent terminology and naming.
* Removed: reserved flags (protocol).

## v2.0.0
Released 17 September 2015

Highlights:
* Added: Python 3.4 support.
* Improved: more strict handling of bytes.
* Improved: formatted code according to PEP8.
* Changed: ResetFrame is now a Frame, with correct flags set.
* Changed: DamagedFrame is now a property on a Frame.

The full list of commits can be found [here](https://github.com/basilfx/python-tinylink/compare/v1.1.0...v2.0.0).

## v1.1.0
Released 01 December 2014

The full list of commits can be found [here](https://github.com/basilfx/python-tinylink/compare/v1.0.0...v1.1.0).

## v1.0.0
Released 07 October 2014

The full list of commits can be found [here](https://github.com/basilfx/python-tinylink/compare/76afcbd301ca3ec4c58e232a10a7547a1e4ce982...v1.0.0).
