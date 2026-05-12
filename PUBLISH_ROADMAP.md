# Publish Roadmap

## Release Goal
Turn the current X/Twitter Scraper into a polished, honest, final-user-publishable desktop app for personal archiving. The release should prioritize reliability, packaging, privacy, and supportability over new features.

## Priority Model
- P0: Blocks public release or causes high user harm/confusion.
- P1: Needed for a polished release but can ship after P0 if clearly documented.
- P2: Nice-to-have polish, portfolio quality, or future expansion.

## Phase 0 - Stabilize Understanding

| Item | Priority | Effort | Risk | Expected user impact | Files likely involved |
| --- | --- | --- | --- | --- | --- |
| Write an architecture map for CLI, sidecar, Tauri, React, SQLite, exports, and logs. | P0 | Small | Low | Gives maintainers and reviewers a shared mental model before changes. | `PROJECT_CONTEXT.md`, `README.md` |
| Document known limitations of X web automation, selectors, login, rate limits, long tweets, articles, and bookmarks. | P0 | Small | Low | Sets realistic expectations and reduces support churn. | `README.md`, `PROJECT_CONTEXT.md`, `RISK_REGISTER.md` |
| Define release criteria for desktop publish readiness. | P0 | Small | Low | Prevents shipping based on UI appearance alone. | `RELEASE_CHECKLIST.md`, `PUBLISH_ROADMAP.md` |
| Document export schema ownership and compatibility policy. | P0 | Medium | Medium | Protects users relying on JSON exports. | `export_schema.py`, `document_generator.py`, `src/components/scrape/ScrapeResults.tsx`, `README.md` |
| Document sidecar protocol and event names. | P1 | Medium | Medium | Makes Python/Rust/React integration easier to test and debug. | `python_sidecar/service.py`, `src-tauri/src/sidecar/mod.rs`, `src/hooks/useScrapeEvents.ts` |
| Inventory shipped vs placeholder product claims. | P0 | Small | Low | Prevents misleading license, scheduling, CSV/Excel, or AI claims. | `src/hooks/useLicense.ts`, `src/components/settings/SettingsPanel.tsx`, `src/components/onboarding/OnboardingWizard.tsx`, `README.md` |

## Phase 1 - Core Reliability

| Item | Priority | Effort | Risk | Expected user impact | Files likely involved |
| --- | --- | --- | --- | --- | --- |
| Decide one scraper owner: unify `scraper.py` and `python_sidecar/scraper.py`, or make one explicitly legacy. | P0 | Large | High | Reduces behavior drift between CLI and desktop. | `scraper.py`, `python_sidecar/scraper.py`, `main.py`, `python_sidecar/service.py`, `tests/` |
| Fix bookmark JSON metadata so exports can set `scrape_type: "bookmarks"`. | P0 | Small | Low | Prevents incorrect archive metadata. | `export_schema.py`, `document_generator.py`, `main.py`, `python_sidecar/service.py`, `tests/test_exports.py` |
| Make export generation single-source or add strict parity tests for Python and desktop-generated exports. | P0 | Medium | Medium | Users get consistent JSON/Markdown/DOCX regardless of export path. | `document_generator.py`, `export_schema.py`, `src/components/scrape/ScrapeResults.tsx`, `src-tauri/src/commands/export.rs`, `tests/` |
| Add selector diagnostics as a visible preflight and post-failure tool in desktop UX. | P0 | Medium | Medium | Users can understand whether X UI changed instead of seeing generic failure. | `diagnostics.py`, `config.py`, `python_sidecar/service.py`, `src/components/scrape/ScrapeProgress.tsx`, `src/components/settings/SettingsPanel.tsx` |
| Normalize retry/backoff and stop conditions for timeline scrolling. | P0 | Medium | High | Reduces hangs, duplicate attempts, and confusing empty exports. | `python_sidecar/scraper.py`, `scraper.py`, `diagnostics.py` |
| Improve empty-state classification for login wall, private profile, blocked profile, no posts, no bookmarks, and rate limit/interstitial. | P0 | Medium | High | Converts failed scrapes into actionable user guidance. | `python_sidecar/scraper.py`, `scraper.py`, `diagnostics.py`, `src/hooks/useScrapeEvents.ts`, `src/components/scrape/ScrapeProgress.tsx` |
| Make partial result recovery explicit for desktop cancellation/errors. | P0 | Medium | Medium | Protects long-running user work when X or Chrome fails. | `python_sidecar/service.py`, `python_sidecar/scraper.py`, `src/stores/scrapeStore.ts`, `src/components/scrape/ScrapeProgress.tsx`, `src/components/scrape/ScrapeResults.tsx` |
| Reconcile Rust scrape ID and Python sidecar scrape ID. | P0 | Medium | Medium | Prevents history/export/debug confusion. | `src-tauri/src/commands/scraper.rs`, `python_sidecar/service.py`, `src/stores/scrapeStore.ts`, `src/hooks/useScrapeEvents.ts`, `src-tauri/src/commands/analytics.rs` |
| Fix persisted tweet date storage and sorting. | P0 | Small | Medium | Makes history, analytics, and re-export reliable. | `src-tauri/src/commands/analytics.rs`, `src-tauri/src/db/mod.rs`, `src/components/history/HistoryList.tsx`, `src/components/analytics/AnalyticsDashboard.tsx` |
| Harden session handling and add clear session reset/delete controls. | P0 | Medium | High | Improves privacy and helps users recover from broken cookies. | `python_sidecar/session_manager.py`, `python_sidecar/service.py`, `src-tauri/src/commands/auth.rs`, `src/components/settings/SettingsPanel.tsx`, `README.md` |
| Remove automatic username/password login from final UX unless there is a clear security story. | P1 | Medium | Medium | Reduces credential-handling risk and simplifies support. | `main.py`, `scraper.py`, `python_sidecar/scraper.py`, `src/components/scrape/ScrapeConfig.tsx`, `README.md` |
| Improve logging for stage transitions, selector names, saved paths, partial status, and support bundles. | P1 | Medium | Medium | Makes failures diagnosable without exposing credentials. | `diagnostics.py`, `python_sidecar/service.py`, `src/stores/logStore.ts`, `src/components/scrape/ScrapeProgress.tsx` |

