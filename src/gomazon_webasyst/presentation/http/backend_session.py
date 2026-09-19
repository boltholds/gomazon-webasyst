from fastapi import Request
from starlette.responses import Response

from gomazon_webasyst.compatibility.webasyst.auth_http.composites.cookies import (
    BackendAuthCookieMutations,
    DeletePersistentCookie,
    DeleteSessionCookie,
    KeepPersistentCookie,
    KeepSessionCookie,
    SetPersistentCookie,
    SetSessionCookie,
)
from gomazon_webasyst.compatibility.webasyst.auth_http.composites.request import (
    BackendAuthHttpCredentialState,
)
from gomazon_webasyst.composition.backend_session_bridge import (
    BackendSessionBridgeComponents,
)


def normalize_backend_auth_request(
    request: Request,
    components: BackendSessionBridgeComponents,
) -> BackendAuthHttpCredentialState:
    user_agent = (
        request.headers["user-agent"]
        if "user-agent" in request.headers
        else ""
    )
    return components.credential_extractor.extract(
        cookies=request.cookies,
        user_agent=user_agent,
        policy=components.cookie_policy,
    )


def apply_backend_auth_cookie_mutations(
    response: Response,
    mutations: BackendAuthCookieMutations,
    policy,
) -> None:
    session = mutations.session
    if isinstance(session, SetSessionCookie):
        response.set_cookie(
            key=policy.session_name.value,
            value=session.value,
            path=policy.path,
            secure=policy.secure,
            httponly=True,
            samesite=policy.same_site.value,
        )
    elif isinstance(session, DeleteSessionCookie):
        response.delete_cookie(
            key=policy.session_name.value,
            path=policy.path,
            secure=policy.secure,
            httponly=True,
            samesite=policy.same_site.value,
        )
    elif not isinstance(session, KeepSessionCookie):
        raise AssertionError("unsupported session cookie mutation")

    persistent = mutations.persistent
    if isinstance(persistent, SetPersistentCookie):
        response.set_cookie(
            key=policy.persistent_name.value,
            value=persistent.value,
            max_age=persistent.max_age_seconds,
            expires=persistent.expires_at,
            path=policy.path,
            secure=policy.secure,
            httponly=True,
            samesite=policy.same_site.value,
        )
    elif isinstance(persistent, DeletePersistentCookie):
        response.delete_cookie(
            key=policy.persistent_name.value,
            path=policy.path,
            secure=policy.secure,
            httponly=True,
            samesite=policy.same_site.value,
        )
    elif not isinstance(persistent, KeepPersistentCookie):
        raise AssertionError("unsupported persistent cookie mutation")
