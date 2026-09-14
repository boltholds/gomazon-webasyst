# Backend Auth & Session Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

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

**Interfaces:** Produces `SessionId`, `AuthSessionKey`, `AuthIdentity`, `IdentityKey`, `IdentityLookupPlan`, identity/password/session/authentication result unions, `AuthenticatedSubject`, `SessionMetadata`, and `AuthSessionRegistration`.

- [ ] Write failing tests proving session VOs are frozen/hashable, negative outcomes are explicit union members, raw string discriminators validate, and JSON serialization preserves string values.
- [ ] Run `python -m pytest tests/unit/test_auth_contracts.py -v` and verify RED.
- [ ] Implement minimal VOs/contracts/enums. `IdentityKey.scheme` remains `str`; `AuthSessionKey` contains `contact_id: int` and `session_id: SessionId`.
- [ ] Re-run contract and architecture tests GREEN.
- [ ] Commit `feat: add typed auth contracts and session value objects`.

### Task 2: Policy-driven login planning

**Files:**
- Create: `src/gomazon_webasyst/application/ports/login_policy.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth/policies.py`
- Test: `tests/unit/test_login_policies.py`
- Test: `tests/compatibility/test_auth_characterization.py`

**Interfaces:** `LoginPolicy.evaluate(value, context) -> LoginPolicyDecision`; `LoginPolicySet.plan(value, context) -> LoginPlanResult`. Built-ins are generic registered policies for email priority, phone priority, and configured-scheme fallback.

- [ ] Write failing tests for Webasyst ordering: configured valid email first, configured valid phone first, otherwise configured scheme order; dedupe; disabled schemes absent; blank input returns typed reject.
- [ ] Run RED.
- [ ] Implement generic policies + policy set; keep validation outside auth use case.
- [ ] Run policy + characterization tests GREEN.
- [ ] Commit `feat: add policy driven backend login planning`.

### Task 3: Identity directory and legacy SQLAlchemy resolvers

**Files:**
- Create: `src/gomazon_webasyst/application/ports/identity_directory.py`
- Modify: `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/models.py`
- Create: `src/gomazon_webasyst/infrastructure/auth/identity_directory.py`
- Test: `tests/unit/test_identity_directory.py`
- Test: `tests/integration/test_sqlalchemy_auth_identity.py`

**Interfaces:** `IdentityKeyResolver.resolve(key) -> IdentityKeyResolution`; `IdentityDirectory.resolve(plan) -> IdentityResolution`; registry maps open schemes to resolvers.

- [ ] Write failing unit tests for ordered first-success, typed all-miss, typed unsupported scheme, and extension by registering `employee_id` without API changes.
- [ ] Write failing SQLite tests for `is_user=1`, non-empty password, primary email/phone `sort=0`, first contact by id, login lookup, cleaned phone digits.
- [ ] Run RED.
- [ ] Map only required legacy email/data columns and implement async resolvers hidden in infrastructure.
- [ ] Run unit/integration/architecture tests GREEN.
- [ ] Commit `feat: add extensible legacy identity directory`.

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

**Interfaces:** `AuthSubjectStore.get(subject_id) -> SubjectResolution`; `PasswordVerifier.verify(candidate, stored_hash) -> PasswordVerification`; `CredentialVersionTokenFactory.create(identity) -> CredentialVersionToken`.

- [ ] Write failing tests for MD5 compatibility, invalid password, exact legacy token formula, and explicit subject miss/disabled outcomes.
- [ ] Run RED.
- [ ] Implement minimal adapters; MD5 exists only in compatibility adapter.
- [ ] Run GREEN + architecture guard.
- [ ] Commit `feat: add legacy password and credential token adapters`.

### Task 5: Session state store and `wa_contact_auths` registry

**Files:**
- Create: `src/gomazon_webasyst/application/ports/session_state.py`
- Create: `src/gomazon_webasyst/application/ports/auth_session_registry.py`
- Create: `src/gomazon_webasyst/infrastructure/sessions/memory.py`
- Modify: `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/models.py`
- Create: `src/gomazon_webasyst/infrastructure/auth/session_registry.py`
- Test: `tests/unit/test_session_state_store.py`
- Test: `tests/integration/test_sqlalchemy_auth_session_registry.py`

**Interfaces:** `SessionStateStore.create(...) -> SessionCreationResult`; `resolve(SessionId)`; `revoke(AuthSessionKey)`. Registry `register(registration)`, `check/touch/revoke(AuthSessionKey)`.

- [ ] Write failing in-memory store tests for create/resolve/revoke/idempotent revoke and VO usage.
- [ ] Write failing SQLite registry tests for mapping/upsert/check/touch/revoke and explicit missing result.
- [ ] Run RED.
- [ ] Implement separate state-store and active-auth registry adapters.
- [ ] Run GREEN.
- [ ] Commit `feat: add session state and active auth registry adapters`.

### Task 6: Backend auth/session application use cases

**Files:**
- Create: `src/gomazon_webasyst/application/auth.py`
- Test: `tests/unit/test_auth_use_cases.py`

**Interfaces:** `AuthenticateBackendPassword(...) -> AuthenticationResult`; `ResolveBackendSession(SessionId) -> SessionResolutionResult`; `LogoutBackendSession(SessionId) -> LogoutResult`.

- [ ] Write failing authentication tests for identity miss, wrong password, disabled subject, successful session+registry creation, and cleanup if registry registration fails.
- [ ] Write failing session tests for state miss/expired, subject unavailable/disabled, token mismatch, registry revoked, touch, and strict-check policy.
- [ ] Write failing logout tests for idempotence and coordinated revoke through `AuthSessionKey`.
- [ ] Run RED.
- [ ] Implement minimal use cases with no password/session algorithm details in application.
- [ ] Run GREEN + full unit suite.
- [ ] Commit `feat: add backend authentication session use cases`.

### Task 7: Composition and end-to-end integration

**Files:**
- Modify: `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/factory.py`
- Modify: `src/gomazon_webasyst/composition/container.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth/factory.py`
- Test: `tests/integration/test_auth_session_flow.py`
- Modify: `tests/architecture/test_dependency_boundaries.py`

**Interfaces:** Composition builds policy set, identity/subject/registry adapters, password/token adapters, in-memory session state store, and three auth use cases. No production auth HTTP route is mounted in `main.py` in this slice.

- [ ] Write failing E2E test: seed legacy rows -> authenticate -> get `AuthSessionKey` -> resolve by `SessionId` -> logout -> resolve returns typed negative outcome.
- [ ] Extend architecture guard for SQLAlchemy/FastAPI/hashlib/session framework leakage.
- [ ] Run RED.
- [ ] Wire concrete adapters at composition root.
- [ ] Run integration GREEN.
- [ ] Run full `python -m pytest -v` and `python -m compileall -q src tests`.
- [ ] Record exact verification counts; update `AGENTS.md` only if implementation reveals a new architecture decision.
- [ ] Commit `feat: wire backend auth session foundation`.

## Verification

Before merge:

- `python -m pytest -v`
- `python -m compileall -q src tests`
- feature-branch GitHub Actions on Python 3.12 with dev drivers
- compare `main...feature/auth-session` for unrelated changes
- confirm no production HTTP auth endpoint has been silently mounted
- confirm no normal auth result contract uses `Optional`/bool sentinel semantics
- confirm no central `find_by_login/find_by_email/find_by_phone` API exists
- confirm `AuthSessionRegistry` does not accept loose `(contact_id, session_id)` parameters
