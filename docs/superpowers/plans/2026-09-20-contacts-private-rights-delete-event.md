# Contacts Private Rights Delete Event — Implementation Plan

Status: implemented
Date: 2026-09-20

- [x] Inspect the deferred `contacts_rights` boundary from the previous contact-delete design.
- [x] Pin the legacy Contacts handler and table schema to an explicit app-source commit.
- [x] Keep framework 4.2.0 and separately versioned Contacts source provenance distinct.
- [x] Add application-owned private-rights cleanup port, use case, and explicit success result.
- [x] Add typed Contacts compatibility event handler for `contacts.delete`.
- [x] Add isolated SQLAlchemy adapter for app-private `contacts_rights`.
- [x] Keep negative personal-principal encoding inside infrastructure.
- [x] Add explicit Contacts bundled runtime module.
- [x] Select/link Contacts only when present in the canonical installed-app snapshot.
- [x] Register Contacts in the default finite known-factory set.
- [x] Preserve canonical installed-application order when linking known modules.
- [x] Unit-test handler payload/result behavior.
- [x] Integration-test private-rights SQL cleanup and unrelated-row preservation.
- [x] Integration-test real `DeleteContacts -> contacts.delete -> Contacts cleanup -> core cleanup`.
- [x] Add architecture guard preventing `contacts_rights` ownership from leaking into core persistence.
- [x] Add source-characterization fixture/test.
- [x] Record ADRs for private-rights ownership and runtime ordering.
- [x] Run full CI.

## Verification record

Final code head before completion-documentation commits: `c7ef99a796c6c49fdd54ed6f4151077d51d17110`.

GitHub Actions completed successfully on that head:

- source-tree compile passed;
- `831 passed, 9 warnings`;
- Contacts 1.1.7 app-source characterization passed;
- positive immutable contact ids remain above infrastructure;
- SQL cleanup removes only matching negative personal `group_id` rows;
- real contact deletion reaches the installed Contacts runtime handler;
- core contact deletion still completes after the event;
- canonical installed-app ordering overrides known-factory declaration order;
- core contact repository remains free of app-private `contacts_rights` ownership.
