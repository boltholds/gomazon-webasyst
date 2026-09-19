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
- [x] Run final full CI on completion head and record exact count.
- [x] Update `AGENTS.md` completion state.

## Verification record

Final code head before completion-documentation commits: `d795762d8b208a5c01e31147e15fb53e80ac0ab7`.

GitHub Actions completed successfully on that head:

- source-tree compile passed;
- `800 passed, 9 warnings`;
- exact Webasyst 4.2.0 Team characterization passed;
- Team application architecture guards passed;
- SQL legacy group projection passed;
- rights/fallback/full-access semantics passed;
- scalar, repeated, trimmed, and explicit-empty type filters passed;
- GET-only behavior passed;
- production `create_app_with_settings()` ASGI path linked Team from `apps.php`, resolved a real legacy API token, authorized Team, read legacy `wa_group`/`wa_contact_rights`, and returned the characterized response.

## Follow-on

Next Team slice should add one source-characterized Team event bridge, preferably the `contacts.delete -> team.contacts_delete` relay, which will exercise nested event publishing without introducing UI/template concerns.
