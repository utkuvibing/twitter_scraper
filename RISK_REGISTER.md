# Risk Register

This register is intentionally conservative. Public release should not depend on assumptions about X/Twitter behavior, user environments, or untested packaging paths.

## Risk Scale
- Severity: Low, Medium, High, Critical
- Likelihood: Low, Medium, High
- Release decision: Ship, Ship with mitigation, Block public release

## Summary

| ID | Category | Risk | Severity | Likelihood | Release decision |
| --- | --- | --- | --- | --- | --- |
| R1 | X/Twitter DOM selectors | X UI changes break scraping or diagnostics. | Critical | High | Ship with mitigation |
| R2 | Login/session | Login state is misdetected or saved cookies fail. | High | High | Block public release until UX and reset are solid |
| R3 | Account safety/rate limits | Automation triggers platform warnings, locks, or degraded account trust. | High | Medium | Ship with mitigation |
| R4 | Long tweet/article extraction | Full text and article extraction are incomplete or polluted with page chrome. | High | High | Ship with mitigation |
| R5 | Export schema stability | Different export paths drift or metadata is wrong. | High | Medium | Block public release until fixed |
| R6 | File path/output safety | Exports/logs are written to unsafe, unexpected, or unwritable paths. | Medium | Medium | Ship with mitigation |
| R7 | Desktop packaging | Installed app cannot find Python, sidecar files, dependencies, Chrome, or ChromeDriver. | Critical | High | Block public release |
| R8 | Windows UX | First-run, installer, tray, paths, and prerequisites fail for non-dev users. | High | High | Block public release |
| R9 | Error handling | Users receive generic failures for distinct conditions. | High | High | Ship with mitigation |
| R10 | Privacy/security | Cookies, local data, API keys, CSP, and Tauri permissions are not release-hardened. | Critical | Medium | Block public release |
| R11 | Dependency/version | Selenium, ChromeDriver, Chrome, Tauri, Python, Node, and Rust versions drift. | High | Medium | Ship with mitigation |
| R12 | Test coverage | Existing tests do not cover scraper, sidecar protocol, frontend, Rust, installer, or live manual flows. | High | High | Block public release |
| R13 | Product claims | Placeholder licensing/scheduling/CSV/Excel/AI claims overstate shipped behavior. | High | High | Block public release |
| R14 | Data persistence | Scrape IDs, dates, history, and re-export behavior are inconsistent. | High | Medium | Block public release until fixed |

## Detailed Risks

### R1 - X/Twitter DOM Selector Fragility

- Severity: Critical
- Likelihood: High
- Current evidence: Selectors in `config.py`, `scraper.py`, and `python_sidecar/scraper.py` depend on X DOM attributes, labels, text, and page structure. The README already warns that X changes frequently.
- User impact: Scrapes fail, collect incomplete data, or silently miss content.
- Mitigation:
  - Keep selector definitions centralized where possible.
  - Surface selector diagnostics in desktop UX.
  - Add static DOM fixture tests for parser behavior.
  - Maintain a "selector breakage" issue template.
  - Include known selector health in release notes.
- Files likely involved: `config.py`, `diagnostics.py`, `scraper.py`, `python_sidecar/scraper.py`, `src/components/scrape/ScrapeProgress.tsx`, `README.md`
- Release decision: Ship with mitigation. Do not claim guaranteed completeness.

### R2 - Login, Session, and Cookie Handling

- Severity: High
- Likelihood: High
- Current evidence: CLI login can continue after ambiguous URL checks. Desktop `check_session` reports whether the sidecar is running, not whether X is authenticated. Cookies are saved as JSON by `python_sidecar/session_manager.py`.
- User impact: Users think they are logged in when they are not, or stale cookies cause confusing failures.
- Mitigation:
  - Make session status mean "X session valid", not "sidecar process exists".
  - Add session clear/reset UI.
  - Document cookie storage path and deletion.
  - Prefer manual browser login over app-collected passwords.
  - Detect login wall/session expiry during navigation.
