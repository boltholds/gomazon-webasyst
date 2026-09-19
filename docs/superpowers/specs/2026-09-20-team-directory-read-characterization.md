# Team Directory Read — Webasyst 4.2.0 Characterization

Status: source-pinned
Date: 2026-09-20
Release commit: 39c267a2fabfb0cd6d94f4dd86b23b4750328dd5

| Case | Source | Exact behavior | Python consequence |
| --- | --- | --- | --- |
| Team version | wa-apps/team/lib/config/app.php | Team version is 2.3.4; rights/plugins/csrf/system flags are enabled. | Runtime module identity is Team and relies on normal API app access. |
| users method | wa-apps/team/api/v1/team.users.getList.method.php | GET-style method target team.users.getList returns list values, not id-keyed map. | Register ApiMethodName("users.getList") and return JSON array. |
| base users | waContactsCollection::usersPrepare | login IS NOT NULL and is_user=1 for users hash. | Candidate reader returns active backend users only. |
| group filter | teamUsersGetListMethod::getFilter/buildHash | Convert to ints, drop non-positive; positive ids use group/<ids>. | Explicit all-users vs users-in-groups filter variants. |
| access scalar/list | formatAccessFilter | Scalar/list app ids mean minimum limited access. | Normalize to TeamAccessLevel.LIMITED. |
| access map | formatAccessFilter | Only limited/full values survive. | Ignore unknown level strings. |
| access threshold | filterByAccess | limited requires >=1, full requires >1; every requested app must pass. | Pure access filter Service. |
| batch access | waContactRightsModel::getByIds | Personal + group rights; Webasyst global admin overrides non-webasyst apps. | Batch TeamUserAppAccessReader. |
| user visibility | teamUser::keepVisible | Full Team admin sees all; self and group-less user visible; grouped user needs >=1 non-hidden group; hidden means manage_users_in_group.* <0. | Team-specific visibility Service preserving negative rights. |
| groups method | team.groups.getList.method.php | wa_group ordered by sort; icon/sort omitted; optional type filter. | TeamGroup read DTO/list. |
| group visibility | teamGroupsGetListMethod::hasAccessToGroup | getRights(team, manage_users_in_group.<id>) >= 0. | Negative exact/.all hides; zero is visible. |
| online | waContactsCollection::_online_status | recent last_datetime => online; open login + idle_since older 60s => idle; else offline. | Batch presence input + pure TeamOnlineStateService. |
| current event | waContactEventsModel::getEventByContact | Current status event, all-day/date aware, all-day desc then start asc, calendar metadata joined. | Batch current event reader with explicit missing state. |
| photo | waContact::getPhotoUrl + Team API workup | 144/original_crop plus 16/32/96/144 thumbs are made absolute by API resource URL helper. | Typed ApiRequestOrigin + compatibility resource URL policy. |
| event bridge | contacts.contacts_collection.handler.php | Returns boolean value of nested team.contacts_collection event results. | Explicit nested EventDispatcher bridge. |
| backend users page | teamUsers.action.php | Uses same user-list concepts but renders Team HTML and first-login redirect. | Deferred to Team Backend slice, no read-model duplication. |
| backend routing | routing.backend.php | Empty Team backend path maps to users/. | Deferred with production backend route loading. |

## Known first-slice boundaries

- User display-name formatting uses stored normalized name until Webasyst user_name_display localization/settings projection is migrated.
- Backend HTML/Smarty output is excluded.
- Team write flows are excluded.
