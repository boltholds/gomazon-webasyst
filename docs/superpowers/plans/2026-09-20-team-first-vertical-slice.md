# Team First Bundled-App Vertical Slice — Implementation Plan

Status: implemented
Date: 2026-09-20

**Goal:** migrate `team.groups.getList` as the first real bundled Webasyst app endpoint through production runtime, ACL and legacy persistence.

- [x] Pin exact Webasyst 4.2.0 Team manifest and `team.groups.getList` source behavior.
- [x] Verify inherited `waAPIMethod` HTTP method is GET.
- [x] Add Team API contracts with explicit nullable-description variants.
- [x] Add narrow `TeamGroupReader` application port.
- [x] Add `ListVisibleTeamGroups` using the shared `RightsEvaluator`.
- [x] Add SQLAlchemy Team group reader over existing `wa_group`.
- [x] Add Webasyst Team filter parser.
- [x] Add Webasyst Team API response projector.
- [x] Add explicit `composition/team.py` runtime module.
- [x] Add installed-aware selection of known Python bundled-app runtime modules.
- [x] Keep explicit runtime-module injection for tests and linker-negative cases.
- [x] Preserve repeated legacy API query parameters.
- [x] Unit-test exact/right-fallback/full-access/type-filter semantics.
- [x] Integration-test legacy sort order and nullable description normalization.
- [x] Test exact Team API response projection.
- [x] Prove production ASGI flow with real legacy tables/token/ACL.
- [x] Prove repeated `filter[type][]` transport.
- [ ] Run final full CI on completion head and record exact count.
- [ ] Update `AGENTS.md` completion state.

## Follow-on

Next Team slice should add one source-characterized Team event bridge, preferably the `contacts.delete -> team.contacts_delete` relay, which will exercise nested event publishing without introducing UI/template concerns.
