# Team Directory Read — First Bundled Application Vertical Slice

Status: accepted baseline
Date: 2026-09-20
Repository: `boltholds/gomazon-webasyst`
Application: Webasyst Team 2.3.4
Authoritative framework/application commit: `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`

## 1. Goal

Migrate the first real bundled Webasyst application behavior into the Python runtime.

The slice implements three real Team 2.3.4 surfaces:

1. `GET /api.php/team.users.getList`;
2. `GET /api.php/team.groups.getList`;
3. Team's `contacts.contacts_collection` event bridge.

This is a read-only vertical slice. It must use the existing legacy Webasyst relational schema and the new explicit `ApplicationRuntimeModule` system.

It is deliberately not a Team rewrite. Invitations, user creation/deletion, profile editing, calendar mutation, access administration, backend Smarty pages, plugin settings, and Team backend route rendering are later slices.

## 2. Why this is the first application slice

Team is identity-adjacent and exercises framework foundations already migrated:

- `wa_contact`;
- contact emails/data;
- groups and memberships;
- numeric Webasyst ACL;
- API credential/auth execution;
- installed application validation;
- application runtime linking;
- event dispatch.

It therefore proves that the Python framework can host a real bundled application rather than only framework test handlers.

## 3. Exact legacy source surfaces

The authoritative source is Webasyst Framework 4.2.0 release commit `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`.

Relevant Team files:

- `wa-apps/team/lib/config/app.php` — Team v2.3.4 manifest;
- `wa-apps/team/api/v1/team.users.getList.method.php`;
- `wa-apps/team/api/v1/team.groups.getList.method.php`;
- `wa-apps/team/api/swagger/v1.yaml`;
- `wa-apps/team/lib/classes/teamUser.class.php`;
- `wa-apps/team/lib/classes/teamUsersCollection.class.php`;
- `wa-apps/team/lib/handlers/contacts.contacts_collection.handler.php`.

Framework behavior used by the methods:

- `waContactsCollection::usersPrepare()`;
- `waContactsCollection::_online_status` post field handling;
- `waContactRightsModel::getByIds()`;
- `waContact::getRights()`;
- `waContact::getPhotoUrl()`;
- `waContactEventsModel::getEventByContact()`.

## 4. Team users API compatibility

### 4.1 Method identity

Register:

```text
ApiMethodTarget(AppId("team"), ApiMethodName("users.getList"))
```

Allowed HTTP method: `GET`.

API Execution already performs app-installed, app-access, OAuth scope and license checks before handler execution. The Team method does not add a second generic app-access check.

### 4.2 Base user population

Legacy `teamUser::getList("users")` uses `waContactsCollection::usersPrepare()`:

```text
login IS NOT NULL
AND is_user = 1
```

Only active backend users are in the default list.

The read repository MUST NOT return ordinary contacts or banned users.

### 4.3 Group filter

Legacy `filter[group_id]`:

- accepts scalar/list input through PHP request-array semantics;
- converts values to integers;
- drops non-positive values;
- when at least one positive id remains, list population becomes membership in ANY supplied group;
- duplicate ids do not change behavior.

Represent normalized state as explicit variants:

- `AllTeamUsers`;
- `TeamUsersInGroups(group_ids: tuple[GroupId, ...])`.

Do not use an empty/nullable group list to encode mode.

### 4.4 Access filter

Legacy accepts:

```text
filter[access]=crm
filter[access][]=crm
filter[access][]=files
filter[access][crm]=limited
filter[access][files]=full
```

Rules:

- scalar/list app ids imply `limited`;
- associative entries accept only `limited` and `full`;
- empty app ids are ignored;
- unrecognized levels are ignored;
- user must satisfy EVERY surviving app requirement;
- `limited` means effective backend right >= 1;
- `full` means effective backend right > 1.

Represent with:

- `TeamAccessLevel.LIMITED | FULL` (`EnumStr`);
- `TeamAppAccessRequirement(AppId, TeamAccessLevel)`;
- immutable tuple of requirements.

### 4.5 Batch legacy access semantics

`waContactRightsModel::getByIds(contact_ids, app_id, "backend", true)` computes access using:

