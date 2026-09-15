from dataclasses import dataclass

from gomazon_webasyst.application.access_values import (
    AccessTarget,
    GroupId,
    GroupTarget,
    GuestsTarget,
    UserTarget,
)


@dataclass(slots=True, frozen=True)
class LegacyPrincipalId:
    value: int


class WebasystPrincipalCodec:
    def encode(self, target: AccessTarget) -> LegacyPrincipalId:
        if isinstance(target, UserTarget):
            return LegacyPrincipalId(-target.contact_id)
        if isinstance(target, GroupTarget):
            return LegacyPrincipalId(target.group_id.value)
        return LegacyPrincipalId(0)

    def decode(self, principal_id: LegacyPrincipalId) -> AccessTarget:
        if principal_id.value < 0:
            return UserTarget(-principal_id.value)
        if principal_id.value > 0:
            return GroupTarget(GroupId(principal_id.value))
        return GuestsTarget()
