# Backend Session HTTP Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a transport-neutral backend-session bridge that resolves the current browser subject, orchestrates password login/logout and persistent-login fallback, and maps explicit credential dispositions to HTTP cookies without introducing a new authentication system or public login route.

**Architecture:** Existing auth/session/persistent-login use cases remain authoritative. New application code is split into VO and Composite responsibilities; no fake Entity is introduced because `AuthenticatedSubject`, `AuthSessionKey` and `StoredAuthSession` already carry identity. Webasyst cookie compatibility and HTTP cookie mutation planning stay outside application, and presentation only normalizes requests/applies typed cookie mutations.

**Tech Stack:** Python 3.12+, Pydantic v2 contracts, FastAPI/Starlette presentation helpers, existing SQLAlchemy/auth composition, pytest/httpx/aiosqlite for tests.

**Spec:** `docs/superpowers/specs/2026-09-19-backend-session-http-bridge-design.md`

## Global Constraints

- Reuse `AuthenticateBackendPassword`, `ResolveBackendSession`, `LogoutBackendSession`, `IssuePersistentCredential`, `RestoreBackendSessionFromPersistentCredential`, and `RevokePersistentCredential`; do not create parallel auth logic.
- All new backend-session bridge application code must be classifiable as VO, Service, or Composite. Do not invent a duplicate Entity.
- Cross-boundary serialized result/status domains use `EnumStr` and discriminated Pydantic unions.
- Expected negative states use explicit variants, never `None`, empty string, `False`, exceptions, or nullable bags.
- `RememberIntent` is a closed typed value and MUST NOT be added to `BackendPasswordCredentials`.
- A valid Python session always wins; persistent restore is fallback only.
- When persistent login is disabled, restore/issue is not invoked and existing `auth_token` transport is untouched.
- Session-only password login does not clear or rotate an existing persistent credential.
- Application code returns credential dispositions; it never reads/writes cookies.
- Default Python session cookie is `gomazon_session`; default persistent cookie is `auth_token`.
- The Python session cookie is not `PHPSESSID`; PHP session-file decoding is out of scope.
- Session cookie is host-only, path `/`, HttpOnly, SameSite=Lax, Secure from explicit setting, and has no Max-Age/Expires.
- Persistent refresh uses `PersistentCredentialLifetime`; clear uses the same name/path/security policy.
- No standalone production login/logout/current-user route is mounted in `main.py`.
- No OAuth consent/redirect/CSRF logic is implemented in this slice.

## Review Focus

1. A malformed/empty Python session cookie must be cleared but must not prevent a valid persistent credential from restoring a session.
2. `auth_token="0"` and an empty `auth_token` must behave like no usable persistent credential, matching PHP `empty()`, and must not be parsed by persistent strategies.
3. When a supplied stale session and a valid persistent credential coexist, the restore result must issue the new session credential and preserve the persistent refresh/keep/clear disposition exactly.
4. A successful password login with `RememberIntent.PERSIST` whose persistent issuance fails must still succeed and must not clear an existing persistent cookie.
5. Cookie policy must stay host-only: no `Domain` attribute may appear, session cookie must not gain Max-Age/Expires, and Secure/SameSite/HttpOnly must match explicit policy.

---

### Task 1: Typed bridge VO, Composite requests and cross-boundary result contracts

**Files:**
- Create: `src/gomazon_webasyst/application/backend_session_bridge/__init__.py`
- Create: `src/gomazon_webasyst/application/backend_session_bridge/vo/__init__.py`
- Create: `src/gomazon_webasyst/application/backend_session_bridge/vo/credentials.py`
- Create: `src/gomazon_webasyst/application/backend_session_bridge/composites/__init__.py`
- Create: `src/gomazon_webasyst/application/backend_session_bridge/composites/requests.py`
- Create: `src/gomazon_webasyst/application/backend_session_bridge/services/__init__.py`
- Create: `src/gomazon_webasyst/contracts/backend_session_bridge.py`
- Modify: `src/gomazon_webasyst/contracts/enums.py`
- Create: `tests/unit/test_backend_session_bridge_contracts.py`
- Create: `tests/architecture/test_backend_session_bridge_taxonomy.py`
- Modify: `tests/architecture/test_no_optional_result_contracts.py`

**Interfaces:**
- Produces VO `SessionCredentialMissing`, `SessionCredentialMalformed`, `SessionCredentialProvided(session_id: SessionId)`.
- Produces VO `PersistentCredentialMissing`, `PersistentCredentialProvided(credential: PersistentCredential)`.
- Produces closed `EnumStr` values:
  - `RememberIntent.SESSION_ONLY | PERSIST`;
  - `PersistentLoginMode.ENABLED | DISABLED`;
  - `SessionCredentialDispositionKind.ISSUE | CLEAR | KEEP`;
  - `CurrentBackendSubjectKind.RESOLVED | UNAUTHENTICATED`;
  - `CurrentBackendSubjectReason.NO_CREDENTIAL | SESSION_REJECTED | PERSISTENT_REJECTED | SESSION_UNAVAILABLE`;
  - `BackendPasswordLoginKind.SUCCEEDED | REJECTED`;
  - `BackendLoginPersistenceStatus.SESSION_ONLY | ISSUED | UNAVAILABLE | DISABLED`;
  - `BackendLogoutKind.COMPLETED`.