- Files likely involved: `main.py`, `scraper.py`, `python_sidecar/session_manager.py`, `python_sidecar/scraper.py`, `python_sidecar/service.py`, `src-tauri/src/commands/auth.rs`, `src/stores/authStore.ts`, `src/hooks/useScrapeEvents.ts`, `src/components/settings/SettingsPanel.tsx`
- Release decision: Block public release until session UX is reliable and privacy handling is documented.

### R3 - Rate Limits and Account Safety

- Severity: High
- Likelihood: Medium
- Current evidence: Scraping scrolls through X via Selenium with repeated waits and browser automation. There is no explicit account safety model beyond manual user control.
- User impact: Users may hit X rate limits, warnings, temporary locks, login challenges, or account trust issues.
- Mitigation:
  - Use conservative defaults for counts and scroll pauses.
  - Warn users before large scrapes.
  - Stop on suspicious interstitials or platform warnings.
  - Add clear account-safety disclaimer.
  - Avoid background scheduled scraping until manual flows are stable.
- Files likely involved: `config.py`, `python_sidecar/scraper.py`, `scraper.py`, `src/components/scrape/ScrapeConfig.tsx`, `src/components/onboarding/OnboardingWizard.tsx`, `README.md`
- Release decision: Ship with mitigation. Do not market aggressive/high-volume scraping.

### R4 - Long Tweet and Article Extraction Reliability

- Severity: High
- Likelihood: High
- Current evidence: Full-text extraction opens tweet pages and reads `tweetText`; article extraction uses page navigation and heuristic text filtering. Root and sidecar implementations differ.
- User impact: Exports may include truncated text, missing articles, duplicated text, or unrelated page text.
- Mitigation:
  - Mark `needs_full_text` and article extraction outcomes in exports/logs.
  - Preserve original visible text if full extraction fails.
  - Add article/full-text regression fixtures.
  - Document that article extraction is best-effort.
  - Prefer structured selectors over body text filtering where possible.
- Files likely involved: `scraper.py`, `python_sidecar/scraper.py`, `export_schema.py`, `document_generator.py`, `diagnostics.py`, `tests/`
- Release decision: Ship with mitigation. Do not promise complete article archiving.

### R5 - Export Schema Stability and Drift

- Severity: High
- Likelihood: Medium
- Current evidence: Python export uses `export_schema.py`; React results generate JSON/Markdown/DOCX separately in `ScrapeResults.tsx`; bookmark exports can default to profile metadata if `scrape_type` is not passed.
- User impact: Archives are mislabeled, incompatible, or inconsistent across CLI/desktop/history paths.
- Mitigation:
  - Make `export_schema.py` the source of truth or add parity tests for all export paths.
  - Fix bookmark `scrape_type`.
  - Add schema compatibility tests and changelog.
  - Include schema version in Markdown and document DOCX limits.
- Files likely involved: `export_schema.py`, `document_generator.py`, `main.py`, `python_sidecar/service.py`, `src/components/scrape/ScrapeResults.tsx`, `src-tauri/src/commands/export.rs`, `tests/test_exports.py`
- Release decision: Block public release until metadata correctness and parity are fixed.

### R6 - File Path and Output Safety

- Severity: Medium
- Likelihood: Medium
- Current evidence: Python path helpers sanitize filenames and target directories. Rust export writers have their own safety implementation. Output defaults differ between CLI, sidecar, and installed app expectations.
- User impact: Users may lose exports, write to unexpected app directories, or hit permission errors.
- Mitigation:
  - Use one safe path implementation or test parity.
  - Default to a user-writable documents/app-data location.
  - Show final output path and allow opening folder.
  - Label partial/error exports.
- Files likely involved: `export_schema.py`, `document_generator.py`, `src-tauri/src/commands/export.rs`, `src/components/scrape/ScrapeResults.tsx`, `src/components/settings/SettingsPanel.tsx`
- Release decision: Ship with mitigation after clean Windows output tests pass.

### R7 - Desktop Packaging and Sidecar Distribution

