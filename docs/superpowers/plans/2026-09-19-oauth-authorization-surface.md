# OAuth Authorization Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Webasyst 4.2.0-compatible OAuth authorization surface for `/api.php/auth`, `/api.php/token`, and `/api.php/revoke` on top of the existing backend-session bridge, ACL, API credential core, and API response infrastructure.

**Architecture:** Browser authorization is a typed application Composite that receives a resolved backend subject and delegates scope filtering and grant issuance through injected ports/use cases. Webasyst transport quirks—CSRF, cancel-before-auth, unregistered redirects, controller-level HTTP-200 payload errors, HTML rendering, and revoke target extraction—stay in compatibility/presentation. Static OAuth routes are mounted before generic `/api.php/{api_path:path}` method execution.

**Tech Stack:** Python 3.12+, FastAPI/Starlette presentation, Pydantic v2 boundary contracts, SQLAlchemy 2 async adapters already present in the repository, stdlib `html`/`secrets`/`urllib.parse`, pytest/httpx/aiosqlite.

**Spec:** `docs/superpowers/specs/2026-09-19-oauth-authorization-surface-design.md`

## Global Constraints

- Webasyst Framework 4.2.0 supplied source is authoritative for compatibility behavior.
- New OAuth application code must be explicitly classifiable as Entity, VO, Service, or Composite.
- `OAuthConsentApplication` is the only new identity-bearing Entity in this slice.
- Closed protocol/result domains use `EnumStr`; open identifiers remain immutable VOs.
- Expected negative outcomes use explicit typed variants, never `None`, empty strings, booleans, or exceptions as ordinary control flow.
- OAuth application code imports no FastAPI/Starlette, SQLAlchemy, compatibility modules, HTML renderer, cookie names, or ORM rows.
- Browser identity is resolved only through `BackendCurrentSubjectFlow`; login/logout use the existing backend-session bridge.
- Credential issue/exchange/revoke use existing `IssueAuthorizationCode`, `IssueImplicitApiAccessToken`, `ExchangeAuthorizationCode`, `ResolveApiAccessToken`, and `RevokeApiAccessToken`.
- Outer POST `cancel` runs before current-subject resolution and CSRF.
- Authenticated POST ordering is request validation -> CSRF -> logout -> scope filter -> approve/deny.
- Requested scope silently drops missing/unauthorized apps; empty effective scope is invalid.
- Consent access does not reuse the API execution `webasyst` access exception implicitly.
- `response_type=token` requires redirect URI; `response_type=code` does not.
- Legacy redirect acceptance is isolated behind `OAuthRedirectPolicy`.
- `/api.php/token` reads required protocol fields from POST only.
- Token/revoke controller-level payload errors are HTTP 200, default JSON/optional XML, invalid explicit format -> JSON `invalid_request`, no JSONP.
- Revoke authentication credential and request-level deletion target are separate typed states.
- Header-only Bearer revoke authenticates but performs no deletion and returns an empty access-token value.
- Static `/api.php/auth`, `/api.php/token`, `/api.php/revoke` routes are registered before generic API catch-all.
- `token-headless`, client registration, PKCE, refresh tokens, OIDC, Webasyst ID/social auth, PHP sessions, and general audit migration are out of scope.

## Review Focus

1. A `redirect_uri` containing an existing query and/or fragment must receive code/error parameters in the exact legacy query/fragment position without silently re-encoding the supplied URI.
2. A POST containing `cancel` plus stale/missing auth cookies and invalid CSRF must still take the outer cancel branch without touching session resolution or CSRF.
3. A scope containing duplicates, missing apps, unauthorized apps, and authorized apps must preserve first-occurrence request order for surviving apps and must not leak denied apps into the consent screen.
4. A revoke request with request-level token A and Bearer token B must authenticate using A because request input has precedence and must target A; header B must not override it.
5. Controller response formatting must never accidentally apply API-method JSONP semantics: callback parameters on token/revoke must be ignored and ordinary controller errors must remain HTTP 200.

---

### Task 1: OAuth taxonomy foundation — Entity, VO, request/result contracts

**Files:**
- Create: `src/gomazon_webasyst/application/oauth_authorization/__init__.py`
- Create: `src/gomazon_webasyst/application/oauth_authorization/entities/__init__.py`
- Create: `src/gomazon_webasyst/application/oauth_authorization/entities/consent_application.py`
- Create: `src/gomazon_webasyst/application/oauth_authorization/vo/__init__.py`
- Create: `src/gomazon_webasyst/application/oauth_authorization/vo/client.py`
- Create: `src/gomazon_webasyst/application/oauth_authorization/vo/authorization.py`
- Create: `src/gomazon_webasyst/application/oauth_authorization/vo/revoke.py`
- Create: `src/gomazon_webasyst/application/oauth_authorization/services/__init__.py`
- Create: `src/gomazon_webasyst/application/oauth_authorization/composites/__init__.py`
- Create: `src/gomazon_webasyst/application/oauth_authorization/composites/requests.py`
- Create: `src/gomazon_webasyst/contracts/oauth_authorization.py`
- Modify: `src/gomazon_webasyst/contracts/enums.py`
- Create: `tests/unit/test_oauth_authorization_contracts.py`
- Create: `tests/architecture/test_oauth_authorization_taxonomy.py`
- Modify: `tests/architecture/test_no_optional_result_contracts.py`

**Interfaces:**
- Produces Entity:
  - `OAuthConsentApplication(app_id: AppId, display_name: OAuthAppDisplayName, icon: OAuthAppIconReference)`.
- Produces open immutable VOs:
  - `OAuthClientName(value: str)`;
  - `OAuthAppDisplayName(value: str)`;
  - `OAuthAppIconReference(value: str)`;
  - `OAuthRedirectUri(value: str)`;
  - `OAuthCsrfToken(value: str)`;
  - `OAuthRequestedScope(apps: tuple[AppId, ...])`.
