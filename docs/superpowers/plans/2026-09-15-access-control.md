# Access Control / Groups / Permissions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Webasyst 4.2.0-compatible typed ACL core over `wa_contact_rights`, `wa_group`, and `wa_user_groups`, including effective-right evaluation, group/membership CRUD, right assignment/revocation, app/global access mutation, authorization, SQLAlchemy persistence, composition, and tests.

**Architecture:** Application code consumes typed principals, normalized access assignments, discriminated results, a pure evaluator, a pure legacy mutation planner, and a dedicated `AccessControlUnitOfWork`. SQLAlchemy adapters map the existing legacy schema; only the compatibility/persistence edge knows signed principal IDs and raw `backend`/`webasyst` storage names. All mutations are authorized inside the same ACL transaction before writes.

**Tech Stack:** Python 3.12+, Pydantic v2, SQLAlchemy 2 async, asyncmy, aiosqlite, pytest.

**Spec:** `docs/superpowers/specs/2026-09-15-access-control-design.md`

## Implementation Status

Tasks 1–10 were implemented TDD-first on `feature/access-control` and passed the full branch verification before this documentation-only completion commit.

Verification evidence:

- functional implementation head: `ae450bdfd921fef4bf5206bfc45f926b5305bfc4`;
- GitHub Actions run: `34984645388`, job `104433502888`;
- Python: 3.12.14;
- `python -m compileall -q src tests`: success;
- `python -m pytest -v`: **246 passed, 0 failed, 0 skipped**;
- architecture guards passed, including ADR-023 Optional/nullability enforcement and ACL dependency/storage-boundary guards;
- SQLite vertical flow passed for effective MAX rights, membership/count mutations, app/global access transitions, named right assign/revoke, group-right cleanup, and denied mutation;
- `main...feature/access-control` review at functional head: **68 commits ahead / 0 behind** and changes were limited to ACL contracts/application/compatibility/infrastructure/composition, legacy ORM mappings, tests, and ACL docs;
- review found no HTTP ACL endpoints, new RBAC tables, Team location persistence, app catalog, OAuth/API-scope changes, permission cache, or unrelated refactors;
- implementation introduced no architectural decision beyond ADR-026…029.

The unchecked boxes below are the original execution checklist retained as the historical plan; the implementation status above is the authoritative completion record.

## Global Constraints

- Exact supplied Webasyst Framework 4.2.0 source is authoritative.
- Preserve existing `wa_contact_rights`, `wa_group`, and `wa_user_groups` schema; do not create a new RBAC schema.
- Numeric rights remain integers; canonical evaluation results are typed, not bools.
- No expected result/lookup branch uses `None`, `Optional`, empty sentinel values, or bool sentinels.
- Negative/signed legacy principal IDs never cross the persistence/compatibility boundary.
- Generic named-right mutation cannot mutate reserved `backend`.
- Literal `backend`, global-control app storage naming, and `.all` storage fallback semantics stay in Webasyst compatibility implementations rather than application use cases.
- Application/contracts import no SQLAlchemy/FastAPI or compatibility implementations.
- Multi-table mutations use a dedicated `AccessControlUnitOfWork`.
- Mutation authorization occurs before writes inside the same UoW transaction.
- Group deletion intentionally removes orphan group rights in addition to memberships and group row.
- New group-membership writes accept only contacts with `is_user > 0`; legacy invalid rows remain readable.
- No HTTP endpoints, Team location storage, app catalog, OAuth/API scopes, permission cache, or audit UI in this slice.

---

### Task 1: Access-control value objects, result contracts, and source characterization

**Files:**
- Create: `src/gomazon_webasyst/application/access_values.py`
- Create: `src/gomazon_webasyst/contracts/access_control.py`
- Modify: `src/gomazon_webasyst/contracts/enums.py`
- Create: `tests/unit/test_access_control_contracts.py`
- Create: `tests/compatibility/test_access_control_characterization.py`
- Modify: `tests/architecture/test_no_optional_result_contracts.py`

