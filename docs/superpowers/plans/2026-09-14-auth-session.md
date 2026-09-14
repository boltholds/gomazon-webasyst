# Backend Auth & Session Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Implement Webasyst 4.2.0 backend password authentication and authenticated-session create/resolve/revoke with policy-driven identity lookup, explicit typed outcomes, immutable session VOs, and existing legacy tables.

**Architecture:** Raw login input is normalized by an ordered `LoginPolicySet` into an `IdentityLookupPlan`; an `IdentityDirectory` resolves keys through a scheme registry. Password verification, subject loading, session state, active-auth registry, and credential-version token generation are injected ports. Expected negative outcomes are typed unions; `SessionId`/`AuthSessionKey` are immutable dataclass VOs; SQLAlchemy remains infrastructure-private.

**Tech Stack:** Python 3.12+, Pydantic v2, SQLAlchemy 2 async, asyncmy, aiosqlite, FastAPI/Starlette only at presentation boundaries, pytest.

**Spec:** `docs/superpowers/specs/2026-09-14-auth-session-design.md`

## Global Constraints

- Webasyst 4.2.0 source is authoritative over newer docs when behavior conflicts.
- No normal auth failure/miss/revocation uses `None`, `False`, empty values, or exception-as-branch.
- Extensible identity lookup uses open string schemes + policies/registry; do not add `find_by_*` methods.
- Serialized discriminators use `EnumStr`; Pydantic field discriminators use `Literal[EnumMember]`.
- Correlated session identifiers use immutable `@dataclass(slots=True, frozen=True)` VOs.
- `SessionStateStore` and `AuthSessionRegistry` are separate ports.
- Application/contracts may not import SQLAlchemy/FastAPI/session framework/concrete password algorithms.
- Existing `wa_contact`, `wa_contact_emails`, `wa_contact_data`, and `wa_contact_auths` are mapped; no destructive schema migration.
- Remember-me, OTP, frontend signup/confirmation, permissions, OAuth/social/Webasyst ID, API OAuth2, and PHP session-file interoperability remain out of scope.

---

### Task 1: Auth value objects and explicit result contracts

**Files:**
- Create: `src/gomazon_webasyst/application/auth_values.py`
- Create: `src/gomazon_webasyst/contracts/auth.py`
- Modify: `src/gomazon_webasyst/contracts/enums.py`
- Test: `tests/unit/test_auth_contracts.py`

**Interfaces:**
- Produces `SessionId`, `AuthSessionKey` immutable VOs.
- Produces Pydantic `AuthIdentity`, `IdentityKey`, `IdentityLookupPlan`, identity/password/session/authentication result unions, `AuthenticatedSubject`, `SessionMetadata`, `AuthSessionRegistration`.
- Adds auth discriminator/error enums derived from `EnumStr`.

- [x] **Step 1: Write failing contract/VO tests** proving `SessionId`/`AuthSessionKey` are frozen/hashable, negative outcomes are explicit union members, raw string discriminators validate, and JSON serialization preserves legacy string values.
- [x] **Step 2: Run** `python -m pytest tests/unit/test_auth_contracts.py -v` and verify failure is caused by missing auth contracts.
- [x] **Step 3: Implement minimal VOs/contracts/enums**. `AuthSessionKey` contains `contact_id: int` and `session_id: SessionId`; no duplicate loose pair fields. `IdentityKey.scheme` remains `str`.
- [x] **Step 4: Re-run auth contract tests**, then architecture tests.
- [x] **Step 5: Commit** `feat: add typed auth contracts and session value objects`.

### Task 2: Policy-driven login planning

**Files:**
- Create: `src/gomazon_webasyst/application/ports/login_policy.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth/policies.py`
- Test: `tests/unit/test_login_policies.py`
- Test: `tests/compatibility/test_auth_characterization.py`

**Interfaces:**
- `LoginPolicy.evaluate(value: str, context: LoginPolicyContext) -> LoginPolicyDecision`.
- `LoginPolicySet.plan(value, context) -> LoginPlanResult`.
- Built-ins are generic registered policies for email priority, phone priority, and configured-scheme fallback; adding another scheme does not modify `AuthenticateBackendPassword`.

- [x] **Step 1: Write failing tests** for Webasyst ordering: valid configured email first, valid configured phone first, otherwise configured scheme order; dedupe repeated keys; disabled schemes are not added; blank identifier returns typed reject.
- [x] **Step 2: Run policy tests and verify RED**.
- [x] **Step 3: Implement minimal generic policies + policy set**. Phone recognition follows legacy allowed characters; email recognizer covers characterized Webasyst-compatible cases without putting validation inside the auth use case.
- [x] **Step 4: Run policy + characterization tests GREEN**.
- [x] **Step 5: Commit** `feat: add policy driven backend login planning`.

