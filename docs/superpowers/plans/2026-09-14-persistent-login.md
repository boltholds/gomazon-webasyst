# Persistent Login / Remember-Me Compatibility Implementation Plan

Status: implemented and verified on `feature/persistent-login`

**Goal:** Add Webasyst 4.2.0-compatible backend persistent login using the legacy `auth_token` format behind an extensible strategy/issuer bridge, reusing the existing typed auth/session foundation.

**Architecture:** A raw `PersistentCredential` is accepted through an ordered `PersistentCredentialStrategy` chain and restored through `RestoreBackendSessionFromPersistentCredential`. Credential issuance is a separate `IssuePersistentCredential` operation using an injected `PersistentCredentialIssuer`. Password login and persistent restore share one `BackendSessionEstablisher`, while application results carry transport-neutral `refresh / clear / keep` dispositions and never expose cookie/HTTP types.

**Spec:** `docs/superpowers/specs/2026-09-14-persistent-login-design.md`

## Global constraints

- Webasyst 4.2.0 source is authoritative when behavior conflicts with newer documentation.
- Ordinary persistent-login outcomes never use `None`, `Optional`, bool sentinels, empty strings, or exception-as-branch semantics.
- Serialized discriminator values derive from `EnumStr`.
- `PersistentCredential` and `PersistentCredentialLifetime` are immutable `@dataclass(slots=True, frozen=True)` VOs.
- Persistent credential acceptance uses an ordered strategy chain; issuance is a separately injected port.
- Application code does not import `hashlib`, SQLAlchemy, FastAPI/Starlette, cookie types, or Webasyst compatibility implementations.
- Legacy `auth_token` mechanics stay in `compatibility/webasyst/auth` and use constant-time comparison.
- No persistent-token table or schema migration is introduced.
- `remember` UI preference is not authentication state and does not enter password-auth contracts.
- Global remember-me disablement means restore is not invoked; it is not modeled as `CLEAR`.
- Password login without persistent issuance does not revoke an existing persistent credential.
- Production login/cookie HTTP routes remain out of scope.

## Completed tasks

### Task 1 — Persistent VOs and explicit result contracts

- [x] Added `PersistentCredential` and `PersistentCredentialLifetime` immutable VOs.
- [x] Added typed strategy, resolution, issuance, session-establishment, restore, and transport-disposition unions.
- [x] Added closed `EnumStr` discriminator/reason domains.
- [x] Added contract tests proving frozen value semantics, raw-string discriminator validation, and explicit negative variants.
- [x] Existing Optional/sentinel architecture guard remains green.

### Task 2 — Strategy resolver and issuer ports

- [x] Added `PersistentCredentialStrategy`, `PersistentCredentialResolver`, and `PersistentCredentialIssuer` application-owned ports.
- [x] Added `OrderedPersistentCredentialResolver`.
- [x] `NotApplicable` continues the chain, `Resolved` returns, `Rejected` is terminal, and all-skipped maps to typed `UNSUPPORTED + CLEAR`.
- [x] Tests prove a future prefixed strategy can be registered without changing resolver/use-case code.

### Task 3 — Webasyst 4.2.0 legacy `auth_token` compatibility

- [x] Added compatibility-private legacy token parser/VO.
- [x] Characterized exact `waAuth::getToken()` formula and contact-id placement between 15-character hash fragments.
- [x] Added exact 30-day lifetime (`2592000` seconds) through a typed lifetime VO.
- [x] Added `LegacyAuthTokenStrategy` and `LegacyAuthTokenIssuer`.
- [x] Token comparison uses `hmac.compare_digest`.
- [x] Malformed, stale, missing-subject and disabled-subject credentials return typed rejection + `CLEAR`.
- [x] Successful legacy restore returns `REFRESH` with the same credential for another 30 days.
- [x] MD5 token generation remains delegated to the existing compatibility token factory; the formula is not duplicated in application code.