- Severity: Critical
- Likelihood: High
- Current evidence: `src-tauri/src/sidecar/mod.rs` starts system Python and searches for `python_sidecar/service.py`; Tauri config does not clearly bundle the Python tree, root helper modules, or site packages.
- User impact: Installed app works on the developer machine but fails for final users.
- Mitigation:
  - Choose and implement a sidecar distribution strategy.
  - Include all sidecar files and dependencies as resources or build a standalone sidecar executable.
  - Avoid relying on current working directory.
  - Add clean Windows installer smoke tests.
- Files likely involved: `src-tauri/src/sidecar/mod.rs`, `src-tauri/tauri.conf.json`, `python_sidecar/**`, `document_generator.py`, `export_schema.py`, `diagnostics.py`, `config.py`, `python_sidecar/requirements.txt`
- Release decision: Block public release.

### R8 - Windows User Experience

- Severity: High
- Likelihood: High
- Current evidence: Windows is the current OS context. Packaging prerequisites, clean install behavior, shortcut launch behavior, and user data cleanup are not documented or validated.
- User impact: Non-technical users cannot install, launch, configure, or recover the app.
- Mitigation:
  - Add clean Windows VM test matrix.
  - Improve onboarding and settings checks.
  - Document Python/Chrome/WebView/runtime expectations.
  - Verify installer, uninstaller, tray, output directories, and app data paths.
- Files likely involved: `src-tauri/tauri.conf.json`, `src-tauri/src/commands/settings.rs`, `src/components/onboarding/OnboardingWizard.tsx`, `src/components/settings/SettingsPanel.tsx`, `RELEASE_CHECKLIST.md`, `README.md`
- Release decision: Block public release until clean install passes.

### R9 - Error Handling and Diagnostics

- Severity: High
- Likelihood: High
- Current evidence: Diagnostics and reason codes exist, but UI handling is still broad. Many Selenium exceptions can collapse into generic navigation or empty timeline failures.
- User impact: Users cannot tell whether to log in again, reduce count, update Chrome, wait, report selector breakage, or change settings.
- Mitigation:
  - Map common failure reasons to user-facing messages and next steps.
  - Include run log path and diagnostics options in errors.
  - Add empty-state classification for private/no posts/rate limit/login wall.
  - Preserve technical logs behind a copy/export support bundle.
- Files likely involved: `diagnostics.py`, `python_sidecar/service.py`, `python_sidecar/scraper.py`, `src/hooks/useScrapeEvents.ts`, `src/stores/logStore.ts`, `src/components/scrape/ScrapeProgress.tsx`
- Release decision: Ship with mitigation, but do not release with only generic errors.

### R10 - Privacy and Security

- Severity: Critical
- Likelihood: Medium
- Current evidence: The app handles scraped personal data, local exports, optional OpenAI API keys, browser cookies, disabled CSP, and broad shell permissions.
- User impact: Sensitive local data may be exposed, users may misunderstand data handling, or desktop attack surface may be wider than needed.
- Mitigation:
  - Add privacy documentation and data deletion controls.
  - Review Tauri capabilities and CSP.
  - Avoid storing API keys unless necessary and secure.
  - Keep credentials out of logs.
  - Document AI data transfer.
  - Consider OS-protected storage for cookies or explicit user consent.
- Files likely involved: `src-tauri/tauri.conf.json`, `src-tauri/capabilities/default.json`, `python_sidecar/session_manager.py`, `python_sidecar/ai_analyzer.py`, `src/components/settings/SettingsPanel.tsx`, `README.md`, `SECURITY.md`, `PRIVACY.md`
- Release decision: Block public release until reviewed.

### R11 - Dependency and Version Risk

- Severity: High
- Likelihood: Medium
- Current evidence: Runtime depends on Selenium, webdriver-manager, Chrome, ChromeDriver, Python, Tauri, WebView, Node, Rust, and optional OpenAI. There is no CI workflow.
- User impact: Builds or runtime fail after upstream version changes.
- Mitigation:
  - Add CI build/test matrix.
  - Document tested versions.
  - Pin or constrain dependencies where necessary.
  - Add release notes with tested Chrome/Python/app versions.
  - Validate ChromeDriver failure paths.
