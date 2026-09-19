# Team Directory Read Implementation Plan

Status: active
Date: 2026-09-20
Spec: docs/superpowers/specs/2026-09-20-team-directory-read-design.md
Authoritative source: Webasyst Framework 4.2.0 release commit 39c267a2fabfb0cd6d94f4dd86b23b4750328dd5.

## Global constraints

- No backend HTML/Smarty work in this slice.
- No PHP execution or PHP class-name discovery.
- Team application code imports no FastAPI, Starlette, SQLAlchemy, or Webasyst compatibility modules.
- Use separate Team read models; do not inflate generic ContactRead.
- Preserve negative Team group visibility rights.
- Batch memberships, access, presence and current-event reads; avoid per-user N+1.
- Expected absence uses typed variants.
- Team runtime module is linked only when Team is installed.
- Existing API Execution owns token, app access, scope and rendering.
- PHP bracket decoding is a generic compatibility improvement and must not regress token, format or callback handling.

### Task 0: Pin exact Team 2.3.4 characterization

Files:
- docs/superpowers/specs/2026-09-20-team-directory-read-characterization.md
- tests/fixtures/webasyst_4_2/team_directory/
- tests/compatibility/test_team_directory_characterization.py

- [ ] Extract minimal source-backed Team manifest/API/users/rights/event fixtures.
- [ ] Record exact source/behavior/implementation-consequence table.
- [ ] Pin users.getList and groups.getList method names and GET behavior.
- [ ] Pin keepVisible, access filter and group visibility inequalities.
- [ ] Pin online, current-event and contact photo behavior.
- [ ] Pin contacts.contacts_collection bridge.
- [ ] Commit characterization.

### Task 1: Decode PHP bracket API parameters without data loss

Files:
- compatibility/webasyst/api/services/parameter_decoder.py
- presentation/http/legacy_api.py
- tests/unit/test_legacy_api_parameter_decoder.py

- [ ] RED nested list group_id values.
- [ ] RED access list and associative access values.
- [ ] RED type list values.
- [ ] RED scalar/nested shape collision.
- [ ] RED depth/entry/key/value limits.
- [ ] Implement ordered bounded decoder.
- [ ] Use query multi_items and ordered form pairs.
- [ ] Run existing API/OAuth transport tests.
- [ ] Commit decoder.

### Task 2: Add typed API request origin

Files:
- application/api_execution/vo/origin.py
- application/api_execution/composites/invocation.py
- application/api_execution/composites/pipeline.py
- presentation/http/legacy_api.py
- focused API tests

- [ ] RED absolute origin validation.
- [ ] RED request and context carry the same origin.
- [ ] Presentation derives origin without passing Request downward.
- [ ] Update direct invocation fixtures.
- [ ] Run API Execution suite.
- [ ] Commit API origin.

### Task 3: Team domain entities, filters and serialized contracts

Create application/team_directory and contracts/team_directory.py.

- [ ] TeamUser and TeamGroup Entities.
- [ ] Team email/phone/current-event/last-seen value states.
- [ ] TeamOnlineStatus and TeamAccessLevel EnumStr domains.
- [ ] AllTeamUsers vs TeamUsersInGroups explicit filter modes.
- [ ] TeamUsersFilter and TeamGroupsFilter.
- [ ] Pydantic legacy API read DTOs.
- [ ] Architecture taxonomy/import guards.
- [ ] Commit Team contracts.

### Task 4: Application-owned Team read ports

Create narrow batch ports:
- TeamDirectoryReader
- TeamMembershipReader
- TeamUserAppAccessReader
- TeamPrincipalGroupRightsReader
- TeamPresenceReader
- TeamCurrentEventReader

- [ ] No SQLAlchemy types.
- [ ] Explicit current-event missing/present.
- [ ] Batch operations where list behavior requires batch semantics.
- [ ] No Optional lookup/result states.
- [ ] Commit ports.

### Task 5: Team visibility/access/online Services

- [ ] Full Team admin sees all candidate users/groups.
- [ ] Current principal always sees self.
- [ ] Group-less target user visible.
- [ ] All-groups-hidden target omitted.
- [ ] At least one visible group target visible.
- [ ] Access limited means >=1; full means >1.
- [ ] Global Webasyst admin satisfies app access filters.
- [ ] Idle requires recent activity plus open login and idle_since older than 60 seconds.
- [ ] Commit pure Services.

### Task 6: Extend infrastructure-private legacy mappings

Add WaContactSettingRow, WaLoginLogRow, WaContactCalendarRow, WaContactEventRow.

- [ ] Pin exact 4.2.0 table/column/nullability subset.
- [ ] SQLite mapping creation tests.
- [ ] No schema migrations.
- [ ] Commit mappings.

### Task 7: SQLAlchemy Team directory reader

- [ ] Active users only.
- [ ] Any-group filter with duplicate-safe ids.
- [ ] Deterministic name order.
- [ ] Ordered email rows.
- [ ] Ordered phone rows.
- [ ] Group id enrichment.
- [ ] Ordered group listing.
- [ ] Commit reader.

