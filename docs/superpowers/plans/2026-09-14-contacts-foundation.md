# Contacts Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working Python vertical slice for Webasyst contacts, proving Pydantic contracts, DI, application-owned persistence ports, SQLAlchemy infrastructure, and FastAPI wiring without claiming legacy contact API parity.

**Architecture:** The first slice targets the legacy `wa_contact` base table only. `wa_contact_emails`, `wa_contact_data`, and `wa_contact_data_text` remain separate follow-up compatibility slices so profile CRUD, authentication, email state, and arbitrary custom fields are not coupled prematurely. Application code depends only on Pydantic contracts and `Protocol` ports; SQLAlchemy remains infrastructure-private and is selected at the composition root.

**Tech Stack:** Python 3.12+, FastAPI/Starlette, Pydantic v2, pydantic-settings, SQLAlchemy 2.x async ORM, `asyncmy` for MySQL/MariaDB, `aiosqlite` for fast persistence-contract tests, pytest, pytest-asyncio, httpx.

**Spec:** `docs/superpowers/specs/2026-09-14-webasyst-python-rewrite-design.md`

## Global Constraints

- Python version: `>=3.12`.
- Pydantic major version: `>=2,<3`.
- SQLAlchemy major version: `>=2,<3`.
- FastAPI is presentation-only; application and contracts packages must not import FastAPI.
- SQLAlchemy and DB-driver types must not cross out of `infrastructure.persistence.sqlalchemy`.
- Persistence must be replaceable through constructor/composition-root DI.
- Pydantic v2 models are the data contracts crossing presentation/application and application/persistence boundaries.
- Existing Webasyst data is preserved; no destructive schema redesign is part of this slice.
- This slice maps the legacy `wa_contact` table and deliberately excludes `wa_contact_emails`, `wa_contact_data`, `wa_contact_data_text`, auth sessions, passwords, permissions, and OAuth behavior from the public application contract.
- No Webasyst compatibility claim is made until separate characterization tests exist.

---

## File Structure Locked by This Plan

```text
pyproject.toml
src/
  gomazon_webasyst/
    __init__.py
    main.py
    composition/
      __init__.py
      settings.py
      container.py
    contracts/
      __init__.py
      contacts.py
    application/
      __init__.py
      errors.py
      contacts.py
      ports/
        __init__.py
        contacts.py
        unit_of_work.py
    infrastructure/
      __init__.py
      persistence/
        __init__.py
        sqlalchemy/
          __init__.py
          base.py
          models.py
          mappings.py
          repositories.py
          unit_of_work.py
          factory.py
    presentation/
      __init__.py
      http/
        __init__.py
        dependencies.py
        contacts.py
        errors.py

tests/
  architecture/
    test_dependency_boundaries.py
  unit/
    test_contact_contracts.py
    test_contact_use_cases.py
  persistence_contracts/
    test_contacts_repository.py
  integration/
    test_sqlalchemy_contact_repository.py
    test_http_contacts.py

AGENTS.md
```

Each file has one responsibility: contracts define typed data, application files define use cases and ports, infrastructure files implement persistence, presentation files translate HTTP, and composition files wire concrete implementations.

---

### Task 1: Project bootstrap, settings, and architecture guards

**Files:**
- Create: `pyproject.toml`
- Create: `src/gomazon_webasyst/__init__.py`
- Create: `src/gomazon_webasyst/composition/__init__.py`
- Create: `src/gomazon_webasyst/composition/settings.py`
- Create: `tests/architecture/test_dependency_boundaries.py`
- Modify: `AGENTS.md`

**Interfaces:**
- Produces: `Settings(database_backend: Literal["sqlalchemy"], database_url: str, app_name: str)`.
- Produces: repository-wide import guard that prevents `fastapi`/`sqlalchemy` imports in contracts/application.
- Records: async persistence and `wa_contact`-only first-slice scope in `AGENTS.md`.

- [ ] **Step 1: Add packaging and runtime dependencies**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "gomazon-webasyst"
version = "0.1.0"
description = "Python rewrite of the Webasyst-backed Gomazon service"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "pydantic>=2,<3",
  "pydantic-settings>=2,<3",
  "sqlalchemy>=2,<3",
  "asyncmy>=0.2",
  "uvicorn[standard]>=0.30",
]

