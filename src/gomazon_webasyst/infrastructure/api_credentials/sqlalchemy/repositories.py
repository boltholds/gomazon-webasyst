from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiClientId,
    ApiScope,
    AuthorizationCode,
)
from gomazon_webasyst.application.ports.api_credentials import (
    ApiTokenAlreadyMissing,
    ApiTokenCreateResult,
    ApiTokenForSubjectClientFound,
    ApiTokenForSubjectClientMissing,
    ApiTokenRevocationResult,
    ApiTokenRevoked,
    ApiTokenScopeUpdateMissing,
    ApiTokenScopeUpdateResult,
    ApiTokenScopeUpdated,
    ApiTokenStored,
    ApiTokenSubjectClientCollision,
    ApiTokenSubjectClientLookup,
    ApiTokenTouchMissing,
    ApiTokenTouchResult,
    ApiTokenTouched,
    ApiTokenValueCollision,
    AuthorizationCodeAlreadyMissing,
    AuthorizationCodeCreateCollision,
    AuthorizationCodeCreateResult,
    AuthorizationCodeDeleteResult,
    AuthorizationCodeDeleted,
    AuthorizationCodeFound,
    AuthorizationCodeMissing,
    AuthorizationCodeResolution,
    AuthorizationCodeStored,
)
from gomazon_webasyst.compatibility.webasyst.api_credentials import LegacyApiScopeCodec
from gomazon_webasyst.contracts.api_credentials import (
    ApiTokenExpiresAt,
    ApiTokenLastUsedAt,
    ApiTokenMissing,
    ApiTokenNeverExpires,
    ApiTokenNeverUsed,
    ApiTokenResolved,
    ApiTokenResolution,
    StoredApiAccessToken,
    StoredAuthorizationCode,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaApiAuthCodeRow,
    WaApiTokenRow,
)


def _authorization_code_record(
    row: WaApiAuthCodeRow,
    scope_codec: LegacyApiScopeCodec,
) -> StoredAuthorizationCode:
    return StoredAuthorizationCode(
        code=AuthorizationCode(row.code),
        contact_id=row.contact_id,
        client_id=ApiClientId(row.client_id),
        scope=scope_codec.decode(row.scope),
        expires_at=row.expires,
    )


def _api_token_record(
    row: WaApiTokenRow,
    scope_codec: LegacyApiScopeCodec,
) -> StoredApiAccessToken:
    last_use = (
        ApiTokenNeverUsed()
        if row.last_use_datetime is None
        else ApiTokenLastUsedAt(at=row.last_use_datetime)
    )
    expiry = (
        ApiTokenNeverExpires()
        if row.expires is None
        else ApiTokenExpiresAt(at=row.expires)
    )
    return StoredApiAccessToken(
        token=ApiAccessToken(row.token),
        contact_id=row.contact_id,
        client_id=ApiClientId(row.client_id),
        scope=scope_codec.decode(row.scope),
        created_at=row.create_datetime,
        last_use=last_use,
        expiry=expiry,
    )