- Files likely involved: `requirements.txt`, `python_sidecar/requirements.txt`, `package.json`, `package-lock.json`, `src-tauri/Cargo.toml`, `.github/workflows/**`, `README.md`
- Release decision: Ship with mitigation after CI exists.

### R12 - Test Coverage Gaps

- Severity: High
- Likelihood: High
- Current evidence: Tests cover export helpers and diagnostics helpers only. No tests cover Selenium scrapers, sidecar protocol, Rust commands, frontend components, packaging, or manual live flows.
- User impact: Regressions reach users easily, especially in integration code.
- Mitigation:
  - Add CI for current tests/builds.
  - Add sidecar protocol tests.
  - Add Rust command/DB tests.
  - Add frontend smoke/component tests.
  - Add manual Windows and live-X checklist.
- Files likely involved: `tests/**`, `python_sidecar/service.py`, `src-tauri/src/commands/**`, `src-tauri/src/db/mod.rs`, `src/components/**`, `.github/workflows/**`, `RELEASE_CHECKLIST.md`
- Release decision: Block public release until minimum CI and manual release checklist exist.

### R13 - Product Claims and Placeholder Monetization

- Severity: High
- Likelihood: High
- Current evidence: License validation accepts prefixes, frontend copy mentions Pro/Pro+, CSV/Excel, scheduled scraping, and priority support, while the requested product is personal archiving.
- User impact: Users and reviewers may see the app as misleading or unfinished.
- Mitigation:
  - Remove paid-tier UI and placeholder claims for public release.
  - If licensing remains, implement real validation and feature gates.
  - Align README, onboarding, settings, and code.
  - Do not claim scheduling until scheduler commands/UI exist.
- Files likely involved: `src-tauri/src/commands/license.rs`, `src/hooks/useLicense.ts`, `src/components/settings/SettingsPanel.tsx`, `src/components/onboarding/OnboardingWizard.tsx`, `README.md`
- Release decision: Block public release until messaging matches implementation.

### R14 - Data Persistence, IDs, and History Re-Export

- Severity: High
- Likelihood: Medium
- Current evidence: Rust creates one scrape ID, sidecar creates another. `save_scrape_tweets` stores `date_str` as `date`. History export sends a scrape ID to sidecar export, but sidecar export uses in-memory `current_tweets`.
- User impact: History may be incomplete, incorrectly sorted, impossible to re-export after restart, or difficult to debug.
- Mitigation:
  - Use one scrape ID across Rust, Python, React, DB, logs, and exports.
  - Store ISO `date` and display `date_str` separately.
  - Re-export from SQLite via Rust or load DB tweets into the export layer.
  - Add DB and command tests.
- Files likely involved: `src-tauri/src/commands/scraper.rs`, `python_sidecar/service.py`, `src-tauri/src/commands/analytics.rs`, `src-tauri/src/db/mod.rs`, `src/components/history/HistoryList.tsx`, `src/hooks/useScrapeEvents.ts`, `src/stores/scrapeStore.ts`
- Release decision: Block public release until fixed.

## Top Release Blockers

1. Sidecar packaging and Python dependency strategy are not final-user ready.
2. Privacy/security review is incomplete for cookies, local data, API keys, CSP, and Tauri capabilities.
3. Export schema and metadata can drift or be wrong across export paths.
4. Dual scraper implementations increase selector and behavior drift.
5. Scrape IDs, persisted dates, and history re-export behavior are inconsistent.
6. Login/session status can be misleading.
7. Placeholder license and feature claims overstate shipped behavior.
8. Test coverage does not cover integration, frontend, Rust, packaging, or live manual workflows.
9. Desktop onboarding does not yet fully explain prerequisites, data storage, and platform limits.
10. X/Twitter automation fragility must be visible in UX and release notes.

## Risk Review Cadence

- Review all Critical and High risks before each release candidate.
- Any new selector breakage or packaging failure should update this file and `RELEASE_CHECKLIST.md`.
- No P0/Critical risk should be silently accepted in a public release.
