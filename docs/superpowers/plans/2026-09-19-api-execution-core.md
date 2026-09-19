# API Execution Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build the Webasyst 4.2.0-compatible authenticated API method execution path on top of the existing OAuth credential and access-control cores, with all new domain/application code explicitly separated into Entity, VO, Services, and Composite packages.

**Architecture:** Raw HTTP is normalized only in the compatibility/presentation boundary. Application execution is a typed staged Composite: access-token resolution -> compatibility activity touch -> installed-app/app-access/scope/license authorization -> explicit method registry -> HTTP method validation -> handler execution. Dynamic PHP class discovery is replaced by registered ApiMethodDefinition Entities; JSON/XML/JSONP and legacy error envelopes remain outside application execution.

**Tech Stack:** Python 3.12+, FastAPI/Starlette presentation adapter, Pydantic v2 cross-boundary contracts, SQLAlchemy 2 async persistence adapters, stdlib XML/JSON helpers, pytest.

**Spec:** docs/superpowers/specs/2026-09-19-api-execution-core-design.md

## Global Constraints

- Webasyst Framework 4.2.0 supplied source is authoritative over newer documentation when behavior conflicts.
- Every new API Execution Core domain/application type MUST be classified as Entity, VO, Service, or Composite.
- Entity/VO/Services/Composite taxonomy does not replace application-owned Ports, infrastructure adapters, compatibility adapters, presentation, or composition root.
- Closed serialized discriminator/status/error/format domains derive from EnumStr; open extension identifiers remain immutable open VOs.
- ApiMethodName, AppId, ApiHttpMethod and application-defined error codes remain open VOs.
- Expected negative outcomes use explicit typed variants, never None, Optional, False, empty values, magic strings, or exceptions as normal branch markers.
- Application API execution code imports no FastAPI/Starlette, SQLAlchemy, compatibility modules, dynamic import helpers, or legacy table names.
- Existing ResolveApiAccessToken is the only API access-token resolution/touch entry point used by execution; no execution code queries wa_api_tokens directly.
- Observable authorization order is app exists -> app access -> token scope -> license -> method lookup -> HTTP method validation -> execute.
- The Webasyst app access exception belongs to an injected compatibility ApiAppAccessPolicy, never an if app == "webasyst" branch in the Composite pipeline.
- Method discovery uses explicit ApiMethodRegistry registration; request strings never become Python module/class names.
- Query and form parameter sources remain distinct through ApiRequestParameters.
- Legacy required-parameter falsy behavior belongs to a compatibility Service; native handlers may use their own typed DTO validation.
- JSON/XML/JSONP formatting belongs to compatibility/presentation and never leaks into ApiMethodHandler.
- API user last_datetime compatibility update uses a separate Service with the exact >30 second threshold.
- /api.php/auth consent/redirect/CSRF, token-headless, cron dispatch, installer subsystem migration, Redis/Supabase state adapters, and bulk bundled-app method migration are out of scope.
- Production composition may start with an empty method registry/app directory; tests register explicit fixture methods.

## Review Focus

These are the five high-risk inputs/conditions that must be pinned by tests in the owning tasks:

1. A POST access_token key shadows the same GET key exactly like waRequest::request; if the POST value is empty, header fallback is allowed but the GET token must not reappear.
2. Authorization short-circuits in legacy order; app-not-installed must prevent app-access/scope/license/method calls, and app-access denial must prevent later stages.
3. ApiHttpMethod is an open uppercase protocol VO; unknown-but-valid extension methods are representable even when no registered method allows them.
4. JSONP follows PHP truthiness: empty callback and string "0" do not enable JSONP; a non-empty callback forces HTTP 200 even for an error payload.
5. XML formatting preserves nested _element metadata and plural child-name inference without exposing formatter concerns to application handlers.

---

### Task 1: Taxonomy foundation — VO, Entity, Composite request/result contracts

**Files:**
- Create: src/gomazon_webasyst/application/api_execution/__init__.py
- Create: src/gomazon_webasyst/application/api_execution/entities/__init__.py
- Create: src/gomazon_webasyst/application/api_execution/entities/method_definition.py
- Create: src/gomazon_webasyst/application/api_execution/vo/__init__.py
- Create: src/gomazon_webasyst/application/api_execution/vo/method.py
- Create: src/gomazon_webasyst/application/api_execution/vo/parameters.py
- Create: src/gomazon_webasyst/application/api_execution/vo/errors.py
- Create: src/gomazon_webasyst/application/api_execution/composites/__init__.py
- Create: src/gomazon_webasyst/application/api_execution/composites/invocation.py
- Create: src/gomazon_webasyst/application/api_execution/composites/results.py
- Create: src/gomazon_webasyst/application/ports/api_methods.py
- Create: src/gomazon_webasyst/contracts/api_execution.py
- Modify: src/gomazon_webasyst/contracts/enums.py
- Create: tests/unit/test_api_execution_types.py
- Create: tests/architecture/test_api_execution_taxonomy.py
- Modify: tests/architecture/test_no_optional_result_contracts.py