- `OAuthRequestedScope` preserves first occurrence order and removes duplicate app ids.
- Produces closed `EnumStr` domains:
  - `OAuthResponseType.CODE | TOKEN`;
  - `OAuthConsentDecision.APPROVE | DENY`;
  - `OAuthGrantType.AUTHORIZATION_CODE`;
  - `OAuthAuthorizationResultKind.CONSENT_REQUIRED | CODE_GRANTED | TOKEN_GRANTED | DENIED | INVALID_SCOPE | GRANT_UNAVAILABLE`;
  - `OAuthConsentAppLookupKind.RESOLVED | MISSING`;
  - `OAuthConsentAccessKind.GRANTED | DENIED`;
  - `OAuthRevokeTargetKind.PROVIDED | MISSING`;
  - `OAuthRevokeAuthenticationKind.AUTHENTICATED | REJECTED`.
- Produces Composite requests:
  - `OAuthAuthorizationRequest(client_id: ApiClientId, client_name: OAuthClientName, response_type: OAuthResponseType, requested_scope: OAuthRequestedScope, redirect_target: OAuthRedirectTarget)`;
  - explicit redirect state `OAuthRedirectProvided(uri) | OAuthRedirectMissing`;
  - `OAuthAuthenticatedDecisionRequest(subject, authorization_request, decision)`.
- Produces Pydantic result contracts:
  - `OAuthConsentRequired(client_name, effective_scope, applications)`;
  - `OAuthAuthorizationCodeGranted(code, redirect_target)`;
  - `OAuthImplicitTokenGranted(access_token, redirect_target)`;
  - `OAuthAuthorizationDenied(response_type, redirect_target, client_name)`;
  - `OAuthAuthorizationInvalidScope`;
  - `OAuthAuthorizationGrantUnavailable`.
- Produces revoke VO:
  - `RevokeTargetProvided(token: ApiAccessToken)`;
  - `RevokeTargetMissing`.

- [ ] **Step 1: Write failing Entity/VO tests**

```python
def test_consent_application_identity_is_app_id() -> None:
    app = OAuthConsentApplication(
        app_id=AppId("shop"),
        display_name=OAuthAppDisplayName("Shop"),
        icon=OAuthAppIconReference("/wa-apps/shop/img/shop48.png"),
    )
    assert app.app_id == AppId("shop")


def test_requested_scope_preserves_order_and_deduplicates() -> None:
    scope = OAuthRequestedScope(
        (AppId("shop"), AppId("crm"), AppId("shop"))
    )
    assert scope.apps == (AppId("shop"), AppId("crm"))
```

- [ ] **Step 2: Write failing discriminator/serialization tests**

Use `TypeAdapter` to assert raw strings such as `"code"`, `"token"`, `"approve"`, and `"missing"` parse into the matching `EnumStr`/discriminated variants and serialize back as strings.

Assert all Pydantic OAuth result contracts are frozen and contain no `NoneType` fields.

- [ ] **Step 3: Write failing taxonomy/dependency guard**

Assert every non-`__init__.py` module below `application/oauth_authorization` is under `entities/`, `vo/`, `services/`, or `composites/`, and reject imports of FastAPI, Starlette, SQLAlchemy and `gomazon_webasyst.compatibility`.

- [ ] **Step 4: Run RED**

```bash
python -m pytest   tests/unit/test_oauth_authorization_contracts.py   tests/architecture/test_oauth_authorization_taxonomy.py   tests/architecture/test_no_optional_result_contracts.py -v
```

Expected: FAIL because OAuth application packages/contracts do not yet exist.

- [ ] **Step 5: Implement minimal taxonomy foundation**

Use frozen/slotted dataclasses for internal Entity/VO/request types and frozen Pydantic models for serialized result contracts. Do not add HTTP/query/form concepts here.

- [ ] **Step 6: Run GREEN**

Run the Step 4 command.

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/gomazon_webasyst/application/oauth_authorization   src/gomazon_webasyst/contracts/oauth_authorization.py   src/gomazon_webasyst/contracts/enums.py   tests/unit/test_oauth_authorization_contracts.py   tests/architecture/test_oauth_authorization_taxonomy.py   tests/architecture/test_no_optional_result_contracts.py
git commit -m "feat: add oauth authorization contracts"
```

### Task 2: Consent app catalog and ordinary backend-access policy

**Files:**
- Create: `src/gomazon_webasyst/application/ports/oauth_consent_apps.py`
- Create: `src/gomazon_webasyst/application/ports/oauth_consent_access.py`
- Create: `src/gomazon_webasyst/infrastructure/oauth_authorization/__init__.py`
- Create: `src/gomazon_webasyst/infrastructure/oauth_authorization/app_catalog.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/__init__.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/services/__init__.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/services/consent_access.py`
- Create: `tests/unit/test_oauth_consent_catalog.py`
- Create: `tests/unit/test_oauth_consent_access.py`

**Interfaces:**
- `OAuthConsentAppCatalog.resolve(AppId) -> OAuthConsentApplicationResolved | OAuthConsentApplicationMissing`.
- `InMemoryOAuthConsentAppCatalog(applications: tuple[OAuthConsentApplication, ...])` stores explicit registrations and rejects duplicate app ids at construction.
- `OAuthConsentAccessPolicy.authorize(subject: AuthenticatedSubject, app_id: AppId) -> OAuthConsentAccessGranted | OAuthConsentAccessDenied`.
- `LegacyOAuthConsentAccessService` uses existing `AccessControlUnitOfWorkFactory` + `RightsEvaluator`.
- It evaluates the actual subject as backend user and ordinary app backend access; unlike `LegacyApiAppAccessService`, it has no unconditional `AppId("webasyst")` grant.

- [ ] **Step 1: Write failing catalog tests**

```python
def test_catalog_resolves_registered_entity_and_reports_missing() -> None:
    catalog = InMemoryOAuthConsentAppCatalog((SHOP_APP,))
    resolved = catalog.resolve(AppId("shop"))
    missing = catalog.resolve(AppId("crm"))
    assert isinstance(resolved, OAuthConsentApplicationResolved)
    assert resolved.application is SHOP_APP
    assert isinstance(missing, OAuthConsentApplicationMissing)
