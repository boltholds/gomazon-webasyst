from gomazon_webasyst.application.access_values import AppId, RightName
from gomazon_webasyst.application.ports.access_semantics import (
    AppClassification,
    GlobalControlApp,
    RegularApp,
    RightFallbackAvailable,
    RightFallbackDecision,
    RightFallbackUnavailable,
)


_GLOBAL_CONTROL_APP = AppId("webasyst")


class WebasystAccessSemantics:
    def global_control_app(self) -> GlobalControlApp:
        return GlobalControlApp(_GLOBAL_CONTROL_APP)

    def classify_app(self, app_id: AppId) -> AppClassification:
        if app_id == _GLOBAL_CONTROL_APP:
            return GlobalControlApp(app_id)
        return RegularApp(app_id)


class ExactThenLegacyAllFallback:
    def fallback(self, name: RightName) -> RightFallbackDecision:
        if "." not in name.value:
            return RightFallbackUnavailable()
        prefix, _ = name.value.rsplit(".", 1)
        return RightFallbackAvailable(RightName(f"{prefix}.all"))