**Interfaces:**
- Produces immutable `GroupId`, `AppId`, `RightName`, `RightValue`, `PermissionKey`, `UserTarget`, `GroupTarget`, `GuestsTarget`, `GroupMembership`.
- Produces Pydantic group/read/mutation/evaluation result variants consumed by later tasks.
- Produces `GroupType`, access/result discriminator enums, rejection reason enums, `AppAccessMode`, `GlobalAdminMode`, `UnlimitedRightReason`.

- [ ] **Step 1: Write failing contract tests** for positive `GroupId`, non-empty `AppId`/`RightName`, hashable/frozen VOs, typed target variants, `GroupType`, raw-string discriminator parsing, explicit negative results, and absence of nullable result fields.

```python

def test_access_values_are_frozen_and_hashable():
    key = PermissionKey(AppId("shop"), RightName("orders.edit"))
    target = UserTarget(42)
    assert {key}
    assert {target}


def test_app_access_is_explicit_variant_not_integer_sentinel():
    result = LimitedAppAccess(app_id="shop")
    assert result.kind is AppAccessKind.LIMITED
```

- [ ] **Step 2: Add source-characterization tests** that pin exact 4.2.0 rules: personal/group/guest MAX aggregation; global override; app backend >=2; `.all` fallback after zero exact value; negative nonzero exact value blocks fallback; zero write deletes; global/backend destructive cleanup; app/backend !=1 cleanup; principal sign encoding; group count rule; duplicate membership behavior.
- [ ] **Step 3: Run RED**.

Run: `python -m pytest tests/unit/test_access_control_contracts.py tests/compatibility/test_access_control_characterization.py tests/architecture/test_no_optional_result_contracts.py -v`

- [ ] **Step 4: Implement minimal VOs, enums, and Pydantic contracts**. Use closed discriminators via `EnumStr`; open identifiers remain VOs, not enums.
- [ ] **Step 5: Run GREEN + architecture guard**.
- [ ] **Step 6: Commit** `feat: add typed access control contracts`.

### Task 2: Typed assignment normalization, app classification, and right fallback policy

**Files:**
- Create: `src/gomazon_webasyst/application/ports/rights.py`
- Create: `src/gomazon_webasyst/application/rights_evaluator.py`
- Create: `src/gomazon_webasyst/application/ports/access_semantics.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/access_control/evaluation.py`
- Test: `tests/unit/test_rights_evaluator.py`

**Interfaces:**
- `RightAssignment = GlobalAccessAssignment | AppAccessAssignment | NamedRightAssignment`, each carrying typed target/value fields.
- `RightsSnapshot(assignments: tuple[RightAssignment, ...])`.
- `AccessSemantics.classify_app(AppId) -> GlobalControlApp | RegularApp`.
- `RightFallbackPolicy.fallback(RightName) -> RightFallbackAvailable | RightFallbackUnavailable`.
- `WebasystAccessSemantics` classifies only the legacy global-control app and implements exact-then-`.all` fallback.
- `RightsEvaluator` consumes normalized assignments and policies; it contains no literal storage key `backend`.

- [ ] **Step 1: Write failing evaluator tests** for MAX across `UserTarget`, two groups, and guests; no app access; limited access; full access; global override on a regular app; global-control app value `1` not making arbitrary named rights unlimited; `.all` fallback only after exact zero; negative exact value suppressing fallback.
- [ ] **Step 2: Run RED**.
- [ ] **Step 3: Implement normalized assignment types, semantics/fallback ports, Webasyst compatibility implementation, and pure evaluator**.
- [ ] **Step 4: Run GREEN + dependency-boundary tests**.
- [ ] **Step 5: Commit** `feat: add access rights evaluator`.

### Task 3: Pure legacy rights mutation planner

**Files:**
- Create: `src/gomazon_webasyst/application/rights_mutation_policy.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/access_control/mutation.py`
- Test: `tests/unit/test_rights_mutation_policy.py`