[project.optional-dependencies]
dev = [
  "aiosqlite>=0.20",
  "httpx>=0.27",
  "pytest>=8",
  "pytest-asyncio>=0.24",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
addopts = "-ra"
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Write settings tests first**

Create `tests/unit/test_settings.py`:

```python
from gomazon_webasyst.composition.settings import Settings


def test_settings_default_to_sqlalchemy() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert settings.database_backend == "sqlalchemy"


def test_settings_accept_mysql_async_url() -> None:
    settings = Settings(database_url="mysql+asyncmy://user:pass@db/webasyst")
    assert settings.database_url.startswith("mysql+asyncmy://")
```

Run:

```bash
python -m pytest tests/unit/test_settings.py -v
```

Expected result: FAIL because `composition.settings` does not exist.

- [ ] **Step 3: Implement settings**

Create `src/gomazon_webasyst/composition/settings.py`:

```python
from typing import Literal

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_prefix="GOMAZON_", extra="ignore")

    app_name: str = "gomazon-webasyst"
    database_backend: Literal["sqlalchemy"] = "sqlalchemy"
    database_url: str
```

Create empty `__init__.py` files for the package and `composition` package.

Run:

```bash
python -m pytest tests/unit/test_settings.py -v
```

Expected result: PASS.

- [ ] **Step 4: Add dependency-boundary test**

Create `tests/architecture/test_dependency_boundaries.py`:

```python
import ast
from pathlib import Path


ROOT = Path("src/gomazon_webasyst")
CHECK_DIRS = [ROOT / "contracts", ROOT / "application"]
FORBIDDEN = {"fastapi", "sqlalchemy"}


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module.split(".", 1)[0])
    return result


def test_application_and_contracts_do_not_import_framework_infrastructure() -> None:
    violations: list[str] = []
    for directory in CHECK_DIRS:
        if not directory.exists():
            continue
        for path in directory.rglob("*.py"):
            bad = imported_roots(path) & FORBIDDEN
            if bad:
                violations.append(f"{path}: {sorted(bad)}")
    assert violations == []
```

Run:

```bash
python -m pytest tests/architecture/test_dependency_boundaries.py -v
```

Expected result: PASS.

- [ ] **Step 5: Record implementation-level architecture in `AGENTS.md`**

Append two accepted ADRs:

```markdown
### ADR-012 — First contact slice maps only `wa_contact`
Status: accepted
Date: 2026-09-14

The first contacts vertical slice maps only the base legacy `wa_contact` table.
`wa_contact_emails`, `wa_contact_data`, and `wa_contact_data_text` are separate later slices.
Authentication fields such as password/session/token behavior are not exposed through the first contact application contract.

### ADR-013 — Initial relational persistence path is async
Status: accepted
Date: 2026-09-14

The first SQLAlchemy adapter uses `AsyncEngine`, `AsyncSession`, async repositories, and an async Unit of Work.
MySQL/MariaDB uses the `asyncmy` driver. Fast persistence-contract tests use `aiosqlite` without changing application code.
Async SQLAlchemy primitives remain infrastructure-private.
```

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/gomazon_webasyst tests/architecture tests/unit/test_settings.py AGENTS.md
git commit -m "chore: bootstrap python rewrite foundation"
```

---

### Task 2: Define contact Pydantic contracts

**Files:**
- Create: `src/gomazon_webasyst/contracts/__init__.py`
- Create: `src/gomazon_webasyst/contracts/contacts.py`
- Create: `tests/unit/test_contact_contracts.py`

**Interfaces:**
- Produces: `ContactId`, `ContactCreate`, `ContactUpdate`, `ContactRead`.
- Excludes: email, phone, password, login/session behavior, arbitrary `wa_contact_data` fields.

- [ ] **Step 1: Write contract tests**

Create `tests/unit/test_contact_contracts.py`:

```python
from datetime import datetime

import pytest
from pydantic import ValidationError

from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate


def test_contact_create_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ContactCreate(name="Alice", email="alice@example.com")


def test_contact_create_accepts_legacy_profile_columns() -> None:
    contact = ContactCreate(
        name="Alice Example",
        firstname="Alice",
        lastname="Example",
        company="Example Ltd",
        locale="en_US",
        timezone="Europe/Amsterdam",
    )
    assert contact.firstname == "Alice"
    assert contact.is_company is False


def test_contact_update_rejects_empty_patch() -> None:
    with pytest.raises(ValidationError):
        ContactUpdate()


def test_contact_read_is_frozen() -> None:
    contact = ContactRead(
        id=1,
        name="Alice",
        firstname="Alice",
        create_datetime=datetime(2026, 9, 14, 12, 0, 0),
    )
    with pytest.raises(ValidationError):
        contact.name = "Changed"
```

Run:

```bash
python -m pytest tests/unit/test_contact_contracts.py -v
```

Expected result: FAIL because contact contracts do not exist.

- [ ] **Step 2: Implement the contracts**

Create `src/gomazon_webasyst/contracts/contacts.py`:

```python
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


ContactId = Annotated[int, Field(gt=0)]


class ContactCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=150)]
    firstname: Annotated[str, Field(max_length=50)] = ""
    middlename: Annotated[str, Field(max_length=50)] = ""
    lastname: Annotated[str, Field(max_length=50)] = ""
    title: Annotated[str, Field(max_length=50)] = ""
    company: Annotated[str, Field(max_length=150)] = ""
    jobtitle: Annotated[str, Field(max_length=50)] = ""
    company_contact_id: int = 0
    is_company: bool = False
    locale: Annotated[str, Field(max_length=8)] = ""
    timezone: Annotated[str, Field(max_length=64)] = ""


class ContactUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=150)] | None = None
    firstname: Annotated[str, Field(max_length=50)] | None = None
    middlename: Annotated[str, Field(max_length=50)] | None = None
    lastname: Annotated[str, Field(max_length=50)] | None = None
    title: Annotated[str, Field(max_length=50)] | None = None
    company: Annotated[str, Field(max_length=150)] | None = None
    jobtitle: Annotated[str, Field(max_length=50)] | None = None
    company_contact_id: int | None = None
    is_company: bool | None = None
    locale: Annotated[str, Field(max_length=8)] | None = None
    timezone: Annotated[str, Field(max_length=64)] | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "ContactUpdate":
        if not self.model_fields_set:
            raise ValueError("contact update must contain at least one field")
        return self


class ContactRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: ContactId
    name: str
    firstname: str = ""
    middlename: str = ""
    lastname: str = ""
    title: str = ""
    company: str = ""
    jobtitle: str = ""
    company_contact_id: int = 0
    is_company: bool = False
    locale: str = ""
    timezone: str = ""
    create_datetime: datetime
```

Create `src/gomazon_webasyst/contracts/__init__.py` exporting those four names.

Run:

```bash
python -m pytest tests/unit/test_contact_contracts.py tests/architecture/test_dependency_boundaries.py -v
```

Expected result: PASS.

- [ ] **Step 3: Commit**

```bash
git add src/gomazon_webasyst/contracts tests/unit/test_contact_contracts.py
git commit -m "feat: define contact pydantic contracts"
```

---

### Task 3: Add application ports, typed errors, and contact use cases

**Files:**
- Create: `src/gomazon_webasyst/application/__init__.py`
- Create: `src/gomazon_webasyst/application/errors.py`
- Create: `src/gomazon_webasyst/application/contacts.py`
- Create: `src/gomazon_webasyst/application/ports/__init__.py`
- Create: `src/gomazon_webasyst/application/ports/contacts.py`
- Create: `src/gomazon_webasyst/application/ports/unit_of_work.py`
- Create: `tests/unit/test_contact_use_cases.py`

**Interfaces:**
- Produces: `ContactRepository.get/create/update` async protocol.
- Produces: `UnitOfWork` async context manager and `UnitOfWorkFactory` callable protocol.
- Produces: `GetContact`, `CreateContact`, `UpdateContact` use cases.
- Produces: `ContactNotFound(contact_id)`.

- [ ] **Step 1: Define failing use-case tests with fakes**

Create `tests/unit/test_contact_use_cases.py` containing in-memory fakes and these assertions:

```python
from datetime import datetime

import pytest

from gomazon_webasyst.application.contacts import CreateContact, GetContact, UpdateContact
from gomazon_webasyst.application.errors import ContactNotFound
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate


NOW = datetime(2026, 9, 14, 12, 0, 0)


class FakeContactRepository:
    def __init__(self) -> None:
        self.items: dict[int, ContactRead] = {}
        self.next_id = 1

    async def get(self, contact_id: int) -> ContactRead | None:
        return self.items.get(contact_id)

    async def create(self, data: ContactCreate) -> ContactRead:
        contact = ContactRead(id=self.next_id, create_datetime=NOW, **data.model_dump())
        self.items[contact.id] = contact
        self.next_id += 1
        return contact

    async def update(self, contact_id: int, data: ContactUpdate) -> ContactRead | None:
        current = self.items.get(contact_id)
        if current is None:
            return None
        values = current.model_dump()
        values.update(data.model_dump(exclude_unset=True))
        updated = ContactRead(**values)
        self.items[contact_id] = updated
        return updated


