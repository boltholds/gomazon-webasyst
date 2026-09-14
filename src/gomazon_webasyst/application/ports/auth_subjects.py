from typing import Protocol

from gomazon_webasyst.contracts.auth import SubjectResolution


class AuthSubjectStore(Protocol):
    async def get(self, subject_id: int) -> SubjectResolution: ...
