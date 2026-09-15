# Access Control / Groups / Permissions Design

**Status:** approved design
**Date:** 2026-09-15
**Scope:** Webasyst 4.2.0-compatible framework access-control core: effective rights evaluation, group CRUD, group membership mutation, named-right assignment/revocation, application access, global-admin access, authorization of ACL mutations, SQLAlchemy mapping of the existing legacy tables, composition and tests.

## 1. Goal

Add a typed access-control subsystem on top of the existing Webasyst tables without translating their integer/principal conventions into application-level magic values and without redesigning the model as conventional RBAC.

The subsystem preserves these observable Webasyst 4.2.0 semantics:

- effective user rights are the maximum of personal, group and guest assignments;
- `webasyst/backend > 0` gives global administrative access;
- application `backend == 1` means limited access and `backend >= 2` means full/application-admin access;
- full/global access makes named rights unlimited;
- `foo.bar` falls back to `foo.all` only when the exact effective value is zero/falsy;
- right values are integers, not booleans;
- saving `backend` has destructive cleanup semantics;
- setting a right to zero removes the persisted assignment;
- memberships live in `wa_user_groups` and `wa_group.cnt` is denormalized;
- the legacy schema is mapped rather than replaced.

The Python application layer exposes explicit typed states/results and does not leak signed legacy principals, literal `backend` storage rules, SQLAlchemy, nullable sentinel outcomes, or PHP integer sentinels.

## 2. Authoritative Webasyst 4.2.0 source

The exact supplied `webasyst-framework-v.4.2.0.zip` is authoritative under ADR-015. Relevant files:

- `wa-system/webasyst/lib/models/waContactRights.model.php`
- `wa-system/webasyst/lib/models/waGroup.model.php`
- `wa-system/webasyst/lib/models/waUserGroups.model.php`
- `wa-system/contact/waContact.class.php`
- `wa-system/webasyst/lib/config/db.php`
- `wa-apps/team/lib/actions/group/teamGroupDelete.controller.php`
- `wa-apps/team/lib/actions/access/teamAccessSave.actions.php`

Observed behavior used by this design:

1. `waContactRightsModel::get()` builds candidate principals from personal rights, guests (`0`) and memberships, then uses `MAX(value)` grouped by right name.
2. For any application other than `webasyst`, a non-zero effective `webasyst/backend` returns unlimited access.
3. Effective application `backend >= 2` returns unlimited access for any requested named right.
4. `waContact::getRights()` returns no named rights without application backend access and applies `foo.bar -> foo.all` when the exact value is zero/falsy.
5. `waContactRightsModel::save()` negates its logical id into the storage principal. Saving `webasyst/backend` first deletes every assignment for that principal. Saving another application's `backend` with a value other than `1` first deletes every assignment for that principal+application. A zero value deletes rather than upserts.
6. `waGroupModel::delete()` removes memberships and the group but does not explicitly remove group-owned rows from `wa_contact_rights`.
7. `waGroupModel::updateCounts()` counts only joined contacts with `wa_contact.is_user > 0`.
8. `waUserGroupsModel::add()` is duplicate-tolerant (`INSERT IGNORE`) and refreshes counts after membership changes.
9. Team's group/access mutation controllers require Webasyst administrative access.
10. Legacy tables are:
   - `wa_contact_rights(group_id, app_id, name, value)` with PK `(group_id, app_id, name)`;
   - `wa_group(id, name, cnt, icon, sort, type, description)`;
   - `wa_user_groups(contact_id, group_id, datetime)` with PK `(contact_id, group_id)`.

## 3. Chosen architecture

Use a typed compatibility ACL over the existing Webasyst model.

Rejected alternatives:

- **Conventional RBAC (`Role -> Permission`)** loses personal assignments, guest assignments, numeric values, `MAX` aggregation and special backend semantics.
- **Generic policy engine (`principal/resource/action/condition`)** is broader than this migration slice and would make parity harder to prove.

The core remains Webasyst-compatible while storage accidents and PHP sentinels are normalized at explicit boundaries.

## 4. Package boundaries

Target layout:

```text
src/gomazon_webasyst/
  contracts/
    access_control.py
    enums.py

  application/
    access_control.py
    access_values.py
    rights_evaluator.py
    rights_mutation_policy.py
    ports/
      access_control_uow.py
      groups.py
      memberships.py
      rights.py
      access_subjects.py
      access_admin_policy.py

  infrastructure/
    access_control/
      sqlalchemy/
        groups.py
        memberships.py
        rights.py
        unit_of_work.py

  compatibility/
    webasyst/
      access_control/
        principals.py
        evaluation.py
        mutation.py

  composition/
    access_control.py
```