```

Pin duplicate registration rejection.

- [ ] **Step 2: Write failing consent access tests**

Pin:
- missing subject -> denied;
- non-backend user -> denied;
- normal app with `NoAppAccess` -> denied;
- normal app with limited/full/global access -> granted;
- `webasyst` with no backend right -> denied, proving no API-execution special case leaks in.

- [ ] **Step 3: Run RED**

```bash
python -m pytest   tests/unit/test_oauth_consent_catalog.py   tests/unit/test_oauth_consent_access.py -v
```

Expected: FAIL because ports/adapters do not exist.

- [ ] **Step 4: Implement catalog and access policy**

Reuse `create_webasyst_rights_evaluator()`; do not duplicate rights math.

- [ ] **Step 5: Run GREEN + existing access tests**

```bash
python -m pytest   tests/unit/test_oauth_consent_catalog.py   tests/unit/test_oauth_consent_access.py   tests/unit/test_access_control_reads.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/gomazon_webasyst/application/ports/oauth_consent_apps.py   src/gomazon_webasyst/application/ports/oauth_consent_access.py   src/gomazon_webasyst/infrastructure/oauth_authorization   src/gomazon_webasyst/compatibility/webasyst/oauth   tests/unit/test_oauth_consent_catalog.py   tests/unit/test_oauth_consent_access.py
git commit -m "feat: add oauth consent catalog and access policy"
```

### Task 3: Effective-scope Service

**Files:**
- Create: `src/gomazon_webasyst/application/oauth_authorization/services/scope.py`
- Create: `tests/unit/test_oauth_consent_scope_service.py`

**Interfaces:**
- `OAuthConsentScopeService(catalog: OAuthConsentAppCatalog, access: OAuthConsentAccessPolicy)`.
- `filter(subject: AuthenticatedSubject, requested: OAuthRequestedScope) -> OAuthEffectiveScopeResolved | OAuthEffectiveScopeEmpty`.
- Resolved result contains:
  - `scope: ApiScope`;
  - `applications: tuple[OAuthConsentApplication, ...]`.
- Iterates request order once:
  1. catalog resolve;
  2. missing -> skip;
  3. access authorize;
  4. denied -> skip;
  5. granted -> append app id/entity.
- Empty survivors return explicit `OAuthEffectiveScopeEmpty`, not invalid `ApiScope`.

- [ ] **Step 1: Write failing mixed-scope test for Review Focus #3**

```python
@pytest.mark.asyncio
async def test_scope_filter_preserves_survivor_order_and_hides_denied_apps() -> None:
    service = OAuthConsentScopeService(
        catalog=Catalog({
            "shop": SHOP,
            "crm": CRM,
            "tasks": TASKS,
        }),
        access=AccessPolicy(granted={"shop", "tasks"}),
    )
    result = await service.filter(
        SUBJECT,
        OAuthRequestedScope(
            (
                AppId("shop"),
                AppId("missing"),
                AppId("crm"),
                AppId("shop"),
                AppId("tasks"),
            )
        ),
    )
    assert result.scope.apps == (AppId("shop"), AppId("tasks"))
    assert result.applications == (SHOP, TASKS)
```

- [ ] **Step 2: Write empty-effective-scope test**

All missing/denied requested apps -> `OAuthEffectiveScopeEmpty`; no `ApiScope` constructor is invoked with an empty tuple.

- [ ] **Step 3: Run RED**

Run: `python -m pytest tests/unit/test_oauth_consent_scope_service.py -v`

Expected: FAIL because Service does not exist.

- [ ] **Step 4: Implement minimal scope Service**

No HTML/client/redirect logic.

- [ ] **Step 5: Run GREEN**

Run the Step 3 command.

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/gomazon_webasyst/application/oauth_authorization/services/scope.py   tests/unit/test_oauth_consent_scope_service.py
git commit -m "feat: add oauth consent scope filtering"
```

### Task 4: Authorization Composite — consent, approve, authenticated deny

**Files:**
- Create: `src/gomazon_webasyst/application/oauth_authorization/composites/authorization.py`
- Create: `tests/unit/test_oauth_authorization_flow.py`

**Interfaces:**
- `OAuthAuthorizationFlow(scope_service, issue_authorization_code, issue_implicit_api_access_token)`.
- `prepare(subject, authorization_request) -> OAuthAuthorizationResult`:
  - empty scope -> `OAuthAuthorizationInvalidScope`;
  - resolved scope -> `OAuthConsentRequired`.
- `decide(subject, authorization_request, decision) -> OAuthAuthorizationResult`:
  - first filter effective scope;
  - empty -> invalid scope;
  - DENY -> `OAuthAuthorizationDenied`;
  - APPROVE + CODE -> call `IssueAuthorizationCode`;
  - APPROVE + TOKEN -> call `IssueImplicitApiAccessToken`.
- Existing credential issue results are mapped:
  - issued code -> `OAuthAuthorizationCodeGranted`;
  - issued token -> `OAuthImplicitTokenGranted`;
  - collision/concurrent issue rejection -> `OAuthAuthorizationGrantUnavailable`.

- [ ] **Step 1: Write failing consent preparation tests**

Pin successful `ConsentRequired` exact applications/scope and invalid-scope short circuit.

- [ ] **Step 2: Write failing approval tests**

```python
@pytest.mark.asyncio
async def test_code_approval_uses_effective_scope_only() -> None:
    issuer = CodeIssuer()
    flow = OAuthAuthorizationFlow(
        scope_service=ScopeService(EFFECTIVE),
        issue_authorization_code=issuer,
        issue_implicit_api_access_token=FailIfCalled(),
    )
    result = await flow.decide(SUBJECT, CODE_REQUEST, OAuthConsentDecision.APPROVE)
    assert isinstance(result, OAuthAuthorizationCodeGranted)
    assert issuer.calls == [(SUBJECT, CODE_REQUEST.client_id, EFFECTIVE.scope)]
```