### Task 4 — Shared backend session establishment

- [x] Added `BackendSessionEstablisher`.
- [x] Password auth now delegates normal session creation/registration to the shared establisher.
- [x] Persistent restore uses the same establisher instance in composition.
- [x] Session creation errors become typed `SESSION_UNAVAILABLE`.
- [x] Registry infrastructure failure compensates by revoking freshly-created session state and re-raises the infrastructure exception.
- [x] Existing password-auth external behavior remains unchanged.

### Task 5 — Persistent issuance and restore use cases

- [x] Added `IssuePersistentCredential`.
- [x] Added `RestoreBackendSessionFromPersistentCredential`.
- [x] Issue resolves the current subject before delegating to the configured issuer.
- [x] Rejected credential preserves its `CLEAR` disposition and never calls the session establisher.
- [x] Valid credential + successful session returns `PersistentLoginRestored` with resolver disposition.
- [x] Valid credential + session-unavailable returns typed rejection + `KEEP`.
- [x] Application use cases never inspect legacy token shape.

### Task 6 — Persistent revoke and logout separation

- [x] Added transport-neutral `RevokePersistentCredential`, returning `ClearPersistentCredential`.
- [x] Existing `LogoutBackendSession` remains session-only and accepts only `SessionId`.
- [x] No storage dependency was added for legacy persistent revoke because the legacy credential is stateless.

### Task 7 — Composition

- [x] `AuthUseCases` and the main container expose issue/restore/revoke persistent-login operations.
- [x] Default composition accepts exactly one terminal legacy strategy through `OrderedPersistentCredentialResolver` and uses `LegacyAuthTokenIssuer` for issuance.
- [x] Password auth and persistent restore share one `BackendSessionEstablisher`, `SessionStateStore`, `AuthSessionRegistry`, `AuthSubjectStore`, and credential-version token factory.
- [x] Added explicit `create_auth_use_cases_with_persistent_credentials(...)` for custom resolver/issuer injection.
- [x] Custom resolver/issuer injection uses required arguments rather than nullable defaults.

### Task 8 — End-to-end and architecture verification

- [x] Added SQLite E2E: seed backend user -> password login -> issue legacy credential -> logout normal session -> restore new normal session -> mutate login/password -> old credential rejects with `CLEAR`.
- [x] Added persistent-login dependency guard: application persistent-login/session-establishment code cannot import transport, DB, concrete hash, or Webasyst codec modules.
- [x] Existing project-wide Optional/sentinel guard remains green.
- [x] E2E mutation avoids nullable ORM lookup control flow by using an explicit SQL update statement.
- [x] Quality pass removed non-semantic `is not None` wiring assertions from new container tests.

## Verification evidence

Final code-bearing verification SHA before this status-only update: `2a0e8bafe3c44e804dec9e6bc261844192051ad1`.

GitHub Actions, Python 3.12.14:

- [x] `python -m compileall -q src tests` — success.
- [x] `python -m pytest -v` — **180 passed, 0 failed, 0 skipped**.
- [x] Architecture dependency guard — passed.
- [x] Optional/sentinel contract guard — passed.
- [x] Persistent-login SQLite E2E — passed.
- [x] Exact Webasyst legacy token characterization — passed.

Repository scope review against `main`:

- [x] no production login/cookie HTTP route or middleware added;
- [x] no persistent token DB table, Alembic migration, or other schema change added;
- [x] no permissions/RBAC implementation added;
- [x] no OAuth/social/Webasyst ID/API OAuth2 implementation added;
- [x] no opaque-v2 storage implementation added;
- [x] no `remember` field added to `BackendPasswordCredentials`;
- [x] legacy token mechanics remain compatibility-only;
- [x] application contracts remain explicit typed variants without Optional sentinels.

The CI workflow now includes the compile step permanently before pytest so future branches verify syntax for the complete `src` and `tests` trees as part of normal CI.