class SQLAlchemyAuthorizationCodeRepository:
    def __init__(
        self,
        session: AsyncSession,
        scope_codec: LegacyApiScopeCodec,
    ) -> None:
        self._session = session
        self._scope_codec = scope_codec

    async def create(self, record: StoredAuthorizationCode) -> AuthorizationCodeCreateResult:
        row = WaApiAuthCodeRow(
            code=record.code.value,
            contact_id=record.contact_id,
            client_id=record.client_id.value,
            scope=self._scope_codec.encode(record.scope),
            expires=record.expires_at,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(row)
                await self._session.flush()
        except IntegrityError:
            return AuthorizationCodeCreateCollision(code=record.code)
        return AuthorizationCodeStored(record=record)

    async def resolve(self, code: AuthorizationCode) -> AuthorizationCodeResolution:
        row = await self._session.get(WaApiAuthCodeRow, code.value)
        if row is None:
            return AuthorizationCodeMissing(code=code)
        return AuthorizationCodeFound(
            record=_authorization_code_record(row, self._scope_codec)
        )

    async def delete(self, code: AuthorizationCode) -> AuthorizationCodeDeleteResult:
        row = await self._session.get(WaApiAuthCodeRow, code.value)
        if row is None:
            return AuthorizationCodeAlreadyMissing(code=code)
        await self._session.delete(row)
        await self._session.flush()
        return AuthorizationCodeDeleted(code=code)


class SQLAlchemyApiTokenRepository:
    def __init__(
        self,
        session: AsyncSession,
        scope_codec: LegacyApiScopeCodec,
    ) -> None:
        self._session = session
        self._scope_codec = scope_codec

    async def resolve(self, token: ApiAccessToken) -> ApiTokenResolution:
        row = await self._session.get(WaApiTokenRow, token.value)
        if row is None:
            return ApiTokenMissing(token=token)
        return ApiTokenResolved(record=_api_token_record(row, self._scope_codec))

    async def find_for_subject_client(
        self,
        contact_id: int,
        client_id: ApiClientId,
    ) -> ApiTokenSubjectClientLookup:
        result = await self._session.execute(
            select(WaApiTokenRow).where(
                WaApiTokenRow.contact_id == contact_id,
                WaApiTokenRow.client_id == client_id.value,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return ApiTokenForSubjectClientMissing(
                contact_id=contact_id,
                client_id=client_id,
            )
        return ApiTokenForSubjectClientFound(
            record=_api_token_record(row, self._scope_codec)
        )

    async def create(self, record: StoredApiAccessToken) -> ApiTokenCreateResult:
        row = WaApiTokenRow(
            contact_id=record.contact_id,
            client_id=record.client_id.value,
            token=record.token.value,
            scope=self._scope_codec.encode(record.scope),
            create_datetime=record.created_at,
            last_use_datetime=(
                None
                if isinstance(record.last_use, ApiTokenNeverUsed)
                else record.last_use.at
            ),
            expires=(
                None
                if isinstance(record.expiry, ApiTokenNeverExpires)
                else record.expiry.at
            ),
        )
        try:
            async with self._session.begin_nested():
                self._session.add(row)
                await self._session.flush()
        except IntegrityError as error:
            subject_client = await self.find_for_subject_client(
                record.contact_id,
                record.client_id,
            )
            if isinstance(subject_client, ApiTokenForSubjectClientFound):
                return ApiTokenSubjectClientCollision(
                    contact_id=record.contact_id,
                    client_id=record.client_id,
                )
            existing_token = await self._session.get(WaApiTokenRow, record.token.value)
            if existing_token is not None:
                return ApiTokenValueCollision(token=record.token)
            raise error
        return ApiTokenStored(record=record)

    async def update_scope(
        self,
        token: ApiAccessToken,
        scope: ApiScope,
    ) -> ApiTokenScopeUpdateResult:
        row = await self._session.get(WaApiTokenRow, token.value)
        if row is None:
            return ApiTokenScopeUpdateMissing(token=token)
        row.scope = self._scope_codec.encode(scope)
        await self._session.flush()
        return ApiTokenScopeUpdated(token=token, scope=scope)

    async def touch_last_use(
        self,
        token: ApiAccessToken,
        at: datetime,
    ) -> ApiTokenTouchResult:
        row = await self._session.get(WaApiTokenRow, token.value)
        if row is None:
            return ApiTokenTouchMissing(token=token)
        row.last_use_datetime = at
        await self._session.flush()
        return ApiTokenTouched(token=token, at=at)

    async def revoke(self, token: ApiAccessToken) -> ApiTokenRevocationResult:
        row = await self._session.get(WaApiTokenRow, token.value)
        if row is None:
            return ApiTokenAlreadyMissing(token=token)
        await self._session.delete(row)
        await self._session.flush()
        return ApiTokenRevoked(token=token)