**Interfaces:**
- Produces VO ApiMethodName(value: str), ApiMethodTarget(app_id: AppId, method: ApiMethodName), ApiHttpMethod(value: str), ApiParameterName(value: str), ApiParameterMap(values: Mapping[str, ApiParameterValue]), ApiRequestParameters(query, form), ApiApplicationErrorCode(value: str).
- ApiHttpMethod validates an RFC-token-compatible non-empty value and normalizes to uppercase. It is NOT an EnumStr.
- Produces Composite ApiInvocationRequest(access_token: ApiAccessToken, target: ApiMethodTarget, http_method: ApiHttpMethod, parameters: ApiRequestParameters).
- Produces Composite ApiPrincipalContext(contact_id: int, client_id: ApiClientId, scope: ApiScope) and ApiInvocationContext(principal, target).
- Produces ApiMethodSucceeded(payload, status_code) and ApiMethodRejected(error) handler result variants.
- Produces application-owned ApiMethodHandler Protocol: async execute(context: ApiInvocationContext, parameters: ApiRequestParameters) -> ApiMethodResult.
- Produces Entity ApiMethodDefinition(target, allowed_methods: frozenset[ApiHttpMethod], handler). allowed_methods must be non-empty.
- Produces closed EnumStr domains ApiResponseFormat, ApiFrameworkErrorCode, ApiExecutionResultKind, ApiMethodResultKind, ApiCredentialSourceKind and any lookup/authorization discriminators required by later tasks.
- Produces Pydantic ApiFrameworkError and ApiExecutionSucceeded / ApiExecutionRejected cross-boundary contracts.

- [ ] **Step 1: Write failing VO/Entity/Composite tests**

~~~python
def test_api_http_method_is_open_uppercase_vo() -> None:
    assert ApiHttpMethod("get") == ApiHttpMethod("GET")
    assert ApiHttpMethod("PROPFIND").value == "PROPFIND"
    with pytest.raises(ValueError):
        ApiHttpMethod("bad method")


def test_method_definition_requires_identity_and_allowed_methods() -> None:
    target = ApiMethodTarget(AppId("shop"), ApiMethodName("order.get"))
    definition = ApiMethodDefinition(
        target=target,
        allowed_methods=frozenset({ApiHttpMethod("GET")}),
        handler=StubHandler(),
    )
    assert definition.target == target
    with pytest.raises(ValueError):
        ApiMethodDefinition(target=target, allowed_methods=frozenset(), handler=StubHandler())


def test_request_parameters_preserve_query_and_form_sources() -> None:
    params = ApiRequestParameters(
        query=ApiParameterMap({"id": "query"}),
        form=ApiParameterMap({"id": "form"}),
    )
    assert params.query["id"] == "query"
    assert params.form["id"] == "form"
~~~

- [ ] **Step 2: Write failing EnumStr/serialization and no-Optional tests**

Use TypeAdapter on the execution result union and raw string discriminators. Assert ApiResponseFormat.JSON serializes as "json", framework error code serializes as its legacy string, and no result/model field annotation contains NoneType.

- [ ] **Step 3: Run RED**

Run: python -m pytest tests/unit/test_api_execution_types.py tests/architecture/test_api_execution_taxonomy.py tests/architecture/test_no_optional_result_contracts.py -v

Expected: FAIL because the api_execution packages/contracts do not yet exist.

- [ ] **Step 4: Implement the minimal taxonomy foundation**

Use frozen/slotted dataclasses for internal VOs/Entities/Composites and Pydantic frozen models for serialized contracts. ApiParameterMap must copy input into an immutable MappingProxyType or equivalent immutable value representation; callers must not be able to mutate request parameters after construction.

ApiFrameworkErrorCode must initially contain exactly the framework-owned codes required by this slice: DISABLED="disabled", INVALID_REQUEST="invalid_request", TOKEN_REQUIRED="token_required", INVALID_TOKEN="invalid_token", APP_NOT_INSTALLED="app_not_installed", ACCESS_DENIED="access_denied", PAYMENT_REQUIRED="payment_required", INVALID_METHOD="invalid_method", INVALID_PARAM="invalid_param".

- [ ] **Step 5: Add taxonomy architecture guard**

The guard checks that every Python module under application/api_execution is below exactly one of entities/, vo/, services/, composites/, except package __init__.py. It also rejects FastAPI, Starlette, SQLAlchemy and compatibility imports from that tree.

- [ ] **Step 6: Run GREEN**

Run: python -m pytest tests/unit/test_api_execution_types.py tests/architecture/test_api_execution_taxonomy.py tests/architecture/test_no_optional_result_contracts.py -v

Expected: PASS.

- [ ] **Step 7: Commit**

~~~bash
git add src/gomazon_webasyst/application/api_execution src/gomazon_webasyst/application/ports/api_methods.py src/gomazon_webasyst/contracts/api_execution.py src/gomazon_webasyst/contracts/enums.py tests/unit/test_api_execution_types.py tests/architecture/test_api_execution_taxonomy.py tests/architecture/test_no_optional_result_contracts.py
git commit -m "feat: add api execution taxonomy foundation"
~~~

### Task 2: Explicit method registry Entity lookup and method executor Service

**Files:**
- Create: src/gomazon_webasyst/application/ports/api_method_registry.py
- Create: src/gomazon_webasyst/application/api_execution/services/__init__.py
- Create: src/gomazon_webasyst/application/api_execution/services/method_executor.py
- Create: src/gomazon_webasyst/infrastructure/api_execution/__init__.py
- Create: src/gomazon_webasyst/infrastructure/api_execution/method_registry.py
- Create: tests/unit/test_api_method_registry.py
- Create: tests/unit/test_api_method_executor.py