- Produces Composite request dataclasses:
  - `BackendCurrentSubjectRequest(session_credential, persistent_credential, session_metadata, persistent_login_mode)`;
  - `BackendPasswordLoginRequest(credentials, remember_intent, persistent_login_mode)`;
  - `BackendLogoutRequest(session_credential)`.
- Produces Pydantic transport-neutral dispositions:
  - `IssueSessionCredential(session_id: SessionId)`;
  - `ClearSessionCredential`;
  - `KeepSessionCredential`;
  - union `SessionCredentialDisposition`.
- Reuses existing `PersistentCredentialDisposition` unchanged.
- Produces Pydantic results:
  - `CurrentBackendSubjectResolved(subject, session_disposition, persistent_disposition)`;
  - `CurrentBackendSubjectUnauthenticated(reason, session_disposition, persistent_disposition)`;
  - `BackendPasswordLoginSucceeded(subject, session_disposition, persistent_disposition, persistence_status)`;
  - `BackendPasswordLoginRejected(authentication_type, session_disposition, persistent_disposition)`;
  - `BackendLogoutCompleted(session_status, session_disposition, persistent_disposition)`.

- [x] **Step 1: Write failing VO/request tests**

```python
from dataclasses import FrozenInstanceError

import pytest

from gomazon_webasyst.application.auth_values import SessionId
from gomazon_webasyst.application.backend_session_bridge.vo.credentials import (
    SessionCredentialMalformed,
    SessionCredentialMissing,
    SessionCredentialProvided,
)
from gomazon_webasyst.contracts.enums import RememberIntent, PersistentLoginMode


def test_bridge_credential_states_are_explicit_frozen_values() -> None:
    provided = SessionCredentialProvided(SessionId("sess-1"))
    assert provided.session_id == SessionId("sess-1")
    assert SessionCredentialMissing() != SessionCredentialMalformed()
    with pytest.raises(FrozenInstanceError):
        provided.session_id = SessionId("other")  # type: ignore[misc]


def test_remember_and_persistent_mode_are_closed_enumstr_domains() -> None:
    assert RememberIntent.PERSIST.value == "persist"
    assert PersistentLoginMode.DISABLED.value == "disabled"
```

- [x] **Step 2: Write failing disposition/result serialization tests**

```python
from pydantic import TypeAdapter

from gomazon_webasyst.application.auth_values import SessionId
from gomazon_webasyst.contracts.backend_session_bridge import (
    IssueSessionCredential,
    SessionCredentialDisposition,
)


def test_session_disposition_accepts_raw_discriminator_and_serializes_string() -> None:
    adapter = TypeAdapter(SessionCredentialDisposition)
    value = adapter.validate_python({
        "kind": "issue",
        "session_id": SessionId("sess-1"),
    })
    assert isinstance(value, IssueSessionCredential)
    assert adapter.dump_python(value)["kind"] == "issue"
```

Also assert every result/disposition Pydantic model is frozen and no result field annotation contains `NoneType`.

- [x] **Step 3: Write failing taxonomy guard**

The architecture test must assert:
- every non-`__init__.py` file under `application/backend_session_bridge` is under `vo/`, `services/` or `composites/`;
- no `entities/` directory exists in this slice;
- no FastAPI, Starlette, SQLAlchemy or compatibility import appears below `application/backend_session_bridge`.

- [x] **Step 4: Run RED**

Run:

```bash
python -m pytest   tests/unit/test_backend_session_bridge_contracts.py   tests/architecture/test_backend_session_bridge_taxonomy.py   tests/architecture/test_no_optional_result_contracts.py -v
```

Expected: FAIL because bridge packages/contracts/enums do not exist.

- [x] **Step 5: Implement minimal VO, requests and Pydantic contracts**

Use frozen/slotted dataclasses for internal VO/Composite requests and Pydantic frozen models with `arbitrary_types_allowed=True` where `SessionId`/`PersistentCredential` are carried.

Do not add a bridge Entity.

- [x] **Step 6: Run GREEN**

Run the same command from Step 4.

Expected: PASS.

- [x] **Step 7: Commit**

```bash
git add src/gomazon_webasyst/application/backend_session_bridge   src/gomazon_webasyst/contracts/backend_session_bridge.py   src/gomazon_webasyst/contracts/enums.py   tests/unit/test_backend_session_bridge_contracts.py   tests/architecture/test_backend_session_bridge_taxonomy.py   tests/architecture/test_no_optional_result_contracts.py
git commit -m "feat: add backend session bridge contracts"
```

### Task 2: Current-subject Composite with session-first persistent fallback

**Files:**
- Create: `src/gomazon_webasyst/application/backend_session_bridge/composites/current_subject.py`
- Create: `tests/unit/test_backend_current_subject_flow.py`