- personal assignment encoded as negative `group_id`;
- group assignments through `wa_user_groups`;
- max personal/group backend value;
- `webasyst/backend > 0` gives global/superadmin access to non-webasyst applications;
- unknown non-webasyst app id produces no access.

The Team application owns a narrow batch `TeamUserAppAccessReader` port. Its SQL adapter may share the existing principal codec/legacy schema, but the use case MUST NOT issue one ACL query per user.

### 4.6 Visibility of users to the current API principal

Before `filter[access]`, legacy `teamUser::keepVisible()` applies Team-specific visibility:

- Team full admin sees all candidates;
- current principal always sees self;
- a non-self user with no groups is visible;
- a user in groups is visible when at least one of those groups is not hidden;
- hidden groups are Team rights matching `manage_users_in_group.%` whose effective value is < 0;
- if every group containing the target user is hidden, the target is omitted.

The current API principal is `ApiInvocationContext.principal.contact_id`.

Model this with a Team-specific visibility Service consuming a batch `TeamPrincipalGroupRightsReader`. Do not reuse generic access-level classification in a way that discards negative rights.

### 4.7 Name/order behavior

For this API method, `teamUser::getList()` receives no explicit order, so legacy falls back to name ascending.

The first slice uses the stored/formatted `name` value as the canonical display name and sorts ascending using deterministic Unicode string ordering.

Locale-specific Webasyst name-format settings are deferred to a dedicated contact-display projection; the method MUST document this as a narrow parity gap.

### 4.8 Returned core fields

The compatibility output includes:

- `id`;
- `name`;
- `firstname`;
- `lastname`;
- `middlename`;
- `company`;
- `login`;
- `email`;
- `phone`;
- `locale`;
- `jobtitle`;
- `last_datetime`;
- `birth_day`;
- `birth_month`;
- `create_datetime`;
- `_online_status`;
- `_event`;
- `group_id`;
- userpic fields.

Internal application entities use explicit state variants for genuine absence where the absence participates in logic. Serialized legacy-compatible DTOs may expose genuine nullable legacy fields.

### 4.9 Email

Legacy API exposes `email` as an ordered list of address strings.

Use `wa_contact_emails`, ordered by `sort`.

### 4.10 Phone

Legacy API exposes `phone` as ordered entries containing at least:

- `value`;
- `ext`;
- `status`.

Use `wa_contact_data` rows with `field='phone'`, ordered by `sort`.

Nullable legacy status remains a boundary-nullable serialized field. It is normalized internally before crossing application ports.

### 4.11 Group ids

After selecting users, legacy `extendByGroups()` uses `wa_user_groups` and emits `group_id: int[]`.

Preserve ascending deterministic group ids per user.

## 5. Online status

Legacy `_online_status` is one of:

- `offline`;
- `online`;
- `idle`.

Rules characterized from `waContactsCollection`:

1. default offline;
2. valid `last_datetime` within configured online timeout -> online;
3. `webasyst/idle_since` older than 60 seconds -> idle, but idle settings are loaded only for contacts with an open `wa_login_log` row (`datetime_out IS NULL`).

Create:

- `TeamOnlineStatus` EnumStr;
- `TeamOnlineStateService`;
- `TeamPresenceReader` batch port returning open-session and idle-since data;
- injected clock and `TeamOnlineTimeout` VO.

The first production timeout defaults to Webasyst's characterized default; it remains an injected setting/policy and is not hard-coded into repository SQL.

## 6. Current status event

Legacy `_event` uses `waContactEventsModel::getEventByContact()`:

- `is_status=1`;
- current time falls inside event;
- all-day events compare dates;
- ordered by all-day descending, start ascending;
- calendar metadata is joined from `wa_contact_calendars`.

Add infrastructure-private mappings for:

- `wa_contact_events`;
- `wa_contact_calendars`.

Application port:

```text
TeamCurrentEventReader.current_for_users(contact_ids, now)
```

Internal result is explicit:

- `TeamCurrentEventPresent`;
- `TeamCurrentEventMissing`.

Legacy API projection maps missing to empty string and present to the characterized event object.

## 7. User pictures and API request origin

Legacy Team turns relative contact photo URLs into absolute resource URLs.

Do not inject FastAPI `Request` into Team/application handlers.

Extend API execution with immutable:

```text
ApiRequestOrigin
```

