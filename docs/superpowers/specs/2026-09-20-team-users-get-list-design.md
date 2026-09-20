# Team users.getList — Design

Status: implemented
Date: 2026-09-20
Source: Webasyst 4.2.0 release commit `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`

## Goal

Migrate `team.users.getList` as the second real Team API method through the existing installed-application runtime, API token pipeline, ACL semantics and legacy persistence.

The slice must preserve observable Team selection, visibility, app-access filtering, enrichment, naming, ordering and response shape without widening the generic contact repository or leaking HTTP/SQL details into application code.

## Boundaries

The implementation is split into three deliberately separate concerns.

### Team user source projection

`TeamUserReader` is a narrow application-owned read port. `SQLAlchemyTeamUserReader` implements the source-specific candidate/enrichment projection over legacy tables.

It owns:

- `users` versus `group/<ids>` candidate semantics;
- email/phone/group enrichment;
- current status event projection;
- online/idle state inputs;
- display-name source settings;
- server-time to UTC conversion.

It does not evaluate actor visibility or candidate application access.

Legacy SQL NULL values are normalized into explicit presence variants before leaving infrastructure.

### Team policy

`ListVisibleTeamUsers` owns two distinct policies.

Actor visibility uses the actor's personal, group and guest principals, matching normal `waContactRightsModel::get()` behavior. Team admins bypass visibility filtering. For non-admins, wildcard `manage_users_in_group.%` behavior is reconstructed from exact right assignments already present in the actor snapshot.

The wildcard path intentionally does not apply scalar `.all` fallback. A stored `manage_users_in_group.all=-1` does not make every numeric group hidden.

Candidate `filter[access]` evaluation is different: it uses only candidate personal and group principals, because `waContactRightsModel::getByIds()` does not add guest rights. Every requested app requirement must pass. Installed-app existence is checked against the canonical `InstalledApplicationCatalog`.

### Compatibility projection

`LegacyTeamUserFilterParser` owns Webasyst query normalization.

`TeamUsersGetListApiMethod` owns the exact API payload projection. Genuine nullable legacy fields become JSON `null` only here; missing current event becomes the legacy empty string.

`LegacyTeamUserMediaProjector` owns userpic fields. Application contracts carry only photo identity and company/person state, never request/root/CDN URLs.

## Candidate selection

Without a usable group filter:

```text
wa_contact.login IS NOT NULL
wa_contact.is_user = 1
```

With one or more normalized positive group ids:

```text
JOIN wa_user_groups
wa_user_groups.group_id IN (...)
wa_contact.is_user > 0
```

The group path therefore may return a user with a null login. Duplicate group ids are normalized away after legacy-compatible integer coercion.

## Access filter

`filter[access]` supports:

- scalar/list app ids -> `limited`;
- app-to-level mapping -> `limited | full`;
- invalid levels -> ignored.

Thresholds:

- limited: effective backend >= 1;
- full: effective backend > 1.

A requested non-installed application makes the filtered result empty, matching legacy `getByIds()`.

Global Webasyst backend access continues to use the shared `RightsEvaluator` semantics.

## Naming and ordering

The Team reader loads `webasyst/user_name_display`.

- missing setting -> stored contact name fallback;
- empty setting -> legacy default name order;
- explicit setting -> only `firstname,middlename,lastname,login` participate.

Empty formatted output falls back to stored contact name, then `user_id=<id>`.

The final collection is sorted by the formatted name with bytewise-compatible ordering rather than relying on the initial SQL contact name.

## Time-sensitive fields

The reader receives an injected clock and server timezone.

- current event selection uses server-local legacy datetimes;
- recent activity threshold is 300 seconds;
- idle threshold is 60 seconds;
- `create_datetime` is converted from configured server timezone to UTC before compatibility serialization.

The pre-existing API execution pipeline updates an authenticated API user's stale `wa_contact.last_datetime` before method execution, so this method observes the same activity side effect rather than adding a Team-specific write.

## Resource URLs

Legacy source first asks the CDN resolver and otherwise builds an absolute root URL. `waContact::getPhotoUrl()` also has a separate non-`mod_rewrite` thumbnail path.

The first Python resource implementation is intentionally narrower and explicit:

- configurable absolute public root;
- direct `wa-data/public/contacts/photos/... ` thumbnail URLs;
- API environment is non-retina;
- Team UI 2.0 default user/company SVGs.

CDN parity and the non-`mod_rewrite` `thumb.php` fallback are deferred resource-resolver adapters. They are not claimed by this slice. The separation is confined to compatibility/media projection and requires no application contract changes later.

## Runtime registration

The installed Team runtime now declares two GET methods:

```text
team.groups.getList
team.users.getList
```

The same canonical installed-app catalog is injected into the Team users policy that API execution already uses.

Production composition also injects:

- `webasyst_public_root_url`;
- `webasyst_server_timezone`.

No FastAPI request, SQLAlchemy session or filesystem path crosses into the Team application layer.

## Acceptance

Complete when:

- exact source characterization is release-pinned;
- both candidate collection modes are tested;
- group/access query normalization is tested;
- actor visibility preserves wildcard semantics without `.all` fallback;
- candidate access excludes guest rights;
- uninstalled access-filter apps produce no matches;
- nullable legacy data is normalized before application;
- enrichment/name/UTC/online/event behavior is tested;
- media fields are projected only at compatibility edge;
- production `/api.php/team.users.getList` executes through real token, app catalog, ACL and SQL persistence;
- GET-only transport is preserved;
- full CI is green.
