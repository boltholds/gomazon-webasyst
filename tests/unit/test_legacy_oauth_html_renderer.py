from importlib import import_module

import pytest


def _module():
    try:
        return import_module(
            "gomazon_webasyst.compatibility.webasyst.oauth.services.html_renderer"
        )
    except ModuleNotFoundError as error:
        pytest.fail(f"oauth html renderer missing: {error}")


def test_consent_renderer_escapes_client_and_app_names() -> None:
    m = _module()
    html = m.LegacyOAuthHtmlRenderer().consent(
        m.OAuthConsentPageModel(
            client_name='<img src=x onerror="boom">',
            applications=(
                m.ConsentAppView(
                    app_id="shop",
                    name="<b>Shop</b>",
                    icon="/icon.png",
                ),
            ),
            csrf_token="csrf",
            action='/api.php/auth?client_name="bad"',
        )
    )
    assert '<img src=x onerror="boom">' not in html
    assert "&lt;img" in html
    assert "&lt;b&gt;Shop&lt;/b&gt;" in html
    assert 'action="/api.php/auth?client_name=&quot;bad&quot;"' in html


def test_login_form_contains_post_csrf_credentials_and_remember_controls() -> None:
    m = _module()
    html = m.LegacyOAuthHtmlRenderer().login(
        m.OAuthLoginPageModel(
            client_name="Client",
            csrf_token="csrf-token",
            action="/api.php/auth?client_id=client",
        )
    )
    assert 'method="post"' in html
    assert 'name="_csrf"' in html
    assert 'value="csrf-token"' in html
    assert 'name="identifier"' in html
    assert 'name="password"' in html
    assert 'name="remember"' in html


def test_consent_form_has_distinct_approve_deny_and_logout_controls() -> None:
    m = _module()
    html = m.LegacyOAuthHtmlRenderer().consent(
        m.OAuthConsentPageModel(
            client_name="Client",
            applications=(
                m.ConsentAppView("shop", "Shop", "/icon.png"),
            ),
            csrf_token="csrf",
            action="/api.php/auth",
        )
    )
    assert 'name="approve"' in html
    assert 'name="deny"' in html
    assert 'name="logout"' in html


def test_code_and_error_pages_escape_values() -> None:
    m = _module()
    renderer = m.LegacyOAuthHtmlRenderer()
    code = renderer.code(m.OAuthCodePageModel(code="<code>"))
    error = renderer.error(
        m.OAuthErrorPageModel(
            error_code="<bad>",
            description='<script>alert("x")</script>',
        )
    )
    assert "<code>&lt;code&gt;</code>" in code
    assert "<code><code></code></code>" not in code
    assert "<script>" not in error
    assert "&lt;script&gt;" in error
    assert "&lt;bad&gt;" in error