### Task 3: Identity directory and legacy SQLAlchemy resolvers

**Files:**
- Create: `src/gomazon_webasyst/application/ports/identity_directory.py`
- Modify: `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/models.py`
- Create: `src/gomazon_webasyst/infrastructure/auth/identity_directory.py`
- Test: `tests/unit/test_identity_directory.py`
- Test: `tests/integration/test_sqlalchemy_auth_identity.py`

**Interfaces:**
- `IdentityKeyResolver.resolve(key) -> IdentityKeyResolution`.
- `IdentityDirectory.resolve(plan) -> IdentityResolution`.
- Registry maps open schemes to resolvers.
- Built-in SQLAlchemy resolvers: `login`, `email`, `phone`.

- [x] **Step 1: Write failing unit tests** proving ordered first-success, typed all-miss, typed unsupported scheme, and extensibility by registering `employee_id` without changing the directory API.
- [x] **Step 2: Write failing SQLite integration tests** for legacy semantics: `is_user=1`, non-empty password, primary email/phone (`sort=0`), first matching contact by id, login lookup, cleaned phone digits.
- [x] **Step 3: Run tests RED**.
- [x] **Step 4: Map only required legacy columns for `wa_contact_emails` and `wa_contact_data`, then implement directory/resolvers with async SQLAlchemy sessions hidden inside infrastructure**.
- [x] **Step 5: Run unit/integration tests GREEN** and architecture guard.
- [x] **Step 6: Commit** `feat: add extensible legacy identity directory`.

### Task 4: Subject store, password verifier, and credential token factory

**Files:**
- Create: `src/gomazon_webasyst/application/ports/auth_subjects.py`
- Create: `src/gomazon_webasyst/application/ports/password_verifier.py`
- Create: `src/gomazon_webasyst/application/ports/credential_tokens.py`
- Create: `src/gomazon_webasyst/infrastructure/auth/subjects.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth/passwords.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth/tokens.py`
- Test: `tests/unit/test_password_verifier.py`
- Test: `tests/unit/test_credential_token.py`
- Test: `tests/integration/test_sqlalchemy_auth_subjects.py`

**Interfaces:**
- `AuthSubjectStore.get(subject_id: int) -> SubjectResolution` explicit result.
- `PasswordVerifier.verify(candidate: SecretStr, stored_hash: str) -> PasswordVerification`.
- `CredentialVersionTokenFactory.create(identity) -> CredentialVersionToken`.

- [x] **Step 1: Write failing tests** for MD5 compatibility, invalid password, injected verifier shape, exact legacy token formula `md5(create_datetime + login + password_hash)` with id inserted between first/last 15 chars, and explicit subject miss/disabled outcomes.
- [x] **Step 2: Run RED**.
- [x] **Step 3: Implement minimal adapters**. MD5 exists only in compatibility adapter. Token formatting matches `waAuth::getToken()` exactly.
- [x] **Step 4: Run GREEN** plus architecture guard proving application does not import `hashlib`/compat password implementation.
- [x] **Step 5: Commit** `feat: add legacy password and credential token adapters`.

### Task 5: Session state store and `wa_contact_auths` registry

**Files:**
- Create: `src/gomazon_webasyst/application/ports/session_state.py`
- Create: `src/gomazon_webasyst/application/ports/auth_session_registry.py`
- Create: `src/gomazon_webasyst/infrastructure/sessions/memory.py`
- Modify: `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/models.py`
- Create: `src/gomazon_webasyst/infrastructure/auth/session_registry.py`
- Test: `tests/unit/test_session_state_store.py`
- Test: `tests/integration/test_sqlalchemy_auth_session_registry.py`

**Interfaces:**
- `SessionStateStore.create(...) -> SessionCreationResult` carrying `AuthSessionKey`.
- `SessionStateStore.resolve(SessionId) -> SessionStateResolution`.
- `SessionStateStore.revoke(AuthSessionKey) -> SessionRevocationResult`.
- `AuthSessionRegistry.register(registration)`, `check(key)`, `touch(key)`, `revoke(key)` all explicit typed results.

- [x] **Step 1: Write failing in-memory state-store tests** for create/resolve/revoke/idempotent revoke and VO usage.
- [x] **Step 2: Write failing SQLite registry tests** mapping `wa_contact_auths`, unique session id semantics, register/upsert, check, touch, revoke, and explicit missing result.
- [x] **Step 3: Run RED**.
- [x] **Step 4: Implement the in-memory state adapter and SQLAlchemy active-auth registry**; do not merge responsibilities.
- [x] **Step 5: Run GREEN**.
- [x] **Step 6: Commit** `feat: add session state and active auth registry adapters`.