Also pin implicit token issuer.

- [ ] **Step 3: Write failing authenticated-deny and issuer-rejection tests**

DENY must not invoke either issuer. Credential issue rejection maps to `GRANT_UNAVAILABLE`.

- [ ] **Step 4: Run RED**

Run: `python -m pytest tests/unit/test_oauth_authorization_flow.py -v`

Expected: FAIL because Composite does not exist.

- [ ] **Step 5: Implement orchestration only**

No redirect string construction, CSRF, HTML or HTTP status in application Composite.

- [ ] **Step 6: Run GREEN**

Run the Step 4 command.

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/gomazon_webasyst/application/oauth_authorization/composites/authorization.py   tests/unit/test_oauth_authorization_flow.py
git commit -m "feat: add oauth authorization composite"
```

### Task 5: Legacy auth request validation, redirect policy, cancel/deny semantics and CSRF

**Files:**
- Create: `src/gomazon_webasyst/application/ports/oauth_redirect_policy.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/vo/__init__.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/vo/transport.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/services/request_validation.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/services/redirects.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/services/csrf.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/services/cancel.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/services/deny.py`
- Create: `tests/compatibility/test_legacy_oauth_auth_characterization.py`
- Create: `tests/unit/test_legacy_oauth_auth_services.py`

**Interfaces:**
- Raw query/form are `ApiParameterMap`/`ApiRequestParameters`.
- `LegacyOAuthAuthorizationRequestService.parse(query) -> OAuthAuthorizationRequestParsed | OAuthAuthorizationRequestRejected`.
- Required query fields use PHP-falsy semantics:
  - client_id;
  - client_name;
  - response_type;
  - scope;
  - redirect_uri only for TOKEN.
- Scope parsing splits comma-separated values, drops empty tokens, creates `OAuthRequestedScope`.
- Unsupported response type -> invalid request typed rejection.
- `OAuthRedirectPolicy.validate(client_id, redirect_target) -> OAuthRedirectAccepted | OAuthRedirectRejected`.
- `LegacyUnregisteredRedirectPolicy` accepts both provided and missing redirects.
- `LegacyOAuthRedirectService` constructs:
  - code/error query parameter with `?` or `&`;
  - token/error fragment by appending `#...` exactly as legacy;
  - it does not rebuild/normalize URL components through `urlencode`.
- `LegacyOAuthCsrfService(generator)`:
  - `issue(existing_cookie_state) -> OAuthCsrfIssued(token, set_cookie: bool)`;
  - `validate(cookie_state, form_state) -> OAuthCsrfAccepted | OAuthCsrfRejected`;
  - secure generator defaults to `secrets.token_hex(16)`.
- `LegacyOAuthCancelService.cancel(request) -> OAuthCancelRedirect | OAuthCancelFrameworkError`.
- `LegacyOAuthDenyService.deny(request) -> OAuthDenyRedirect | OAuthDenyHtmlError`.

- [ ] **Step 1: Write failing request-validation characterization tests**

Pin PHP-falsy required inputs, code redirect optional, token redirect required, ordered deduped scope.

- [ ] **Step 2: Write redirect tests for Review Focus #1**

```python
def test_code_redirect_appends_query_without_reencoding_existing_uri() -> None:
    uri = OAuthRedirectUri("https://client.test/cb?x=1#frag")
    result = redirects.code(uri, AuthorizationCode("abc"))
    assert result.location == "https://client.test/cb?x=1#frag&code=abc"
```

Use the exact source-characterized concatenation rules; add error query and token fragment cases. The tests must document any unusual placement relative to an existing fragment rather than “fixing” it.

- [ ] **Step 3: Write cancel-before-auth tests for Review Focus #2**

Cancel TOKEN -> fragment redirect. Cancel CODE + redirect -> query redirect. Cancel CODE without redirect -> `access_denied`/403 framework error. Assert Service has no current-subject/CSRF dependency.

- [ ] **Step 4: Write CSRF tests**

Pin:
- no cookie -> issue new token;
- existing non-falsy cookie -> retain token/no replacement;
- matching cookie/form -> accepted;
- missing/mismatched/falsy -> rejected;
- generator collision is irrelevant because token has no registry.

- [ ] **Step 5: Write authenticated deny tests**

Pin distinction from outer cancel: CODE without redirect returns HTML error state, not framework 403.

- [ ] **Step 6: Run RED**

```bash
python -m pytest   tests/compatibility/test_legacy_oauth_auth_characterization.py   tests/unit/test_legacy_oauth_auth_services.py -v
```

Expected: FAIL because compatibility Services do not exist.

- [ ] **Step 7: Implement minimal services and legacy redirect policy**

Do not place login/session/cookie mutation logic here.

- [ ] **Step 8: Run GREEN**

Run the Step 6 command.

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/gomazon_webasyst/application/ports/oauth_redirect_policy.py   src/gomazon_webasyst/compatibility/webasyst/oauth   tests/compatibility/test_legacy_oauth_auth_characterization.py   tests/unit/test_legacy_oauth_auth_services.py
git commit -m "feat: add legacy oauth authorization compatibility"
```

### Task 6: Minimal escaped OAuth HTML renderers

**Files:**
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/services/html_renderer.py`
- Create: `tests/unit/test_legacy_oauth_html_renderer.py`

**Interfaces:**
- `LegacyOAuthHtmlRenderer` pure Service with:
  - `login(model: OAuthLoginPageModel) -> str`;
  - `consent(model: OAuthConsentPageModel) -> str`;
  - `code(model: OAuthCodePageModel) -> str`;
  - `error(model: OAuthErrorPageModel) -> str`.