class FakeUnitOfWork:
    def __init__(self, contacts: FakeContactRepository) -> None:
        self.contacts = contacts
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeUnitOfWorkFactory:
    def __init__(self, uow: FakeUnitOfWork) -> None:
        self.uow = uow

    def __call__(self) -> FakeUnitOfWork:
        return self.uow


@pytest.mark.asyncio
async def test_create_contact_commits() -> None:
    repo = FakeContactRepository()
    uow = FakeUnitOfWork(repo)
    result = await CreateContact(FakeUnitOfWorkFactory(uow)).execute(ContactCreate(name="Alice"))
    assert result.id == 1
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_get_missing_contact_raises_typed_error() -> None:
    uow = FakeUnitOfWork(FakeContactRepository())
    with pytest.raises(ContactNotFound):
        await GetContact(FakeUnitOfWorkFactory(uow)).execute(42)


@pytest.mark.asyncio
async def test_update_contact_commits_changed_value() -> None:
    repo = FakeContactRepository()
    existing = await repo.create(ContactCreate(name="Before"))
    uow = FakeUnitOfWork(repo)
    result = await UpdateContact(FakeUnitOfWorkFactory(uow)).execute(existing.id, ContactUpdate(name="After"))
    assert result.name == "After"
    assert uow.commits == 1
```

Run:

```bash
python -m pytest tests/unit/test_contact_use_cases.py -v
```

Expected result: FAIL because the application ports and use cases do not exist.

- [ ] **Step 2: Implement repository port**

Create `src/gomazon_webasyst/application/ports/contacts.py`:

```python
from typing import Protocol

from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate


class ContactRepository(Protocol):
    async def get(self, contact_id: int) -> ContactRead | None: ...
    async def create(self, data: ContactCreate) -> ContactRead: ...
    async def update(self, contact_id: int, data: ContactUpdate) -> ContactRead | None: ...
```

- [ ] **Step 3: Implement Unit of Work port**

Create `src/gomazon_webasyst/application/ports/unit_of_work.py`:

```python
from types import TracebackType
from typing import Protocol, Self

from gomazon_webasyst.application.ports.contacts import ContactRepository


class UnitOfWork(Protocol):
    contacts: ContactRepository

    async def __aenter__(self) -> Self: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...
```

- [ ] **Step 4: Implement typed application error**

Create `src/gomazon_webasyst/application/errors.py`:

```python
class ContactNotFound(LookupError):
    def __init__(self, contact_id: int) -> None:
        self.contact_id = contact_id
        super().__init__(f"contact {contact_id} not found")
```

- [ ] **Step 5: Implement use cases**

Create `src/gomazon_webasyst/application/contacts.py`:

```python
from gomazon_webasyst.application.errors import ContactNotFound
from gomazon_webasyst.application.ports.unit_of_work import UnitOfWorkFactory
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate


class GetContact:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, contact_id: int) -> ContactRead:
        async with self._uow_factory() as uow:
            contact = await uow.contacts.get(contact_id)
        if contact is None:
            raise ContactNotFound(contact_id)
        return contact


class CreateContact:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, data: ContactCreate) -> ContactRead:
        async with self._uow_factory() as uow:
            contact = await uow.contacts.create(data)
            await uow.commit()
            return contact


class UpdateContact:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, contact_id: int, data: ContactUpdate) -> ContactRead:
        async with self._uow_factory() as uow:
            contact = await uow.contacts.update(contact_id, data)
            if contact is None:
                raise ContactNotFound(contact_id)
            await uow.commit()
            return contact
```

Run:

```bash
python -m pytest tests/unit/test_contact_use_cases.py tests/architecture/test_dependency_boundaries.py -v
```

Expected result: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/gomazon_webasyst/application tests/unit/test_contact_use_cases.py
git commit -m "feat: add contact application ports and use cases"
```

---

### Task 4: Implement SQLAlchemy mapping, repository, and Unit of Work

**Files:**
- Create: `src/gomazon_webasyst/infrastructure/__init__.py`
- Create: `src/gomazon_webasyst/infrastructure/persistence/__init__.py`
- Create: `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/__init__.py`
- Create: `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/base.py`
- Create: `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/models.py`
- Create: `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/mappings.py`
- Create: `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/repositories.py`
- Create: `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/unit_of_work.py`
- Create: `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/factory.py`
- Create: `tests/persistence_contracts/test_contacts_repository.py`
- Create: `tests/integration/test_sqlalchemy_contact_repository.py`