**Interfaces:**
- Immutable operations: `DeleteAllTargetRights`, `DeleteAppRights`, `DeleteExactRight`, `UpsertGlobalAccess`, `UpsertAppAccess`, `UpsertNamedRight`.
- `RightsMutationPlan(operations: tuple[RightsMutationOperation, ...])`.
- `RightsMutationPolicy.plan_named_assign`, `.plan_named_revoke`, `.plan_app_access`, `.plan_global_access`.
- `LegacyRightsMutationPolicy` implements exact Webasyst 4.2.0 destructive semantics.

- [ ] **Step 1: Write failing planner tests**: global enable deletes all then upserts global=1; global disable deletes all only; app limited preserves granular and upserts=1; app none deletes app scope only; app full deletes app scope then upserts=2; named assign upserts nonzero; revoke deletes exact; `SetAppAccess` for global-control app is rejected by typed planning result.
- [ ] **Step 2: Run RED**.
- [ ] **Step 3: Implement immutable plans and compatibility planner** without DB calls.
- [ ] **Step 4: Run GREEN**.
- [ ] **Step 5: Commit** `feat: add legacy rights mutation planner`.

### Task 4: SQLAlchemy mappings and signed-principal codec

**Files:**
- Modify: `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/models.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/access_control/principals.py`
- Create: `tests/unit/test_access_control_sqlalchemy_mapping.py`
- Create: `tests/unit/test_legacy_principal_codec.py`

**Interfaces:**
- Adds ORM rows for `wa_group`, `wa_user_groups`, and `wa_contact_rights` using legacy column names/nullability and composite keys.
- `WebasystPrincipalCodec.encode(AccessTarget) -> LegacyPrincipalId` and `.decode(LegacyPrincipalId) -> AccessTarget` with explicit typed decode rejection rather than nullable miss.

- [ ] **Step 1: Write failing mapping tests** asserting table names, PK columns, nullable legacy columns, and ability for SQLite metadata to create the three tables.
- [ ] **Step 2: Write failing codec tests** for user `42 -> -42`, group `7 -> 7`, guests `0`, inverse decode, and invalid impossible typed input rejection.
- [ ] **Step 3: Run RED**.
- [ ] **Step 4: Implement mappings and codec**. Genuine nullable legacy columns may use `T | None` only in ORM fields under ADR-023.
- [ ] **Step 5: Run GREEN + optional-contract architecture tests**.
- [ ] **Step 6: Commit** `feat: map legacy access control tables`.

### Task 5: SQLAlchemy repositories and dedicated AccessControlUnitOfWork

**Files:**
- Create: `src/gomazon_webasyst/application/ports/groups.py`
- Create: `src/gomazon_webasyst/application/ports/memberships.py`
- Create: `src/gomazon_webasyst/application/ports/access_subjects.py`
- Create: `src/gomazon_webasyst/application/ports/access_control_uow.py`
- Create: `src/gomazon_webasyst/infrastructure/access_control/sqlalchemy/groups.py`
- Create: `src/gomazon_webasyst/infrastructure/access_control/sqlalchemy/memberships.py`
- Create: `src/gomazon_webasyst/infrastructure/access_control/sqlalchemy/rights.py`
- Create: `src/gomazon_webasyst/infrastructure/access_control/sqlalchemy/subjects.py`
- Create: `src/gomazon_webasyst/infrastructure/access_control/sqlalchemy/unit_of_work.py`
- Test: `tests/integration/test_sqlalchemy_access_control_repositories.py`
- Test: `tests/unit/test_access_control_unit_of_work.py`

**Interfaces:**
- `GroupRepository`: typed `create/get/list/update/delete`.
- `MembershipRepository`: typed `list_for_user/list_for_group/add/remove/apply_delta/recount_group`.
- `RightsRepository`: `load_for_targets`, `execute_plan`, `delete_all_for_target` using normalized assignment types and `RightsMutationPlan`.
- `AccessSubjectStore.resolve(contact_id) -> AccessSubjectResolved | AccessSubjectMissing | AccessSubjectNotUser`.
- `AccessControlUnitOfWork` exposes `groups`, `memberships`, `rights`, `subjects`, `commit`, `rollback` and explicit active/inactive lifecycle state.

