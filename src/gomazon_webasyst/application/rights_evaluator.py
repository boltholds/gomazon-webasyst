from gomazon_webasyst.application.access_values import AppId, PermissionKey, RightName
from gomazon_webasyst.application.ports.access_semantics import (
    AccessSemantics,
    GlobalControlApp,
    RightFallbackAvailable,
    RightFallbackPolicy,
)
from gomazon_webasyst.application.ports.rights import (
    AppAccessAssignment,
    GlobalAccessAssignment,
    NamedRightAssignment,
    RightsSnapshot,
)
from gomazon_webasyst.contracts.access_control import (
    AppAccess,
    EffectiveRight,
    FiniteRight,
    FullAppAccess,
    GlobalAdminAccess,
    LimitedAppAccess,
    NoAppAccess,
    UnlimitedRight,
)
from gomazon_webasyst.contracts.enums import UnlimitedRightReason


class RightsEvaluator:
    def __init__(
        self,
        *,
        app_semantics: AccessSemantics,
        fallback_policy: RightFallbackPolicy,
    ) -> None:
        self._app_semantics = app_semantics
        self._fallback_policy = fallback_policy

    def app_access(self, snapshot: RightsSnapshot, app_id: AppId) -> AppAccess:
        classification = self._app_semantics.classify_app(app_id)
        global_value = self._global_value(snapshot)

        if isinstance(classification, GlobalControlApp):
            if global_value > 0:
                return GlobalAdminAccess(app_id=app_id.value)
            return NoAppAccess(app_id=app_id.value)

        if global_value > 0:
            return GlobalAdminAccess(app_id=app_id.value)

        app_value = self._app_value(snapshot, app_id)
        if app_value >= 2:
            return FullAppAccess(app_id=app_id.value)
        if app_value == 1:
            return LimitedAppAccess(app_id=app_id.value)
        return NoAppAccess(app_id=app_id.value)

    def effective_right(
        self,
        snapshot: RightsSnapshot,
        key: PermissionKey,
    ) -> EffectiveRight:
        classification = self._app_semantics.classify_app(key.app_id)
        global_value = self._global_value(snapshot)

        if not isinstance(classification, GlobalControlApp) and global_value > 0:
            return UnlimitedRight(reason=UnlimitedRightReason.GLOBAL_ADMIN)

        app_value = (
            global_value
            if isinstance(classification, GlobalControlApp)
            else self._app_value(snapshot, key.app_id)
        )
        if app_value >= 2:
            return UnlimitedRight(reason=UnlimitedRightReason.APP_FULL_ACCESS)
        if app_value <= 0:
            return FiniteRight(value=0)

        exact = self._named_value(snapshot, key)
        if exact != 0:
            return FiniteRight(value=exact)

        fallback = self._fallback_policy.fallback(key.name)
        if isinstance(fallback, RightFallbackAvailable):
            fallback_key = PermissionKey(key.app_id, fallback.name)
            return FiniteRight(value=self._named_value(snapshot, fallback_key))
        return FiniteRight(value=0)

    def effective_named_rights(
        self,
        snapshot: RightsSnapshot,
        app_id: AppId,
    ) -> dict[str, int]:
        values: dict[str, int] = {}
        for assignment in snapshot.assignments:
            if not isinstance(assignment, NamedRightAssignment):
                continue
            if assignment.key.app_id != app_id:
                continue
            current = values.get(assignment.key.name.value, assignment.value.value)
            values[assignment.key.name.value] = max(current, assignment.value.value)
        return values

    @staticmethod
    def _global_value(snapshot: RightsSnapshot) -> int:
        values = [
            assignment.value.value
            for assignment in snapshot.assignments
            if isinstance(assignment, GlobalAccessAssignment)
        ]
        return max(values, default=0)

    @staticmethod
    def _app_value(snapshot: RightsSnapshot, app_id: AppId) -> int:
        values = [
            assignment.value.value
            for assignment in snapshot.assignments
            if isinstance(assignment, AppAccessAssignment) and assignment.app_id == app_id
        ]
        return max(values, default=0)

    @staticmethod
    def _named_value(snapshot: RightsSnapshot, key: PermissionKey) -> int:
        values = [
            assignment.value.value
            for assignment in snapshot.assignments
            if isinstance(assignment, NamedRightAssignment) and assignment.key == key
        ]
        return max(values, default=0)
