# Webasyst 4.2.0 Team groups.getList — Characterization

Status: source-pinned
Date: 2026-09-20
Authoritative release commit: `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`

This document pins the first real bundled-application compatibility endpoint migrated to Python.

## Source locations

- `wa-apps/team/lib/config/app.php`
- `wa-apps/team/api/v1/team.groups.getList.method.php`
- `wa-system/api/waAPIMethod.class.php`
- `wa-system/contact/waContactRightsModel.class.php` semantics already characterized by the ACL slice

## Exact behavior

| Case | 4.2.0 behavior | Python consequence |
| --- | --- | --- |
| Team app identity | Team manifest version is `2.3.4`, vendor `webasyst`, with `rights=true` and `plugins=true`. | Runtime module identity is `AppId("team")` and is linked only when Team is installed. |
| HTTP method | `waAPIMethod::$method` defaults to `GET`; Team method does not override it. | Python method definition allows GET only. |
| Method name | Legacy API file is `team.groups.getList.method.php`. | Registered target is `team / groups.getList`. |
| Group source | Uses `waGroupModel`. | Reads existing `wa_group`; no Team-owned schema is introduced. |
| Response fields | Takes group metadata fields then removes only `icon` and `sort`. | Response contains exactly `id`, `name`, `cnt`, `type`, `description`. |
| Ordering | Query orders by `sort`. | Team-specific reader preserves `ORDER BY sort`; the generic ACL GroupRepository is intentionally not reused for this projection. |
| Type filter | GET `filter[type]` is normalized through `waUtils::toStrArray()`: scalar values become a one-item array, scalar items are trimmed, and an explicitly supplied empty scalar becomes `['']`; only an absent `filter[type]` means no type filter. | Compatibility parser preserves scalar/repeated array shape, trims scalar values, and does not collapse an explicit empty item into missing state. |
| Visibility | Group is included when `getRights('team', 'manage_users_in_group.<id>') >= 0`. | Existing `RightsEvaluator` is reused; finite negative hides, zero/positive shows, full/global access yields unlimited visibility. |
| Dotted-right fallback | Webasyst rights semantics permit `manage_users_in_group.all` fallback when exact dotted right is zero/missing. | Existing `ExactThenLegacyAllFallback` is reused rather than duplicating Team ACL rules. |
| Output container | Visible groups are appended with `[]`, producing a JSON list rather than an id-keyed map. | Python returns a list preserving query order. |
| Nullable description | `wa_group.description` may be SQL NULL and is returned as such. | ORM `None` is normalized immediately to `TeamGroupDescriptionPresent | TeamGroupDescriptionMissing`; compatibility projection converts Missing back to JSON `null`. |
| Duplicate query keys | PHP request arrays can express `filter[type][]=group&filter[type][]=location`. | Legacy API HTTP adapter preserves repeated query keys as immutable tuples before Team parsing. |

## Deliberate non-goals

This first Team slice does not claim compatibility for:

- `team.users.getList`;
- userpic/CDN/contact-data aggregation;
- invitations;
- Team backend pages or Smarty templates;
- profile/calendar/schedule functionality;
- Team plugin runtime;
- Team event relays such as `contacts.delete -> team.contacts_delete`;
- Team mutations.

Those are separate vertical slices.

## Proof boundary

The acceptance path is the real production graph:

```text
wa-config/apps.php (team enabled)
        ↓
InstalledApplicationCatalog
        ↓
known Python Team runtime module selection
        ↓
ApplicationRuntimeLinker
        ↓
ApiMethodRegistry: team.groups.getList
        ↓
legacy API token + Team ACL authorization
        ↓
ListVisibleTeamGroups
        ↓
wa_group / wa_user_groups / wa_contact_rights
        ↓
legacy JSON response
```