- Page models are frozen compatibility dataclasses, not application contracts.
- All request/catalog strings are escaped with `html.escape(..., quote=True)`.
- Login/consent forms include exact action URL and hidden `_csrf`.
- Consent controls produce distinct `approve`, deny/default submit, and `logout` actions.
- No JavaScript is required.

- [ ] **Step 1: Write failing HTML-escaping tests**

```python
def test_consent_renderer_escapes_client_and_app_names() -> None:
    html = renderer.consent(
        OAuthConsentPageModel(
            client_name='<img src=x onerror="boom">',
            applications=(ConsentAppView("shop", "<b>Shop</b>", "/icon.png"),),
            csrf_token="csrf",
            action="/api.php/auth?...",
        )
    )
    assert '<img src=x onerror="boom">' not in html
    assert "&lt;img" in html
    assert "&lt;b&gt;Shop&lt;/b&gt;" in html
```

- [ ] **Step 2: Write form-state tests**

Assert POST method, explicit action, CSRF hidden field, login identifier/password inputs, remember control, approve/deny/logout names.

- [ ] **Step 3: Run RED**

Run: `python -m pytest tests/unit/test_legacy_oauth_html_renderer.py -v`

Expected: FAIL.

- [ ] **Step 4: Implement renderer using stdlib only**

Use string composition over escaped values. No Jinja/Smarty dependency is added in this slice.

- [ ] **Step 5: Run GREEN**

Run the Step 3 command.

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/gomazon_webasyst/compatibility/webasyst/oauth/services/html_renderer.py   tests/unit/test_legacy_oauth_html_renderer.py
git commit -m "feat: add oauth compatibility html renderer"
```

### Task 7: Token endpoint compatibility adapter Services

**Files:**
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/services/controller_format.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/services/token_controller.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/composites/__init__.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/composites/controller_response.py`
- Create: `tests/compatibility/test_legacy_oauth_token_characterization.py`
- Create: `tests/unit/test_legacy_oauth_token_controller.py`

**Interfaces:**
- `LegacyOAuthControllerFormatService.resolve(query) -> OAuthControllerFormatResolved | OAuthControllerFormatRejected`.
- Default JSON; explicit JSON/XML; invalid explicit -> JSON error state containing exact legacy description `Invalid format: <FORMAT>`.
- `LegacyOAuthTokenRequestService.parse(parameters: ApiRequestParameters) -> OAuthTokenExchangeRequestParsed | OAuthTokenExchangeRequestRejected`.
- Reads only `parameters.form`.
- Required: code, client_id, grant_type; PHP-falsy semantics.
- Wrong non-falsy grant_type -> `UNSUPPORTED_GRANT_TYPE`.
- `LegacyOAuthTokenController(exchange_authorization_code)` maps:
  - parsed request + exchanged -> payload `{"access_token": token}`;
  - NOT_FOUND/CLIENT_MISMATCH/EXPIRED -> `invalid_grant`;
  - other typed exchange rejection -> controlled `invalid_grant` compatibility payload, never exception.
- `OAuthControllerPayloadResponse(status_code=200, payload, format)`.
- Serializer uses existing `LegacyJsonApiFormatter`/`LegacyXmlApiFormatter` directly; no `LegacyApiResponseRenderer`, so JSONP cannot activate.

- [ ] **Step 1: Write POST-only request tests**

Put valid protocol values in query with empty form -> invalid_request. Put form values -> parsed.

- [ ] **Step 2: Write grant/error mapping tests**

Pin unsupported_grant_type vs invalid_request vs invalid_grant and success-only access_token field.

- [ ] **Step 3: Write format/JSONP Review Focus #5 tests**

```python
def test_callback_does_not_enable_jsonp_for_token_controller() -> None:
    response = controller_renderer.render(
        payload={"error": "invalid_grant"},
        response_format=ApiResponseFormat.JSON,
    )
    assert response.status_code == 200
    assert response.media_type == "application/json; charset=utf-8"
```

A query callback must never be consumed by this service.

- [ ] **Step 4: Run RED**

```bash
python -m pytest   tests/compatibility/test_legacy_oauth_token_characterization.py   tests/unit/test_legacy_oauth_token_controller.py -v
```

Expected: FAIL.

- [ ] **Step 5: Implement token Services/response Composite**

Keep all ordinary controller outcomes at status 200.

- [ ] **Step 6: Run GREEN**

Run the Step 4 command.

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/gomazon_webasyst/compatibility/webasyst/oauth/services/controller_format.py   src/gomazon_webasyst/compatibility/webasyst/oauth/services/token_controller.py   src/gomazon_webasyst/compatibility/webasyst/oauth/composites   tests/compatibility/test_legacy_oauth_token_characterization.py   tests/unit/test_legacy_oauth_token_controller.py
git commit -m "feat: add legacy oauth token controller"
```

### Task 8: Revoke authentication Composite and legacy revoke-target Services

**Files:**
- Create: `src/gomazon_webasyst/application/oauth_authorization/composites/revoke_authentication.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/services/revoke_target.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/services/revoke_controller.py`
- Create: `tests/unit/test_oauth_revoke_authentication_flow.py`
- Create: `tests/compatibility/test_legacy_oauth_revoke_characterization.py`
- Create: `tests/unit/test_legacy_oauth_revoke_controller.py`

**Interfaces:**
- `OAuthRevokeAuthenticationFlow(resolve_access_token, activity_service)`.
- `authenticate(token) -> OAuthRevokeAuthenticated(contact_id, token) | OAuthRevokeAuthenticationRejected(reason)`.
- Successful resolution calls `ApiUserActivityService.touch_if_due(contact_id)`; activity missing/skipped remains non-fatal as in API execution.
- `LegacyRevokeTargetExtractor.extract(query, form) -> RevokeTargetProvided | RevokeTargetMissing`.
- Request target semantics match `waRequest::request`: form key shadows query key; selected PHP-falsy value -> target missing; header sources are never considered.
- `LegacyOAuthRevokeController(revoke_api_access_token)`:
  - target missing -> payload access_token empty string, no revoke call;
  - target provided -> invoke revoke use case, return the exact target token on both revoked/already-missing result.
- Authentication token extraction itself reuses existing `LegacyApiCredentialExtractionService`.

- [ ] **Step 1: Write failing revoke-auth sequencing test**

Assert `resolve token -> activity` and rejection short-circuits activity.

- [ ] **Step 2: Write target extraction tests for Review Focus #4**

```python
def test_request_token_shadows_bearer_and_becomes_revoke_target() -> None:
    credential = credential_extractor.extract(
        query=ApiParameterMap({"access_token": "query-a"}),
        form=ApiParameterMap({"access_token": "form-a"}),
        authorization=AuthorizationHeader("Bearer header-b"),
        server_authorization=NoAuthorizationHeader(),
    )
    target = revoke_target.extract(
        query=ApiParameterMap({"access_token": "query-a"}),
        form=ApiParameterMap({"access_token": "form-a"}),
    )
    assert credential.token == ApiAccessToken("form-a")
    assert target.token == ApiAccessToken("form-a")
