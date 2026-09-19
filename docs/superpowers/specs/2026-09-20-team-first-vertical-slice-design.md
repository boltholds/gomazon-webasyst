# Team First Bundled-App Vertical Slice — Design

Status: implemented
Date: 2026-09-20
Repository: `boltholds/gomazon-webasyst`

## Goal

Prove the new application runtime with the first real bundled Webasyst application by migrating `team.groups.getList` end-to-end against the legacy database and existing API/OAuth/ACL framework.

## Architecture

The Team slice follows existing dependency direction:

```text
compatibility/webasyst/team
          |
          v
   application/team
          |
          v
 contracts/team + Team-owned read port
          ^
          |
 infrastructure/team/sqlalchemy
```

Composition explicitly constructs the Team runtime module. No package scanning or import-from-app-id behavior is introduced.

## Runtime selection

Production composition keeps a finite explicit set of known Python runtime module factories. At startup:

1. construct those known module declarations with injected dependencies;
2. obtain canonical `InstalledApplicationSnapshot`;
3. select only modules whose `AppId` is installed;
4. pass selected modules to `ApplicationRuntimeLinker`.

Therefore a Python Team implementation may exist in the codebase while remaining unlinked when the legacy installation does not enable Team.

Explicit test composition continues to use `ProvidedRuntimeModules`, allowing deliberate validation of uninstalled-module rejection.

## Team read projection

`team.groups.getList` needs a consumer-specific projection. The generic access-control `GroupRepository.list()` is not the correct read path because it:

- sorts by `type, sort, name`;
- exposes normalized ACL-domain fields;
- supplies normalized icon/sort/description values.

The Team API instead requires the source-characterized projection:

- `id`;
- `name`;
- `cnt`;
- `type`;
- nullable `description`;
- order by legacy `sort`.

Accordingly `TeamGroupReader` is a narrow application-owned query port and `SQLAlchemyTeamGroupReader` is its adapter.

## Nullable legacy data

SQL NULL description is a genuine database boundary but MUST NOT escape into Team application contracts.

The adapter maps:

```text
NULL   -> TeamGroupDescriptionMissing
string -> TeamGroupDescriptionPresent
```

The Webasyst API compatibility adapter maps Missing back to JSON `null`.

## Rights semantics

Team does not reimplement ACL evaluation.

`ListVisibleTeamGroups` builds the same personal/group/guest target set used by API app-access authorization, loads one `RightsSnapshot`, and delegates each `manage_users_in_group.<id>` decision to the shared `RightsEvaluator`.

Visible means:

- `UnlimitedRight`; or
- `FiniteRight(value >= 0)`.

Negative finite rights hide the group.

## Transport

The generic legacy API query adapter now preserves duplicate query keys as immutable tuples, allowing Webasyst-style array query parameters such as repeated `filter[type][]`.

This is a transport correction shared by future legacy API methods, not Team-specific HTTP parsing.

## Production registration

`composition/team.py` declares one method:

```text
App: team
Method: groups.getList
HTTP: GET
```

The method becomes executable only if Team exists in the canonical installed-app snapshot.

## Acceptance

The slice is accepted when an ASGI test using production `create_app_with_settings()`:

- discovers Team from a temporary Webasyst root;
- initializes the startup runtime;
- resolves a real legacy API token from `wa_api_tokens`;
- authorizes Team through `wa_contact_rights`;
- reads `wa_group`;
- applies per-group Team rights;
- preserves sort order;
- handles scalar and repeated type filters;
- returns exact characterized JSON fields;
- keeps unrelated foundation tests green.
