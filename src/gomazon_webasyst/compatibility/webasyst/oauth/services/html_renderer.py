from dataclasses import dataclass
from html import escape


@dataclass(slots=True, frozen=True)
class ConsentAppView:
    app_id: str
    name: str
    icon: str


@dataclass(slots=True, frozen=True)
class OAuthLoginPageModel:
    client_name: str
    csrf_token: str
    action: str


@dataclass(slots=True, frozen=True)
class OAuthConsentPageModel:
    client_name: str
    applications: tuple[ConsentAppView, ...]
    csrf_token: str
    action: str


@dataclass(slots=True, frozen=True)
class OAuthCodePageModel:
    code: str


@dataclass(slots=True, frozen=True)
class OAuthErrorPageModel:
    error_code: str
    description: str


class LegacyOAuthHtmlRenderer:
    @staticmethod
    def login(model: OAuthLoginPageModel) -> str:
        action = escape(model.action, quote=True)
        client = escape(model.client_name, quote=True)
        csrf = escape(model.csrf_token, quote=True)
        return (
            "<!doctype html><html><head><meta charset=\"utf-8\">"
            "<title>Authorization</title></head><body>"
            f"<h1>{client}</h1>"
            f"<form method=\"post\" action=\"{action}\">"
            f"<input type=\"hidden\" name=\"_csrf\" value=\"{csrf}\">"
            "<label>Login <input name=\"identifier\" autocomplete=\"username\"></label>"
            "<label>Password <input type=\"password\" name=\"password\" "
            "autocomplete=\"current-password\"></label>"
            "<label><input type=\"checkbox\" name=\"remember\" value=\"1\">"
            " Remember me</label>"
            "<button type=\"submit\" name=\"login\" value=\"1\">Login</button>"
            "</form></body></html>"
        )

    @staticmethod
    def consent(model: OAuthConsentPageModel) -> str:
        action = escape(model.action, quote=True)
        client = escape(model.client_name, quote=True)
        csrf = escape(model.csrf_token, quote=True)
        app_items = "".join(
            "<li>"
            f"<img src=\"{escape(app.icon, quote=True)}\" alt=\"\">"
            f"<span>{escape(app.name, quote=True)}</span>"
            "</li>"
            for app in model.applications
        )
        return (
            "<!doctype html><html><head><meta charset=\"utf-8\">"
            "<title>Authorization</title></head><body>"
            f"<h1>{client}</h1><ul>{app_items}</ul>"
            f"<form method=\"post\" action=\"{action}\">"
            f"<input type=\"hidden\" name=\"_csrf\" value=\"{csrf}\">"
            "<button type=\"submit\" name=\"approve\" value=\"1\">Approve</button>"
            "<button type=\"submit\" name=\"deny\" value=\"1\">Deny</button>"
            "<button type=\"submit\" name=\"logout\" value=\"1\">Logout</button>"
            "</form></body></html>"
        )

    @staticmethod
    def code(model: OAuthCodePageModel) -> str:
        return (
            "<!doctype html><html><head><meta charset=\"utf-8\">"
            "<title>Authorization code</title></head><body>"
            f"<code>{escape(model.code, quote=True)}</code>"
            "</body></html>"
        )

    @staticmethod
    def error(model: OAuthErrorPageModel) -> str:
        return (
            "<!doctype html><html><head><meta charset=\"utf-8\">"
            "<title>Authorization error</title></head><body>"
            f"<h1>{escape(model.error_code, quote=True)}</h1>"
            f"<p>{escape(model.description, quote=True)}</p>"
            "</body></html>"
        )