The exact file split may be tightened during implementation when a file would only contain forwarding code. Dependency direction is fixed:

```text
composition / presentation / compatibility
                    |
                    v
                application
                    |
                    v
       contracts + application ports
                    ^
                    |
         infrastructure implementations
```

Application code must not import compatibility or SQLAlchemy modules.

## 5. Value objects and principals

Internal non-wire value objects use frozen/slotted dataclasses:

```python
@dataclass(slots=True, frozen=True)
class ContactId:
    value: int

@dataclass(slots=True, frozen=True)
class GroupId:
    value: int

@dataclass(slots=True, frozen=True)
class AppId:
    value: str

@dataclass(slots=True, frozen=True)
class RightName:
    value: str

@dataclass(slots=True, frozen=True)
class RightValue:
    value: int
```

`AppId` and `RightName` are open identifiers because applications may add values. Closed status/result domains use `EnumStr`.

Application principals are explicit variants:

```text
UserTarget(ContactId)
GroupTarget(GroupId)
GuestsTarget
```

Legacy storage encoding:

```text
UserTarget(ContactId(42)) -> wa_contact_rights.group_id = -42
GroupTarget(GroupId(7))   -> wa_contact_rights.group_id = 7
GuestsTarget()            -> wa_contact_rights.group_id = 0
```

This conversion belongs only to the Webasyst persistence/compatibility codec. Negative principal IDs MUST NOT appear in application contracts or use-case APIs.

## 6. Normalized right assignments

Raw `wa_contact_rights` rows are normalized before crossing into application code. Application code does not inspect the string `backend`.

Normalized variants:

```text
GlobalAccessAssignment(target, value)
AppAccessAssignment(target, app_id, value)
NamedRightAssignment(target, PermissionKey, value)
```

A Webasyst rights-row codec recognizes:

```text
app_id == "webasyst" and name == "backend" -> GlobalAccessAssignment
name == "backend"                           -> AppAccessAssignment
anything else                                -> NamedRightAssignment
```

The literal values `webasyst`/`backend` therefore stay in compatibility/infrastructure normalization code rather than application evaluator branches.

`PermissionKey` is a stable identity:

```text
PermissionKey(AppId, RightName)
```

## 7. Group model

Framework group contracts expose the legacy `wa_group` data needed by the framework:

```text
Group
  id: GroupId
  name
  type
  member_count
  icon
  sort
  description
```

`GroupType` is a closed `EnumStr` domain with `GROUP` and `LOCATION`, matching the legacy enum.

Team-specific location records are outside this framework slice. Creating or updating a `LOCATION` group changes only the base `wa_group` record here; location metadata belongs to a later Team adapter/slice.

Group reads use explicit variants such as `GroupResolved | GroupMissing`, never `Group | None`.

## 8. Membership model

Membership identity is `(ContactId, GroupId)` and becomes an immutable VO when it repeatedly crosses internal ports.

Operations:

```text
ListUserGroups
ListGroupMembers
AddGroupMember
RemoveGroupMember
ReplaceGroupMembers
```

New membership mutations validate both contact and group. The first Python writer accepts only contacts with `is_user > 0` as new members. Existing legacy rows pointing at other contacts are tolerated on read, but Python does not create more of them.

Idempotent outcomes are explicit:

```text
MembershipAdded
MembershipAlreadyPresent
MembershipRemoved
MembershipAlreadyAbsent
MembershipRejected(reason)
```

`ReplaceGroupMembers` applies a delta rather than delete-all/insert-all, preserving `datetime` for unchanged memberships.

After membership mutation, the same transaction recomputes `wa_group.cnt` according to legacy semantics: count only memberships whose joined contact has `is_user > 0`.

## 9. Effective-right evaluation

Persistence loads normalized assignments and memberships. A pure application evaluator aggregates them; Webasyst-specific key recognition has already happened at the compatibility boundary.

For a user:

```text
personal assignments
+ every assigned group
+ guest assignments
        |
        v
MAX(value) by normalized assignment identity
```

The evaluator applies typed access semantics:

1. For a non-Webasyst application, effective `GlobalAccessAssignment.value > 0` yields `GlobalAdminAccess` and unlimited named rights.
2. Otherwise effective `AppAccessAssignment.value >= 2` yields `FullAppAccess` and unlimited named rights.
3. App-access value `1` yields `LimitedAppAccess`.
4. App-access value `<= 0` or absence yields `NoAppAccess`.
5. Without application access, a named right resolves to finite `0`.
6. With limited access, use the exact effective named-right value.
7. If the exact value is `0`, invoke the configured right-fallback policy.
8. Negative non-zero exact values remain explicit and do not trigger fallback.