**Interfaces:**
- Consumes: `ContactRepository`, `UnitOfWorkFactory`, contact Pydantic contracts.
- Produces: `SQLAlchemyContactRepository`, `SQLAlchemyUnitOfWork`, `SQLAlchemyUnitOfWorkFactory`, `create_engine(settings)`.
- Maps: legacy base table `wa_contact` with its actual core columns and defaults.

- [ ] **Step 1: Add a reusable persistence contract test**

Create `tests/persistence_contracts/test_contacts_repository.py` with an async helper that every adapter can call:

```python
from gomazon_webasyst.application.ports.contacts import ContactRepository
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactUpdate


async def assert_contact_repository_contract(repo: ContactRepository) -> None:
    created = await repo.create(ContactCreate(name="Alice", firstname="Alice"))
    assert created.id > 0
    assert created.name == "Alice"

    loaded = await repo.get(created.id)
    assert loaded == created

    updated = await repo.update(created.id, ContactUpdate(company="Example Ltd"))
    assert updated is not None
    assert updated.company == "Example Ltd"

    missing = await repo.get(999_999)
    assert missing is None
```

- [ ] **Step 2: Write failing SQLAlchemy integration test**

Create `tests/integration/test_sqlalchemy_contact_repository.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.repositories import SQLAlchemyContactRepository
from tests.persistence_contracts.test_contacts_repository import assert_contact_repository_contract


@pytest.mark.asyncio
async def test_sqlalchemy_contact_repository_satisfies_contract() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        repo = SQLAlchemyContactRepository(session)
        await assert_contact_repository_contract(repo)
        await session.commit()

    await engine.dispose()
```

Run:

```bash
python -m pytest tests/integration/test_sqlalchemy_contact_repository.py -v
```

Expected result: FAIL because SQLAlchemy infrastructure does not exist.

- [ ] **Step 3: Implement declarative base and full `wa_contact` row mapping**

Create `base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

Create `models.py` with table name `wa_contact` and these legacy columns:

```python
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, SmallInteger, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class WaContactRow(Base):
    __tablename__ = "wa_contact"
    __table_args__ = (
        Index("ix_wa_contact_name", "name"),
        Index("ix_wa_contact_is_user", "is_user"),
        Index("ix_wa_contact_is_staff", "is_staff"),
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
    login: Mapped[str | None] = mapped_column(String(32), unique=True)
    password: Mapped[str] = mapped_column(String(128), nullable=False, server_default=text("''"))
    last_datetime: Mapped[datetime | None] = mapped_column(DateTime)
    sex: Mapped[str | None] = mapped_column(String(1))
    birth_day: Mapped[int | None] = mapped_column(SmallInteger)
    birth_month: Mapped[int | None] = mapped_column(SmallInteger)
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)
    about: Mapped[str | None] = mapped_column(Text)
    photo: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    create_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    create_app_id: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("''"))
    create_method: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("''"))
    create_contact_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    locale: Mapped[str] = mapped_column(String(8), nullable=False, server_default=text("''"))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, server_default=text("''"))
```

- [ ] **Step 4: Implement ORM-to-Pydantic mapper**

Create `mappings.py`:

```python
from gomazon_webasyst.contracts.contacts import ContactRead

from .models import WaContactRow


def contact_row_to_read(row: WaContactRow) -> ContactRead:
    return ContactRead(
        id=row.id,
        name=row.name,
        firstname=row.firstname,
        middlename=row.middlename,
        lastname=row.lastname,
        title=row.title,
        company=row.company,
        jobtitle=row.jobtitle,
        company_contact_id=row.company_contact_id,
        is_company=bool(row.is_company),
        locale=row.locale,
        timezone=row.timezone,
        create_datetime=row.create_datetime,
    )
```

- [ ] **Step 5: Implement repository**

Create `repositories.py`:

```python
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate

from .mappings import contact_row_to_read
from .models import WaContactRow


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SQLAlchemyContactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, contact_id: int) -> ContactRead | None:
        row = await self._session.get(WaContactRow, contact_id)
        return None if row is None else contact_row_to_read(row)

    async def create(self, data: ContactCreate) -> ContactRead:
        row = WaContactRow(
            **data.model_dump(exclude={"is_company"}),
            is_company=int(data.is_company),
            create_datetime=utc_now_naive(),
        )
        self._session.add(row)
        await self._session.flush()
        return contact_row_to_read(row)

    async def update(self, contact_id: int, data: ContactUpdate) -> ContactRead | None:
        row = await self._session.get(WaContactRow, contact_id)
        if row is None:
            return None
        changes = data.model_dump(exclude_unset=True)
        if "is_company" in changes:
            changes["is_company"] = int(changes["is_company"])
        for name, value in changes.items():
            setattr(row, name, value)
        await self._session.flush()
        return contact_row_to_read(row)
