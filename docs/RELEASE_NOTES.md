# x-scraper 1.0.0b1 release notes

This beta is the first release candidate with a stable CLI outcome contract and JSON schema 1.0. It is intended for maintainers and early users to complete the live-X checklist before tagging stable `1.0.0`.

The most important behavioral change is that an incomplete archive is no longer reported as success. Usable shortfalls are saved as `partial` and exit 3; Ctrl+C is `cancelled` and exits 130. All internal dates are UTC-aware, pinned old posts no longer terminate a profile date scan, and unavailable dates remain null.

Authentication now uses a normal Chrome window and an isolated local profile prepared by `x-scraper login`. Scripted and headless scrapes require that prepared profile and verify signed-in X UI after WebDriver starts. Passwords are not accepted by CLI arguments or the interactive wizard.

The package is marked Beta because automated tests intentionally do not require a live X account. Complete [the maintainer release checklist](RELEASE_CHECKLIST.md) before promoting this build to stable `1.0.0`.