`RightValue` therefore remains numeric. Boolean `can_*` is not the canonical framework contract.

Effective named-right state:

```text
FiniteRight(RightValue)
UnlimitedRight(reason)
```

`UnlimitedRightReason` initially contains:

```text
GLOBAL_ADMIN
APP_FULL_ACCESS
```

Application access is a discriminated family:

```text
NoAppAccess
LimitedAppAccess
FullAppAccess
GlobalAdminAccess
```

No application caller compares raw backend integers.

## 10. `.all` fallback is a compatibility policy

`foo.bar -> foo.all` is Webasyst compatibility behavior, not an intrinsic property of `RightName`.

Application owns the policy interface; compatibility provides the initial implementation:

```text
RightFallbackPolicy
  ExactThenLegacyAllFallback
```

Given an exact-zero dotted right, the legacy policy returns the corresponding fallback `PermissionKey`; otherwise it returns an explicit no-fallback variant. It does not use `None`.

Future applications may inject different behavior without changing evaluator/storage APIs.

## 11. Rights snapshots

`GetRightsSnapshot(subject, app_id)` must not pretend to enumerate an infinite set of named rights under full/global access.

Use variants:

```text
FiniteRightsSnapshot
  app_access
  effective_named_rights

UnlimitedRightsSnapshot
  app_access
  reason
```

`GetEffectiveRight` remains the precise operation for arbitrary `RightName`.

## 12. Mutation API

Generic named-right mutation is separate from access-level mutation:

```text
AssignRight(target, PermissionKey, nonzero RightValue)
RevokeRight(target, PermissionKey)
SetAppAccess(target, AppId, AppAccessMode)
SetGlobalAdminAccess(target, GlobalAdminMode)
```

Application does not hardcode which raw right name is reserved. It calls an injected compatibility policy:

```text
ReservedRightPolicy.classify(PermissionKey)
  OrdinaryNamedRight
  ReservedAccessRight
```

The Webasyst policy classifies raw `backend` as reserved. Generic assign/revoke rejects `ReservedAccessRight`; callers use structured access operations instead.

`AppAccessMode` is closed:

```text
NONE
LIMITED
FULL
```

The Webasyst mutation codec/planner maps these to persisted backend semantics (`0`, `1`, `2`). Reads map any legacy value `>= 2` to `FullAppAccess`.

`GlobalAdminMode` is closed `ENABLED | DISABLED`; the Webasyst compatibility planner maps enabled to a non-zero global backend assignment and disabled to removal.

Generic `AssignRight` requires a non-zero value. Zero is represented explicitly by `RevokeRight`.

## 13. Pure legacy mutation planner

Webasyst-specific destructive write behavior is centralized in a pure compatibility policy:

```text
LegacyRightsMutationPolicy
        |
        v
RightsMutationPlan
```

Application owns plan/result types; compatibility owns the concrete Webasyst planner. `RightsMutationPlan` is immutable and contains typed operations, not SQL:

```text
DeleteAllTargetRights
DeleteAppScope
UpsertGlobalAccess
DeleteGlobalAccess
UpsertAppAccess
DeleteAppAccess
UpsertNamedRight
DeleteNamedRight
```

Required legacy planning semantics:

### Global access

For global backend mutation:

1. delete every assignment for the target;
2. if enabling, upsert the normalized global access assignment;
3. if disabling, leave no global assignment.

The storage codec maps that normalized global assignment to `webasyst/backend`, reproducing `waContactRightsModel::save()` without exposing its strings in application code.

### Application access

- `LIMITED`: preserve granular application assignments and upsert app access value `1`;
- `NONE`: delete every assignment for target+app and leave no app-access assignment;
- `FULL`: delete every assignment for target+app and upsert app access value `2`.

The storage codec maps app-access assignment to the legacy `backend` row.

### Named rights

- non-zero assignment -> upsert exact named assignment;
- revoke -> delete exact assignment.

Repositories execute plans but do not duplicate these rules.

## 14. Persistence ports

### Group repository

```text
create
get
list
update
delete
```

Expected misses use typed variants rather than `None`.

### Membership repository

```text
list_for_user
list_for_group
add
remove
replace_delta
recount_group
```

The repository accepts typed `ContactId`/`GroupId`.

### Rights repository

```text
load_normalized_assignments
upsert_normalized_assignment
delete_exact
delete_scope
delete_all_for_target
```

