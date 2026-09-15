# Access Control / Groups / Permissions Design

**Status:** approved design
**Date:** 2026-09-15
**Scope:** Webasyst 4.2.0-compatible framework access-control core: effective rights evaluation, group CRUD, group membership mutation, named-right assignment/revocation, application access, global-admin access, authorization of ACL mutations, SQLAlchemy mapping of the existing legacy tables, composition and tests.

## 1. Goal

Add a typed access-control subsystem on top of the existing Webasyst tables without translating their legacy integer/principal conventions into application-level magic values and without redesigning the model as conventional RBAC.

The subsystem must preserve the observable semantics of Webasyst 4.2.0 where they matter:

- effective user rights are the maximum of personal, group and guest assignments;
- `webasyst/backend > 0` gives global administrative access;
- an application `backend` value of `1` is limited access and `>= 2` is full/application-admin access;
- full application access makes named rights unlimited;
- `foo.bar` falls back to `foo.all` only when the exact effective value is falsy/zero;
- rights values are integers, not booleans;
- saving `backend` has destructive cleanup semantics in the legacy model;
- setting a right to zero removes the persisted assignment;
- group membership is stored in `wa_user_groups` and `wa_group.cnt` is denormalized;
- the legacy schema is preserved and mapped, not replaced.

The Python application layer must expose explicit typed states/results and must not leak negative legacy principal IDs, SQLAlchemy, nullable sentinel outcomes, or raw `backend` magic-string mutation rules.

## 2. Authoritative Webasyst 4.2.0 source

The exact supplied `webasyst-framework-v.4.2.0.zip` is authoritative for this design, per ADR-015. Relevant files:

- `wa-system/webasyst/lib/models/waContactRights.model.php`
- `wa-system/webasyst/lib/models/waGroup.model.php`
- `wa-system/webasyst/lib/models/waUserGroups.model.php`
- `wa-system/contact/waContact.class.php`
- `wa-system/webasyst/lib/config/db.php`

Observed 4.2.0 behavior used by this design:

1. `waContactRightsModel::get()` builds the candidate legacy principals from the personal assignment, guests (`0`) and group memberships, then uses `MAX(value)` grouped by right name.
2. For any application other than `webasyst`, a non-zero effective `webasyst/backend` returns unlimited access.
3. Effective application `backend >= 2` returns unlimited access for any requested named right.
4. `waContact::getRights()` refuses named rights when application backend access is absent and applies the `foo.bar -> foo.all` fallback when the exact value is zero/falsy.
5. `waContactRightsModel::save()` negates its logical id into the storage principal. Saving `webasyst/backend` first deletes every assignment for that principal. Saving another application's `backend` with a value other than `1` first deletes every assignment for that principal and application. A zero value deletes rather than upserts.
6. `waGroupModel::delete()` removes memberships and the group, but does not explicitly remove `wa_contact_rights` rows for the deleted group.
7. `waGroupModel::updateCounts()` counts only joined contacts with `wa_contact.is_user > 0`.
8. `waUserGroupsModel::add()` is duplicate-tolerant (`INSERT IGNORE`) and refreshes group counts after membership changes.
9. Legacy tables are:
   - `wa_contact_rights(group_id, app_id, name, value)` with composite primary key `(group_id, app_id, name)`;
   - `wa_group(id, name, cnt, icon, sort, type, description)`;
   - `wa_user_groups(contact_id, group_id, datetime)` with composite primary key `(contact_id, group_id)`.

## 3. Chosen architecture

Use a typed compatibility ACL over the existing Webasyst model.

Rejected alternatives:

- **Conventional RBAC (`Role -> Permission`)** loses personal assignments, guest assignments, numeric right values, `MAX` aggregation and Webasyst's special backend semantics.
- **Generic policy engine (`principal/resource/action/condition`)** is unnecessarily broad for this migration slice and would make parity harder to prove.

The core remains Webasyst-compatible but removes storage accidents from application contracts.

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

The exact file split may be tightened during implementation if a file would only contain trivial forwarding code, but the dependency direction is fixed:

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

Internal value objects use immutable stdlib dataclasses when no wire serialization is needed:

```python
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

`RightName` and `AppId` are open identifiers because applications may introduce their own names. Closed status/result domains use `EnumStr`.

Application principals are explicit variants:

```text
UserTarget(contact_id)
GroupTarget(group_id)
GuestsTarget
```

The legacy storage encoding is not a domain model:

```text
UserTarget(ContactId(42)) -> wa_contact_rights.group_id = -42
GroupTarget(GroupId(7))   -> wa_contact_rights.group_id = 7
GuestsTarget()            -> wa_contact_rights.group_id = 0
```

Only the compatibility/infrastructure persistence adapter may perform this conversion.

Negative IDs MUST NOT appear in application contracts or use-case APIs.

## 6. Group model

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

Location-specific Team application records are outside this framework slice. Creating or updating a `LOCATION` group changes only the base `wa_group` record here; Team-specific location metadata belongs to a later application adapter/slice.

Group reads use explicit variants such as `GroupResolved | GroupMissing`; they never return `Group | None`.

## 7. Membership model

Membership is the stable identity `(ContactId, GroupId)` and should use an immutable value object where it repeatedly crosses internal ports.

Operations:

```text
ListUserGroups
ListGroupMembers
AddGroupMember
RemoveGroupMember
ReplaceGroupMembers
```

New membership mutations validate both the group and contact. The first Python mutation implementation accepts only contacts with `is_user > 0` as new members. This is an intentional application invariant: existing legacy rows pointing at other contacts are tolerated when reading, but new Python writes do not create them.

Idempotent outcomes are explicit:

```text
MembershipAdded
MembershipAlreadyPresent
MembershipRemoved
MembershipAlreadyAbsent
MembershipRejected(reason)
```

`ReplaceGroupMembers` computes a delta rather than deleting and reinserting every row. Unchanged memberships therefore preserve their existing legacy `datetime`.

After a membership mutation, the same transaction recomputes `wa_group.cnt` according to the legacy rule: count only memberships whose joined contact has `is_user > 0`.

## 8. Effective-right evaluation

Persistence loads assignments and memberships; a pure evaluator computes effective state.

For a user:

```text
personal assignment
+ every assigned group
+ guests
        |
        v
MAX(value) per (app_id, right_name)
```

The evaluator then applies access rules in this order:

1. For non-`webasyst` applications, effective `webasyst/backend > 0` yields `GlobalAdminAccess` and unlimited named rights.
2. Otherwise effective application `backend >= 2` yields `FullAppAccess` and unlimited named rights.
3. `backend == 1` yields `LimitedAppAccess`.
4. `backend <= 0` or absence yields `NoAppAccess`.
5. Without application access, a named right resolves to finite `0`.
6. With limited access, an exact named-right value is used.
7. If the exact named-right value is `0` and the name contains `.`, evaluate the corresponding `prefix.all` value.
8. Negative non-zero right values remain explicit values and do not trigger `.all` fallback.

`RightValue` therefore remains numeric. Boolean `can_*` is not the canonical framework contract.

Effective named-right result:

```text
FiniteRight(value: RightValue)
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

This prevents callers from reproducing `backend == 1` / `backend >= 2` logic.

## 9. `.all` fallback is an injected policy

`foo.bar -> foo.all` is compatibility behavior, not an intrinsic property of `RightName`.

Use an application-owned policy interface with the initial compatibility implementation:

```text
RightFallbackPolicy
  ExactThenLegacyAllFallback
```

Future applications may register different right fallback behavior without changing the evaluator or storage API.

## 10. Rights snapshots

`GetRightsSnapshot(subject, app_id)` must not pretend to enumerate an infinite set of rights when the subject has full/global access.

Use a variant result:

```text
FiniteRightsSnapshot
  app_access
  effective_named_rights

UnlimitedRightsSnapshot
  app_access
  reason
```

`GetEffectiveRight` remains the precise operation for an arbitrary `RightName`.

## 11. Mutation API

Generic named-right mutation is separate from backend access mutation.

```text
AssignRight(target, PermissionKey, nonzero RightValue)
RevokeRight(target, PermissionKey)
SetAppAccess(target, AppId, AppAccessMode)
SetGlobalAdminAccess(target, GlobalAdminMode)
```

`PermissionKey` combines `AppId + RightName` as one stable identity.

`backend` is reserved in the generic `AssignRight`/`RevokeRight` API. Callers must use `SetAppAccess` or `SetGlobalAdminAccess`, so the destructive legacy cleanup semantics cannot be bypassed accidentally.

`AppAccessMode` is closed:

```text
NONE    -> backend 0
LIMITED -> backend 1
FULL    -> backend 2
```

When reading legacy data, any `backend >= 2` maps to `FullAppAccess`.

