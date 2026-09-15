# Persistent Login / Remember-Me Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Webasyst 4.2.0-compatible backend persistent login using the legacy `auth_token` format behind an extensible strategy/issuer bridge, reusing the existing typed auth/session foundation.

**Architecture:** A raw `PersistentCredential` is accepted through an ordered `PersistentCredentialStrategy` chain and restored through `RestoreBackendSessionFromPersistentCredential`. Credential issuance is a separate `IssuePersistentCredential` operation using an injected `PersistentCredentialIssuer`. Password login and persistent restore share one `BackendSessionEstablisher`, while application results carry transport-neutral `refresh / clear / keep` dispositions and never expose cookie/HTTP types.

**Tech Stack:** Python 3.12+, Pydantic v2, SQLAlchemy 2 async, asyncmy, aiosqlite, pytest; FastAPI/Starlette only at presentation boundaries.

**Spec:** `docs/superpowers/specs/2026-09-14-persistent-login-design.md`

## Global Constraints

- Webasyst 4.2.0 source is authoritative over newer documentation when behavior conflicts.
- No ordinary persistent-login result uses `None`, `Optional`, bool sentinels, empty strings, or exception-as-branch semantics.
- Serialized discriminator values derive from `EnumStr`; Pydantic discriminators use `Literal[EnumMember]`.
- `PersistentCredential` and `PersistentCredentialLifetime` are immutable `@dataclass(slots=True, frozen=True)` VOs.
- Persistent credential acceptance uses an ordered strategy chain; issuance is a separate injected port.
- Application code must not import `hashlib`, SQLAlchemy, FastAPI/Starlette, cookie types, or Webasyst compatibility implementations.
- Legacy `auth_token` mechanics stay in `compatibility/webasyst/auth` and use constant-time comparison.
- No new persistent-token database table or schema migration is introduced.
- `remember` UI preference is not authentication state and is not represented in persistent-login application contracts.
- Global remember-me disablement is represented by not invoking restore; it is not a `CLEAR` result.
- Ordinary password login with remember=false does not revoke an existing persistent credential.
- Production login/cookie HTTP routes are out of scope for this slice.

---

### Task 1: Persistent value objects and explicit result contracts

**Files:**
- Create: `src/gomazon_webasyst/application/persistent_values.py`
- Create: `src/gomazon_webasyst/contracts/persistent_login.py`
- Modify: `src/gomazon_webasyst/contracts/enums.py`
- Test: `tests/unit/test_persistent_login_contracts.py`
- Modify: `tests/architecture/test_no_optional_result_contracts.py`

**Interfaces:**
- Produces `PersistentCredential(value: str)` and `PersistentCredentialLifetime(value: timedelta)` immutable VOs.
- Produces strategy, resolver, issue, restore, session-establishment, and transport-disposition result unions.
- Produces closed `EnumStr` domains for result discriminators and rejection reasons.
- Later tasks consume these contracts without introducing nullable control fields.

- [ ] **Step 1: Write failing contract tests** proving both VOs are frozen/hashable, all negative outcomes are explicit variants, raw discriminator strings validate, JSON serialization preserves string values, and no new result annotation contains `| None`.

```python
from datetime import timedelta


def test_persistent_values_are_frozen_hashable():
    credential = PersistentCredential("abc")
    lifetime = PersistentCredentialLifetime(timedelta(days=30))
    assert {credential}
    assert {lifetime}


def test_restore_result_is_discriminated_without_optional_fields():
    result = PersistentLoginRejected(
        reason=PersistentLoginRejectReason.CREDENTIAL_REJECTED,
        credential_disposition=ClearPersistentCredential(),
    )
    assert result.kind is PersistentLoginResultKind.REJECTED
```

- [ ] **Step 2: Run the contract tests and verify RED** because the persistent-login contract layer does not yet exist.

Run: `python -m pytest tests/unit/test_persistent_login_contracts.py tests/architecture/test_no_optional_result_contracts.py -v`

- [ ] **Step 3: Implement the minimal VOs, enums and Pydantic unions**. Use these concrete public names:

```text
PersistentStrategyResolved(identity, disposition)
PersistentStrategyNotApplicable
PersistentStrategyRejected(reason, disposition)
PersistentCredentialResolved(identity, disposition)
PersistentCredentialRejected(reason, disposition)
PersistentCredentialIssued(credential, lifetime)
PersistentCredentialIssueRejected(reason)
RefreshPersistentCredential(credential, lifetime)
ClearPersistentCredential
KeepPersistentCredential
BackendSessionEstablished(subject, session_key)
BackendSessionEstablishmentRejected(reason)
PersistentLoginRestored(subject, session_key, credential_disposition)
PersistentLoginRejected(reason, credential_disposition)
```

- [ ] **Step 4: Re-run contract + architecture tests GREEN**.
- [ ] **Step 5: Commit** `feat: add persistent login typed contracts`.

### Task 2: Persistent strategy resolver and issuer ports

**Files:**
- Create: `src/gomazon_webasyst/application/ports/persistent_credentials.py`
- Create: `src/gomazon_webasyst/infrastructure/auth/persistent_credentials.py`
- Test: `tests/unit/test_persistent_credential_resolver.py`

**Interfaces:**
- `PersistentCredentialStrategy.resolve(PersistentCredential) -> PersistentCredentialStrategyResult`.
- `PersistentCredentialResolver.resolve(PersistentCredential) -> PersistentCredentialResolution`.
- `PersistentCredentialIssuer.issue(AuthIdentity) -> PersistentCredentialIssueResult`.
- `OrderedPersistentCredentialResolver(strategies: tuple[PersistentCredentialStrategy, ...])` implements the resolver port.

- [ ] **Step 1: Write failing resolver tests** for ordered first-success, terminal rejection, skipping `NotApplicable`, explicit unsupported rejection after all strategies skip, and extension with a fake `opaque_v2` strategy without changing resolver/use-case code.
- [ ] **Step 2: Run RED**.

Run: `python -m pytest tests/unit/test_persistent_credential_resolver.py -v`

- [ ] **Step 3: Implement the ports and ordered resolver**. The resolver must branch only on typed strategy variants; it must not inspect credential format itself.
- [ ] **Step 4: Run GREEN + architecture guard**.
- [ ] **Step 5: Commit** `feat: add persistent credential strategy resolver`.

### Task 3: Source-backed legacy `auth_token` parser, strategy and issuer

