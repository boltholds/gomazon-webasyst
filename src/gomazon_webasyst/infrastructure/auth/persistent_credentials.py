from gomazon_webasyst.application.persistent_values import PersistentCredential
from gomazon_webasyst.application.ports.persistent_credentials import PersistentCredentialStrategy
from gomazon_webasyst.contracts.enums import PersistentCredentialRejectReason
from gomazon_webasyst.contracts.persistent_login import (
    ClearPersistentCredential,
    PersistentCredentialRejected,
    PersistentCredentialResolution,
    PersistentCredentialResolved,
    PersistentStrategyNotApplicable,
    PersistentStrategyRejected,
    PersistentStrategyResolved,
)


class OrderedPersistentCredentialResolver:
    def __init__(self, strategies: tuple[PersistentCredentialStrategy, ...]) -> None:
        self._strategies = strategies

    async def resolve(self, credential: PersistentCredential) -> PersistentCredentialResolution:
        for strategy in self._strategies:
            result = await strategy.resolve(credential)
            if isinstance(result, PersistentStrategyNotApplicable):
                continue
            if isinstance(result, PersistentStrategyResolved):
                return PersistentCredentialResolved(
                    identity=result.identity,
                    disposition=result.disposition,
                )
            assert isinstance(result, PersistentStrategyRejected)
            return PersistentCredentialRejected(
                reason=result.reason,
                disposition=result.disposition,
            )

        return PersistentCredentialRejected(
            reason=PersistentCredentialRejectReason.UNSUPPORTED,
            disposition=ClearPersistentCredential(),
        )