## Phase 2 - Desktop UX Polish

| Item | Priority | Effort | Risk | Expected user impact | Files likely involved |
| --- | --- | --- | --- | --- | --- |
| Rewrite onboarding around real prerequisites, privacy, local storage, X limitations, and first-run checks. | P0 | Medium | Medium | Prevents first-run confusion and unsafe assumptions. | `src/components/onboarding/OnboardingWizard.tsx`, `src-tauri/src/commands/settings.rs`, `README.md` |
| Add first-run checks for Chrome, Python/sidecar runtime strategy, output write access, and dependency state. | P0 | Medium | High | Users learn what is missing before a scrape fails. | `src-tauri/src/commands/settings.rs`, `src-tauri/src/sidecar/mod.rs`, `src/components/onboarding/OnboardingWizard.tsx`, `src/components/settings/SettingsPanel.tsx` |
| Clean up settings into browser, output, session/privacy, diagnostics, language, and advanced sections. | P1 | Medium | Medium | Makes the app understandable for non-technical users. | `src/components/settings/SettingsPanel.tsx`, `src/stores/settingsStore.ts`, `src/hooks/useSettings.ts` |
| Align settings persistence to one authoritative source or define sync rules. | P0 | Medium | Medium | Avoids stale localStorage vs SQLite behavior. | `src/stores/settingsStore.ts`, `src/hooks/useSettings.ts`, `src-tauri/src/commands/settings.rs`, `src-tauri/src/db/mod.rs` |
| Improve scrape configuration validation and guidance. | P1 | Small | Low | Prevents bad usernames, impossible date ranges, and overlarge requests. | `src/components/scrape/ScrapeConfig.tsx`, `src/stores/scrapeStore.ts` |
| Replace optimistic progress with stage-aware progress and indeterminate mode for bookmarks/all/date-range. | P1 | Medium | Medium | Users get accurate expectations on long or unknown-length scrapes. | `src/components/scrape/ScrapeProgress.tsx`, `python_sidecar/service.py`, `python_sidecar/scraper.py` |
| Add clear result statuses: completed, partial, cancelled, failed, empty, diagnostics available. | P0 | Medium | Medium | Users can trust what an export represents. | `src/stores/scrapeStore.ts`, `src/components/scrape/ScrapeResults.tsx`, `python_sidecar/service.py`, `diagnostics.py` |
| Rework export UX around JSON as primary and Markdown/DOCX as secondary. | P1 | Medium | Medium | Reduces schema drift and makes export choices clear. | `src/components/scrape/ScrapeResults.tsx`, `src-tauri/src/commands/export.rs`, `document_generator.py`, `export_schema.py` |
| Make history re-export load tweets from SQLite instead of sidecar memory. | P0 | Medium | Medium | Allows old scrapes to be exported after app restart. | `src/components/history/HistoryList.tsx`, `src-tauri/src/commands/analytics.rs`, `src-tauri/src/commands/export.rs`, `src-tauri/src/db/mod.rs` |
| Remove or clearly hide placeholder license, CSV/Excel, scheduled scraping, and unsupported paid-tier copy. | P0 | Small | Low | Avoids misleading users and reviewers. | `src/hooks/useLicense.ts`, `src/components/settings/SettingsPanel.tsx`, `src/components/onboarding/OnboardingWizard.tsx`, `src/components/ai/AIAnalysis.tsx` |
| Improve non-technical error messages with direct next actions. | P1 | Medium | Medium | Users can recover from login, Chrome, selector, output, and permission failures. | `diagnostics.py`, `python_sidecar/service.py`, `src/hooks/useScrapeEvents.ts`, `src/components/scrape/ScrapeProgress.tsx` |
| Finish i18n coverage or ship one language intentionally. | P2 | Medium | Low | Reduces mixed-language UI. | `src/locales/en.json`, `src/locales/tr.json`, `src/components/**` |

