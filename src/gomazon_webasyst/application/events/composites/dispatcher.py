from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchReport,
    EventDispatchRequest,
    EventDispatchResult,
    EventHandlerFailureDiagnostic,
)
from gomazon_webasyst.application.events.vo.owners import EventHandlerOwner
from gomazon_webasyst.application.events.vo.payload import (
    EventHandlerNoResult,
    EventHandlerReturned,
)
from gomazon_webasyst.application.ports.event_handlers import (
    EventHandlerContext,
    EventHandlerRegistry,
)


class EventDispatcher:
    def __init__(self, registry: EventHandlerRegistry) -> None:
        self._registry = registry

    async def dispatch(
        self,
        request: EventDispatchRequest,
    ) -> EventDispatchReport:
        matched = self._registry.matching(request.event)
        closed_owners: set[EventHandlerOwner] = set()
        results: list[EventDispatchResult] = []
        failures: list[EventHandlerFailureDiagnostic] = []

        for definition in matched.definitions:
            if definition.owner in closed_owners:
                continue

            context = EventHandlerContext(
                event=request.event,
                handler_id=definition.handler_id,
            )
            try:
                outcome = await definition.handler.handle(
                    context,
                    request.payload,
                )
            except Exception as error:
                failures.append(
                    EventHandlerFailureDiagnostic(
                        handler_id=definition.handler_id,
                        owner=definition.owner,
                        error_type=type(error).__name__,
                        message=str(error),
                    )
                )
                continue

            if isinstance(outcome, EventHandlerNoResult):
                continue
            if isinstance(outcome, EventHandlerReturned):
                results.append(
                    EventDispatchResult(
                        handler_id=definition.handler_id,
                        owner=definition.owner,
                        value=outcome.value,
                    )
                )
                closed_owners.add(definition.owner)
                continue
            raise AssertionError("unsupported event handler outcome")

        return EventDispatchReport(
            event=request.event,
            results=tuple(results),
            failures=tuple(failures),
        )