**Interfaces:**
- ApiMethodRegistry.register(definition) -> ApiMethodRegistered | ApiMethodRegistrationRejected.
- ApiMethodRegistry.resolve(target) -> ApiMethodResolved | ApiMethodMissing.
- InMemoryApiMethodRegistry implements the port with explicit membership checks, never dict.get sentinel semantics.
- ApiMethodExecutor.execute(definition, context, parameters, http_method) -> ApiMethodResult.
- Verb mismatch returns ApiMethodRejected(ApiFrameworkError(code=INVALID_REQUEST, http_status=405, description="Method <VERB> not allowed")) without calling the handler.
- Allowed verb delegates exactly once to definition.handler.execute(context, parameters).

- [ ] **Step 1: Write failing registry tests**

~~~python
def test_registry_is_extended_by_registration_not_dispatch_branch() -> None:
    registry = InMemoryApiMethodRegistry()
    definition = fixture_definition("shop", "order.get", "GET")

    registered = registry.register(definition)
    duplicate = registry.register(definition)
    resolved = registry.resolve(definition.target)
    missing = registry.resolve(ApiMethodTarget(AppId("shop"), ApiMethodName("missing")))

    assert isinstance(registered, ApiMethodRegistered)
    assert isinstance(duplicate, ApiMethodRegistrationRejected)
    assert isinstance(resolved, ApiMethodResolved)
    assert resolved.definition is definition
    assert isinstance(missing, ApiMethodMissing)
~~~

- [ ] **Step 2: Write failing executor tests, including Review Focus #3**

~~~python
@pytest.mark.asyncio
async def test_executor_rejects_unknown_extension_verb_before_handler_call() -> None:
    handler = RecordingHandler()
    definition = ApiMethodDefinition(
        target=TARGET,
        allowed_methods=frozenset({ApiHttpMethod("GET")}),
        handler=handler,
    )

    result = await ApiMethodExecutor().execute(
        definition,
        CONTEXT,
        PARAMETERS,
        ApiHttpMethod("PROPFIND"),
    )

    assert isinstance(result, ApiMethodRejected)
    assert result.error.http_status == 405
    assert handler.calls == []
~~~

Also pin multiple allowed verbs and successful handler pass-through.

- [ ] **Step 3: Run RED**

Run: python -m pytest tests/unit/test_api_method_registry.py tests/unit/test_api_method_executor.py -v

Expected: FAIL for missing registry/executor.

- [ ] **Step 4: Implement registry and executor**

Do not use importlib, globals, class-name construction, module scanning, plugin autoloading, or app/method if/elif dispatch.

- [ ] **Step 5: Run GREEN**

Run: python -m pytest tests/unit/test_api_method_registry.py tests/unit/test_api_method_executor.py tests/architecture/test_api_execution_taxonomy.py -v

Expected: PASS.

- [ ] **Step 6: Commit**

~~~bash
git add src/gomazon_webasyst/application/ports/api_method_registry.py src/gomazon_webasyst/application/api_execution/services/method_executor.py src/gomazon_webasyst/infrastructure/api_execution tests/unit/test_api_method_registry.py tests/unit/test_api_method_executor.py
git commit -m "feat: add explicit api method registry"
~~~

### Task 3: Installed-app, app-access, scope and license authorization Services

**Files:**
- Create: src/gomazon_webasyst/application/ports/installed_apps.py
- Create: src/gomazon_webasyst/application/ports/api_app_access.py
- Create: src/gomazon_webasyst/application/ports/app_license.py
- Create: src/gomazon_webasyst/application/api_execution/composites/authorization.py
- Create: src/gomazon_webasyst/application/api_execution/services/authorizer.py
- Create: src/gomazon_webasyst/infrastructure/api_execution/app_directory.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/__init__.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/services/__init__.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/services/app_access.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/services/license.py
- Modify: src/gomazon_webasyst/composition/access_control.py
- Create: tests/unit/test_api_request_authorizer.py
- Create: tests/unit/test_legacy_api_app_access.py

**Interfaces:**
- InstalledAppDirectory.resolve(AppId) -> InstalledAppResolved | InstalledAppMissing.
- InMemoryInstalledAppDirectory(app_ids: frozenset[AppId]) implements the port.
- ApiAppAccessPolicy.authorize(contact_id: int, app_id: AppId) -> ApiAppAccessGranted | ApiAppAccessDenied | ApiAppSubjectUnavailable.
- AppLicensePolicy.check(app_id: AppId) -> AppLicenseGranted | AppLicenseBlocked.
- AllowAllAppLicensePolicy returns AppLicenseGranted explicitly; no nullable installer dependency exists.
- ApiRequestAuthorizer.authorize(principal: ApiPrincipalContext, target: ApiMethodTarget) -> ApiAuthorizationGranted | ApiAuthorizationRejected.
- create_webasyst_rights_evaluator() is extracted from composition/access_control.py and used both by create_access_control_use_cases and API compatibility composition so effective-right semantics cannot drift.
- LegacyApiAppAccessService uses AccessControlUnitOfWorkFactory + RightsEvaluator. It denies Missing/NotUser; grants resolved users for AppId("webasyst"); for other apps it loads effective access and grants Limited/Full/GlobalAdmin but denies NoAppAccess.