carried by `ApiInvocationRequest` -> `ApiInvocationContext`.

It contains a validated absolute root origin/base URL supplied by presentation.

Team compatibility uses `TeamUserResourceUrlPolicy` to produce:

- `userpic` (144);
- `userpic_original_crop`;
- `userpic_uploaded`;
- `userpic_thumbs` for 16/32/96/144.

Contact photo path normalization is Webasyst compatibility behavior, not Team business logic.

The policy must characterize:

- no-photo UI 2.0 fallback;
- contact-id directory layout;
- normal crop/thumbnails;
- `original_crop`;
- mod_rewrite choice.

## 8. Team groups API compatibility

Register:

```text
ApiMethodTarget(AppId("team"), ApiMethodName("groups.getList"))
```

Allowed method: `GET`.

### 8.1 Group fields/order

Read `wa_group`, ordered by legacy `sort`.

Return fields excluding `icon` and `sort`, including:

- `id`;
- `name`;
- `cnt`;
- `type`;
- `description`.

### 8.2 Type filter

`filter[type]` accepts scalar/list strings.

Only groups whose type is in the surviving filter are returned. Empty filter means all group types.

Use the existing closed `GroupType` where compatible. Unknown filter strings are ignored, matching the permissive legacy request normalization.

### 8.3 Principal visibility

Legacy:

```php
getRights('team', 'manage_users_in_group.<id>') >= 0
```

Outer API app access is already checked.

For limited Team access:

- explicit group-specific negative value hides the group;
- when exact value is falsy, legacy falls back to `manage_users_in_group.all`;
- zero/default means visible;
- Team full admin means visible.

Create Team-specific batch `TeamGroupVisibilityReader` preserving negative named rights.

Do not infer visibility from generic `AppAccess` alone.

## 9. Team contacts_collection event bridge

Register an application event handler:

```text
source = ExactEventSource(AppId("contacts"))
pattern = ExactEventPattern(EventName("contacts_collection"))
owner = ApplicationEventOwner(AppId("team"))
```

Legacy behavior:

```php
return !!wa('team')->event('contacts_collection', $params);
```

Python behavior:

1. receive legacy payload;
2. nested-dispatch `EventKey(AppId("team"), EventName("contacts_collection"))`;
3. return boolean `true` when nested dispatch produced at least one result, otherwise `false`.

The handler receives an injected event-dispatch port. No global current application state is introduced.

Nested event dispatch must not recurse back into the same bridge because source app changes from `contacts` to `team`.

## 10. Team domain/application package

Create a feature-local package:

```text
application/team_directory/
  entities/
  vo/
  services/
  composites/
```

Taxonomy:

- Entity: `TeamUser`, `TeamGroup`;
- VO: filters, email/phone values, access requirements, online/current-event states;
- Service: visibility/access/filter/online-state policies;
- Composite: `ListTeamUsers`, `ListTeamGroups`.

Application code imports no SQLAlchemy/FastAPI/Webasyst compatibility modules.

## 11. Application-owned ports

Required narrow ports:

- `TeamDirectoryReader` — candidate users and groups;
- `TeamMembershipReader` — group ids for users;
- `TeamUserAppAccessReader` — batch effective backend rights for user/app pairs;
- `TeamPrincipalGroupRightsReader` — current principal Team group-management rights;
- `TeamPresenceReader`;
- `TeamCurrentEventReader`.

Avoid one universal Team repository/query builder.

## 12. SQLAlchemy adapter

Create Team-specific infrastructure package over existing legacy rows.

Existing mappings reused:

- `WaContactRow`;
- `WaContactEmailRow`;
- `WaContactDataRow`;
- `WaContactRightRow`;
- `WaGroupRow`;
- `WaUserGroupRow`.

Add mappings only for source-backed core tables needed now:

- `WaContactSettingRow`;
- `WaLoginLogRow`;
- `WaContactCalendarRow`;
- `WaContactEventRow`.

No new schema/migration is introduced.

## 13. PHP-style API parameter decoder

Current `legacy_api.py` collapses query/form parameters through a Python dict and loses repeated keys / bracket arrays.

Add compatibility Service:

```text
LegacyApiParameterDecoder
```

Input: ordered `tuple[(str, str), ...]`.

