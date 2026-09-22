# Team contacts.contacts_collection relay — Implementation Plan

Status: implemented
Date: 2026-09-22

- [x] Source-characterize the Webasyst 4.2.0 Team handler.
- [x] Characterize `waEvent::run()` non-null result-array semantics.
- [x] Add exact `team.contacts_collection` nested publication.
- [x] Preserve payload object identity.
- [x] Return an explicit outer boolean payload for both true and false.
- [x] Base outer boolean on nested result presence rather than nested payload truthiness.
- [x] Preserve failure-without-result as false.
- [x] Register `contacts.contacts_collection` in the installed Team runtime.
- [x] Add unit coverage for empty/result-false/failure nested reports.
- [x] Add runtime-registration coverage.
- [x] Record the result-presence relay rule in AGENTS.md.
- [x] Run full CI.

## Verification record

Initial implementation head: `26786d7f990745ed0e606b1208c0a9cc90dd19b8`.

GitHub Actions on that head passed:

- source-tree compile;
- **894 passed, 11 warnings**;
- source characterization;
- nested false-payload result-presence regression;
- nested failure/no-result regression;
- explicit Team runtime registration.