- [ ] **Step 1: Write failing exact-order authorizer tests, including Review Focus #2**

Use recording stubs with call logs.

~~~python
@pytest.mark.asyncio
async def test_missing_app_stops_all_later_authorization_stages() -> None:
    log: list[str] = []
    authorizer = authorizer_with(
        directory=MissingDirectory(log),
        access=FailIfCalledAccess(log),
        license=FailIfCalledLicense(log),
    )

    result = await authorizer.authorize(PRINCIPAL, TARGET)

    assert result.error.code is ApiFrameworkErrorCode.APP_NOT_INSTALLED
    assert log == ["app"]


@pytest.mark.asyncio
async def test_access_denial_stops_scope_and_license() -> None:
    log: list[str] = []
    result = await authorizer_with(
        directory=ResolvedDirectory(log),
        access=DeniedAccess(log),
        license=FailIfCalledLicense(log),
    ).authorize(PRINCIPAL, TARGET)

    assert result.error.code is ApiFrameworkErrorCode.ACCESS_DENIED
    assert log == ["app", "access"]
~~~

Add separate tests: granted app/access but scope excludes target -> ACCESS_DENIED without license; granted scope but blocked license -> PAYMENT_REQUIRED 402.

- [ ] **Step 2: Write failing legacy app-access tests**

Pin: AccessSubjectMissing -> unavailable/denied; AccessSubjectNotUser -> denied; resolved user + webasyst -> granted without rights lookup; normal app NoAppAccess -> denied; Limited/Full/GlobalAdmin -> granted.

- [ ] **Step 3: Run RED**

Run: python -m pytest tests/unit/test_api_request_authorizer.py tests/unit/test_legacy_api_app_access.py -v

Expected: FAIL for missing ports/services.

- [ ] **Step 4: Implement authorization ports/services and evaluator factory**

Keep the literal Webasyst compatibility exception only in compatibility/webasyst/api/services/app_access.py. The application authorizer must never compare app_id.value to "webasyst".

- [ ] **Step 5: Run GREEN plus existing ACL tests**

Run: python -m pytest tests/unit/test_api_request_authorizer.py tests/unit/test_legacy_api_app_access.py tests/unit/test_access_control_reads.py tests/unit/test_access_control_container.py -v

Expected: PASS.

- [ ] **Step 6: Commit**

~~~bash
git add src/gomazon_webasyst/application/ports/installed_apps.py src/gomazon_webasyst/application/ports/api_app_access.py src/gomazon_webasyst/application/ports/app_license.py src/gomazon_webasyst/application/api_execution/composites/authorization.py src/gomazon_webasyst/application/api_execution/services/authorizer.py src/gomazon_webasyst/infrastructure/api_execution/app_directory.py src/gomazon_webasyst/compatibility/webasyst/api src/gomazon_webasyst/composition/access_control.py tests/unit/test_api_request_authorizer.py tests/unit/test_legacy_api_app_access.py
git commit -m "feat: add api request authorization services"
~~~

### Task 4: API user activity VO, Store Port and Service

**Files:**
- Create: src/gomazon_webasyst/application/api_execution/vo/activity.py
- Create: src/gomazon_webasyst/application/ports/api_activity.py
- Create: src/gomazon_webasyst/application/api_execution/services/activity.py
- Create: src/gomazon_webasyst/infrastructure/api_execution/activity.py
- Create: tests/unit/test_api_user_activity_service.py
- Create: tests/integration/test_sqlalchemy_api_activity_store.py

**Interfaces:**
- ApiUserNeverActive | ApiUserLastActiveAt are explicit VOs/state variants; SQL NULL is normalized immediately.
- ApiUserActivityStore.resolve(contact_id) -> ApiActivityFound(state) | ApiActivitySubjectMissing.
- ApiUserActivityStore.touch(contact_id, at) -> ApiActivityTouched | ApiActivityTouchMissing.
- ApiUserActivityService.touch_if_due(contact_id) -> ApiActivityUpdated | ApiActivitySkipped | ApiActivitySubjectMissing.
- Service receives clock and threshold=timedelta(seconds=30).
- Exact legacy rule: touch only when a previous last_datetime exists AND now - last_datetime > 30 seconds. Never-active, exactly 30 seconds, and newer values are skipped.
- SQLAlchemyApiUserActivityStore maps WaContactRow.last_datetime and never returns None.

- [ ] **Step 1: Write failing threshold tests**

~~~python
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state",
    [
        ApiUserNeverActive(),
        ApiUserLastActiveAt(at=NOW - timedelta(seconds=30)),
        ApiUserLastActiveAt(at=NOW - timedelta(seconds=29)),
    ],
)
async def test_activity_is_not_touched_until_strictly_older_than_30_seconds(state) -> None:
    store = FakeActivityStore(state)
    result = await service(store, now=NOW).touch_if_due(42)
    assert isinstance(result, ApiActivitySkipped)
    assert store.touches == []


@pytest.mark.asyncio
async def test_activity_older_than_30_seconds_is_touched() -> None:
    store = FakeActivityStore(ApiUserLastActiveAt(at=NOW - timedelta(seconds=31)))
    result = await service(store, now=NOW).touch_if_due(42)
    assert isinstance(result, ApiActivityUpdated)
    assert store.touches == [(42, NOW)]
~~~

- [ ] **Step 2: Write failing SQLite null-normalization and update tests**

