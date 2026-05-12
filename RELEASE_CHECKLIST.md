# Release Checklist

Use this checklist before tagging or publishing a desktop release. A release is not ready if any P0 gate is unchecked or intentionally waived in release notes.

## Release Gate Summary

| Gate | Status | Required for public release |
| --- | --- | --- |
| Documentation reflects actual shipped behavior | Not verified | Yes |
| Python unit tests pass | Not verified | Yes |
| Python compile check passes | Not verified | Yes |
| Frontend build passes | Not verified | Yes |
| Rust/Tauri build passes | Not verified | Yes |
| Windows installer runs on a clean machine | Not verified | Yes |
| Python sidecar works from installed app layout | Not verified | Yes |
| Chrome detection and ChromeDriver path are usable | Not verified | Yes |
| Privacy/security review completed | Not verified | Yes |
| Manual X login/profile/bookmarks smoke tests completed | Not verified | Yes |
| Export validation completed for JSON/Markdown/DOCX | Not verified | Yes |
| Known limitations and disclaimers included | Not verified | Yes |

## Pre-Release Code Validation

### Python
- [ ] Run `python -m unittest discover -s tests`.
- [ ] Run `python -m compileall main.py scraper.py document_generator.py export_schema.py diagnostics.py python_sidecar`.
- [ ] Verify `tests/test_exports.py` covers JSON schema version, safe paths, Markdown, and DOCX output.
- [ ] Add or verify a test that bookmark exports can emit `scrape_type: "bookmarks"`.
- [ ] Add or verify sidecar command tests for `login`, `scrape`, `export`, `diagnostics`, `pause`, `resume`, `cancel`, `status`, and `stop` without launching Chrome.
- [ ] Confirm `python_sidecar/requirements.txt` and packaged sidecar dependencies match the release runtime.

### Frontend
- [ ] Run `npm install` on a clean checkout.
- [ ] Run `npm run build`.
- [ ] Verify TypeScript build has no hidden errors from unused or stale hooks.
- [ ] Verify `src/hooks/useScraper.ts` is either removed, covered, or clearly unused.
- [ ] Verify result export UI uses the intended source of truth for JSON/Markdown/DOCX.
- [ ] Verify hardcoded feature copy does not claim unshipped CSV/Excel/scheduling/paid-tier behavior.

### Rust/Tauri
- [ ] Run `cargo test` in `src-tauri` after Rust tests exist.
- [ ] Run `npm run tauri build`.
- [ ] Verify command argument naming between React invokes and Rust command structs.
- [ ] Verify `src-tauri/src/commands/analytics.rs` stores sortable dates correctly.
- [ ] Verify Rust scrape ID and sidecar scrape ID are reconciled.
- [ ] Verify `get_scrape_status` and `check_session` return accurate semantics or are not exposed as misleading UX.

### Security and Privacy
- [ ] Review and reduce `src-tauri/capabilities/default.json` permissions.
- [ ] Replace `csp: null` in `src-tauri/tauri.conf.json` with a production-appropriate CSP or document a reviewed exception.
- [ ] Document local data paths: SQLite database, exports, run logs, and session cookies.
- [ ] Add user controls to clear saved X cookies and local history.
- [ ] Confirm logs do not include credentials or sensitive cookie values.
- [ ] Confirm OpenAI API keys are not persisted unless explicitly documented and secured.
- [ ] Add a privacy note and responsible-use disclaimer to public docs.

## Windows Packaging Checklist

### Clean Machine Test
- [ ] Install the release artifact on a Windows machine or VM without the development repo.
- [ ] Launch from Start Menu and desktop shortcut.
- [ ] Confirm app window, tray, and custom title bar work.
- [ ] Confirm app can find or start the sidecar from installed layout.
- [ ] Confirm missing Python behavior is acceptable if Python is not bundled.
- [ ] Confirm missing Chrome behavior is clear and actionable.
- [ ] Confirm output directory defaults to a user-writable location.
- [ ] Confirm logs and database are written under expected user data paths, not the installer directory.
- [ ] Uninstall and confirm app files are removed. Document whether user data remains.

### Sidecar Packaging
- [ ] Decide release model: bundled executable, embedded Python, or external Python prerequisite.
- [ ] If bundled, verify `python_sidecar/service.py` and dependencies are included.
- [ ] If bundled, verify root modules used by the sidecar are included: `document_generator.py`, `export_schema.py`, `diagnostics.py`, and `config.py`.
- [ ] If external Python is required, first-run checks must detect Python and guide installation.
- [ ] Verify `webdriver-manager` can download ChromeDriver or provide an offline/failure path.
- [ ] Verify sidecar startup does not depend on the current working directory.

### App Metadata
- [ ] Product name is final in `src-tauri/tauri.conf.json`.
- [ ] Identifier is final in `src-tauri/tauri.conf.json`.
- [ ] Version is aligned across `package.json`, `src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json`, UI About copy, and release notes.
- [ ] Author/publisher fields are final.
- [ ] App icon is final and renders correctly in installer, Start Menu, taskbar, and tray.
- [ ] Windows installer language, upgrade behavior, and signing strategy are documented.

## Manual Scrape Test Matrix

Run these manually before public release. Record browser version, app version, OS, account type, and date.

