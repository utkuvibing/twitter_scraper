# x-scraper terminal and authentication UX

## Goal

Make the interactive `x-scraper` experience English, visually clear in Windows terminals, and compatible with Google or Apple X sign-in without attempting OAuth inside a Selenium-controlled browser.

## Terminal design

- Use only the Python standard library. No additional UI dependency is introduced.
- Render a compact `x-scraper` banner, section titles, numbered choices, status labels, and errors with ANSI colors.
- Detect unsupported output or `NO_COLOR` and render the same information without escape sequences.
- Keep prompts ASCII-safe so CMD and PowerShell remain readable regardless of the active code page.
- Keep non-interactive `scrape`, `diagnostics`, `--help`, and `--version` suitable for scripts; decorative output is limited to the interactive wizard and user-facing status messages.

## Authentication design

- Add `x-scraper login [--browser-profile PATH]`.
- It opens the normal installed Chrome executable, not ChromeDriver, using an isolated persistent profile at `.sessions/x-scraper` by default.
- The user completes their X login, including Google or Apple if desired, in that normal Chrome window and closes it when finished.
- Later scraping uses that same profile. Selenium only reuses the authenticated X session; it does not drive the Google or Apple OAuth screen.
- The interactive wizard defaults to this profile setup. It launches normal Chrome before the scraper begins, then supplies the profile path to `XScraper`.
- If a Selenium browser reaches an unauthenticated X page, it stops with an instruction to run the normal-Chrome login flow rather than suggesting Google/Apple sign-in there.

## Error handling

- If Chrome cannot be found or launched, show a clear action-oriented error and return a non-zero status.
- The normal-Chrome login setup never records credentials, cookies, or profile paths in run logs.
- The session directory remains ignored by Git.

## Verification

- Unit tests cover `login` command dispatch, the interactive wizard choosing the persistent profile, ANSI fallback behavior, and Chrome launch command construction.
- Run the full test suite, invoke `x-scraper --version`, and verify the `login` command reaches the normal-Chrome launcher with a mocked process.