**Files:**
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth/persistent.py`
- Modify: `src/gomazon_webasyst/compatibility/webasyst/auth/tokens.py` only if a reusable wrapper around the existing token factory is needed; do not duplicate the MD5 formula.
- Test: `tests/compatibility/test_persistent_auth_characterization.py`
- Test: `tests/unit/test_legacy_persistent_credential.py`

**Interfaces:**
- Compatibility-private `LegacyAuthTokenCredential(contact_id: int, credential: PersistentCredential)` VO.
- `LegacyAuthTokenParser.parse(PersistentCredential) -> LegacyTokenParseResult` with `LegacyTokenParsed | LegacyTokenMalformed`.
- `LegacyAuthTokenStrategy(subject_store, token_factory, lifetime)` implements `PersistentCredentialStrategy`.
- `LegacyAuthTokenIssuer(token_factory, lifetime)` implements `PersistentCredentialIssuer`.
- Legacy lifetime is `PersistentCredentialLifetime(timedelta(days=30))`.

- [ ] **Step 1: Write source-characterization tests** for the exact 4.2.0 formula/shape, 15-char prefix/suffix id extraction, 30-day issuance/refresh, same-value renewal, invalid/stale clear, logout/clearAuth credential clearing intent, and distinct `remember` UI-cookie semantics.
- [ ] **Step 2: Write failing unit tests** for malformed token parsing, missing/disabled subject rejection, stale token rejection, successful resolution, exact legacy issuance, and same credential returned in refresh disposition.
- [ ] **Step 3: Run RED**.

Run: `python -m pytest tests/compatibility/test_persistent_auth_characterization.py tests/unit/test_legacy_persistent_credential.py -v`

- [ ] **Step 4: Implement parser/strategy/issuer**. Parsing accepts only `^[0-9a-fA-F]{15}[0-9]+[0-9a-fA-F]{15}$`. The middle decimal digits become `contact_id`. Compare supplied and expected token with `hmac.compare_digest`. Do not log the credential value.
- [ ] **Step 5: Run GREEN + architecture tests** proving compatibility classes do not leak into application imports.
- [ ] **Step 6: Commit** `feat: add legacy auth token persistent strategy`.

### Task 4: Extract shared backend session establishment

**Files:**
- Create: `src/gomazon_webasyst/application/session_establishment.py`
- Modify: `src/gomazon_webasyst/application/auth.py`
- Test: `tests/unit/test_session_establishment.py`
- Modify: `tests/unit/test_auth_use_cases.py`

**Interfaces:**
- `BackendSessionEstablisher(session_state, session_registry, token_factory)`.
- Call signature: `await establish(identity: AuthIdentity, metadata: SessionMetadata) -> BackendSessionEstablishmentResult`.
- On success returns `BackendSessionEstablished(subject, session_key)`.
- On `SessionCreationError` returns `BackendSessionEstablishmentRejected(reason=SESSION_UNAVAILABLE)`.
- If registry registration raises an infrastructure exception, revoke freshly-created state and re-raise.
- `AuthenticateBackendPassword` consumes the establisher instead of directly coordinating state + registry + token creation.

- [ ] **Step 1: Write failing establisher tests** for success, session-create rejection, and compensation on registry exception.
- [ ] **Step 2: Run RED**.
- [ ] **Step 3: Implement `BackendSessionEstablisher`** using the exact existing `SessionStateStore`, `AuthSessionRegistry`, `CredentialVersionTokenFactory`, `SessionCreateRequest`, and `AuthSessionRegistration` contracts.
- [ ] **Step 4: Refactor `AuthenticateBackendPassword`** to call the establisher and map its typed result back to the existing `AuthenticationResult` without changing public password-auth behavior.
- [ ] **Step 5: Run session-establishment tests + all existing auth tests GREEN**.
- [ ] **Step 6: Commit** `refactor: share backend session establishment`.

### Task 5: Issue and restore persistent login use cases

**Files:**
- Create: `src/gomazon_webasyst/application/persistent_login.py`
- Test: `tests/unit/test_persistent_login_use_cases.py`

**Interfaces:**
- `IssuePersistentCredential(subject_store, issuer)` callable with `AuthenticatedSubject` and returning `PersistentCredentialIssueResult`.
- `RestoreBackendSessionFromPersistentCredential(resolver, establisher)` callable with `PersistentLoginRequest` and returning `PersistentLoginResult`.
- `PersistentLoginRequest` contains only `credential: PersistentCredential` and `session_metadata: SessionMetadata`.

- [ ] **Step 1: Write failing issuance tests** for missing subject, disabled subject, and successful issuance. No invocation represents “do not issue”; there is no remember bool.
- [ ] **Step 2: Write failing restore tests** for credential rejection -> clear, successful resolve + session establish -> refresh, and session establishment rejection -> keep.
- [ ] **Step 3: Run RED**.

Run: `python -m pytest tests/unit/test_persistent_login_use_cases.py -v`

- [ ] **Step 4: Implement issue/restore use cases**. Restore must not inspect legacy token shape or credential scheme; it delegates entirely to the resolver and establisher.
- [ ] **Step 5: Run GREEN + architecture guard**.
- [ ] **Step 6: Commit** `feat: add persistent login application use cases`.

### Task 6: Persistent credential revocation intent and logout separation

**Files:**
- Modify: `src/gomazon_webasyst/application/persistent_login.py`
- Test: `tests/unit/test_persistent_login_use_cases.py`
- Modify: `tests/unit/test_auth_use_cases.py`

**Interfaces:**
- Add `RevokePersistentCredential` as a transport-neutral operation returning `ClearPersistentCredential`.
- Existing `LogoutBackendSession` remains session-only and does not accept persistent credentials or cookie state.
- Presentation may later execute both logout + persistent revoke when implementing Webasyst `clearAuth()` parity.

- [ ] **Step 1: Write failing tests** proving session logout remains independent and explicit persistent revoke returns a clear directive.
- [ ] **Step 2: Run RED**.
- [ ] **Step 3: Implement the minimal revoke operation** without storage I/O because the legacy credential is stateless.
- [ ] **Step 4: Run GREEN**.
- [ ] **Step 5: Commit** `feat: separate persistent credential revocation intent`.

### Task 7: Composition wiring and exact initial compatibility configuration

**Files:**
- Modify: `src/gomazon_webasyst/composition/auth.py`
- Modify: `src/gomazon_webasyst/composition/container.py`
- Test: `tests/unit/test_auth_container.py`
- Test: `tests/unit/test_persistent_login_container.py`

**Interfaces:**
- Extend `AuthUseCases` with `issue_persistent_credential`, `restore_backend_session_from_persistent_credential`, and `revoke_persistent_credential`.
- Composition creates one shared `BackendSessionEstablisher` for password auth and persistent restore.
- Initial accepted resolver chain is exactly `(LegacyAuthTokenStrategy(...),)`.
- Initial issuer is exactly `LegacyAuthTokenIssuer(...)`.
- `SessionStateStore`, `AuthSessionRegistry`, `AuthSubjectStore`, and `CredentialVersionTokenFactory` instances are shared with existing auth use cases.

- [ ] **Step 1: Write failing composition tests** proving the new use cases are wired, password/restore share the same session infrastructure, and a custom resolver/issuer can be injected without modifying use cases.
- [ ] **Step 2: Run RED**.
- [ ] **Step 3: Extend composition with explicit persistent strategy/issuer dependencies**. Keep defaults in compatibility factory helpers; no global discovery.
- [ ] **Step 4: Run GREEN + existing container tests**.
- [ ] **Step 5: Commit** `feat: wire persistent login compatibility`.

### Task 8: SQLite end-to-end restore/invalidation flow

**Files:**
- Create: `tests/integration/test_persistent_login_flow.py`
- Modify: `tests/architecture/test_dependency_boundaries.py`
- Modify: `tests/architecture/test_no_optional_result_contracts.py`

**Interfaces:** Uses the real SQLite-backed `AuthSubjectStore` + `AuthSessionRegistry`, in-memory session state, legacy strategy/issuer and production application use cases.

- [ ] **Step 1: Write failing E2E test**: seed backend user -> issue legacy credential -> restore session -> verify new `AuthSessionKey` active -> mutate password/login -> restore old credential -> explicit rejected + clear directive.
- [ ] **Step 2: Add architecture assertions** that application persistent-login/session-establishment code imports no `hashlib`, SQLAlchemy, FastAPI/Starlette, cookie libraries or `compatibility.webasyst.auth.persistent`, and that no operation/lookup contract returns `Optional` sentinels.
- [ ] **Step 3: Run RED where appropriate**.
- [ ] **Step 4: Make only wiring/adapter corrections needed for the E2E path**; do not add a persistent-token table or HTTP route.
- [ ] **Step 5: Run integration + architecture GREEN**.
- [ ] **Step 6: Run full verification**:

```bash
python -m pytest -v
python -m compileall -q src tests
```

- [ ] **Step 7: Compare `main...feature/persistent-login`** and confirm no production cookie/login route, persistence migration, permissions, OAuth or opaque-v2 storage slipped into scope.
- [ ] **Step 8: Record exact local/CI counts in this plan and update `AGENTS.md` only if implementation reveals a new architectural decision beyond ADR-024/025**.
- [ ] **Step 9: Commit** `test: verify persistent login compatibility flow`.

## Verification

Before integration:

- full local `python -m pytest -v` has zero failures;
- `python -m compileall -q src tests` exits 0;
- GitHub Actions passes on Python 3.12 with `aiosqlite` and `asyncmy` installed;
- architecture guard rejects new `Optional`/`T | None` sentinel contracts;
- application persistent-login code imports no Webasyst legacy token class/codec;
- no password-auth request gains a `remember` field;
- no persistent token DB schema/table is introduced;
- legacy token comparison is constant-time;
- successful restore creates a fresh normal session and refreshes the same legacy credential for 30 days;
- invalid/stale legacy credential produces a clear directive;
- session-establishment rejection keeps a valid persistent credential;
- remember-me disabled is modeled by not calling restore, not by returning clear;
- ordinary password login without persistent issuance does not revoke an existing persistent credential.