- [ ] **Step 1: Write repository integration tests** for group typed miss/create/update/delete; membership idempotent raw operations and count recomputation; subject classification; rights round-trip normalization without signed IDs escaping; mutation plan execution.
- [ ] **Step 2: Write UoW lifecycle/rollback tests** matching the existing explicit active-state pattern.
- [ ] **Step 3: Run RED**.
- [ ] **Step 4: Implement ports and SQLAlchemy adapters**. Raw SQLAlchemy `None` is normalized immediately inside adapters.
- [ ] **Step 5: Run GREEN**.
- [ ] **Step 6: Commit** `feat: add access control persistence adapters`.

### Task 6: ACL read/evaluation use cases

**Files:**
- Create: `src/gomazon_webasyst/application/access_control.py`
- Test: `tests/unit/test_access_control_reads.py`

**Interfaces:**
- `GetGroup`, `ListGroups`, `ListUserGroups`, `ListGroupMembers`.
- `GetEffectiveRight`, `GetAppAccess`, `GetRightsSnapshot`.
- Evaluation loads user subject, memberships, then typed target assignments through the UoW and delegates to `RightsEvaluator`.
- `GetRightsSnapshot` returns `FiniteRightsSnapshot | UnlimitedRightsSnapshot` and never fabricates infinite named-right maps.

- [ ] **Step 1: Write failing read-use-case tests** for typed misses, membership reads, regular finite evaluation, global/full unlimited snapshots, and subject-not-found/not-user rejection.
- [ ] **Step 2: Run RED**.
- [ ] **Step 3: Implement read use cases** with no mutation or authorization concerns.
- [ ] **Step 4: Run GREEN**.
- [ ] **Step 5: Commit** `feat: add access control read use cases`.

### Task 7: Administration authorization policy

**Files:**
- Create: `src/gomazon_webasyst/application/ports/access_admin_policy.py`
- Create: `src/gomazon_webasyst/application/access_admin_policy.py`
- Test: `tests/unit/test_access_admin_policy.py`

**Interfaces:**
- `AccessAdministrationPolicy.authorize(actor, uow) -> AccessAdministrationAuthorized | AccessAdministrationDenied`.
- `GlobalAdminAccessAdministrationPolicy` evaluates the actor through the same active ACL UoW and authorizes only effective global admin access.

- [ ] **Step 1: Write failing tests** for global admin authorize, regular/full app admin deny, missing/not-user actor deny, and infrastructure failure propagation.
- [ ] **Step 2: Run RED**.
- [ ] **Step 3: Implement policy** using typed evaluator results, not bool shortcuts.
- [ ] **Step 4: Run GREEN**.
- [ ] **Step 5: Commit** `feat: add access administration policy`.

### Task 8: Group and membership mutation use cases

**Files:**
- Modify: `src/gomazon_webasyst/application/access_control.py`
- Test: `tests/unit/test_access_control_group_mutations.py`

**Interfaces:**
- `CreateGroup`, `UpdateGroup`, `DeleteGroup`.
- `AddGroupMember`, `RemoveGroupMember`, `ReplaceGroupMembers`.
- Every call accepts `AuthenticatedSubject actor` plus typed command data.
- Authorization runs inside the opened UoW before any write.

- [ ] **Step 1: Write failing tests** for denied actor no-write behavior; group create/update/delete; group miss; group delete sequence memberships -> rights -> group; add duplicate -> already-present; remove absent -> already-absent; contact missing/not-user rejection; replace delta preserving unchanged memberships; recount after changes; rollback on infrastructure failure.
- [ ] **Step 2: Run RED**.
- [ ] **Step 3: Implement group/membership mutations**. `DeleteGroup` intentionally calls `rights.delete_all_for_target(GroupTarget(...))` before deleting the row.
- [ ] **Step 4: Run GREEN**.
- [ ] **Step 5: Commit** `feat: add group and membership mutations`.

### Task 9: Named rights and app/global access mutation use cases

**Files:**
- Modify: `src/gomazon_webasyst/application/access_control.py`
- Test: `tests/unit/test_access_control_right_mutations.py`