## Phase 3 - Packaging and Release

| Item | Priority | Effort | Risk | Expected user impact | Files likely involved |
| --- | --- | --- | --- | --- | --- |
| Choose sidecar distribution strategy: embedded Python app, bundled executable, or documented external Python requirement. | P0 | Large | High | Determines whether final users can run the app at all. | `src-tauri/tauri.conf.json`, `src-tauri/src/sidecar/mod.rs`, `python_sidecar/**`, `requirements.txt`, `python_sidecar/requirements.txt` |
| Bundle or declare required Python modules and root helper files used by the sidecar. | P0 | Large | High | Prevents missing-file and missing-package failures in installer builds. | `python_sidecar/service.py`, `document_generator.py`, `export_schema.py`, `diagnostics.py`, `config.py`, `src-tauri/tauri.conf.json` |
| Define Chrome and ChromeDriver expectations for final users. | P0 | Medium | High | Reduces first-run failures and support requests. | `src-tauri/src/commands/settings.rs`, `config.py`, `python_sidecar/scraper.py`, `README.md` |
| Add robust sidecar discovery independent of current working directory. | P0 | Medium | High | Desktop shortcuts and installed apps can start reliably. | `src-tauri/src/sidecar/mod.rs`, `src-tauri/tauri.conf.json` |
| Review Tauri capabilities and restore a CSP suitable for production. | P0 | Medium | High | Reduces desktop attack surface. | `src-tauri/tauri.conf.json`, `src-tauri/capabilities/default.json`, `src-tauri/src/lib.rs` |
| Align product name, identifier, version, author, app icon, window title, UI About, package, and Cargo metadata. | P0 | Small | Low | Creates a professional, consistent installer and release. | `package.json`, `src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json`, `src/components/settings/SettingsPanel.tsx`, `src-tauri/icons/**` |
| Build a Windows installer on a clean machine or CI runner. | P0 | Medium | High | Proves the artifact is installable outside the dev machine. | `src-tauri/tauri.conf.json`, `.github/workflows/**`, `package.json` |
| Add first-run and post-install smoke tests. | P0 | Medium | High | Catches missing sidecar, Python, Chrome, permissions, and output failures. | `RELEASE_CHECKLIST.md`, `src-tauri/src/commands/settings.rs`, `src/components/onboarding/OnboardingWizard.tsx` |
| Decide update strategy: manual GitHub releases first, auto-update later. | P1 | Small | Medium | Avoids prematurely supporting update infrastructure. | `README.md`, `CHANGELOG.md`, `src-tauri/tauri.conf.json` |
| Create release notes template with known limitations and verification status. | P1 | Small | Low | Users understand what changed and what remains fragile. | `CHANGELOG.md`, `.github/release.yml`, `README.md` |
| Remove absolute/local build assumptions from Cargo config. | P1 | Small | Medium | Makes builds reproducible for CI and contributors. | `src-tauri/.cargo/config.toml`, `.github/workflows/**` |

## Phase 4 - QA and Test