Output: `ApiParameterMap`.

Required supported forms:

```text
key=value
filter[group_id][]=1
filter[group_id][]=2
filter[access][]=crm
filter[access][crm]=limited
filter[type][]=group
```

Rules:

- repeated `[]` values preserve order;
- nested associative maps preserve insertion order;
- scalar/nested shape collisions fail with an explicit decode rejection;
- maximum nesting depth, entry count, key length and value length are bounded;
- no PHP execution/coercion library is used.

Presentation maps decoder rejection to legacy `invalid_request`.

Credential/format/callback top-level parameter semantics remain unchanged.

## 14. API request origin

Add `ApiRequestOrigin` VO and carry it through invocation.

Presentation derives it from the normalized request URL/root.

It is data, not an HTTP object.

Existing API method tests use an explicit test origin.

## 15. Team API compatibility handlers

Create compatibility handlers implementing `ApiMethodHandler`:

- `TeamUsersGetListApiMethod`;
- `TeamGroupsGetListApiMethod`.

Responsibilities:

- parse normalized Team filters from `ApiRequestParameters.query`;
- call application Composites;
- project Team Entities into exact JSON-compatible legacy fields;
- apply resource URL policy;
- return `ApiMethodSucceeded`.

Business filtering/ACL is not implemented inside these transport/projector handlers.

## 16. Runtime module

Create production composition factory:

```text
create_team_runtime_module(...)
```

It declares:

- API `users.getList`;
- API `groups.getList`;
- `contacts.contacts_collection` event bridge.

No backend dispatch definition is registered in this slice.

## 17. Runtime composition dependency ordering

Team event bridge needs the shared `EventDispatcher`, while Team API handlers need SQL-backed application services.

Refactor composition so registries/dispatcher are constructed before default runtime modules are built.

Use an explicit composition-only runtime module factory, for example:

```text
ApplicationRuntimeModuleFactory.build(event_dispatcher)
```

Production factory builds Team using:

- session factory / Team adapters;
- event dispatcher;
- API compatibility policies.

Tests may use a static module factory.

The factory is composition-only and is not a service locator.

## 18. Tests

### Characterization

Pin exact 4.2.0 source behavior for:

- Team manifest/version;
- two API method source files;
- user/group filters;
- user visibility;
- batch app access;
- online/idle;
- current status event;
- photo URLs;
- event bridge.

### Unit

Cover:

- PHP bracket decoder;
- Team filter parsing;
- Team visibility;
- access requirement filtering;
- online-state service;
- group visibility;
- event bridge;
- API projection.

### Persistence

Use SQLite legacy-shaped rows to verify:

- active-user population;
- group filtering/memberships;
- emails/phones;
- app access matrix;
- negative group management rights;
- presence;
- current events.

### Integration

Full API execution:

```text
Bearer/query token
-> API target team.users.getList / team.groups.getList
-> existing authorization
-> linked Team ApiMethodDefinition
-> Team use case
-> legacy DB
-> legacy JSON renderer
```

Also prove `contacts.contacts_collection` nested event bridge.

## 19. Non-goals

Not in this slice:

- Team backend HTML/Smarty page;
- production loading of `routing.backend.php`;
- Team profile routes;
- invitations;
- create/delete users;
- access mutation UI;
- calendar write paths;
- Team plugin UI;
- custom name-format localization parity;
- Webasyst ID invite flows.

## 20. Acceptance criteria

Complete when:

- Team is a real production default runtime module when installed;
- both Team API methods resolve through existing API runtime;
- user/group filters preserve characterized semantics;
- Team user visibility and access filters preserve legacy ACL behavior without N+1 queries;
- emails/phones/groups/online/current-event/userpic fields are returned;
- PHP bracket query decoding works for Team filters and preserves existing API behavior;
- Team contacts_collection bridge dispatches through Python event runtime;
- installed Team absent -> runtime linking fails fast rather than silently registering methods;
- application Team code has no transport/ORM/compatibility imports;
- full CI is green.

## 21. Follow-on

Next Team slice:

- production backend route loading for `routing.backend.php`;
- `users/` backend action using the same Team read Composites;
- rendering replacement / HTML compatibility boundary.

No read-model duplication is allowed in that follow-on.