Seed WaContactRow with last_datetime NULL, assert ApiUserNeverActive. Seed timestamp, assert ApiUserLastActiveAt. Touch and commit, reload exact timestamp.

- [ ] **Step 3: Run RED**

Run: python -m pytest tests/unit/test_api_user_activity_service.py tests/integration/test_sqlalchemy_api_activity_store.py -v

Expected: FAIL for missing activity types/store/service.

- [ ] **Step 4: Implement minimal activity adapter and Service**

Activity subject disappearance is an ordinary typed result. Pipeline integration in Task 5 treats missing/skipped activity as non-fatal compatibility side-effect outcomes; infrastructure errors still propagate.

- [ ] **Step 5: Run GREEN**

Run: python -m pytest tests/unit/test_api_user_activity_service.py tests/integration/test_sqlalchemy_api_activity_store.py -v

Expected: PASS.

- [ ] **Step 6: Commit**

~~~bash
git add src/gomazon_webasyst/application/api_execution/vo/activity.py src/gomazon_webasyst/application/ports/api_activity.py src/gomazon_webasyst/application/api_execution/services/activity.py src/gomazon_webasyst/infrastructure/api_execution/activity.py tests/unit/test_api_user_activity_service.py tests/integration/test_sqlalchemy_api_activity_store.py
git commit -m "feat: add api user activity service"
~~~

### Task 5: ApiExecutionPipeline Composite

**Files:**
- Create: src/gomazon_webasyst/application/api_execution/composites/pipeline.py
- Create: tests/unit/test_api_execution_pipeline.py

**Interfaces:**
- ApiExecutionPipeline(resolve_access_token, activity_service, authorizer, method_registry, method_executor).
- __call__(request: ApiInvocationRequest) -> ApiExecutionResult.
- Existing ResolveApiAccessToken is consumed directly.
- ApiAccessTokenResolved becomes ApiPrincipalContext(contact_id, client_id, scope).
- Existing token MISSING/EXPIRED/CONCURRENT_STATE_CHANGED results map to ApiExecutionRejected with INVALID_TOKEN/401. Missing token itself is handled earlier by credential extraction; pipeline always receives an ApiAccessToken.
- Successful token resolution calls activity Service, then authorizer, registry.resolve, executor in exact order.
- Activity skipped/missing does not reject method execution; infrastructure exceptions propagate.
- Registry miss maps INVALID_METHOD/404.
- Executor/handler result becomes ApiExecutionSucceeded or ApiExecutionRejected without response formatting.

- [ ] **Step 1: Write failing pipeline sequencing tests**

~~~python
@pytest.mark.asyncio
async def test_pipeline_sequences_token_activity_authorization_registry_executor() -> None:
    log: list[str] = []
    pipeline = pipeline_with_recorders(log)

    result = await pipeline(REQUEST)

    assert isinstance(result, ApiExecutionSucceeded)
    assert log == ["token", "activity", "authorize", "registry", "execute"]
~~~

- [ ] **Step 2: Write short-circuit tests for each stage**

Token rejection must leave log ["token"]. Authorization rejection must leave ["token", "activity", "authorize"]. Registry missing must not call executor. Handler/framework rejection must return typed rejection unchanged.

- [ ] **Step 3: Run RED**

Run: python -m pytest tests/unit/test_api_execution_pipeline.py -v

Expected: FAIL because pipeline Composite does not exist.

- [ ] **Step 4: Implement orchestration only**

The pipeline file must contain no SQL, no compatibility string checks, no JSON/XML logic, no header parsing, no method-specific parameter parsing.

- [ ] **Step 5: Run GREEN and taxonomy guard**

Run: python -m pytest tests/unit/test_api_execution_pipeline.py tests/architecture/test_api_execution_taxonomy.py -v

Expected: PASS.

- [ ] **Step 6: Commit**

~~~bash
git add src/gomazon_webasyst/application/api_execution/composites/pipeline.py tests/unit/test_api_execution_pipeline.py
git commit -m "feat: add api execution composite pipeline"
~~~

### Task 6: Legacy transport VO/Composite normalization Services

**Files:**
- Create: src/gomazon_webasyst/compatibility/webasyst/api/vo/__init__.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/vo/transport.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/composites/__init__.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/composites/request.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/services/target_parser.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/services/credential_extractor.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/services/response_format.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/services/parameter_reader.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/services/preconditions.py
- Create: tests/compatibility/test_api_execution_transport_characterization.py
- Create: tests/unit/test_legacy_api_transport_services.py

**Interfaces:**
- LegacyApiHttpRequestComposite contains request_path, query ApiParameterMap, form ApiParameterMap, authorization_header state, server_authorization state, http_method, is_https and requested format/callback data. Absence states are explicit transport variants, not None.
- LegacyApiTargetParser.parse(path, query) -> ApiTargetParsed | ApiTargetMalformed | ApiTargetReservedEndpoint.
- Supported method forms normalize to one ApiMethodTarget:
  - api.php + GET app/method
  - api.php/shop/order.get
  - api.php/shop.order.get
- Known special one-segment endpoints auth, token, revoke, token-headless, license-cache, profile-update and cron prefix return ApiTargetReservedEndpoint so method execution does not accidentally consume them.
- LegacyApiCredentialExtractionService returns ApiCredentialExtracted(token, source) | ApiCredentialMissing.
- Source precedence exactly follows waRequest::request + checkToken:
  1. form access_token when the key exists;
  2. otherwise query access_token;
  3. if selected request value is PHP-falsy, Authorization header;
  4. then server HTTP_AUTHORIZATION;
  5. strip leading Bearer case-insensitively and trim for header sources.