The SQLAlchemy/Webasyst adapter alone knows signed principal IDs and raw `backend` rows.

### Subject access

A narrow ACL-subject port resolves only existence and user eligibility required by ACL. It must not depend on the full contact CRUD contract.

## 15. Dedicated AccessControlUnitOfWork

ACL writes span multiple tables, so they use a dedicated application-owned UoW rather than turning the contact UoW into a universal container.

```text
AccessControlUnitOfWork
  groups
  memberships
  rights
  subjects
  commit
  rollback
```

All multi-table changes are atomic.

Examples:

### DeleteGroup

```text
open UoW
authorize actor in same UoW
resolve group
delete memberships
delete rights for GroupTarget(group_id)
delete group
commit
```

### ReplaceGroupMembers

```text
open UoW
authorize actor in same UoW
resolve group
validate requested contacts
load current memberships
compute added / removed delta
apply delta
recount group
commit
```

### SetAppAccess / SetGlobalAdminAccess

```text
open UoW
authorize actor in same UoW
validate target
build RightsMutationPlan
execute plan
commit
```

Infrastructure faults propagate; ordinary misses/rejections are typed results.

## 16. Intentional integrity improvement: group deletion

Webasyst 4.2.0 `waGroupModel::delete()` removes membership links and the group row but does not explicitly delete `wa_contact_rights` rows owned by that group.

The Python rewrite intentionally performs:

```text
delete memberships
+ delete group rights
+ delete group
```

This is an accepted compatibility deviation because deleted-group rights are not legitimate effective rights, while retaining them creates orphan ACL state and risks accidental resurrection if an identifier is reused.

The behavior must be covered by integration tests.

## 17. Authorization of administrative mutations

Repositories are not security boundaries. Every group/membership/right mutation use case receives the authenticated actor and checks an injected application-owned administration policy before writing.

```text
AuthenticatedSubject actor
        |
        v
effective access loaded inside UoW
        |
        v
AccessAdministrationPolicy
        |
        v
Authorized | AccessDenied
        |
        v
mutation
```

The first compatibility policy permits ACL administration only to effective `GlobalAdminAccess` subjects, matching the exact 4.2.0 Team administrative gate for access/group management.

Authorization MUST be evaluated inside the same `AccessControlUnitOfWork` transaction used for mutation, before any write.

Expected denial is typed; infrastructure failures remain exceptional.

## 18. Use cases

Read/evaluate:

```text
GetGroup
ListGroups
ListUserGroups
ListGroupMembers
GetEffectiveRight
GetAppAccess
GetRightsSnapshot
```

Mutations:

```text
CreateGroup
UpdateGroup
DeleteGroup
AddGroupMember
RemoveGroupMember
ReplaceGroupMembers
AssignRight
RevokeRight
SetAppAccess
SetGlobalAdminAccess
```

Representative result families:

```text
GroupResolved | GroupMissing
GroupCreated | GroupCreateRejected
GroupUpdated | GroupUpdateRejected
GroupDeleted | GroupDeleteRejected

MembershipAdded | MembershipAlreadyPresent | MembershipRejected
MembershipRemoved | MembershipAlreadyAbsent | MembershipRejected

RightAssigned | RightAssignmentRejected
RightRevoked | RightAlreadyAbsent | RightRevocationRejected

EffectiveRightResolved | EffectiveRightRejected
AccessAdministrationAuthorized | AccessAdministrationDenied
```

Do not predeclare speculative reasons such as `PROTECTED_GROUP` until the model gains that concept.

## 19. Error and validation rules

- Ordinary not-found/already-present/already-absent/access-denied/invalid-command outcomes are typed results per ADR-020.
- No operation result uses `T | None`, `Optional`, bool sentinels or magic strings.
- DB failures, transaction failures and corruption remain exceptions.
- Generic `AssignRight` rejects a compatibility-classified reserved access right and zero-valued assignment commands.
- `SetAppAccess`/`SetGlobalAdminAccess` own structured access mutation.
- A `UserTarget` must resolve to a valid backend user for new mutations.
- A `GroupTarget` must resolve to an existing group.
- `GuestsTarget` is structurally valid and may receive rights under administrator control.
- Reads tolerate legacy membership rows violating the new-write user invariant; new writes do not create more.

## 20. Application identifiers and installed-app validation

`AppId` is open. This slice does not introduce the application installation/catalog subsystem solely to validate app existence.

Callers/composition are expected to request rights for installed/configured applications. The legacy rule where `waContactRightsModel::get()` forces unknown apps to zero will be completed when an application registry/catalog exists.