`GlobalAdminMode` is closed `ENABLED | DISABLED`; the initial legacy writer uses `webasyst/backend = 1` for enabled and removes it for disabled.

Generic `AssignRight` requires a non-zero value. A requested zero is represented explicitly by `RevokeRight` rather than overloading assignment with deletion semantics.

## 12. Pure legacy mutation planner

Webasyst-specific destructive write behavior is centralized in a pure compatibility policy:

```text
LegacyRightsMutationPolicy
        |
        v
RightsMutationPlan
```

`RightsMutationPlan` is immutable and consists of typed delete/upsert operations.

Required planning semantics:

### Global backend

For `webasyst/backend`:

1. delete every assignment for the target;
2. if enabling, upsert `webasyst/backend = 1`;
3. if disabling, leave no assignment.

This reproduces the legacy `save()` cleanup behavior.

### Application backend

For `app/backend`:

- `LIMITED` (`1`): preserve existing granular application assignments and upsert backend `1`;
- `NONE` (`0`): delete every assignment for that target+app and leave no backend assignment;
- `FULL` (`2`): delete every assignment for that target+app and upsert backend `2`.

### Named rights

- non-zero assignment -> upsert exact `(target, app, name, value)`;
- revoke -> delete exact assignment.

No repository duplicates these rules.

## 13. Persistence ports

### Group repository

Intent-oriented operations:

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

The repository accepts typed `ContactId`/`GroupId`, never loose legacy principal integers.

### Rights repository

```text
load_assignments
group/user/guest snapshot loading through typed targets
upsert
delete_exact
delete_scope
delete_all_for_target
```

The SQLAlchemy adapter alone knows `wa_contact_rights.group_id` encoding.

### Subject access

A narrow access-subject port resolves only what ACL needs from contacts, especially existence and `is_user` eligibility. It must not depend on the full contact CRUD contract.

## 14. Dedicated AccessControlUnitOfWork

ACL writes span multiple tables, so they use a dedicated application-owned UoW rather than extending the contact UoW into a universal service locator.

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
authorize actor
resolve group
delete memberships
delete rights for GroupTarget(group_id)
delete group
commit
```

### ReplaceGroupMembers

```text
authorize actor
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
authorize actor
validate target
build RightsMutationPlan
execute plan
commit
```

Infrastructure faults propagate; ordinary misses/rejections are typed results.

## 15. Intentional integrity improvement: group deletion

Webasyst 4.2.0 `waGroupModel::delete()` removes membership links and the group row but does not explicitly delete `wa_contact_rights` rows owned by that group.

The Python rewrite intentionally improves this behavior:

```text
delete memberships
+ delete group rights
+ delete group
```

This is an accepted compatibility deviation because once the group no longer exists those rights are not observable through legitimate group membership, while retaining them creates orphan ACL data and risks accidental resurrection if identifiers are reused.

The behavior must be documented and covered by integration tests.

## 16. Authorization of administrative mutations

Repositories are not security boundaries. Every group/membership/right mutation use case receives the authenticated actor and checks an injected application-owned administration policy before modifying state.

```text
AuthenticatedSubject actor
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

The first compatibility policy permits ACL administration only to effective `GlobalAdminAccess` subjects.

Authorization MUST be evaluated inside the same `AccessControlUnitOfWork` transaction used for the mutation, before any write, so the authorization decision and state change share one consistent transactional view.

The policy itself remains framework/database-agnostic; it consumes typed effective access state produced by application evaluation services.

Expected denial is a typed result, not an exception or bool sentinel. Infrastructure failures remain exceptional.

## 17. Use cases

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

All expected negative outcomes use explicit typed variants.

Representative families:

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

Do not predeclare speculative error reasons such as `PROTECTED_GROUP` until the model actually gains protected groups.

## 18. Error and validation rules

- Ordinary not-found/already-present/already-absent/access-denied/invalid-command outcomes are typed results per ADR-020.
- No operation result uses `T | None`, `Optional`, bool sentinels or magic strings.
- DB failures, transaction errors and corruption propagate as infrastructure exceptions.
- `AssignRight` rejects reserved `backend` and zero-valued assignment commands.
- `SetAppAccess`/`SetGlobalAdminAccess` own backend semantics.
- Target validation is explicit: a `UserTarget` must resolve to a valid backend user for new mutations; a `GroupTarget` must resolve to an existing group; `GuestsTarget` is always structurally valid.
- Reads tolerate legacy membership rows that violate the new-write `is_user > 0` invariant; new membership writes do not create more of them.