| Item | Priority | Effort | Risk | Expected user impact | Files likely involved |
| --- | --- | --- | --- | --- | --- |
| Add CI for Python unit tests, Python compile checks, frontend build, and Rust build/tests. | P0 | Medium | Medium | Prevents simple regressions from reaching release artifacts. | `.github/workflows/**`, `package.json`, `requirements.txt`, `src-tauri/Cargo.toml` |
| Add sidecar protocol unit tests without launching Chrome. | P0 | Medium | Medium | Validates command/response behavior, errors, export, pause/cancel, and IDs. | `python_sidecar/service.py`, `python_sidecar/models.py`, `tests/` |
| Add scraper parser tests using saved/static DOM fixtures where possible. | P1 | Large | High | Catches selector drift without live X dependency. | `python_sidecar/scraper.py`, `scraper.py`, `tests/fixtures/**`, `config.py` |
| Add export compatibility tests for JSON schema, Markdown, DOCX, bookmarks metadata, and desktop-generated exports. | P0 | Medium | Medium | Protects archive quality. | `export_schema.py`, `document_generator.py`, `src/components/scrape/ScrapeResults.tsx`, `tests/test_exports.py` |
| Add Rust command and DB tests. | P1 | Medium | Medium | Catches data persistence and serde naming bugs. | `src-tauri/src/commands/*.rs`, `src-tauri/src/db/mod.rs` |
| Add frontend component tests for onboarding, scrape config, progress, results export, history, and settings. | P1 | Medium | Medium | Reduces UI regressions. | `src/components/**`, `src/stores/**`, `package.json` |
| Create manual Windows install test matrix. | P0 | Small | Low | Ensures clean-machine readiness. | `RELEASE_CHECKLIST.md` |
| Create logged-in X session manual test matrix. | P0 | Medium | High | Validates the real user flow that tests cannot safely automate. | `RELEASE_CHECKLIST.md`, `RISK_REGISTER.md` |
| Create regression checklist for long tweets, articles, media, bookmarks, empty states, private profiles, cancellation, and partial saves. | P0 | Medium | High | Reduces false confidence before release. | `RELEASE_CHECKLIST.md`, `diagnostics.py`, `python_sidecar/scraper.py` |
| Add support bundle or diagnostics export for bug reports. | P1 | Medium | Medium | Speeds triage without asking users for raw screenshots/logs. | `diagnostics.py`, `python_sidecar/service.py`, `src/components/settings/SettingsPanel.tsx` |

## Phase 5 - Public GitHub and Portfolio Polish

| Item | Priority | Effort | Risk | Expected user impact | Files likely involved |
| --- | --- | --- | --- | --- | --- |
| Rewrite README around final desktop install, CLI/dev usage, privacy, limitations, and troubleshooting. | P0 | Medium | Low | Makes the project credible and usable. | `README.md`, `PROJECT_CONTEXT.md` |
| Add screenshots and a short GIF/demo of the happy path. | P1 | Medium | Low | Helps users and portfolio viewers understand the app. | `README.md`, `docs/assets/**` |
| Create a demo video outline showing install, login, scrape, logs, results, and export. | P2 | Small | Low | Improves portfolio presentation. | `docs/demo-video-outline.md`, `README.md` |
| Add disclaimer section and responsible-use policy. | P0 | Small | Low | Sets ethical and legal boundaries. | `README.md`, `SECURITY.md` or `PRIVACY.md` |
| Confirm license choice and third-party attribution. | P0 | Small | Low | Avoids legal ambiguity. | `LICENSE`, `README.md`, `package.json`, `src-tauri/Cargo.toml` |
| Add issue templates for bug report, selector breakage, packaging issue, and feature request. | P1 | Small | Low | Improves support quality. | `.github/ISSUE_TEMPLATE/**` |
| Add roadmap and changelog. | P1 | Small | Low | Shows maintained direction without overpromising. | `PUBLISH_ROADMAP.md`, `CHANGELOG.md` |
| Add release page checklist and artifact verification notes. | P1 | Small | Low | Makes GitHub releases repeatable. | `RELEASE_CHECKLIST.md`, `.github/release.yml` |
| Remove or mark non-shipping monetization and AI claims before portfolio publication. | P0 | Small | Low | Keeps public messaging honest. | `README.md`, `src/components/settings/SettingsPanel.tsx`, `src/components/onboarding/OnboardingWizard.tsx`, `src/hooks/useLicense.ts` |

## Recommended First Sprint

The first sprint should not add features. It should make the app honest, runnable, and testable:

1. Fix export metadata and export parity.
2. Reconcile scrape IDs and history persistence.
3. Decide the sidecar packaging strategy.
4. Remove or hide placeholder product claims.
5. Add CI for existing tests/builds.
6. Write first-run privacy/prerequisite documentation.

## Do Not Prioritize Yet

- Paid licensing, Pro tiers, and CSV/Excel if the personal archiving product is not commercialized.
- Scheduling until basic manual scraping and packaging are reliable.
- Automated live-X tests in CI, because they are brittle, account-risky, and likely violate good test hygiene.
- More AI analysis until local archiving, privacy, and export correctness are stable.
- Large UI redesigns before core flow, packaging, and error handling are dependable.
