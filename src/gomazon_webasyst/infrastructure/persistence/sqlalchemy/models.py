from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, SmallInteger, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class WaContactRow(Base):
    __tablename__ = "wa_contact"
    __table_args__ = (
        Index("login", "login", unique=True),
        Index("name", "name"),
        Index("is_user", "is_user"),
        Index("is_staff", "is_staff"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    firstname: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("''"))
    middlename: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("''"))
    lastname: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("''"))
    title: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("''"))
    company: Mapped[str] = mapped_column(String(150), nullable=False, server_default=text("''"))
    jobtitle: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("''"))
    company_contact_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    is_company: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    is_user: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    is_staff: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    login: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password: Mapped[str] = mapped_column(String(128), nullable=False, server_default=text("''"))
    last_datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(1), nullable=True)
    birth_day: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    birth_month: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    birth_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    about: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    create_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    create_app_id: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("''"))
    create_method: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("''"))
    create_contact_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    locale: Mapped[str] = mapped_column(String(8), nullable=False, server_default=text("''"))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, server_default=text("''"))


class WaContactEmailRow(Base):
    __tablename__ = "wa_contact_emails"
    __table_args__ = (
        Index("wa_contact_emails_contact_sort", "contact_id", "sort", unique=True),
        Index("wa_contact_emails_email", "email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int] = mapped_column(Integer, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    ext: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("''"))
    sort: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'unknown'"))


class WaContactDataRow(Base):
    __tablename__ = "wa_contact_data"
    __table_args__ = (
        Index("wa_contact_data_contact_field_sort", "contact_id", "field", "sort", unique=True),
        Index("wa_contact_data_contact_id", "contact_id"),
        Index("wa_contact_data_value", "value"),
        Index("wa_contact_data_field", "field"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int] = mapped_column(Integer, nullable=False)
    field: Mapped[str] = mapped_column(String(32), nullable=False)
    ext: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("''"))
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    status: Mapped[str | None] = mapped_column(String(255), nullable=True)


class WaContactAuthRow(Base):
    __tablename__ = "wa_contact_auths"
    __table_args__ = (
        Index("wa_contact_auths_contact_id", "contact_id"),
        Index("wa_contact_auths_token", "token"),
        Index("wa_contact_auths_session_id", "session_id", unique=True),
        Index("wa_contact_auths_contact_session_id", "contact_id", "session_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int] = mapped_column(Integer, nullable=False)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    token: Mapped[str] = mapped_column(String(42), nullable=False)
    login_datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)


class WaContactRightRow(Base):
    __tablename__ = "wa_contact_rights"
    __table_args__ = (
        Index("wa_contact_rights_name_value", "name", "value", "group_id", "app_id"),
    )

    group_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    app_id: Mapped[str] = mapped_column(String(32), primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)


class WaGroupRow(Base):
    __tablename__ = "wa_group"
    __table_args__ = (Index("wa_group_name", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cnt: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    icon: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort: Mapped[int | None] = mapped_column(Integer, nullable=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'group'"))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class WaUserGroupRow(Base):
    __tablename__ = "wa_user_groups"

    contact_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    group_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class WaApiAuthCodeRow(Base):
    __tablename__ = "wa_api_auth_codes"

    code: Mapped[str] = mapped_column(String(32), primary_key=True, nullable=False)
    contact_id: Mapped[int] = mapped_column(Integer, nullable=False)
    client_id: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    expires: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class WaApiTokenRow(Base):
    __tablename__ = "wa_api_tokens"
    __table_args__ = (
        Index("contact_client", "contact_id", "client_id", unique=True),
    )

    contact_id: Mapped[int] = mapped_column(Integer, nullable=False)
    client_id: Mapped[str] = mapped_column(String(32), nullable=False)
    token: Mapped[str] = mapped_column(String(32), primary_key=True, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    create_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_use_datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