```

Also pin form empty shadows query -> target missing while header may authenticate.

- [ ] **Step 3: Write header-only no-op controller test**

Authenticated Bearer token + `RevokeTargetMissing` -> no revoke call and payload `{"access_token": ""}`.

- [ ] **Step 4: Run RED**

```bash
python -m pytest   tests/unit/test_oauth_revoke_authentication_flow.py   tests/compatibility/test_legacy_oauth_revoke_characterization.py   tests/unit/test_legacy_oauth_revoke_controller.py -v
```

Expected: FAIL.

- [ ] **Step 5: Implement Composite and target/controller Services**

Do not create empty `ApiAccessToken`.

- [ ] **Step 6: Run GREEN**

Run the Step 4 command.

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/gomazon_webasyst/application/oauth_authorization/composites/revoke_authentication.py   src/gomazon_webasyst/compatibility/webasyst/oauth/services/revoke_target.py   src/gomazon_webasyst/compatibility/webasyst/oauth/services/revoke_controller.py   tests/unit/test_oauth_revoke_authentication_flow.py   tests/compatibility/test_legacy_oauth_revoke_characterization.py   tests/unit/test_legacy_oauth_revoke_controller.py
git commit -m "feat: add legacy oauth revoke flow"
```

### Task 9: OAuth composition root

**Files:**
- Create: `src/gomazon_webasyst/composition/oauth_authorization.py`
- Modify: `src/gomazon_webasyst/composition/container.py`
- Create: `tests/unit/test_oauth_authorization_container.py`
- Modify: `tests/unit/test_container.py`

**Interfaces:**
- Produces `OAuthAuthorizationComponents` with:
  - authorization_flow;
  - revoke_authentication_flow;
  - consent_catalog;
  - consent_access_policy;
  - redirect_policy;
  - authorization_request_service;
  - csrf_service;
  - cancel_service;
  - deny_service;
  - html_renderer;
  - token_request/controller/format services;
  - revoke_target/controller services;
  - backend_session_bridge;
  - shared API preconditions;
  - existing API credential use cases needed by presentation.
- `create_oauth_authorization_components(...)` takes explicit dependencies:
  - session_factory;
  - backend_session_bridge;
  - issue_authorization_code;
  - issue_implicit_api_access_token;
  - exchange_authorization_code;
  - resolve_api_access_token;
  - revoke_api_access_token;
  - shared `LegacyApiTransportPreconditionService`;
  - consent catalog;
  - redirect policy;
  - CSRF generator/clock where required.
- Default composition uses:
  - empty `InMemoryOAuthConsentAppCatalog`;
  - `LegacyUnregisteredRedirectPolicy`.
- `Container.oauth_authorization: OAuthAuthorizationComponents`.

- [ ] **Step 1: Write failing composition reuse tests**

Assert exact identity reuse for backend session bridge and all API credential use cases; do not create second credential cores.

- [ ] **Step 2: Write default-policy tests**

Default catalog empty; redirect policy legacy-unregistered; shared precondition object is `container.api_execution.preconditions`.

- [ ] **Step 3: Run RED**

Run: `python -m pytest tests/unit/test_oauth_authorization_container.py tests/unit/test_container.py -v`

Expected: FAIL.

- [ ] **Step 4: Implement composition/container wiring**

Do not mount HTTP routes in this task.

- [ ] **Step 5: Run GREEN**

