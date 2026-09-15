from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from gomazon_webasyst.application.access_values import (
    AccessTarget,
    AppId,
    PermissionKey,
    RightName,
    RightValue,
)
from gomazon_webasyst.application.ports.rights import (
    AppAccessAssignment,
    GlobalAccessAssignment,
    NamedRightAssignment,
    RightsDeleted,
    RightsPlanApplied,
    RightsSnapshot,
)
from gomazon_webasyst.application.rights_mutation_policy import (
    DeleteAllTargetRights,
    DeleteAppRights,
    DeleteExactRight,
    RightsMutationPlan,
    UpsertAppAccess,
    UpsertGlobalAccess,
    UpsertNamedRight,
)
from gomazon_webasyst.compatibility.webasyst.access_control.principals import (
    LegacyPrincipalId,
    WebasystPrincipalCodec,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaContactRightRow


_GLOBAL_APP_ID = "webasyst"
_BACKEND_RIGHT = "backend"


class SQLAlchemyRightsRepository:
    def __init__(
        self,
        session: AsyncSession,
        *,
        principal_codec: WebasystPrincipalCodec,
    ) -> None:
        self._session = session
        self._principal_codec = principal_codec

    async def load_for_targets(
        self,
        targets: tuple[AccessTarget, ...],
    ) -> RightsSnapshot:
        if not targets:
            return RightsSnapshot(())
        principal_ids = tuple(self._principal_codec.encode(target).value for target in targets)
        result = await self._session.execute(
            select(WaContactRightRow).where(WaContactRightRow.group_id.in_(principal_ids))
        )
        assignments = []
        for row in result.scalars():
            target = self._principal_codec.decode(LegacyPrincipalId(row.group_id))
            value = RightValue(row.value)
            if row.name == _BACKEND_RIGHT:
                if row.app_id == _GLOBAL_APP_ID:
                    assignments.append(GlobalAccessAssignment(target, value))
                else:
                    assignments.append(AppAccessAssignment(target, AppId(row.app_id), value))
            else:
                assignments.append(
                    NamedRightAssignment(
                        target,
                        PermissionKey(AppId(row.app_id), RightName(row.name)),
                        value,
                    )
                )
        return RightsSnapshot(tuple(assignments))

    async def execute_plan(self, plan: RightsMutationPlan) -> RightsPlanApplied:
        for operation in plan.operations:
            if isinstance(operation, DeleteAllTargetRights):
                await self._delete_all(operation.target)
            elif isinstance(operation, DeleteAppRights):
                await self._delete_app(operation.target, operation.app_id)
            elif isinstance(operation, DeleteExactRight):
                await self._delete_exact(operation.target, operation.key)
            elif isinstance(operation, UpsertGlobalAccess):
                await self._upsert(
                    operation.target,
                    AppId(_GLOBAL_APP_ID),
                    RightName(_BACKEND_RIGHT),
                    operation.value,
                )
            elif isinstance(operation, UpsertAppAccess):
                await self._upsert(
                    operation.target,
                    operation.app_id,
                    RightName(_BACKEND_RIGHT),
                    operation.value,
                )
            else:
                assert isinstance(operation, UpsertNamedRight)
                await self._upsert(
                    operation.target,
                    operation.key.app_id,
                    operation.key.name,
                    operation.value,
                )
        await self._session.flush()
        return RightsPlanApplied(operation_count=len(plan.operations))

    async def delete_all_for_target(self, target: AccessTarget) -> RightsDeleted:
        result = await self._session.execute(
            delete(WaContactRightRow).where(
                WaContactRightRow.group_id == self._principal_codec.encode(target).value
            )
        )
        await self._session.flush()
        return RightsDeleted(target=target, deleted_count=max(0, int(result.rowcount)))

    async def _delete_all(self, target: AccessTarget) -> None:
        await self._session.execute(
            delete(WaContactRightRow).where(
                WaContactRightRow.group_id == self._principal_codec.encode(target).value
            )
        )

    async def _delete_app(self, target: AccessTarget, app_id: AppId) -> None:
        await self._session.execute(
            delete(WaContactRightRow).where(
                WaContactRightRow.group_id == self._principal_codec.encode(target).value,
                WaContactRightRow.app_id == app_id.value,
            )
        )

    async def _delete_exact(self, target: AccessTarget, key: PermissionKey) -> None:
        await self._session.execute(
            delete(WaContactRightRow).where(
                WaContactRightRow.group_id == self._principal_codec.encode(target).value,
                WaContactRightRow.app_id == key.app_id.value,
                WaContactRightRow.name == key.name.value,
            )
        )

    async def _upsert(
        self,
        target: AccessTarget,
        app_id: AppId,
        name: RightName,
        value: RightValue,
    ) -> None:
        identity = {
            "group_id": self._principal_codec.encode(target).value,
            "app_id": app_id.value,
            "name": name.value,
        }
        row = await self._session.get(WaContactRightRow, identity)
        if row is None:
            self._session.add(WaContactRightRow(**identity, value=value.value))
        else:
            row.value = value.value
