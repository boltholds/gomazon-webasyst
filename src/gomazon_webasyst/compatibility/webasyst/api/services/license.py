from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.ports.app_license import AppLicenseDecision, AppLicenseGranted


class AllowAllAppLicensePolicy:
    async def check(self, app_id: AppId) -> AppLicenseDecision:
        return AppLicenseGranted(app_id=app_id)