### Task 8: SQLAlchemy batch Team access/visibility readers

- [ ] Personal + group max semantics for target-user app access.
- [ ] Webasyst global admin override.
- [ ] Unknown app yields no access.
- [ ] Current-principal manage_users_in_group negative exact rights.
- [ ] .all fallback.
- [ ] Full Team app admin visibility.
- [ ] Commit access readers.

### Task 9: SQLAlchemy presence/current-event readers

- [ ] Recent last_datetime produces online.
- [ ] Open login plus stale idle_since produces idle.
- [ ] Old/absent activity produces offline.
- [ ] Timed current status event.
- [ ] All-day current status event.
- [ ] All-day desc/start asc selection.
- [ ] Explicit no-current-event state.
- [ ] Commit readers.

### Task 10: ListTeamUsers and ListTeamGroups Composites

- [ ] Candidate read then principal visibility then access filter.
- [ ] Presence/current-event enrichment.
- [ ] Type + principal group visibility for groups.
- [ ] Unit tests with batch fakes.
- [ ] Assert no N+1 port usage pattern.
- [ ] Commit use cases.

### Task 11: Team legacy API filter parsing/projectors

- [ ] group_id scalar/list and non-positive drop.
- [ ] access scalar/list defaults to limited.
- [ ] associative limited/full accepted; invalid levels ignored.
- [ ] group type parsing.
- [ ] User/group JSON projection.
- [ ] Commit API compatibility normalization.

### Task 12: Team user resource URL policy

- [ ] No-photo UI 2.0 fallback.
- [ ] Contact photo directory layout.
- [ ] 16/32/96/144 thumbnails.
- [ ] original_crop.
- [ ] Combine with ApiRequestOrigin.
- [ ] Explicit mod_rewrite mode.
- [ ] Commit resource projection.

### Task 13: Team API method handlers

- [ ] Register GET team.users.getList.
- [ ] Register GET team.groups.getList.
- [ ] users returns pure array rather than id map.
- [ ] groups returns pure array.
- [ ] Reuse existing ApiMethodSucceeded/Rejected.
- [ ] Commit handlers.

### Task 14: contacts_collection Team event bridge

- [ ] Subscribe to contacts.contacts_collection.
- [ ] Nested dispatch team.contacts_collection.
- [ ] Return false with no nested result.
- [ ] Return true when nested dispatch yields any result.
- [ ] Prove no recursion.
- [ ] Commit bridge.

### Task 15: Dependency-aware runtime module factory

- [ ] Build event registry/dispatcher before default modules.
- [ ] Explicit composition-only module factory receives EventDispatcher.
- [ ] Keep static module factory for tests.
- [ ] No global registration.
- [ ] Existing runtime tests remain green.
- [ ] Commit runtime factory refactor.

### Task 16: Production Team runtime module

- [ ] Team SQL adapters/use cases built from session factory.
- [ ] Runtime module contributes two API methods and one event handler.
- [ ] Team must be installed for linker to accept module.
- [ ] No backend dispatch contribution yet.
- [ ] Commit production Team module.

### Task 17: End-to-end Team API integration

Seed legacy-shaped SQLite data with active/banned/non-user contacts, groups, memberships, rights, emails/phones, presence/current event and API token.

- [ ] GET /api.php/team.users.getList.
- [ ] bracket group filter.
- [ ] bracket access filter.
- [ ] hidden-group principal visibility.
- [ ] request-origin userpic URLs.
- [ ] GET /api.php/team.groups.getList.
- [ ] negative group right hides group.
- [ ] Existing JSON/XML renderer remains framework-owned.
- [ ] Commit API vertical tests.

### Task 18: Event bridge integration

- [ ] Link Team plus test team.contacts_collection subscriber.
- [ ] Emit contacts.contacts_collection.
- [ ] Verify false/true bridge result semantics.
- [ ] Commit event vertical test.

### Task 19: Architecture/security guards

- [ ] Team application package has no transport/ORM/compatibility dependencies.
- [ ] Team SQL adapters remain infrastructure-private.
- [ ] Team methods register only through runtime module.
- [ ] No dynamic PHP/Python loading.
- [ ] No backend template/routing work accidentally included.
- [ ] No Optional operation result contracts.
- [ ] Commit guards.

### Task 20: Full acceptance

- [ ] Compile source tree.
- [ ] Run full pytest.
- [ ] Run focused Team/API/runtime/ACL suites.
- [ ] Record exact passing count.
- [ ] Mark spec implemented.
- [ ] Mark plan complete.
- [ ] Update AGENTS with first real bundled-app slice boundary/completion.
- [ ] Commit verification record.

## Completion definition

Complete only when real Team 2.3.4 API reads and the contacts collection bridge are linked through production Python runtime, use legacy-shaped data, preserve characterized filtering/ACL behavior, and full CI is green.