**Interfaces:**
- Produces `BackendCurrentSubjectFlow(resolve_backend_session, restore_backend_session_from_persistent_credential)`.
- Consumes `BackendCurrentSubjectRequest`.
- Returns `CurrentBackendSubjectResult`.
- Calls persistent restore only when no subject was resolved from the Python session and `PersistentLoginMode.ENABLED`.
- A rejected supplied session maps to `ClearSessionCredential`; missing session maps to `KeepSessionCredential`; malformed session maps to `ClearSessionCredential`.
- When persistent restore succeeds, return `IssueSessionCredential(restored.session_key.session_id)` and preserve `restored.credential_disposition` exactly.
- When persistent restore rejects, preserve its persistent disposition exactly.
- Infrastructure exceptions propagate.

- [x] **Step 1: Write failing valid-session precedence test**

```python
@pytest.mark.asyncio
async def test_valid_session_wins_and_persistent_restore_is_not_called() -> None:
    resolver = SessionResolver(
        SessionResolved(subject=SUBJECT, session_key=KEY)
    )
    persistent = FailIfCalledPersistentRestore()
    flow = BackendCurrentSubjectFlow(
        resolve_backend_session=resolver,
        restore_backend_session_from_persistent_credential=persistent,
    )

    result = await flow(
        BackendCurrentSubjectRequest(
            session_credential=SessionCredentialProvided(KEY.session_id),
            persistent_credential=PersistentCredentialProvided(CREDENTIAL),
            session_metadata=SessionMetadata(user_agent="pytest"),
            persistent_login_mode=PersistentLoginMode.ENABLED,
        )
    )

    assert isinstance(result, CurrentBackendSubjectResolved)
    assert result.subject == SUBJECT
    assert isinstance(result.session_disposition, KeepSessionCredential)
    assert isinstance(result.persistent_disposition, KeepPersistentCredential)
    assert resolver.calls == [KEY.session_id]
```

- [x] **Step 2: Write failing stale-session + persistent-restore test for Review Focus #3**

```python
@pytest.mark.asyncio
async def test_rejected_session_falls_back_to_persistent_and_issues_new_session() -> None:
    new_key = AuthSessionKey(42, SessionId("sess-new"))
    flow = BackendCurrentSubjectFlow(
        resolve_backend_session=SessionResolver(
            SessionResolutionError(type=SessionResolutionErrorType.EXPIRED)
        ),
        restore_backend_session_from_persistent_credential=PersistentRestore(
            PersistentLoginRestored(
                subject=SUBJECT,
                session_key=new_key,
                credential_disposition=REFRESH,
            )
        ),
    )

    result = await flow(current_request(
        SessionCredentialProvided(SessionId("sess-old")),
        PersistentCredentialProvided(CREDENTIAL),
    ))

    assert isinstance(result, CurrentBackendSubjectResolved)
    assert result.session_disposition == IssueSessionCredential(new_key.session_id)
    assert result.persistent_disposition == REFRESH
```

- [x] **Step 3: Write failing malformed/missing/disabled/rejection tests**

