from gomazon_webasyst.contracts.api_execution import ApiError


class LegacyApiErrorMapper:
    def payload(self, error: ApiError) -> dict[str, object]:
        payload: dict[str, object] = {"error": error.code.value}
        for key, value in error.details.items():
            if key not in {"error", "error_description"} and not key.startswith("_"):
                payload[key] = value
        if error.description:
            payload["error_description"] = error.description
        return payload
