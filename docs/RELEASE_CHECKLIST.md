# Maintainer release checklist

Run this checklist from a clean checkout of `prod-ready`. Record the date, OS, Python/Chrome versions, target handles, command exits, export paths, and run-log paths in the release issue. Never attach the `.sessions` directory or cookie data.

## Automated release gate

- [ ] Install development tools with `python -m pip install ".[dev]"`.
- [ ] Run `python -m pytest -q` with no failures or skips beyond OS-specific launcher behavior.
- [ ] Run Ruff lint and format checks, configured mypy, and compileall.
- [ ] Build wheel and sdist with `python -m build`.
- [ ] Run `python -m twine check dist/*`.
- [ ] Inspect wheel/sdist contents for all runtime modules and no session/output/generated/planning files.
- [ ] Run `python scripts/wheel_smoke.py` from the clean build.
- [ ] Run `pip-audit -r requirements.txt`, `python -m pip check`, and the tracked-file secret scan.
- [ ] Confirm GitHub Actions is green on Ubuntu, Windows, and macOS for Python 3.11-3.13.

## Session and browser checks

- [ ] In a fresh directory, run `x-scraper login`; sign in directly on X in normal Chrome and close the dedicated window.
- [ ] Run `x-scraper paths` and confirm the profile/output paths are below the current directory.
- [ ] Confirm a scrape with a missing profile exits 2 before Chrome or ChromeDriver starts.
- [ ] Confirm logs do not contain the profile path, passwords, cookies, tokens, or private page contents.

## Live X smoke checks

- [ ] Public profile count: request at least 10 posts and verify IDs, text, UTC timestamps, order, and unique rows.
- [ ] Public profile date range: use a profile with an old pinned post and newer posts below it; verify the pinned post does not stop collection.
- [ ] Public profile last-N-days: verify boundary inclusion and no naive/aware datetime error.
- [ ] Bookmarks count: verify only the authorized account's visible bookmarks are exported.
- [ ] Bookmarks date range and last-N-days: verify UTC filtering and visible warnings for unavailable dates.
- [ ] Headless profile and bookmark runs using the prepared profile.
- [ ] Interrupt a count scrape with Ctrl+C after several posts; verify partial data is saved, status is `cancelled`, and exit is 130.
- [ ] Request more posts than a small profile contains; verify status `partial`, exit 3, and requested/collected counts agree.
- [ ] Run selector diagnostics on Home and a public profile; review every required selector result.
- [ ] Exercise a long post, X Article, media-only post, quote post, repost, reply, and unavailable/deleted post where available.

## Platform checks

- [ ] Windows: run the installed console command and `x-scraper.cmd` from a path containing spaces.
- [ ] macOS: verify Google Chrome discovery and visible/headless profile reuse.
- [ ] Linux: verify Google Chrome or Chromium discovery and visible/headless profile reuse.
- [ ] Verify plain terminal output with ANSI color disabled or redirected.
- [ ] Verify a Unicode output directory on each release platform where supported.

## Promotion

- [ ] Review known limitations and all live-X evidence; do not mark untested items complete.
- [ ] If the checklist passes, change `version.__version__` from `1.0.0b1` to `1.0.0`, update the classifier to Production/Stable, add the stable changelog entry, rebuild, and repeat the complete automated gate.
- [ ] Merge `prod-ready` into `main`, tag `v1.0.0`, and publish only the freshly verified artifacts.