Pin all of:
- missing session + missing persistent -> unauthenticated, keep/keep, reason NO_CREDENTIAL;
- malformed session + valid persistent -> restore succeeds and new session is issued (Review Focus #1);
- persistent-login disabled -> persistent restore spy remains uncalled and persistent disposition is KEEP;
- invalid persistent restore with `ClearPersistentCredential` -> result preserves CLEAR;
- valid credential but session-establishment failure with `KeepPersistentCredential` -> result reason SESSION_UNAVAILABLE and preserves KEEP;
- resolver/restore `RuntimeError("backend down")` propagates.

- [x] **Step 4: Run RED**

Run: `python -m pytest tests/unit/test_backend_current_subject_flow.py -v`

Expected: FAIL because `BackendCurrentSubjectFlow` does not exist.

- [x] **Step 5: Implement orchestration only**

No cookie names, HTTP objects, SQL, token parsing or compatibility imports in this file.

- [x] **Step 6: Run GREEN + taxonomy guard**

Run:

```bash
python -m pytest   tests/unit/test_backend_current_subject_flow.py   tests/architecture/test_backend_session_bridge_taxonomy.py -v
```

Expected: PASS.

- [x] **Step 7: Commit**

```bash
git add src/gomazon_webasyst/application/backend_session_bridge/composites/current_subject.py   tests/unit/test_backend_current_subject_flow.py
git commit -m "feat: add backend current subject flow"
```

### Task 3: Password-login Composite with explicit remember intent

**Files:**
- Create: `src/gomazon_webasyst/application/backend_session_bridge/composites/login.py`
- Create: `tests/unit/test_backend_password_login_flow.py`

**Interfaces:**
- Produces `BackendPasswordLoginFlow(authenticate_backend_password, issue_persistent_credential)`.
- Consumes `BackendPasswordLoginRequest`.
- Primary auth rejection returns `BackendPasswordLoginRejected`, `KeepSessionCredential`, `KeepPersistentCredential`, and never invokes persistent issuance.
- Primary success always returns `IssueSessionCredential(authentication.session_key.session_id)`.
- `RememberIntent.SESSION_ONLY` -> no issuance; `KeepPersistentCredential`; status SESSION_ONLY.
- `RememberIntent.PERSIST` + disabled mode -> no issuance; `KeepPersistentCredential`; status DISABLED.
- `RememberIntent.PERSIST` + enabled + issued credential -> `RefreshPersistentCredential`; status ISSUED.
- Persistent issuance rejection -> login remains successful; `KeepPersistentCredential`; status UNAVAILABLE.

- [x] **Step 1: Write failing auth-rejection/session-only tests**

```python
@pytest.mark.asyncio
async def test_session_only_success_never_calls_persistent_issuer() -> None:
    flow = BackendPasswordLoginFlow(
        authenticate_backend_password=Authenticator(
            AuthenticationSucceeded(subject=SUBJECT, session_key=KEY)
        ),
        issue_persistent_credential=FailIfCalledIssuer(),
    )

    result = await flow(
        BackendPasswordLoginRequest(
            credentials=CREDENTIALS,
            remember_intent=RememberIntent.SESSION_ONLY,
            persistent_login_mode=PersistentLoginMode.ENABLED,
        )
    )

    assert isinstance(result, BackendPasswordLoginSucceeded)
    assert result.session_disposition == IssueSessionCredential(KEY.session_id)
    assert isinstance(result.persistent_disposition, KeepPersistentCredential)
    assert result.persistence_status is BackendLoginPersistenceStatus.SESSION_ONLY
```

Also assert primary rejection never calls issuer.

- [x] **Step 2: Write failing persistent issuance tests including Review Focus #4**

```python
@pytest.mark.asyncio
async def test_persistent_issue_failure_does_not_turn_login_into_failure() -> None:
    flow = BackendPasswordLoginFlow(
        authenticate_backend_password=Authenticator(
            AuthenticationSucceeded(subject=SUBJECT, session_key=KEY)
        ),
        issue_persistent_credential=Issuer(
            PersistentCredentialIssueRejected(
                reason=PersistentCredentialIssueRejectReason.SUBJECT_DISABLED
            )
        ),
    )

    result = await flow(persistent_login_request())

    assert isinstance(result, BackendPasswordLoginSucceeded)
    assert isinstance(result.persistent_disposition, KeepPersistentCredential)
    assert result.persistence_status is BackendLoginPersistenceStatus.UNAVAILABLE
```

Pin successful issue -> exact `RefreshPersistentCredential`; disabled mode -> issuer not called.

- [x] **Step 3: Assert the primary credential contract still has no remember field**

```python
def test_backend_password_credentials_still_has_no_remember_field() -> None:
    assert "remember" not in BackendPasswordCredentials.model_fields
```

- [x] **Step 4: Run RED**

Run: `python -m pytest tests/unit/test_backend_password_login_flow.py -v`

Expected: FAIL because login Composite does not exist.

- [x] **Step 5: Implement minimal login Composite**

Do not mutate persistent credential transport on SESSION_ONLY, disabled mode, auth rejection, or issuance rejection.

- [x] **Step 6: Run GREEN**

Run:

```bash
python -m pytest   tests/unit/test_backend_password_login_flow.py   tests/unit/test_auth_use_cases.py   tests/unit/test_persistent_login_use_cases.py -v
```

Expected: PASS.

- [x] **Step 7: Commit**

```bash
git add src/gomazon_webasyst/application/backend_session_bridge/composites/login.py   tests/unit/test_backend_password_login_flow.py
git commit -m "feat: add backend password login flow"
```

### Task 4: Idempotent logout Composite

**Files:**
- Create: `src/gomazon_webasyst/application/backend_session_bridge/composites/logout.py`
- Create: `tests/unit/test_backend_logout_flow.py`

**Interfaces:**
- Produces `BackendLogoutFlow(logout_backend_session, revoke_persistent_credential)`.
- Consumes `BackendLogoutRequest`.
- Provided session credential invokes `LogoutBackendSession(session_id)`.
- Missing or malformed session credential does not invoke session logout and uses `LogoutStatus.ALREADY_MISSING`.
- Always invokes `RevokePersistentCredential`.
- Always returns `ClearSessionCredential` and the returned `ClearPersistentCredential`.

- [x] **Step 1: Write failing provided-session test**

```python
@pytest.mark.asyncio
async def test_logout_revokes_runtime_session_and_clears_both_transports() -> None:
    logout = SessionLogout(LogoutResult(status=LogoutStatus.REVOKED))
    persistent = PersistentRevoke()
    flow = BackendLogoutFlow(
        logout_backend_session=logout,
        revoke_persistent_credential=persistent,
    )

    result = await flow(
        BackendLogoutRequest(
            session_credential=SessionCredentialProvided(SessionId("sess-1"))
        )
    )

    assert result.session_status is LogoutStatus.REVOKED
    assert isinstance(result.session_disposition, ClearSessionCredential)
    assert isinstance(result.persistent_disposition, ClearPersistentCredential)
    assert logout.calls == [SessionId("sess-1")]
    assert persistent.calls == 1
```

- [x] **Step 2: Write failing missing/malformed idempotency tests**

Assert both missing and malformed session credentials:
- do not invoke session logout;
- return ALREADY_MISSING;
- still invoke persistent revoke once;
- still clear both transports.

- [x] **Step 3: Run RED**

Run: `python -m pytest tests/unit/test_backend_logout_flow.py -v`

Expected: FAIL because logout Composite does not exist.

- [x] **Step 4: Implement minimal logout Composite**

Infrastructure exceptions from actual logout/revoke calls propagate.

- [x] **Step 5: Run GREEN**

Run: `python -m pytest tests/unit/test_backend_logout_flow.py -v`

Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add src/gomazon_webasyst/application/backend_session_bridge/composites/logout.py   tests/unit/test_backend_logout_flow.py
git commit -m "feat: add backend logout flow"
```

### Task 5: Webasyst HTTP credential extraction and typed cookie mutation planning

**Files:**
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth_http/__init__.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth_http/vo/__init__.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth_http/vo/cookies.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth_http/composites/__init__.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth_http/composites/request.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth_http/composites/cookies.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth_http/services/__init__.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth_http/services/credentials.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/auth_http/services/cookie_mutations.py`
- Create: `tests/compatibility/test_backend_session_http_characterization.py`
- Create: `tests/unit/test_backend_auth_cookie_services.py`

**Interfaces:**
- Produces open immutable `CookieName(value: str)`, validated with HTTP token syntax and non-empty trimmed value.
- Produces closed `CookieSameSite(EnumStr)`: LAX/STRICT/NONE.
- Produces frozen `BackendAuthCookiePolicy(session_name, persistent_name, secure, path, same_site)`; no domain field exists in this slice, guaranteeing host-only cookies.
- Produces `BackendAuthHttpCredentialState(session_credential, persistent_credential, session_metadata)`.
- `BackendAuthCredentialExtractionService.extract(cookies: Mapping[str, str], user_agent: str, policy)`:
  - missing session cookie -> `SessionCredentialMissing`;
  - empty session cookie -> `SessionCredentialMalformed`;
  - non-empty session cookie -> `SessionCredentialProvided(SessionId(value))`;
  - missing/empty/`"0"` persistent cookie -> `PersistentCredentialMissing`;
  - otherwise -> `PersistentCredentialProvided(PersistentCredential(value))`;
  - metadata uses exact supplied User-Agent or empty string.
- Produces typed transport mutation variants:
  - `SetSessionCookie(value: str)`, `DeleteSessionCookie`, `KeepSessionCookie`;
  - `SetPersistentCookie(value: str, max_age_seconds: int, expires_at: datetime)`, `DeletePersistentCookie`, `KeepPersistentCookie`;
  - `BackendAuthCookieMutations(session, persistent)`.
- `BackendAuthCookieMutationService(clock: Callable[[], datetime]).plan(session_disposition, persistent_disposition)` maps application dispositions one-to-one. `PersistentCredentialLifetime` is converted to positive integer seconds and `expires_at = clock() + lifetime`.

- [x] **Step 1: Write failing extraction characterization tests including Review Focus #2**

```python
@pytest.mark.parametrize("raw", ["", "0"])
def test_php_falsy_auth_token_is_not_sent_to_persistent_strategy(raw: str) -> None:
    state = extractor().extract(
        cookies={"auth_token": raw},
        user_agent="pytest",
        policy=POLICY,
    )
    assert isinstance(state.persistent_credential, PersistentCredentialMissing)


def test_empty_session_cookie_is_malformed_not_missing() -> None:
    state = extractor().extract(
        cookies={"gomazon_session": ""},
        user_agent="pytest",
        policy=POLICY,
    )
    assert isinstance(state.session_credential, SessionCredentialMalformed)
```

Also pin custom cookie names, `"0"` session id remaining a valid opaque session value, and exact User-Agent propagation.

- [x] **Step 2: Write failing mutation-planning tests**

Pin:
- IssueSessionCredential -> SetSessionCookie exact SessionId value;
- Clear -> Delete;
- Keep -> Keep;
- RefreshPersistentCredential -> SetPersistentCookie exact credential, `30 days == 2592000` seconds, and exact `expires_at == NOW + timedelta(days=30)`;
- ClearPersistent -> Delete;
- KeepPersistent -> Keep.

- [x] **Step 3: Write failing policy tests for Review Focus #5**

Assert policy has no domain attribute, validates non-empty/token-safe cookie names, defaults path `/`, SameSite.LAX and explicit secure flag.

- [x] **Step 4: Run RED**

Run:

```bash
python -m pytest   tests/compatibility/test_backend_session_http_characterization.py   tests/unit/test_backend_auth_cookie_services.py -v
```

Expected: FAIL because HTTP compatibility package does not exist.

- [x] **Step 5: Implement pure compatibility Services/VO/Composites**

Do not import FastAPI/Starlette here. These services operate on plain mappings and typed dispositions.

- [x] **Step 6: Run GREEN**

Run the Step 4 command.

Expected: PASS.

- [x] **Step 7: Commit**

```bash
git add src/gomazon_webasyst/compatibility/webasyst/auth_http   tests/compatibility/test_backend_session_http_characterization.py   tests/unit/test_backend_auth_cookie_services.py
git commit -m "feat: add backend auth cookie compatibility"
```

### Task 6: Composition and presentation helpers without public auth routes

**Files:**
- Create: `src/gomazon_webasyst/composition/backend_session_bridge.py`
- Create: `src/gomazon_webasyst/presentation/http/backend_session.py`
- Modify: `src/gomazon_webasyst/composition/settings.py`
- Modify: `src/gomazon_webasyst/composition/container.py`
- Create: `tests/unit/test_backend_session_bridge_container.py`
- Create: `tests/unit/test_backend_session_http_helpers.py`
- Modify: `tests/unit/test_auth_container.py`

**Interfaces:**
- Produces `BackendSessionBridgeComponents` with:
  - `current_subject_flow`;
  - `password_login_flow`;
  - `logout_flow`;
  - `credential_extractor`;
  - `cookie_mutation_service`;
  - `cookie_policy`;
  - `persistent_login_mode`.
- `create_backend_session_bridge_components(auth: AuthUseCases, settings: Settings, *, clock: Callable[[], datetime] = datetime.now)` wires existing use cases and injects the same explicit clock into cookie mutation planning.
- Settings add:
  - `backend_session_cookie_name: str = "gomazon_session"`;
  - `persistent_auth_cookie_name: str = "auth_token"`;
  - `backend_auth_cookie_secure: bool = False`;
  - `persistent_login_enabled: bool = True`.
- Composition validates cookie-name strings by constructing `CookieName` at startup.
- Container gains `backend_session_bridge: BackendSessionBridgeComponents`.
- Presentation helpers:
  - `normalize_backend_auth_request(request: Request, components) -> BackendAuthHttpCredentialState`;
  - `apply_backend_auth_cookie_mutations(response: Response, mutations, policy) -> None`.
- Presentation helper is not an APIRouter and is not included in `main.py`.

Cookie application:
- SetSessionCookie -> `response.set_cookie(name, value, path="/", httponly=True, secure=policy.secure, samesite="lax")` with no max_age/expires/domain.
- DeleteSessionCookie -> `response.delete_cookie(name, path="/", secure=policy.secure, httponly=True, samesite="lax")`.
- SetPersistentCookie -> set cookie with `max_age` and `expires` from the mutation, HttpOnly/Secure/SameSite/path, no domain.
- DeletePersistentCookie -> delete same cookie/path/security.
- Keep variants -> no header mutation.

- [x] **Step 1: Write failing composition tests**

```python
def test_bridge_composition_reuses_existing_auth_use_cases() -> None:
    auth = fake_auth_use_cases()
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    bridge = create_backend_session_bridge_components(auth, settings)

    assert bridge.current_subject_flow._resolve_backend_session is auth.resolve_backend_session
    assert (
        bridge.current_subject_flow._restore_backend_session_from_persistent_credential
        is auth.restore_backend_session_from_persistent_credential
    )
    assert bridge.password_login_flow._authenticate_backend_password is auth.authenticate_backend_password
    assert bridge.logout_flow._logout_backend_session is auth.logout_backend_session
```

Also assert disabled setting produces `PersistentLoginMode.DISABLED`, and invalid empty cookie name raises at composition creation.

- [x] **Step 2: Write failing HTTP normalization tests**

Use a Starlette/FastAPI `Request` fixture with cookies/User-Agent and assert exact `BackendAuthHttpCredentialState` variants. Do not exercise auth use cases here.

- [x] **Step 3: Write failing cookie application tests for Review Focus #5**

```python
def test_session_cookie_is_host_only_session_cookie_with_security_policy() -> None:
    response = Response()
    apply_backend_auth_cookie_mutations(
        response,
        BackendAuthCookieMutations(
            session=SetSessionCookie("sess-1"),
            persistent=KeepPersistentCookie(),
        ),
        POLICY,
    )
    header = response.headers["set-cookie"]
    assert "gomazon_session=sess-1" in header
    assert "HttpOnly" in header
    assert "SameSite=lax" in header
    assert "Secure" in header
    assert "Domain=" not in header
    assert "Max-Age=" not in header
    assert "Expires=" not in header
```

Also pin persistent set Max-Age + Expires, clear operations, and Keep producing no Set-Cookie.

- [x] **Step 4: Assert no production auth router is mounted**

```python
def test_main_does_not_mount_backend_session_router() -> None:
    source = Path("src/gomazon_webasyst/main.py").read_text()
    assert "backend_session_router" not in source
    assert "create_backend_session_router" not in source
```

- [x] **Step 5: Run RED**

Run:

```bash
python -m pytest   tests/unit/test_backend_session_bridge_container.py   tests/unit/test_backend_session_http_helpers.py   tests/unit/test_auth_container.py -v
```

Expected: FAIL because bridge composition/presentation helper does not exist.

- [x] **Step 6: Implement composition/settings/container/presentation helpers**

Do not modify `main.py`.

- [x] **Step 7: Run GREEN**

Run the Step 5 command.

Expected: PASS.

- [x] **Step 8: Commit**

```bash
git add src/gomazon_webasyst/composition/backend_session_bridge.py   src/gomazon_webasyst/presentation/http/backend_session.py   src/gomazon_webasyst/composition/settings.py   src/gomazon_webasyst/composition/container.py   tests/unit/test_backend_session_bridge_container.py   tests/unit/test_backend_session_http_helpers.py   tests/unit/test_auth_container.py
git commit -m "feat: wire backend session http bridge"
```

### Task 7: Real SQLite + test-only ASGI vertical flow

**Files:**
- Create: `tests/integration/test_backend_session_http_bridge_flow.py`

**Interfaces:**
- Test uses real `Container`, SQLite legacy auth rows, in-memory session provider, real legacy password verifier/token factory/persistent strategy, real bridge composition and presentation helpers.
- Test-only FastAPI routes exist only inside this test module:
  - `POST /fixture/login`;
  - `GET /fixture/current`;
  - `POST /fixture/logout`.
- These fixture routes are not imported by production code.

- [x] **Step 1: Seed a real backend user**

Use the existing characterization pattern:

```python
session.add(
    WaContactRow(
        id=42,
        name="Admin",
        login="admin",
        password=md5(b"secret").hexdigest(),
        is_user=1,
        create_datetime=datetime(2026, 1, 1, 12, 0, 0),
    )
)
```

- [x] **Step 2: Build test-only login/current/logout endpoints**

Login endpoint:
- constructs `BackendPasswordCredentials` from fixture constants;
- calls `container.backend_session_bridge.password_login_flow`;
- plans/applies cookie mutations;
- returns JSON subject id.

Current endpoint:
- normalizes cookies/User-Agent;
- calls `current_subject_flow`;
- plans/applies returned dispositions;
- returns 200 with subject id or 401 unauthenticated.

Logout endpoint:
- normalizes cookies;
- calls `logout_flow`;
- plans/applies clear mutations;
- returns 204.

- [x] **Step 3: Write the full persistent-login browser flow**

Verify in one coherent scenario:

1. POST login with `RememberIntent.PERSIST` returns 200.
2. Response contains `gomazon_session` and `auth_token`.
3. Session cookie is HttpOnly/SameSite=Lax, has no Domain, Max-Age or Expires.
4. Persistent cookie has HttpOnly/SameSite=Lax and matching 30-day Max-Age + Expires.
5. GET current using client cookie jar returns subject 42.
6. Replace `gomazon_session` with a stale opaque value while retaining `auth_token`.
7. GET current restores from persistent credential, returns subject 42 and replaces `gomazon_session`.
8. POST logout clears both cookies.
9. Subsequent GET current returns 401.

- [x] **Step 4: Add session-only preservation scenario**

Login persistently once, then login again with `RememberIntent.SESSION_ONLY` and assert the existing `auth_token` value is unchanged.

This pins ADR-025 at the HTTP boundary.

- [x] **Step 5: Add persistent-disabled scenario**

Build a second container/bridge with `persistent_login_enabled=False`; present a stale session cookie plus a valid legacy `auth_token`; assert current-subject resolution returns unauthenticated, clears only the stale session credential, and emits no persistent cookie mutation.

- [x] **Step 6: Run RED/GREEN**

Run: `python -m pytest tests/integration/test_backend_session_http_bridge_flow.py -v`

Expected after implementation: PASS.

- [x] **Step 7: Commit**

```bash
git add tests/integration/test_backend_session_http_bridge_flow.py
git commit -m "test: verify backend session http bridge flow"
```

### Task 8: Architecture guards, scope verification and completion record

**Files:**
- Create: `tests/architecture/test_backend_session_bridge_boundaries.py`
- Modify: `tests/architecture/test_dependency_boundaries.py`
- Modify: `tests/architecture/test_no_optional_result_contracts.py`
- Modify: `docs/superpowers/plans/2026-09-19-backend-session-http-bridge.md`
- Modify: `AGENTS.md` only if implementation reveals a new architectural decision beyond ADR-038/039/040.

**Interfaces:**
- No new runtime interface; this task pins the architecture and records verification evidence.

- [x] **Step 1: Add application dependency guards**

Reject the following below `application/backend_session_bridge`:
- `fastapi`;
- `starlette`;
- `sqlalchemy`;
- `gomazon_webasyst.compatibility`;
- cookie names `gomazon_session` / `auth_token`;
- `PHPSESSID`;
- `set_cookie` / `delete_cookie`.

- [x] **Step 2: Add auth-contract regression guards**

```python
def test_password_credentials_do_not_gain_remember_transport_state() -> None:
    source = Path("src/gomazon_webasyst/contracts/auth.py").read_text()
    assert "remember:" not in source
    assert "remember :" not in source


def test_bridge_does_not_claim_php_session_interoperability() -> None:
    bridge_sources = "\n".join(
        path.read_text()
        for path in Path("src/gomazon_webasyst").rglob("*.py")
        if "backend_session_bridge" in str(path)
    )
    assert "PHPSESSID" not in bridge_sources
```

- [x] **Step 3: Add presentation scope guard**

Assert `main.py` still mounts contacts + legacy API execution only and contains no backend-session/login/logout router registration.

- [x] **Step 4: Run focused verification**

```bash
python -m pytest   tests/unit/test_backend_session_bridge_contracts.py   tests/unit/test_backend_current_subject_flow.py   tests/unit/test_backend_password_login_flow.py   tests/unit/test_backend_logout_flow.py   tests/unit/test_backend_auth_cookie_services.py   tests/unit/test_backend_session_bridge_container.py   tests/unit/test_backend_session_http_helpers.py   tests/compatibility/test_backend_session_http_characterization.py   tests/integration/test_backend_session_http_bridge_flow.py   tests/architecture/test_backend_session_bridge_taxonomy.py   tests/architecture/test_backend_session_bridge_boundaries.py   tests/architecture/test_no_optional_result_contracts.py -v
```

Expected: PASS.

- [x] **Step 5: Run complete verification**

```bash
python -m compileall -q src tests
python -m pytest -v
```

Expected: compile success and zero test failures.

- [x] **Step 6: Inspect scope against main**

Run:

```bash
git diff --stat main...feature/backend-session-http-bridge
git diff --name-only main...feature/backend-session-http-bridge
```

Confirm no:
- `/api.php/auth` consent code;
- OAuth redirect/CSRF logic;
- public login/logout route mount;
- PHP session parser;
- new auth persistence table;
- Redis/Supabase adapter;
- `remember` field in primary password credentials.

- [x] **Step 7: Update this plan with exact verification evidence**

Append:
- branch SHA;
- compileall result;
- exact pytest passed/failed/skipped count;
- statement that no production auth route was mounted;
- statement that bridge is ready for the OAuth authorization/consent slice.

- [x] **Step 8: Commit completion record**

```bash
git add tests/architecture/test_backend_session_bridge_boundaries.py   tests/architecture/test_dependency_boundaries.py   tests/architecture/test_no_optional_result_contracts.py   docs/superpowers/plans/2026-09-19-backend-session-http-bridge.md   AGENTS.md
git commit -m "test: verify backend session http bridge"
```

## Verification Checklist

Before integration, the feature-branch tip must prove all of the following:

- `python -m compileall -q src tests` succeeds;
- full pytest has zero failures;
- bridge application files are only VO/Services/Composite responsibilities and no fake Entity was introduced;
- application bridge has no HTTP/ORM/compatibility dependency;
- valid session wins over persistent fallback;
- malformed/stale session can fall back to valid persistent credential;
- persistent-login disabled never invokes restore and never clears existing `auth_token`;
- session-only login does not mutate existing persistent transport;
- persistent issuance failure does not invalidate successful password authentication;
- logout clears both credential transports idempotently;
- PHP-falsy `auth_token` values never reach persistent strategy parsing;
- Python session cookie is `gomazon_session`, host-only and runtime-session-only;
- no `PHPSESSID` compatibility is claimed;
- no standalone auth route is mounted in production;
- no OAuth authorization/consent logic entered this branch.


## Implementation Status

Implemented on `feature/backend-session-http-bridge`.

Verified implementation head: `78928b7de7668fdf26d1956c735219ed8a97ceaf`.

Fresh GitHub Actions verification on that implementation head:

- Python 3.12 compile source tree: **success**.
- Full pytest suite: **452 passed, 0 failed, 0 skipped** (2 existing FastAPI/Starlette TestClient deprecation warnings).
- No standalone production login/logout/current-user route was mounted.
- `main.py` was not modified by this slice.
- The bridge is ready to be consumed by the next OAuth authorization/consent slice.

Implementation notes confirmed by the completed TDD cycle:

1. valid runtime session short-circuits persistent restore;
2. stale/malformed session may fall back to persistent credential and issue a replacement session credential;
3. persistent-login disabled mode never invokes restore and never mutates existing `auth_token`;
4. session-only password login preserves existing persistent transport;
5. persistent issuance failure leaves successful primary authentication successful;
6. logout is idempotent and clears both browser credential transports;
7. legacy PHP-falsy `auth_token` values are normalized before persistent strategies;
8. persistent cookie refresh carries both `Max-Age` and absolute UTC `Expires`;
9. Python session transport remains host-only `gomazon_session` with no `PHPSESSID` interoperability;
10. real SQLite + ASGI fixture flow covers login, current-subject resolution, persistent restore and logout.

Task 7 initially exposed an `httpx` test-cookie domain/path conflict caused by manually injected unscoped cookies. The test harness was corrected to send stale credentials through an explicit request `Cookie` header; production cookie behavior was unchanged.