**Interfaces:**
- `AssignRight`, `RevokeRight`, `SetAppAccess`, `SetGlobalAdminAccess`.
- Target validation happens before planning; guests are structurally valid, users/groups must resolve.
- `AssignRight` rejects zero and reserved backend semantic commands; `SetAppAccess` rejects the global-control app and delegates its special case to `SetGlobalAdminAccess`.
- Mutation planner builds a `RightsMutationPlan`; repository executes it atomically.

- [ ] **Step 1: Write failing tests** for denied actor; missing target; reserved right rejection; zero assign rejection; named assignment/revoke; app limited/full/none transitions; global enable/disable; global-control app cannot go through `SetAppAccess`; typed already-absent revoke result where observable.
- [ ] **Step 2: Run RED**.
- [ ] **Step 3: Implement rights/access mutations** with planner + UoW commit.
- [ ] **Step 4: Run GREEN**.
- [ ] **Step 5: Commit** `feat: add access right mutations`.

### Task 10: Composition, vertical SQLite flow, and architecture guards

**Files:**
- Create: `src/gomazon_webasyst/composition/access_control.py`
- Modify: `src/gomazon_webasyst/composition/container.py`
- Modify: `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/factory.py`
- Create: `tests/unit/test_access_control_container.py`
- Create: `tests/integration/test_access_control_flow.py`
- Modify: `tests/architecture/test_dependency_boundaries.py`
- Modify: `tests/architecture/test_no_optional_result_contracts.py`

**Interfaces:**
- `AccessControlUseCases` groups all ACL read/mutation use cases.
- `create_access_control_use_cases(session_factory)` creates the dedicated ACL UoW factory, Webasyst semantics/fallback, evaluator, mutation planner and global-admin policy.
- Main `Container` exposes ACL use cases as first-class dependencies.

- [ ] **Step 1: Write failing composition tests** proving one shared ACL UoW factory is wired across policy/read/mutation services and concrete compatibility policies are injected explicitly.
- [ ] **Step 2: Write failing SQLite vertical E2E**: seed actor/user/groups/guest+personal+group rights; verify effective MAX; add/remove/replace membership and count; set app full/limited/none; set global admin; assign/revoke named rights; delete group and verify memberships + group rights are removed; denied actor cannot mutate.
- [ ] **Step 3: Extend architecture guards** to reject SQLAlchemy/FastAPI/compatibility imports in ACL application/contracts, signed principal encoding outside compatibility/infrastructure, new nullable result contracts, and direct generic reserved-backend mutation behavior.
- [ ] **Step 4: Run RED where appropriate**.
- [ ] **Step 5: Implement composition/container/factory wiring and only corrections required by the vertical test**.
- [ ] **Step 6: Run full verification**:

```bash
python -m compileall -q src tests
python -m pytest -v
```

- [ ] **Step 7: Compare `main...feature/access-control`** and confirm no HTTP endpoints, new RBAC tables, Team location persistence, app catalog, OAuth/API scopes, permission cache, or unrelated refactors entered the slice.
- [ ] **Step 8: Record exact verification evidence in this plan and update `AGENTS.md` only if implementation reveals a new architectural decision beyond ADR-026…029**.
- [ ] **Step 9: Commit** `test: verify access control vertical flow`.

## Verification Checklist

Before integration:

- exact branch head passes `python -m compileall -q src tests`;
- exact branch head passes the full pytest suite with zero failures;
- characterization tests cover exact 4.2.0 ACL semantics listed above;
- no application ACL contract or operation uses `Optional`/`T | None` sentinel state;
- no canonical ACL operation returns bool for an ordinary branch;
- signed principal IDs remain persistence-private;
- generic named-right APIs cannot mutate backend access;
- `webasyst/backend=1` edge does not make arbitrary named rights of the global-control app unlimited;
- authorization is checked inside the same ACL UoW transaction before writes;
- group deletion removes group rights intentionally;
- membership counts follow `is_user > 0` legacy behavior;
- no production HTTP route is mounted for ACL in this slice.