### Task 6: Backend auth/session application use cases

**Files:**
- Create: `src/gomazon_webasyst/application/auth.py`
- Test: `tests/unit/test_auth_use_cases.py`

**Interfaces:**
- `AuthenticateBackendPassword(...) -> AuthenticationResult`.
- `ResolveBackendSession(SessionId) -> SessionResolutionResult`.
- `LogoutBackendSession(SessionId) -> LogoutResult` (initial opaque id is resolved to `AuthSessionKey` before coordinated revoke).
- Uses only application-owned ports/contracts/VOs.

- [x] **Step 1: Write failing authentication tests** for identity miss, wrong password, disabled/non-user subject, successful state creation + registry registration, and compensation (revoke created state if registry registration raises infrastructure error).
- [x] **Step 2: Write failing session-resolution tests** for state miss/expired, subject unavailable/disabled, credential token mismatch, registry revoked, successful touch, and strict-check policy.
- [x] **Step 3: Write failing logout tests** proving idempotence and coordinated revocation through canonical `AuthSessionKey`.
- [x] **Step 4: Run RED**.
- [x] **Step 5: Implement minimal use cases and explicit policy objects**; no password/session algorithm details in application.
- [x] **Step 6: Run GREEN + full unit suite**.
- [x] **Step 7: Commit** `feat: add backend authentication session use cases`.

### Task 7: Composition and end-to-end integration

**Files:**
- Modify: `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/factory.py`
- Modify: `src/gomazon_webasyst/composition/container.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth/factory.py`
- Test: `tests/integration/test_auth_session_flow.py`
- Modify: `tests/architecture/test_dependency_boundaries.py`

**Interfaces:**
- Composition root builds resolver registry, policy set, SQLAlchemy identity/subject/registry adapters, compatibility password/token adapters, in-memory session state store, and three use cases.
- No auth HTTP catch-all/login route is mounted in `main.py` in this slice unless separately approved.

- [x] **Step 1: Write failing end-to-end integration test**: seed legacy contact/email/phone rows -> authenticate -> obtain `AuthSessionKey` -> resolve by `SessionId` -> revoke/logout -> subsequent resolve returns explicit negative result.
- [x] **Step 2: Extend architecture guard** for FastAPI/SQLAlchemy/hashlib/session framework imports in application/contracts.
- [x] **Step 3: Run RED**.
- [x] **Step 4: Wire concrete adapters at composition root** and implement small auth factory helpers.
- [x] **Step 5: Run auth integration GREEN**.
- [x] **Step 6: Run full `python -m pytest -v` and `python -m compileall -q src tests`**.
- [x] **Step 7: Update this plan verification section with exact local/CI counts; update `AGENTS.md` only if implementation revealed a new architecture decision**.
- [x] **Step 8: Commit** `feat: wire backend auth session foundation`.

## Verification

Before merge:

- `python -m pytest -v`
- `python -m compileall -q src tests`
- feature-branch GitHub Actions on Python 3.12 with all dev drivers installed
- compare `main...feature/auth-session` and verify no unrelated changes
- confirm no production HTTP auth endpoint has been silently mounted
- confirm no normal auth result contract uses `Optional`/bool sentinel semantics
- confirm no central `find_by_login/find_by_email/find_by_phone` API exists
- confirm `AuthSessionRegistry` does not accept loose `(contact_id, session_id)` parameters

## Implementation Status

Implemented on `feature/auth-session`.

Verification:

- Local Python 3.13 snapshot: `128 passed, 7 skipped`; skips are driver-dependent integration modules unavailable locally.
- `python -m compileall -q src tests`: exit 0.
- GitHub Actions Python 3.12 with `aiosqlite`/`asyncmy`: `141 passed, 0 failed, 0 skipped` on commit `8344f99dc147791738172dc671c0db60a7f52ca9`.
- `main.py` remains unchanged; no production auth HTTP route is mounted.
- `AuthSessionRegistry` uses `AuthSessionKey`; initial opaque lookup uses `SessionId`.
- Identity lookup remains policy/registry driven with no central `find_by_*` API.
- Session validation cadence is an explicit `SessionValidationPolicy`; composition selects strict-every-request by default and can inject another policy.

Known foundation limitations (intentional, outside this slice):

- default `SessionStateStore` adapter is in-memory and therefore not durable across process restart or suitable for multi-worker shared state;
- legacy auth config is not yet loaded automatically, so enabled login schemes and phone-prefix transform configuration must be supplied by composition/caller;
- legacy `wa_contact_auths` old-session cleanup is not implemented;
- remember-me, frontend auth, permissions, OAuth/API tokens and PHP-session interoperability remain later slices.