- ApiResponseFormatService returns JSON default; explicit json/xml case-insensitive; invalid explicit value returns typed format rejection.
- ApiParameterReaderService.get/post reads only its source and required=True rejects PHP-falsy values with INVALID_PARAM/400.
- LegacyApiTransportPreconditionService returns ApiTransportAccepted | ApiTransportDisabled(message) | ApiHttpsRequired. URL construction stays presentation-side.

- [ ] **Step 1: Write source-backed route/format/precondition characterization tests**

Pin the three route forms, malformed paths, reserved endpoints, JSON default, XML/JSON case normalization, invalid explicit format, API disabled and ssl_all requiring HTTPS.

- [ ] **Step 2: Write credential precedence tests including Review Focus #1**

~~~python
def test_post_access_token_shadows_get_even_when_empty_then_header_wins() -> None:
    result = extractor.extract(
        query=ApiParameterMap({"access_token": "get-token"}),
        form=ApiParameterMap({"access_token": ""}),
        authorization=AuthorizationHeader("Bearer header-token"),
        server_authorization=NoAuthorizationHeader(),
    )

    assert isinstance(result, ApiCredentialExtracted)
    assert result.token == ApiAccessToken("header-token")
    assert result.source is ApiCredentialSourceKind.AUTHORIZATION_HEADER
~~~

Also pin: no POST key -> GET token; non-empty POST beats GET/header; request token "0" is PHP-falsy and falls to header; Bearer stripping is case-insensitive; no credential -> typed missing.

- [ ] **Step 3: Write GET/POST parameter-reader tests**

Required values None, False, 0, 0.0, "", "0", empty tuple/list/mapping reject; non-empty values pass. GET never reads form and POST never reads query.

- [ ] **Step 4: Run RED**

Run: python -m pytest tests/compatibility/test_api_execution_transport_characterization.py tests/unit/test_legacy_api_transport_services.py -v

Expected: FAIL for missing compatibility services.

- [ ] **Step 5: Implement normalization services**

Do not import FastAPI/Starlette in these pure compatibility services. Presentation converts Request into LegacyApiHttpRequestComposite in Task 8.

- [ ] **Step 6: Run GREEN**

Run: python -m pytest tests/compatibility/test_api_execution_transport_characterization.py tests/unit/test_legacy_api_transport_services.py -v

Expected: PASS.

- [ ] **Step 7: Commit**

~~~bash
git add src/gomazon_webasyst/compatibility/webasyst/api tests/compatibility/test_api_execution_transport_characterization.py tests/unit/test_legacy_api_transport_services.py
git commit -m "feat: add legacy api transport normalization"
~~~

### Task 7: Legacy JSON, XML, JSONP and framework error formatting Services

**Files:**
- Create: src/gomazon_webasyst/compatibility/webasyst/api/services/error_mapper.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/services/json_formatter.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/services/xml_formatter.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/composites/response.py
- Create: src/gomazon_webasyst/compatibility/webasyst/api/composites/response_renderer.py
- Create: tests/compatibility/test_api_response_characterization.py
- Create: tests/unit/test_legacy_api_response_formatters.py

**Interfaces:**
- ApiTransportResponse Composite: status_code, media_type, body text, headers tuple.
- LegacyApiErrorMapper maps ApiFrameworkError to payload containing error, error_description and details.
- Invalid-token compatibility details may include sha256 supplied by transport adapter; raw token is never logged or included.
- LegacyJsonApiFormatter recursively removes every key named _element before json.dumps.
- LegacyXmlApiFormatter renders root response, respects explicit _element list child name, infers singular child names for plural keys, recursively emits mappings/lists/scalars and empty elements.
- LegacyApiResponseRenderer.render(execution_result, response_format, callback) selects JSON/XML. JSONP applies only to JSON.
- JSONP uses legacy PHP truthiness for callback: empty string and "0" mean no JSONP. Non-falsy callback forces status 200 and media type text/javascript; body is callback(<json>); for both success and error.

- [ ] **Step 1: Write failing JSON recursive metadata tests**

~~~python
def test_json_formatter_removes_element_metadata_recursively() -> None:
    payload = {
        "_element": "item",
        "items": [
            {"_element": "child", "id": 1},
            {"id": 2},
        ],
    }
    rendered = LegacyJsonApiFormatter().format(payload)
    assert "_element" not in rendered
    assert json.loads(rendered) == {"items": [{"id": 1}, {"id": 2}]}
~~~

- [ ] **Step 2: Write failing XML characterization tests including Review Focus #5**

Pin root <response>, explicit nested _element item names, items -> item and categories -> category inference, associative mapping nesting, scalar text and empty string element.

- [ ] **Step 3: Write JSONP tests including Review Focus #4**

~~~python
@pytest.mark.parametrize("callback", ["", "0"])
def test_php_falsy_callback_does_not_enable_jsonp(callback: str) -> None:
    response = renderer.render(SUCCESS, ApiResponseFormat.JSON, ApiJsonpCallback(callback))
    assert response.status_code == SUCCESS.status_code
    assert response.media_type == "application/json; charset=utf-8"


