# Webasyst 4.2.0 Team users.getList — Characterization

Status: source-pinned
Date: 2026-09-20
Authoritative release commit: `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`

## Source locations

- `wa-apps/team/api/v1/team.users.getList.method.php`
- `wa-apps/team/lib/classes/teamUser.class.php::getList()`
- `wa-apps/team/lib/classes/teamUser.class.php::keepVisible()`
- `wa-apps/team/lib/classes/teamUsersCollection.class.php::groupPrepare()`
- `wa-system/contact/waContactsCollection.class.php::usersPrepare()`
- `wa-system/contact/waContactsCollection.class.php::getContacts()`
- `wa-system/webasyst/lib/models/waContactRights.model.php::getByIds()`
- `wa-system/user/waUser.class.php::formatName()`

## Candidate selection

Without a usable `filter[group_id]`, the method builds the `users` collection. That path requires `c.login IS NOT NULL` and `c.is_user = 1`.

With at least one positive group id, the hash becomes `group/<comma-separated ids>`. Team's collection override accepts multiple ids, normalizes them to unique positive integers, joins `wa_user_groups`, and requires `c.is_user > 0`.

The difference is observable and must not be collapsed into one generic active-contacts query.

## Access filter

`filter[access]` accepts either app ids or an app-to-level mapping:

- scalar/list app ids imply `limited`;
- associative values accept only `limited` and `full`;
- every requested app requirement must pass.

For each candidate contact, legacy `waContactRightsModel::getByIds()` evaluates personal and group principals. It does not include the guest principal. A positive `webasyst/backend` makes a user effectively full-access for non-Webasyst applications.

The thresholds are exact:

- `limited`: backend right `>= 1`;
- `full`: backend right `> 1`.

If an explicitly filtered application is not installed, `getByIds()` returns no rights and therefore no candidate can satisfy that app requirement.

## Visibility to the requesting Team user

A Team app admin bypasses visibility filtering.

For a non-admin actor, negative `manage_users_in_group.<id>` rights mark groups hidden. A candidate remains visible when any of these is true:

- candidate is the actor;
- candidate belongs to no groups;
- candidate belongs to at least one group that is not hidden.

A candidate whose every group is hidden is removed.

This policy is actor visibility and is separate from the candidate's own app-access filter.

## Projection and ordering

The requested source fields are the exact list pinned in the executable fixture.

`teamUser::getList()` formats each display name from `webasyst/user_name_display`, accepting only `firstname,middlename,lastname,login`; it falls back to the stored contact name and then `user_id=<id>`. The final collection is sorted again by the formatted name ascending.

Emails preserve `wa_contact_emails.sort`; phone data comes from `wa_contact_data`. Group ids are appended from `wa_user_groups`.

`_event` is the first currently active status event after the source ordering; absence is an empty string. `_online_status` uses a 300-second recent-activity threshold and may become `idle` when an active login exists and `webasyst/idle_since` is older than 60 seconds.

The method builds userpic URLs during workup, removes internal `photo`/`is_company` and temporary `photo_url_*` fields, and converts `create_datetime` to UTC.

## Python boundaries

The Python migration must keep three concerns separate:

1. Team user source projection/enrichment;
2. actor visibility and candidate app-access policy;
3. Webasyst transport/resource URL projection.

The application layer must not receive HTTP request objects or raw SQL rows. Candidate app-access evaluation must intentionally omit `GuestsTarget`, even though other ACL consumers may include it.
