# Team users.getList — Implementation Plan

Status: implemented
Date: 2026-09-20

- [x] Pin `team.users.getList` to Webasyst 4.2.0 release source.
- [x] Characterize users-vs-group candidate selection.
- [x] Characterize scalar/list/associative access filters.
- [x] Characterize actor visibility and candidate access principal differences.
- [x] Characterize wildcard `manage_users_in_group.%` without scalar `.all` fallback.
- [x] Characterize display-name settings and final ordering.
- [x] Characterize email/phone/group/event/online enrichment.
- [x] Characterize API userpic workup and environment-sensitive resource URL branches.
- [x] Add explicit Team user presence/value contracts.
- [x] Add `TeamUserFilter` and typed limited/full requirements.
- [x] Add narrow `TeamUserReader` port.
- [x] Add `ListVisibleTeamUsers`.
- [x] Keep actor visibility and candidate app-access evaluation separate.
- [x] Keep candidate access free of guest-principal leakage.
- [x] Preserve wildcard rights semantics with exact assignments.
- [x] Remove nullable parser helper result contracts after architecture gate caught them.
- [x] Add SQLAlchemy Team user projection.
- [x] Add deterministic clock/server-timezone handling.
- [x] Add legacy query filter parser.
- [x] Add compatibility response/media projector.
- [x] Register `team.users.getList` as GET in Team runtime.
- [x] Inject canonical installed-app catalog into Team users policy.
- [x] Add public-root/server-timezone composition settings.
- [x] Unit-test policy/filter/API projection.
- [x] Integration-test SQL projection/enrichment.
- [x] Production-ASGI test real token/catalog/ACL/filter/group/GET-only flow.
- [x] Update architecture decisions.
- [x] Run full CI.

## Verification record

Final code head before completion-documentation commits: `d65d6ec0002b6b15a5b764f33480736a8fd08813`.

GitHub Actions completed successfully on that head:

- source-tree compile passed;
- `848 passed, 9 warnings`;
- exact Webasyst 4.2.0 Team users characterization passed;
- architecture no-optional-result guard passed;
- users and group candidate modes passed;
- actor wildcard visibility including no-`.all` fallback passed;
- candidate access AND/limited/full/no-guest semantics passed;
- SQL enrichment/name/event/online/UTC projection passed;
- exact API response projection and UI 2.0 userpics passed;
- production `/api.php/team.users.getList` passed with real legacy token, app catalog, ACL tables and filters;
- POST rejection for GET-only method passed.

## Explicit deferred resource variants

The first resource resolver covers configurable absolute-root direct public thumbnails. CDN URL selection and legacy non-`mod_rewrite` `thumb.php` fallback remain later compatibility adapters and are not included in the parity claim above.