def test_nonempty_jsonp_callback_forces_200_even_for_error() -> None:
    response = renderer.render(ERROR_403, ApiResponseFormat.JSON, ApiJsonpCallback("cb"))
    assert response.status_code == 200
    assert response.media_type == "text/javascript; charset=utf-8"
    assert response.body.startswith("cb(")
    assert response.body.endswith(");")
~~~

- [ ] **Step 4: Run RED**

Run: python -m pytest tests/compatibility/test_api_response_characterization.py tests/unit/test_legacy_api_response_formatters.py -v

Expected: FAIL for missing formatters/renderer.

- [ ] **Step 5: Implement formatters with stdlib only**

Use json and xml.etree.ElementTree or an equivalently safe stdlib XML builder. Never build XML by string concatenating unescaped user values.

- [ ] **Step 6: Run GREEN**

Run: python -m pytest tests/compatibility/test_api_response_characterization.py tests/unit/test_legacy_api_response_formatters.py -v

Expected: PASS.

- [ ] **Step 7: Commit**

~~~bash
git add src/gomazon_webasyst/compatibility/webasyst/api/services src/gomazon_webasyst/compatibility/webasyst/api/composites tests/compatibility/test_api_response_characterization.py tests/unit/test_legacy_api_response_formatters.py
git commit -m "feat: add legacy api response formatters"
~~~

### Task 8: Composition and FastAPI legacy /api.php method adapter

**Files:**
- Create: src/gomazon_webasyst/composition/api_execution.py
- Create: src/gomazon_webasyst/presentation/http/legacy_api.py
- Modify: src/gomazon_webasyst/composition/container.py
- Modify: src/gomazon_webasyst/main.py
- Create: tests/unit/test_api_execution_container.py
- Create: tests/unit/test_legacy_api_http_adapter.py
- Modify: tests/unit/test_container.py

**Interfaces:**
- ApiExecutionComponents contains pipeline, method_registry, installed_app_directory, transport services and response renderer as explicit fields needed by presentation/composition.
- create_api_execution_components(session_factory, resolve_api_access_token, *, method_registry, installed_app_directory, license_policy) is the explicit injectable entry point.
- create_default_api_execution_components(...) creates an empty InMemoryApiMethodRegistry, empty InMemoryInstalledAppDirectory and explicit AllowAllAppLicensePolicy. No Optional injection parameters.
- LegacyApiAppAccessService gets SQLAlchemyAccessControlUnitOfWorkFactory and create_webasyst_rights_evaluator().
- ApiUserActivityService gets SQLAlchemyApiUserActivityStore and clock.
- create_legacy_api_router(components) exposes method-execution routes only:
  - /api.php
  - /api.php/{api_path:path}
- The adapter parses query/form/header/path, evaluates transport preconditions, target, response format and credential extraction, then builds ApiInvocationRequest and calls pipeline.
- Reserved endpoints are NOT executed as methods. This slice does not implement auth/token/revoke/token-headless/cron.
- For invalid token lookup, adapter may compute SHA-256 of the supplied token solely for legacy error detail after the pipeline returns INVALID_TOKEN; it must not log raw token.
- HTTPS redirect location is built from the actual request URL in presentation when ApiHttpsRequired is returned.
- main.py mounts only the legacy API router in addition to existing native contacts router; the broader legacy catch-all router remains unmounted.

- [ ] **Step 1: Write failing composition tests**

Assert default registry/directory are empty, custom registry/directory identity is preserved, ResolveApiAccessToken is reused from the container credential core, and no concrete SQL/HTTP objects enter the pipeline.

- [ ] **Step 2: Write failing HTTP adapter tests**

Use FastAPI TestClient/ASGI client with stub components to pin:
- /api.php?app=shop&method=ping
- /api.php/shop/ping
- /api.php/shop.ping
- malformed path -> invalid_request/400
- missing token -> token_required/400
- Bearer path
- JSON/XML selection
- reserved /api.php/auth does not reach method registry
- API disabled -> disabled/404
- HTTPS-required -> 301 with https URL

- [ ] **Step 3: Run RED**

Run: python -m pytest tests/unit/test_api_execution_container.py tests/unit/test_legacy_api_http_adapter.py tests/unit/test_container.py -v

Expected: FAIL because composition/router do not exist.

- [ ] **Step 4: Implement composition and presentation adapter**

FastAPI Request/Response objects exist only in presentation/http/legacy_api.py. Use existing container lifespan pattern; add the execution components/container field without changing auth/session lifetime semantics.

- [ ] **Step 5: Run GREEN plus main-app import test**

Run: python -m pytest tests/unit/test_api_execution_container.py tests/unit/test_legacy_api_http_adapter.py tests/unit/test_container.py -v

Expected: PASS.

- [ ] **Step 6: Commit**

~~~bash
git add src/gomazon_webasyst/composition/api_execution.py src/gomazon_webasyst/presentation/http/legacy_api.py src/gomazon_webasyst/composition/container.py src/gomazon_webasyst/main.py tests/unit/test_api_execution_container.py tests/unit/test_legacy_api_http_adapter.py tests/unit/test_container.py
git commit -m "feat: wire legacy api execution adapter"
~~~

### Task 9: SQLite/ASGI vertical flow, architecture guards and final verification