```

- [ ] **Step 6: Implement Unit of Work and engine factory**

Create `unit_of_work.py`:

```python
from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .repositories import SQLAlchemyContactRepository


class SQLAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.contacts: SQLAlchemyContactRepository

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self._session = self._session_factory()
        self.contacts = SQLAlchemyContactRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        if exc is not None:
            await self._session.rollback()
        await self._session.close()

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None
        await self._session.rollback()


class SQLAlchemyUnitOfWorkFactory:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def __call__(self) -> SQLAlchemyUnitOfWork:
        return SQLAlchemyUnitOfWork(self._session_factory)
```

Create `factory.py`:

```python
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from gomazon_webasyst.composition.settings import Settings

from .unit_of_work import SQLAlchemyUnitOfWorkFactory


def create_engine(settings: Settings) -> AsyncEngine:
    if settings.database_backend != "sqlalchemy":
        raise ValueError(f"unsupported database backend: {settings.database_backend}")
    return create_async_engine(settings.database_url, pool_pre_ping=True)


def create_uow_factory(engine: AsyncEngine) -> SQLAlchemyUnitOfWorkFactory:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return SQLAlchemyUnitOfWorkFactory(session_factory)
```

Run:

```bash
python -m pytest tests/integration/test_sqlalchemy_contact_repository.py tests/architecture/test_dependency_boundaries.py -v
```

Expected result: PASS.

- [ ] **Step 7: Add transaction integration test**

Extend `tests/integration/test_sqlalchemy_contact_repository.py` with a test that creates through `SQLAlchemyUnitOfWorkFactory`, calls `commit()`, opens a second Unit of Work, and confirms the contact is visible. Add another test that raises inside the first UoW without commit and confirms the row is absent in the second UoW.

Run:

```bash
python -m pytest tests/integration/test_sqlalchemy_contact_repository.py -v
```

Expected result: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/gomazon_webasyst/infrastructure tests/persistence_contracts tests/integration/test_sqlalchemy_contact_repository.py
git commit -m "feat: add sqlalchemy contact persistence adapter"
```

---

### Task 5: Build composition root and FastAPI contact endpoints

**Files:**
- Create: `src/gomazon_webasyst/composition/container.py`
- Create: `src/gomazon_webasyst/presentation/__init__.py`
- Create: `src/gomazon_webasyst/presentation/http/__init__.py`
- Create: `src/gomazon_webasyst/presentation/http/dependencies.py`
- Create: `src/gomazon_webasyst/presentation/http/contacts.py`
- Create: `src/gomazon_webasyst/presentation/http/errors.py`
- Create: `src/gomazon_webasyst/main.py`
- Create: `tests/integration/test_http_contacts.py`

**Interfaces:**
- Produces: `Container`, `create_container(settings)`, `create_app(settings=None)`.
- Produces native Python API routes: `POST /api/v1/contacts`, `GET /api/v1/contacts/{id}`, `PATCH /api/v1/contacts/{id}`.
- Maps `ContactNotFound` to HTTP 404 only in presentation.

- [ ] **Step 1: Write failing HTTP test**

Create `tests/integration/test_http_contacts.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.main import create_app


@pytest.mark.asyncio
async def test_missing_contact_returns_404() -> None:
    app = create_app(Settings(database_url="sqlite+aiosqlite:///:memory:"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/contacts/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "contact 999 not found"}
```

Expected initial result: FAIL because `create_app` does not exist. The final version of this test will use a temporary SQLite database whose schema is created before the request so the 404 comes from the application layer rather than a missing-table error.

- [ ] **Step 2: Implement composition root**

Create `composition/container.py`:

```python
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from gomazon_webasyst.application.contacts import CreateContact, GetContact, UpdateContact
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.factory import create_engine, create_uow_factory


@dataclass(slots=True)
class Container:
    settings: Settings
    engine: AsyncEngine
    get_contact: GetContact
    create_contact: CreateContact
    update_contact: UpdateContact

    async def close(self) -> None:
        await self.engine.dispose()


def create_container(settings: Settings) -> Container:
    engine = create_engine(settings)
    uow_factory = create_uow_factory(engine)
    return Container(
        settings=settings,
        engine=engine,
        get_contact=GetContact(uow_factory),
        create_contact=CreateContact(uow_factory),
        update_contact=UpdateContact(uow_factory),
    )
```