Run the Step 3 command.

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/gomazon_webasyst/composition/oauth_authorization.py   src/gomazon_webasyst/composition/container.py   tests/unit/test_oauth_authorization_container.py   tests/unit/test_container.py
git commit -m "feat: compose oauth authorization surface"
```

### Task 10: FastAPI /api.php/auth presentation flow

**Files:**
- Create: `src/gomazon_webasyst/presentation/http/legacy_oauth.py`
- Create: `tests/unit/test_legacy_oauth_auth_http.py`

**Interfaces:**
- `create_legacy_oauth_router(components: OAuthAuthorizationComponents) -> APIRouter`.
- Adds GET/POST `/api.php/auth`.
- Shared request normalization:
  - query `ApiParameterMap`;
  - form `ApiParameterMap` for urlencoded forms;
  - backend auth credential state through `normalize_backend_auth_request`;
  - HTTPS state.
- Execution order:
  1. shared API preconditions;
  2. raw POST cancel detection -> minimal cancel parsing/service -> response, before current-subject resolution, CSRF and full OAuth request validation;
  3. current-subject flow + apply auth-cookie dispositions;
  4. unauthenticated GET -> issue CSRF + login HTML without requiring full OAuth request validity;
  5. unauthenticated POST -> validate login CSRF -> password login -> apply cookies -> redirect to the same OAuth URL on success / rerender login on failure;
  6. authenticated request -> full auth-request parse/validation;
  7. authenticated GET -> `authorization_flow.prepare` -> consent/code/error HTML;
  8. authenticated POST -> validate CSRF;
  9. logout -> backend logout flow/apply cookie clear/redirect same auth URL;
  10. approve/deny -> application/compatibility result -> redirect/code/error.
- CSRF cookie transport is presentation-only; default cookie name `_csrf`, path `/`, SameSite=Lax, Secure uses `backend_auth_cookie_secure`, HttpOnly=false because double-submit/browser form compatibility needs form access only from server-rendered value, not JS.

- [ ] **Step 1: Write failing cancel-before-auth HTTP test for Review Focus #2**

Use spies for current-subject, CSRF and full authorization-request parser that fail if called. POST `cancel=1` with missing `client_id`/`scope`, invalid cookies and invalid CSRF must still return the legacy cancel redirect/error.

- [ ] **Step 2: Write login/current-subject HTTP tests**

GET unauthenticated, even with incomplete/invalid OAuth query fields, -> login page + CSRF cookie. POST valid password + matching CSRF -> session cookie + redirect to the same OAuth URL; only the subsequent authenticated request performs full OAuth validation/consent. Invalid login remains login page and never issues grant.

- [ ] **Step 3: Write consent/grant/deny/logout tests**

Pin:
- authenticated GET consent;
- approve code redirect;
- approve code no redirect -> code page;
- implicit token fragment redirect;
- authenticated deny code/token;
- authenticated logout clears `gomazon_session`/`auth_token` and redirects same auth URL.

- [ ] **Step 4: Write API disabled/HTTPS tests**

These execute before cancel/login/consent.

- [ ] **Step 5: Run RED**

Run: `python -m pytest tests/unit/test_legacy_oauth_auth_http.py -v`

Expected: FAIL because router does not exist.

- [ ] **Step 6: Implement /auth presentation**

Keep business rules delegated; presentation only sequences transport-aware branches described above.

- [ ] **Step 7: Run GREEN**

Run the Step 5 command.

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/gomazon_webasyst/presentation/http/legacy_oauth.py   tests/unit/test_legacy_oauth_auth_http.py
git commit -m "feat: add legacy oauth authorization http flow"
```

### Task 11: FastAPI /api.php/token and /api.php/revoke routes + static-route precedence

**Files:**
- Modify: `src/gomazon_webasyst/presentation/http/legacy_oauth.py`
- Modify: `src/gomazon_webasyst/main.py`
- Create: `tests/unit/test_legacy_oauth_token_revoke_http.py`
- Create: `tests/unit/test_oauth_route_precedence.py`
- Modify: `tests/unit/test_legacy_api_http_adapter.py`

**Interfaces:**
- POST `/api.php/token`:
  - shared API preconditions;
  - controller format resolution;
  - form normalization;
  - token controller;
  - direct JSON/XML controller serializer;
  - no JSONP.
- `/api.php/revoke` accepts legacy request methods matching source controller routing, with:
  - shared API preconditions;
  - normal API credential extraction;
  - missing credential -> framework token_required using existing framework formatter/status/JSONP semantics;
  - resolve/authenticate through revoke Composite;
  - invalid credential -> framework invalid_token using existing framework formatter/status/JSONP semantics;
  - only after successful authentication: controller format resolution;
  - request-level revoke target extraction;
  - controller response HTTP 200 with no JSONP.
- `main.py` order:
  1. contacts;
  2. `create_legacy_oauth_router(container.oauth_authorization)`;
  3. `create_legacy_api_router(container.api_execution)`.

- [ ] **Step 1: Write token HTTP tests**

Pin success/error JSON/XML, POST-only parameter behavior, invalid format JSON error, callback ignored, all controller payload outcomes status 200.

- [ ] **Step 2: Write revoke HTTP tests**

Pin:
- request token revokes;
- Bearer-only token authenticates but no-op target returns empty value;
- invalid/missing auth token uses framework statuses and framework JSONP behavior when callback is supplied;
- invalid controller `format` does not override a prior token_required/invalid_token authentication failure;
- request token precedence over Bearer;
- callback is ignored only after authentication succeeds and controller response rendering begins.

- [ ] **Step 3: Write static-route precedence test**

Use a method-registry spy that raises if called. Requests to auth/token/revoke must never hit generic method execution router.

- [ ] **Step 4: Run RED**

```bash
python -m pytest   tests/unit/test_legacy_oauth_token_revoke_http.py   tests/unit/test_oauth_route_precedence.py   tests/unit/test_legacy_api_http_adapter.py -v
```

Expected: FAIL.

- [ ] **Step 5: Implement token/revoke routes and main mount order**

Existing generic reserved-endpoint rejection remains unchanged as a defensive fallback.

- [ ] **Step 6: Run GREEN**

Run the Step 4 command.

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/gomazon_webasyst/presentation/http/legacy_oauth.py   src/gomazon_webasyst/main.py   tests/unit/test_legacy_oauth_token_revoke_http.py   tests/unit/test_oauth_route_precedence.py   tests/unit/test_legacy_api_http_adapter.py
git commit -m "feat: mount legacy oauth token and revoke routes"
```

### Task 12: Real SQLite end-to-end OAuth browser/API loop

**Files:**
- Create: `tests/integration/test_oauth_authorization_surface_flow.py`

**Interfaces:**
- Real Container + SQLite legacy tables + in-memory session store.
- Test overrides default empty consent catalog by composing explicit applications before creating router/app fixture.
- Seed:
  - contact 42 backend user with MD5 password;
  - backend rights for `shop`;
  - no rights for `crm`.
- Register consent apps SHOP and CRM.

- [ ] **Step 1: Write code-grant browser flow**

1. GET `/api.php/auth?client_id=client&client_name=Demo&response_type=code&scope=shop,crm&redirect_uri=https://client.test/cb`.
2. Assert login HTML + CSRF.
3. POST login with matching CSRF.
4. Assert consent contains SHOP but not CRM.
5. POST approve with matching CSRF/current session.
6. Assert redirect contains code.
7. POST `/api.php/token` with code/client/grant_type.
8. Assert JSON access_token.
9. Verify stored token scope contains only SHOP.