**Files:**
- Create: tests/integration/test_api_execution_flow.py
- Create: tests/architecture/test_api_execution_boundaries.py
- Modify: tests/architecture/test_dependency_boundaries.py
- Modify: tests/architecture/test_no_optional_result_contracts.py
- Modify: AGENTS.md only if implementation reveals a new architectural decision beyond ADR-035/036/037
- Modify: docs/superpowers/plans/2026-09-19-api-execution-core.md to record final verification evidence

**Interfaces:**
- Vertical test uses real SQLite OAuth token persistence, real ACL tables/evaluator, real SQL activity store, explicit fixture installed app + method registration, pipeline and ASGI adapter.
- Fixture method is an ApiMethodDefinition Entity registered explicitly; it echoes typed query/form data and does not receive Request/AsyncSession.

- [ ] **Step 1: Write the SQLite/ASGI end-to-end fixture flow**

Seed:
- contact 42 as backend user with last_datetime older than 30 seconds;
- wa_api_tokens token scoped to shop;
- rights granting shop backend access;
- installed app directory containing shop;
- fixture method shop.ping registered for GET and POST.

Verify:
1. query-token request succeeds and updates token last_use_datetime + contact last_datetime;
2. Bearer request succeeds;
3. all three target route forms hit the same fixture Entity;
4. scope denial returns access_denied/403;
5. app-access denial returns access_denied/403;
6. unknown installed method returns invalid_method/404;
7. non-installed app returns app_not_installed/400;
8. disallowed HTTP method returns invalid_request/405;
9. JSON output removes _element;
10. XML output has response root;
11. JSONP callback forces status 200;
12. reserved auth path never invokes the fixture registry.

- [ ] **Step 2: Add architecture guards**

Guards reject:
- fastapi/starlette/sqlalchemy/compatibility imports below application/api_execution;
- importlib, __import__, dynamic class construction in API method resolution;
- raw wa_api_tokens/wa_api_auth_codes strings in execution application modules;
- Request, Response, AsyncSession, ORM model types in ApiMethodHandler signatures;
- raw closed discriminator strings where EnumStr members exist;
- T | None / Optional lookup/result/lifecycle state;
- if/elif chains containing both app and method comparisons in execution dispatch;
- new Python files directly under application/api_execution other than __init__.py, enforcing Entity/VO/Services/Composite package classification.

- [ ] **Step 3: Run focused verification**

Run:

~~~bash
python -m pytest   tests/unit/test_api_execution_types.py   tests/unit/test_api_method_registry.py   tests/unit/test_api_method_executor.py   tests/unit/test_api_request_authorizer.py   tests/unit/test_legacy_api_app_access.py   tests/unit/test_api_user_activity_service.py   tests/unit/test_api_execution_pipeline.py   tests/unit/test_legacy_api_transport_services.py   tests/unit/test_legacy_api_response_formatters.py   tests/unit/test_api_execution_container.py   tests/unit/test_legacy_api_http_adapter.py   tests/compatibility/test_api_execution_transport_characterization.py   tests/compatibility/test_api_response_characterization.py   tests/integration/test_sqlalchemy_api_activity_store.py   tests/integration/test_api_execution_flow.py   tests/architecture/test_api_execution_taxonomy.py   tests/architecture/test_api_execution_boundaries.py   tests/architecture/test_no_optional_result_contracts.py -v
~~~

Expected: PASS.

- [ ] **Step 4: Run complete verification**

~~~bash
python -m compileall -q src tests
python -m pytest -v
~~~

Expected: compile success and entire repository suite green.

- [ ] **Step 5: Compare scope against main**

Run: git diff --stat main...feature/api-execution-core and inspect changed paths.

Confirm no /api.php/auth consent implementation, no token/revoke HTTP implementation, no Redis/Supabase adapter, no installer subsystem, no dynamic app method import, and no mass bundled-app migration entered the branch.

- [ ] **Step 6: Update implementation status in this plan**

Record exact branch SHA, full pytest passed/failed/skipped count, compileall status and the fact that method execution HTTP adapter is mounted while OAuth consent/auth remains out of scope.

- [ ] **Step 7: Commit completion**

~~~bash
git add tests/integration/test_api_execution_flow.py tests/architecture/test_api_execution_boundaries.py tests/architecture/test_dependency_boundaries.py tests/architecture/test_no_optional_result_contracts.py docs/superpowers/plans/2026-09-19-api-execution-core.md AGENTS.md
git commit -m "test: verify api execution vertical flow"
~~~

## Verification Checklist

Before integration, all of the following must be evidenced on the feature-branch tip:

- compileall succeeds for src and tests;
- full pytest suite has zero failures;
- every new application/api_execution file is classified under entities, vo, services or composites;
- application API execution contains no FastAPI/Starlette/SQLAlchemy/compatibility import;
- method registry contains no dynamic import/class-name discovery;
- POST-vs-GET access_token precedence matches waRequest::request behavior;
- bearer stripping is case-insensitive and raw invalid tokens are never logged;
- authorization short-circuit order matches Webasyst 4.2.0;
- exact >30-second activity threshold is covered;
- query/form source distinction and PHP-falsy required semantics are covered;
- JSON _element removal, XML list metadata and JSONP legacy status behavior are covered;
- /api.php/auth and other reserved endpoints are not dispatched as application methods;
- production main mounts the method-execution API adapter without mounting the unrelated legacy catch-all.