SQLAlchemy appears here only because `composition` is the explicit construction boundary; route handlers and application services still receive use cases rather than sessions/engines.

- [ ] **Step 3: Implement FastAPI dependencies**

Create `presentation/http/dependencies.py`:

```python
from fastapi import Request

from gomazon_webasyst.application.contacts import CreateContact, GetContact, UpdateContact
from gomazon_webasyst.composition.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_contact_query(request: Request) -> GetContact:
    return get_container(request).get_contact


def get_create_contact(request: Request) -> CreateContact:
    return get_container(request).create_contact


def get_update_contact(request: Request) -> UpdateContact:
    return get_container(request).update_contact
```

- [ ] **Step 4: Implement HTTP error translation**

Create `presentation/http/errors.py`:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from gomazon_webasyst.application.errors import ContactNotFound


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ContactNotFound)
    async def handle_contact_not_found(
        request: Request,
        exc: ContactNotFound,
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
```

- [ ] **Step 5: Implement contact router**

Create `presentation/http/contacts.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, status

from gomazon_webasyst.application.contacts import CreateContact, GetContact, UpdateContact
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate
from gomazon_webasyst.presentation.http.dependencies import (
    get_contact_query,
    get_create_contact,
    get_update_contact,
)


router = APIRouter(prefix="/api/v1/contacts", tags=["contacts"])


@router.post("", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: ContactCreate,
    use_case: Annotated[CreateContact, Depends(get_create_contact)],
) -> ContactRead:
    return await use_case.execute(data)


@router.get("/{contact_id}", response_model=ContactRead)
async def get_contact(
    contact_id: int,
    use_case: Annotated[GetContact, Depends(get_contact_query)],
) -> ContactRead:
    return await use_case.execute(contact_id)


@router.patch("/{contact_id}", response_model=ContactRead)
async def update_contact(
    contact_id: int,
    data: ContactUpdate,
    use_case: Annotated[UpdateContact, Depends(get_update_contact)],
) -> ContactRead:
    return await use_case.execute(contact_id, data)
```

- [ ] **Step 6: Implement app factory and lifespan**

Create `main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from gomazon_webasyst.composition.container import create_container
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.presentation.http.contacts import router as contacts_router
from gomazon_webasyst.presentation.http.errors import install_error_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    container = create_container(resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = container
        try:
            yield
        finally:
            await container.close()

    app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)
    app.include_router(contacts_router)
    install_error_handlers(app)
    return app


app = create_app()
```

- [ ] **Step 7: Complete HTTP integration tests with a temporary SQLite database**

In the HTTP test fixture:

1. create a temporary file URL `sqlite+aiosqlite:///...`,
2. call `create_app(Settings(database_url=url))`,
3. create the legacy-mapped schema through `Base.metadata.create_all` using `app.state.container.engine` inside the app lifespan,
4. verify POST returns 201 and a generated positive id,
5. verify GET returns the created profile,
6. verify PATCH changes the company/name field,
7. verify missing id returns the typed 404 envelope.

Use `httpx.ASGITransport` and explicitly enter the application lifespan with `app.router.lifespan_context(app)` so startup/shutdown resources are exercised.

Run:

```bash
python -m pytest tests/integration/test_http_contacts.py -v
```

Expected result: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/gomazon_webasyst/composition/container.py src/gomazon_webasyst/presentation src/gomazon_webasyst/main.py tests/integration/test_http_contacts.py
git commit -m "feat: expose native contact api through composition root"
```

---

### Task 6: Verify replaceability and MySQL/MariaDB selection without coupling application code

**Files:**
- Create: `tests/integration/test_persistence_factory.py`
- Modify: `tests/architecture/test_dependency_boundaries.py`

**Interfaces:**
- Verifies: application/use-case behavior is unchanged when using fake UoW versus SQLAlchemy UoW.
- Verifies: the configured `mysql+asyncmy://` URL constructs the first production adapter without importing a driver in application code.

- [ ] **Step 1: Test configured dialect selection**

Create `tests/integration/test_persistence_factory.py`:

```python
import pytest

from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.factory import create_engine


def test_mysql_url_selects_async_mysql_dialect_without_connecting() -> None:
    settings = Settings(database_url="mysql+asyncmy://user:pass@localhost/webasyst")
    engine = create_engine(settings)
    try:
        assert engine.dialect.name == "mysql"
        assert engine.dialect.is_async is True
    finally:
        # dispose is async; the engine has not opened a connection in this test.
        pass


@pytest.mark.asyncio
async def test_sqlite_url_selects_async_sqlite_dialect() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    engine = create_engine(settings)
    try:
        assert engine.dialect.name == "sqlite"
        assert engine.dialect.is_async is True
    finally:
        await engine.dispose()
```

Adjust the first test to be async as well so `await engine.dispose()` runs in both branches.

Run:

```bash
python -m pytest tests/integration/test_persistence_factory.py -v
```

Expected result: PASS without requiring a live MySQL server.

- [ ] **Step 2: Tighten the architecture guard**

Extend `tests/architecture/test_dependency_boundaries.py` so application/contracts also reject imports whose root is `asyncmy` or `aiosqlite`:

```python
FORBIDDEN = {"fastapi", "sqlalchemy", "asyncmy", "aiosqlite"}
```

Run:

```bash
python -m pytest tests/architecture/test_dependency_boundaries.py -v
```

Expected result: PASS.

- [ ] **Step 3: Run all tests for the foundation**

```bash
python -m pytest -v
```

Expected result: all unit, architecture, persistence-contract, integration, and HTTP tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_persistence_factory.py tests/architecture/test_dependency_boundaries.py
git commit -m "test: verify persistence adapter replaceability"
```

---

### Task 7: Final architecture verification and documentation sync

**Files:**
- Modify: `AGENTS.md` only if implementation differs from ADR-012/013 text recorded in Task 1.
- Modify: `docs/superpowers/specs/2026-09-14-webasyst-python-rewrite-design.md` only if an accepted design statement became factually wrong during implementation.

**Interfaces:**
- Produces: a verified architecture foundation with no undocumented boundary changes.

- [ ] **Step 1: Verify forbidden imports mechanically**

Run:

```bash
python -m pytest tests/architecture/test_dependency_boundaries.py -v
```

Expected result: PASS.

- [ ] **Step 2: Verify use cases without FastAPI or SQLAlchemy**

Run:

```bash
python -m pytest tests/unit/test_contact_use_cases.py -v
```

Expected result: PASS with only fake repository/UoW implementations.

- [ ] **Step 3: Verify concrete persistence contract**

Run:

```bash
python -m pytest tests/persistence_contracts tests/integration/test_sqlalchemy_contact_repository.py -v
```

Expected result: PASS.

- [ ] **Step 4: Verify HTTP vertical slice**

Run:

```bash
python -m pytest tests/integration/test_http_contacts.py -v
```

Expected result: PASS for create/get/update/404 flows.

- [ ] **Step 5: Run complete suite**

```bash
python -m pytest -v
```

Expected result: PASS.

- [ ] **Step 6: Inspect dependency direction**

Confirm these statements against the code tree:

```text
contracts -> pydantic only
application -> contracts + application ports
infrastructure -> application ports + contracts + sqlalchemy
presentation -> application + contracts + fastapi
composition -> application + infrastructure + settings
```

If implementation introduced a new architectural boundary, record it in `AGENTS.md` as a numbered ADR before completion.

- [ ] **Step 7: Commit any final documentation synchronization**

```bash
git add AGENTS.md docs/superpowers/specs/2026-09-14-webasyst-python-rewrite-design.md
git commit -m "docs: synchronize contact foundation architecture"
```

Skip this commit when neither file changed.

---

## Acceptance Criteria

The first implementation milestone is complete only when all of the following are true:

- `ContactCreate`, `ContactUpdate`, and `ContactRead` are Pydantic v2 contracts.
- Application contact use cases import neither FastAPI nor SQLAlchemy.
- `ContactRepository` and `UnitOfWork` are application-owned protocols.
- SQLAlchemy ORM objects never cross the persistence boundary.
- `wa_contact` is mapped with the legacy core columns needed for safe base-profile reads/writes.
- Email/custom contact data remain outside this slice by explicit architectural decision.
- A fake UoW can execute all application use-case tests.
- The SQLAlchemy repository passes the same repository behavioral contract.
- MySQL/MariaDB can be selected with `mysql+asyncmy://...` through settings/composition without editing application code.
- Native FastAPI create/get/update endpoints work against the concrete persistence adapter.
- Missing contacts become a typed application error and are translated to HTTP 404 only in presentation.
- `AGENTS.md` contains every architectural decision introduced by the implementation.
- The full pytest suite passes before the milestone is reported complete.