This is an explicit bounded compatibility gap; do not hide it behind a nullable or fake app lookup.

## 21. No permission cache in the first slice

Webasyst 4.2.0 statically caches some rights lookups. The first Python ACL slice prioritizes correctness and transaction visibility.

No cross-request/process-global permission cache is introduced. A later performance slice may add cache ports/invalidation after measurement.

## 22. Testing strategy

### Exact-source characterization

Characterize exact 4.2.0 behavior for:

- personal + groups + guests `MAX(value)`;
- global backend override;
- app backend `>= 2` unlimited named rights;
- absent app access -> named right zero;
- exact named right then `.all` fallback;
- non-zero negative exact right does not fall back;
- zero write means delete;
- global backend mutation clears all target assignments;
- app backend other than limited clears that app scope;
- legacy principal sign encoding;
- `wa_group.cnt` counts only `is_user > 0` contacts;
- duplicate membership behavior;
- Webasyst admin gating of group/access administration.

Characterization fixtures may mention raw `webasyst/backend` because they document legacy source. Production application code may not.

### Unit

Use fakes to test:

- VOs and discriminated contracts;
- normalized row codec behavior separately from application evaluator;
- `RightsEvaluator` over normalized assignments;
- `ExactThenLegacyAllFallback`;
- `ReservedRightPolicy`;
- `LegacyRightsMutationPolicy` plans;
- `AccessAdministrationPolicy`;
- group/membership/right use-case branching;
- idempotent mutation outcomes;
- rollback behavior where applicable.

### Integration

SQLite integration maps:

- `wa_group`;
- `wa_user_groups`;
- `wa_contact_rights`;
- ACL-relevant `wa_contact` fields.

Required vertical flows:

1. personal + two groups + guests -> effective `MAX` rights;
2. membership delta and count recomputation;
3. group deletion removes memberships and orphan rights atomically;
4. global-admin transition clears old assignments according to legacy semantics;
5. app full/limited/none transitions preserve or clear granular rights correctly;
6. named-right `.all` fallback;
7. denied actor cannot mutate ACL.

### Architecture guards

Fail on:

- `Optional`/`T | None` operation results;
- SQLAlchemy/FastAPI imports in ACL application/contracts;
- compatibility imports from ACL application code;
- signed principal encoding in application APIs;
- literal Webasyst `backend` handling in production ACL application code;
- bool-sentinel ACL operation results.

## 23. Composition

`composition/access_control.py` wires:

- SQLAlchemy group/membership/rights/subject adapters;
- Webasyst principal/right-row codecs;
- `AccessControlUnitOfWork` factory;
- application rights evaluator;
- legacy `.all` fallback policy;
- legacy reserved-right policy;
- legacy mutation planner;
- global-admin administration policy;
- all ACL read/mutation use cases.

The main container may expose these as first-class dependencies, like auth.

No HTTP endpoints are mounted in this slice.

## 24. Scope boundaries

Included:

- mappings of existing ACL/group tables;
- typed ACL contracts/VOs;
- normalized legacy row/principal codecs;
- group CRUD;
- membership add/remove/replace and count maintenance;
- effective-right evaluation;
- app/global access evaluation;
- named-right assignment/revocation;
- app/global access mutation;
- mutation authorization policy;
- dedicated ACL UoW;
- composition;
- characterization/unit/integration/architecture tests.

Deferred:

- Team UI and HTTP endpoints;
- Team location metadata;
- application-specific right-config rendering;
- installed-app/catalog validation beyond the explicit gap above;
- API/OAuth scopes;
- audit-log UI/events;
- permission caching;
- new RBAC schema;
- generic ABAC/policy-engine features.

## 25. Compatibility/deviation summary

Preserved:

- existing schema;
- numeric values;
- personal/group/guest aggregation;
- global/app admin semantics;
- `.all` fallback;
- destructive access-level mutation semantics;
- zero-as-delete storage behavior;
- legacy group member-count definition.

Intentional Python improvements:

- typed principals instead of signed IDs;
- normalized access assignments instead of raw `backend` strings in application code;
- typed results instead of sentinels;
- atomic multi-table ACL mutations;
- explicit access-level mutation API;
- authorization inside the mutation transaction;
- group deletion cleans orphan rights;
- new memberships require real users;
- no global static rights cache.

## 26. Approval and implementation gate

This document is the approved design target. No implementation begins until the human reviewer accepts the written spec. After written-spec approval, create a separate implementation plan and execute it TDD-first on `feature/access-control`.