| Scenario | Expected result |
| --- | --- |
| First launch with no onboarding state | Onboarding explains prerequisites, privacy, and limitations. |
| Chrome installed at default path | App detects Chrome or starts Chrome successfully. |
| Chrome missing or wrong path | App gives a clear fix, not a generic sidecar error. |
| Manual login success | Auth status becomes connected only after X session is valid. |
| Manual login timeout/cancel | User sees recoverable error and can retry. |
| Saved cookie session restore | Session restore works or asks for fresh login without corrupt state. |
| Clear saved session | Saved X cookies are removed and next run requires login. |
| Public profile count scrape | Requested count is collected or partial/empty state is clear. |
| Profile last N days scrape | Date filtering is correct enough for visible timeline data. |
| Profile date range scrape | Start/end validation prevents impossible ranges. |
| Bookmarks count scrape | Bookmarks page is reached and exported metadata says bookmarks. |
| Bookmarks all scrape | Progress is indeterminate or stage-aware, not misleading. |
| Empty profile or no matching posts | App reports empty state, not generic failure. |
| Private/protected profile | App reports inaccessible/private state if detected. |
| Login wall/session expired during scrape | App stops safely and prompts re-login. |
| Rate-limit/interstitial-like state | App stops or warns without aggressive retry loops. |
| Long tweet with Show More | Full text is attempted and failures are logged. |
| X Article tweet | Article extraction is attempted and failures are logged. |
| Media tweet | Media URLs or placeholders are represented consistently. |
| Pause/resume | Scrape pauses and resumes without losing collected tweets. |
| Cancel | Partial results remain available or are clearly discarded by user choice. |
| App close during scrape | Sidecar is stopped and partial state behavior is documented. |

## Export Validation

### JSON
- [ ] Top-level fields exist: `schema_version`, `source`, `scrape_type`, `user`, `target`, `exported_at`, `total_tweets`, `tweets`.
- [ ] `schema_version` is currently `0.2`.
- [ ] `scrape_type` is correct for profile and bookmarks.
- [ ] `tweet_url` and compatibility `url` are both present.
- [ ] `date` values are ISO strings or explicitly null.
- [ ] Metrics are present and documented as best-effort.
- [ ] Exported count matches `total_tweets`.
- [ ] JSON opens in standard parsers and has UTF-8 encoding.

### Markdown
- [ ] Includes schema version.
- [ ] Includes target, total count, export date, tweet text, date, and tweet link.
- [ ] Handles empty text and media-only posts gracefully.
- [ ] Does not corrupt long text or article text.

### DOCX
- [ ] Opens in Microsoft Word or LibreOffice.
- [ ] Includes target, total count, date, tweet text, media summary, and tweet link.
- [ ] Handles non-ASCII text.
- [ ] Large exports remain usable or have documented limits.

### File Safety
- [ ] Filenames are sanitized for Windows reserved names and path traversal.
- [ ] Output directory is user-writable.
- [ ] Existing files are overwritten only when expected or are named uniquely.
- [ ] Partial/error exports are labeled clearly.

## History and Analytics Validation

- [ ] Completed scrapes appear in dashboard and history.
- [ ] Failed, cancelled, and partial scrapes have accurate statuses.
- [ ] History dates sort correctly.
- [ ] History delete removes scrape and related tweets.
- [ ] Re-export from history works after app restart.
- [ ] Analytics loads persisted tweets, not only current in-memory tweets.
- [ ] AI analysis clearly states that tweet text is sent to OpenAI when used.

## Documentation Checklist

- [ ] `README.md` explains install, dev usage, desktop usage, and CLI usage separately.
- [ ] README lists tested OS, Python, Node, Rust, Chrome, and app versions.
- [ ] README includes screenshots or GIFs only after the UI matches release behavior.
- [ ] README includes responsible-use and non-affiliation disclaimers.
- [ ] README explains local data storage and deletion.
- [ ] README explains known limitations and common failures.
- [ ] `PROJECT_CONTEXT.md` is updated if architecture changes.
- [ ] `PUBLISH_ROADMAP.md` is updated if release scope changes.
- [ ] `RISK_REGISTER.md` has no unresolved P0 risk without mitigation or release note.
- [ ] `CHANGELOG.md` exists before first public release.
- [ ] `LICENSE` is present and matches intended distribution.
- [ ] GitHub issue templates exist for bug report, selector breakage, packaging issue, and feature request.

## Release Notes Template

```markdown
## Version X.Y.Z

### What is included
- 

### Tested environment
- Windows:
- App:
- Chrome:
- Python/runtime:

### Known limitations
- X/Twitter UI changes can break scraping.
- The app does not bypass private content, platform controls, or rate limits.
- Scraped data is best-effort and should be verified before relying on it.

### Verification completed
- Python tests:
- Frontend build:
- Tauri build:
- Windows clean install:
- Manual profile scrape:
- Manual bookmarks scrape:
- Export validation:

### Data and privacy
- Local data locations:
- Session/cookie behavior:
- How to delete data:
```

## Release Decision Rule

Ship only when all P0 checklist items are complete or explicitly waived with a clear reason. If a waiver affects user privacy, data correctness, installer startup, or account safety, do not publish a general-user release; publish a developer preview instead.
