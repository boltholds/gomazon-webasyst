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
- [ ] Run final full CI and record exact test count.