- [ ] **Step 2: Write revoke normal path**

Use returned token as request-level `access_token`; revoke; verify token no longer resolves from persistence.

- [ ] **Step 3: Write header-only revoke quirk path**

Issue/reuse token again, call revoke with Bearer header only, assert response access_token empty and token still resolves in persistence.

- [ ] **Step 4: Write implicit token browser flow**

Login/consent with `response_type=token`; approve; assert fragment `#access_token=`.

- [ ] **Step 5: Write cancel and code-display flows**

Pin unauthenticated cancel before CSRF and code approval without redirect URI showing HTML code.

- [ ] **Step 6: Run RED/GREEN**

Run: `python -m pytest tests/integration/test_oauth_authorization_surface_flow.py -v`

Expected after implementation: PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/integration/test_oauth_authorization_surface_flow.py
git commit -m "test: verify oauth authorization surface flow"
```

### Task 13: Architecture guards, scope audit, final verification record

**Files:**
- Create: `tests/architecture/test_oauth_authorization_boundaries.py`
- Modify: `tests/architecture/test_dependency_boundaries.py`
- Modify: `tests/architecture/test_no_optional_result_contracts.py`
- Modify: `docs/superpowers/plans/2026-09-19-oauth-authorization-surface.md`
- Modify: `AGENTS.md` only if implementation reveals a genuinely new decision beyond ADR-041…044.

**Interfaces:**
- No runtime interface; pins architecture and records verification.

- [ ] **Step 1: Add application boundary guards**

Reject below `application/oauth_authorization`:
- FastAPI/Starlette;
- SQLAlchemy;
- compatibility imports;
- cookie names;
- HTML markup;
- `set_cookie`/`delete_cookie`;
- dynamic import helpers.

- [ ] **Step 2: Add scope guards**

Reject on the feature diff:
- `token-headless`;
- PKCE fields such as `code_challenge`/`code_verifier`;
- refresh token contracts;
- OpenID/OIDC scopes/endpoints;
- new OAuth client persistence tables/models;
- PHP session decoding.

- [ ] **Step 3: Add route-order guard**

Parse/read `main.py` and assert OAuth router include appears before generic legacy API router include.

- [ ] **Step 4: Run focused verification**

```bash
python -m pytest   tests/unit/test_oauth_authorization_contracts.py   tests/unit/test_oauth_consent_catalog.py   tests/unit/test_oauth_consent_access.py   tests/unit/test_oauth_consent_scope_service.py   tests/unit/test_oauth_authorization_flow.py   tests/unit/test_legacy_oauth_auth_services.py   tests/unit/test_legacy_oauth_html_renderer.py   tests/unit/test_legacy_oauth_token_controller.py   tests/unit/test_oauth_revoke_authentication_flow.py   tests/unit/test_legacy_oauth_revoke_controller.py   tests/unit/test_oauth_authorization_container.py   tests/unit/test_legacy_oauth_auth_http.py   tests/unit/test_legacy_oauth_token_revoke_http.py   tests/unit/test_oauth_route_precedence.py   tests/compatibility/test_legacy_oauth_auth_characterization.py   tests/compatibility/test_legacy_oauth_token_characterization.py   tests/compatibility/test_legacy_oauth_revoke_characterization.py   tests/integration/test_oauth_authorization_surface_flow.py   tests/architecture/test_oauth_authorization_taxonomy.py   tests/architecture/test_oauth_authorization_boundaries.py   tests/architecture/test_no_optional_result_contracts.py -v
```

Expected: PASS.

- [ ] **Step 5: Run complete verification**

```bash
python -m compileall -q src tests
python -m pytest -v
```

Expected: compile success and zero failures.

- [ ] **Step 6: Inspect diff against main**

```bash
git diff --name-only main...feature/oauth-authorization-surface
git diff --stat main...feature/oauth-authorization-surface
```

Confirm no out-of-scope token-headless/client-registry/PKCE/refresh-token/PHP-session implementation entered the branch.

- [ ] **Step 7: Update implementation status**

Append exact:
- final feature SHA;
- compile result;
- pytest passed/failed/skipped count;
- confirmation that all three OAuth routes are mounted before method catch-all;
- confirmation that header-only revoke quirk and HTTP-200 token/revoke semantics are covered.

- [ ] **Step 8: Commit completion record**

```bash
git add tests/architecture/test_oauth_authorization_boundaries.py   tests/architecture/test_dependency_boundaries.py   tests/architecture/test_no_optional_result_contracts.py   docs/superpowers/plans/2026-09-19-oauth-authorization-surface.md   AGENTS.md
git commit -m "test: verify oauth authorization surface"
```

## Verification Checklist

Before integration, the branch tip must prove:

- compileall succeeds;
- full pytest has zero failures;
- OAuth application code is classified under Entity/VO/Services/Composite;
- application OAuth has no HTTP/ORM/HTML/compatibility dependency;
- browser subject/login/logout go only through the backend-session bridge;
- consent scope silently filters absent/unauthorized apps and preserves survivor order;
- no API execution `webasyst` access exception leaks into consent;
- cancel runs before auth/CSRF;
- authenticated POST ordering matches source;
- code display and query/fragment redirects match source;
- request-supplied redirects are isolated behind the legacy redirect policy;
- token endpoint is POST-only for protocol fields and uses controller HTTP-200 errors;
- revoke request-token vs header-only target quirk is covered;
- token/revoke ignore JSONP callback;
- OAuth static routes precede generic method catch-all;
- token-headless, client registration, PKCE, refresh tokens, OIDC and PHP sessions remain absent.
