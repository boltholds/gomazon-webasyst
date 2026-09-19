# Team contacts.delete Nested Event Slice — Implementation Plan

Status: implemented
Date: 2026-09-20

- [x] Characterize `teamContactsDeleteHandler` against exact Webasyst 4.2.0 source.
- [x] Add application-owned `EventPublisher` port.
- [x] Make `EventDispatcher` implement nested publication.
- [x] Replace prebuilt production bundled modules with explicit installed-aware runtime factories.
- [x] Validate factory declared app id against built module app id.
- [x] Add `TeamContactsDeleteRelayHandler`.
- [x] Register exact `contacts.delete` Team event definition.
- [x] Preserve exact payload object for nested publication.
- [x] Return `EventHandlerNoResult` and ignore nested result projection.
- [x] Unit-test Team relay.
- [x] Integration-test nested dispatch into a linked Python handler.
- [x] Test factory not invoked for an uninstalled app.
- [x] Test factory identity mismatch fails startup.
- [x] Add source-characterization executable fixture.
- [x] Update architecture record/ADR.
- [x] Run final full CI and record exact test count.


## Verification record

Final code head before completion-documentation commits: `af25c4822797d73afb546ab0b65f8d9df65b63f3`.

GitHub Actions completed successfully on that head:

- source-tree compile passed;
- `809 passed, 9 warnings`;
- exact Webasyst 4.2.0 Team contacts-delete characterization passed;
- Team relay publishes `team.contacts_delete` with the exact same payload object;
- nested handler execution is proven through the real linked EventDispatcher;
- nested results do not leak into the outer `contacts.delete` result;
- uninstalled known runtime factories are not invoked;
- runtime factory identity mismatch fails startup;
- nested-event architecture guards passed;
- existing Team groups API and all earlier framework slices remain green.