## 19. Application identifiers and installed-app validation

`AppId` is an open identifier. This slice does not introduce the application installation/catalog subsystem solely to validate app existence.

Callers/composition are expected to request rights for installed/configured applications. The legacy behavior where `waContactRightsModel::get()` forces an unknown app to zero will be completed when the application registry/catalog slice exists.

This is an explicit, bounded compatibility gap and must not be hidden behind a nullable or fake app lookup.

## 20. No permission cache in the first slice

Webasyst 4.2.0 caches some rights lookups statically. The first Python ACL slice prioritizes correctness and transaction visibility over caching.

No cross-request or process-global permission cache is introduced. A later performance slice may add cache ports and invalidation only after behavior is measured.

## 21. Testing strategy

### Source characterization

Tests must characterize exact 4.2.0 behavior for:

- personal + groups + guests `MAX(value)`;
- `webasyst/backend` global override;
- application `backend >= 2` unlimited named rights;
- application access absent -> named right zero;
- exact named right then `.all` fallback;
- non-zero negative exact right does not fall back;
- zero write means delete;
- `webasyst/backend` mutation clears all target assignments;
- `app/backend != 1` mutation clears that application scope;
- legacy principal sign encoding;
- `wa_group.cnt` counts only `is_user > 0` contacts;
- duplicate membership behavior.

### Unit

Use fakes to test:

- value objects and discriminated result contracts;
- `RightsEvaluator`;
- `ExactThenLegacyAllFallback`;
- `LegacyRightsMutationPolicy` plans;
- `AccessAdministrationPolicy`;
- group/membership/right use-case branching;
- idempotent membership/right removal outcomes;
- transactional compensation/rollback behavior where applicable.

### Integration

SQLite-backed integration tests cover real mappings of:

- `wa_group`;
- `wa_user_groups`;
- `wa_contact_rights`;
- required `wa_contact` fields used by ACL subject validation/counts.

Required vertical flows include:

1. personal + two groups + guests -> effective `MAX` rights;
2. group membership delta and member-count recomputation;
3. deleted group removes memberships and orphan rights atomically;
4. global-admin transition clears old assignments according to legacy semantics;
5. application full/limited/none transitions preserve or clear granular rights correctly;
6. named-right `.all` fallback;
7. denied actor cannot mutate ACL.

### Architecture guards

Extend architecture tests so they fail on:

- `Optional`/`T | None` operation results;
- SQLAlchemy/FastAPI imports in ACL application/contracts;
- compatibility imports from ACL application code;
- negative principal-id encoding in application APIs;
- direct generic handling of reserved `backend` outside the compatibility mutation/evaluation layer;
- bool-sentinel ACL operation results.

## 22. Composition

`composition/access_control.py` wires:

- SQLAlchemy group/membership/rights/subject adapters;
- `AccessControlUnitOfWork` factory;
- pure rights evaluator;
- legacy `.all` fallback policy;
- legacy mutation planner;
- global-admin administration policy;
- all ACL read and mutation use cases.

The main container may expose these use cases as first-class dependencies, as auth does today.

No HTTP endpoints are mounted in this slice.

## 23. Scope boundaries

Included:

- mappings of existing ACL/group tables;
- typed ACL contracts and VOs;
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

- Team application UI and HTTP endpoints;
- Team location metadata management;
- application-specific right-config rendering;
- application install/catalog validation beyond the explicit gap above;
- API/OAuth scopes;
- audit-log UI/events;
- permission caching;
- a new RBAC schema;
- generic ABAC/policy-engine features.

## 24. Compatibility/deviation summary

Preserved intentionally:

- existing schema;
- numeric right values;
- personal/group/guest aggregation;
- global/app admin semantics;
- `.all` fallback;
- destructive `backend` mutation semantics;
- zero-as-delete persistence semantics;
- legacy group member count definition.

Intentional Python-side improvements:

- typed principals instead of signed IDs;
- typed results instead of sentinel values;
- atomic multi-table ACL mutations;
- explicit backend mutation API;
- authorization checks inside the mutation transaction;
- group deletion cleans orphan rights;
- new memberships require real users;
- no global static rights cache.

## 25. Approval and implementation gate

This document is the approved design target. No implementation begins until the human reviewer accepts the written spec. After written-spec approval, create a separate implementation plan and execute it TDD-first on `feature/access-control`.
