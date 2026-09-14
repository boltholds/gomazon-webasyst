# Contacts Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working Python vertical slice for Webasyst contacts, proving Pydantic contracts, DI, application-owned persistence ports, SQLAlchemy infrastructure, and FastAPI wiring without claiming legacy contact API parity.

**Architecture:** The first slice targets the legacy `wa_contact` base table only. `wa_contact_emails`, `wa_contact_data`, and `wa_contact_data_text` are separate later compatibility slices. Application code depends only on Pydantic contracts and `Protocol` ports; SQLAlchemy remains infrastructure-private and is selected in the composition root.

**Tech Stack:** Python 3.12+, FastAPI/Starlette, Pydantic v2, pydantic-settings, SQLAlchemy 2.x async ORM, `asyncmy`, `aiosqlite`, pytest, pytest-asyncio, httpx.

**Spec:** `docs/superpowers/specs/2026-09-14-webasyst-python-rewrite-design.md`

## Global Constraints

- Python `>=3.12`.
- Pydantic `>=2,<3`.
- SQLAlchemy `>=2,<3`.
- FastAPI is presentation-only; `contracts` and `application` must not import FastAPI.
- SQLAlchemy/driver types must not cross out of `infrastructure.persistence.sqlalchemy` except into the composition root that constructs them.
- Persistence is replaceable through DI; use cases never receive a DB session/engine.
- Pydantic v2 models are the contracts crossing presentation/application and application/persistence boundaries.
- Existing Webasyst data is preserved; no destructive schema redesign is part of this slice.
- This slice exposes profile data from `wa_contact`; it excludes email/custom-field tables, passwords, sessions, permissions, tokens, and OAuth.
- Do not claim Webasyst compatibility until characterization tests exist for the behavior being claimed.

---

## File Map

```text
pyproject.toml
src/gomazon_webasyst/
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
  architecture/test_dependency_boundaries.py
  unit/test_settings.py
  unit/test_contact_contracts.py
  unit/test_contact_use_cases.py
  persistence_contracts/__init__.py
  persistence_contracts/contacts_contract.py
  integration/test_sqlalchemy_contact_repository.py
  integration/test_persistence_factory.py
  integration/test_http_contacts.py

AGENTS.md
```

---

### Task 1: Bootstrap packaging, settings, and architecture guards

**Files:**
- Create: `pyproject.toml`
- Create: `src/gomazon_webasyst/__init__.py`
- Create: `src/gomazon_webasyst/composition/__init__.py`
- Create: `src/gomazon_webasyst/composition/settings.py`
- Create: `tests/unit/test_settings.py`
- Create: `tests/architecture/test_dependency_boundaries.py`
- Modify: `AGENTS.md`

**Interfaces:**
- Produces: `Settings(database_backend: Literal["sqlalchemy"], database_url: str, app_name: str)`.
- Produces: an automated guard against leaking FastAPI/SQLAlchemy/drivers into contracts/application.

- [ ] **Step 1: Add project metadata and dependencies**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "gomazon-webasyst"
version = "0.1.0"
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
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Write failing settings tests**

Create `tests/unit/test_settings.py`:

```python
from gomazon_webasyst.composition.settings import Settings


def test_default_backend_is_sqlalchemy() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert settings.database_backend == "sqlalchemy"


def test_mysql_async_url_is_accepted() -> None:
    settings = Settings(database_url="mysql+asyncmy://user:pass@db/webasyst")
    assert settings.database_url == "mysql+asyncmy://user:pass@db/webasyst"
```

Run:

```bash
python -m pytest tests/unit/test_settings.py -v
```

Expected: FAIL because the settings module does not exist.

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

Create the two package `__init__.py` files, then run:

```bash
python -m pytest tests/unit/test_settings.py -v
```

Expected: PASS.

- [ ] **Step 4: Add architecture import guard**

Create `tests/architecture/test_dependency_boundaries.py`:

```python
import ast
from pathlib import Path

ROOT = Path("src/gomazon_webasyst")
CHECK_DIRS = [ROOT / "contracts", ROOT / "application"]
FORBIDDEN = {"fastapi", "sqlalchemy", "asyncmy", "aiosqlite"}


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_application_and_contracts_do_not_import_framework_or_db_internals() -> None:
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

Expected: PASS.

- [ ] **Step 5: Record the two implementation-level ADRs in `AGENTS.md`**

Append:

```markdown
### ADR-012 — First contact slice maps only `wa_contact`
Status: accepted
Date: 2026-09-14

The first contacts vertical slice maps only the base legacy `wa_contact` table.
`wa_contact_emails`, `wa_contact_data`, and `wa_contact_data_text` are separate later slices.
Password/session/token behavior is not exposed through this contact application contract.

### ADR-013 — Initial relational persistence path is async
Status: accepted
Date: 2026-09-14

The first SQLAlchemy adapter uses `AsyncEngine`, `AsyncSession`, async repositories, and an async Unit of Work.
MySQL/MariaDB uses `asyncmy`; persistence-contract tests may use `aiosqlite` without changing application code.
Async SQLAlchemy primitives remain infrastructure-private.
```

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/gomazon_webasyst tests/unit/test_settings.py tests/architecture AGENTS.md
git commit -m "chore: bootstrap python rewrite foundation"
```

---

### Task 2: Define Pydantic contact contracts

**Files:**
- Create: `src/gomazon_webasyst/contracts/__init__.py`
- Create: `src/gomazon_webasyst/contracts/contacts.py`
- Create: `tests/unit/test_contact_contracts.py`

**Interfaces:**
- Produces: `ContactId`, `ContactCreate`, `ContactUpdate`, `ContactRead`.

- [ ] **Step 1: Write failing contract tests**

Create `tests/unit/test_contact_contracts.py`:

```python
from datetime import datetime

import pytest
from pydantic import ValidationError

from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate


def test_create_rejects_fields_owned_by_later_contact_slices() -> None:
    with pytest.raises(ValidationError):
        ContactCreate(name="Alice", email="alice@example.com")


def test_update_rejects_empty_patch() -> None:
    with pytest.raises(ValidationError):
        ContactUpdate()


def test_update_rejects_explicit_null_for_non_nullable_legacy_column() -> None:
    with pytest.raises(ValidationError):
        ContactUpdate(name=None)


def test_read_contract_is_frozen() -> None:
    contact = ContactRead(
        id=1,
        name="Alice",
        create_datetime=datetime(2026, 9, 14, 12, 0, 0),
    )
    with pytest.raises(ValidationError):
        contact.name = "Changed"
```

Run and verify FAIL:

```bash
python -m pytest tests/unit/test_contact_contracts.py -v
```

- [ ] **Step 2: Implement contracts**

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
    company_contact_id: Annotated[int, Field(ge=0)] = 0
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
    company_contact_id: Annotated[int, Field(ge=0)] | None = None
    is_company: bool | None = None
    locale: Annotated[str, Field(max_length=8)] | None = None
    timezone: Annotated[str, Field(max_length=64)] | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "ContactUpdate":
        if not self.model_fields_set:
            raise ValueError("contact update must contain at least one field")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("contact profile fields cannot be set to null")
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

Export these names from `contracts/__init__.py`.

Run:

```bash
python -m pytest tests/unit/test_contact_contracts.py tests/architecture/test_dependency_boundaries.py -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add src/gomazon_webasyst/contracts tests/unit/test_contact_contracts.py
git commit -m "feat: define contact pydantic contracts"
```

---

### Task 3: Add application ports, errors, and use cases

**Files:**
- Create: `src/gomazon_webasyst/application/__init__.py`
- Create: `src/gomazon_webasyst/application/errors.py`
- Create: `src/gomazon_webasyst/application/contacts.py`
- Create: `src/gomazon_webasyst/application/ports/__init__.py`
- Create: `src/gomazon_webasyst/application/ports/contacts.py`
- Create: `src/gomazon_webasyst/application/ports/unit_of_work.py`
- Create: `tests/unit/test_contact_use_cases.py`

**Interfaces:**
- Produces: async `ContactRepository`, async `UnitOfWork`, callable `UnitOfWorkFactory`.
- Produces: `GetContact`, `CreateContact`, `UpdateContact`, `ContactNotFound`.

- [ ] **Step 1: Write failing use-case tests using only fakes**

Create `tests/unit/test_contact_use_cases.py`:

```python
from datetime import datetime

import pytest

from gomazon_webasyst.application.contacts import CreateContact, GetContact, UpdateContact
from gomazon_webasyst.application.errors import ContactNotFound
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate

NOW = datetime(2026, 9, 14, 12, 0, 0)


class FakeRepo:
    def __init__(self) -> None:
        self.items: dict[int, ContactRead] = {}
        self.next_id = 1

    async def get(self, contact_id: int) -> ContactRead | None:
        return self.items.get(contact_id)

    async def create(self, data: ContactCreate) -> ContactRead:
        item = ContactRead(id=self.next_id, create_datetime=NOW, **data.model_dump())
        self.items[item.id] = item
        self.next_id += 1
        return item

    async def update(self, contact_id: int, data: ContactUpdate) -> ContactRead | None:
        current = self.items.get(contact_id)
        if current is None:
            return None
        values = current.model_dump()
        values.update(data.model_dump(exclude_unset=True))
        item = ContactRead(**values)
        self.items[contact_id] = item
        return item


class FakeUow:
    def __init__(self, repo: FakeRepo) -> None:
        self.contacts = repo
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


class FakeUowFactory:
    def __init__(self, uow: FakeUow) -> None:
        self.uow = uow

    def __call__(self) -> FakeUow:
        return self.uow


@pytest.mark.asyncio
async def test_create_commits() -> None:
    uow = FakeUow(FakeRepo())
    result = await CreateContact(FakeUowFactory(uow)).execute(ContactCreate(name="Alice"))
    assert result.id == 1
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_get_missing_raises_typed_error() -> None:
    uow = FakeUow(FakeRepo())
    with pytest.raises(ContactNotFound):
        await GetContact(FakeUowFactory(uow)).execute(99)


@pytest.mark.asyncio
async def test_update_commits() -> None:
    repo = FakeRepo()
    existing = await repo.create(ContactCreate(name="Before"))
    uow = FakeUow(repo)
    result = await UpdateContact(FakeUowFactory(uow)).execute(
        existing.id,
        ContactUpdate(name="After"),
    )
    assert result.name == "After"
    assert uow.commits == 1
```

Run and verify FAIL:

```bash
python -m pytest tests/unit/test_contact_use_cases.py -v
```

- [ ] **Step 2: Implement ports**

Create `application/ports/contacts.py`:

```python
from typing import Protocol

from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate


class ContactRepository(Protocol):
    async def get(self, contact_id: int) -> ContactRead | None: ...
    async def create(self, data: ContactCreate) -> ContactRead: ...
    async def update(self, contact_id: int, data: ContactUpdate) -> ContactRead | None: ...
```

Create `application/ports/unit_of_work.py`:

```python
from types import TracebackType
from typing import Protocol, Self

from .contacts import ContactRepository


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

- [ ] **Step 3: Implement error and use cases**

Create `application/errors.py`:

```python
class ContactNotFound(LookupError):
    def __init__(self, contact_id: int) -> None:
        self.contact_id = contact_id
        super().__init__(f"contact {contact_id} not found")
```

Create `application/contacts.py`:

```python
from gomazon_webasyst.application.errors import ContactNotFound
from gomazon_webasyst.application.ports.unit_of_work import UnitOfWorkFactory
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate


class GetContact:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, contact_id: int) -> ContactRead:
        async with self._uow_factory() as uow:
            result = await uow.contacts.get(contact_id)
        if result is None:
            raise ContactNotFound(contact_id)
        return result


class CreateContact:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, data: ContactCreate) -> ContactRead:
        async with self._uow_factory() as uow:
            result = await uow.contacts.create(data)
            await uow.commit()
            return result


class UpdateContact:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, contact_id: int, data: ContactUpdate) -> ContactRead:
        async with self._uow_factory() as uow:
            result = await uow.contacts.update(contact_id, data)
            if result is None:
                raise ContactNotFound(contact_id)
            await uow.commit()
            return result
```

Run:

```bash
python -m pytest tests/unit/test_contact_use_cases.py tests/architecture/test_dependency_boundaries.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/gomazon_webasyst/application tests/unit/test_contact_use_cases.py
git commit -m "feat: add contact application ports and use cases"
```

---

### Task 4: Implement the SQLAlchemy persistence adapter

**Files:**
- Create all files under `src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/`
- Create: `tests/persistence_contracts/__init__.py`
- Create: `tests/persistence_contracts/contacts_contract.py`
- Create: `tests/integration/test_sqlalchemy_contact_repository.py`

**Interfaces:**
- Consumes: contact contracts and application-owned ports.
- Produces: `SQLAlchemyContactRepository`, `SQLAlchemyUnitOfWorkFactory`, `create_engine`, `create_uow_factory`.

- [ ] **Step 1: Define the reusable repository contract**

Create `tests/persistence_contracts/contacts_contract.py`:

```python
from gomazon_webasyst.application.ports.contacts import ContactRepository
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactUpdate


async def assert_contact_repository_contract(repo: ContactRepository) -> None:
    created = await repo.create(ContactCreate(name="Alice", firstname="Alice"))
    assert created.id > 0
    assert await repo.get(created.id) == created

    updated = await repo.update(created.id, ContactUpdate(company="Example Ltd"))
    assert updated is not None
    assert updated.company == "Example Ltd"

    assert await repo.get(999_999) is None
```

- [ ] **Step 2: Write failing SQLAlchemy integration tests**

Create `tests/integration/test_sqlalchemy_contact_repository.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from gomazon_webasyst.contracts.contacts import ContactCreate
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.repositories import SQLAlchemyContactRepository
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.unit_of_work import SQLAlchemyUnitOfWorkFactory
from tests.persistence_contracts.contacts_contract import assert_contact_repository_contract


async def make_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine


@pytest.mark.asyncio
async def test_repository_satisfies_contact_contract() -> None:
    engine = await make_engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await assert_contact_repository_contract(SQLAlchemyContactRepository(session))
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_uow_commit_is_visible_to_next_uow() -> None:
    engine = await make_engine()
    factory = SQLAlchemyUnitOfWorkFactory(async_sessionmaker(engine, expire_on_commit=False))
    async with factory() as first:
        created = await first.contacts.create(ContactCreate(name="Committed"))
        await first.commit()
    async with factory() as second:
        loaded = await second.contacts.get(created.id)
    assert loaded is not None
    assert loaded.name == "Committed"
    await engine.dispose()


@pytest.mark.asyncio
async def test_uow_exception_rolls_back() -> None:
    engine = await make_engine()
    factory = SQLAlchemyUnitOfWorkFactory(async_sessionmaker(engine, expire_on_commit=False))
    created_id: int | None = None
    with pytest.raises(RuntimeError):
        async with factory() as first:
            created = await first.contacts.create(ContactCreate(name="Rolled back"))
            created_id = created.id
            raise RuntimeError("force rollback")
    assert created_id is not None
    async with factory() as second:
        assert await second.contacts.get(created_id) is None
    await engine.dispose()
```

Run and verify FAIL:

```bash
python -m pytest tests/integration/test_sqlalchemy_contact_repository.py -v
```

- [ ] **Step 3: Implement `Base` and the legacy `wa_contact` ORM mapping**

`base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

`models.py` must map the actual legacy `wa_contact` columns observed in `wa-system/webasyst/lib/config/db.php`: `id`, `name`, `firstname`, `middlename`, `lastname`, `title`, `company`, `jobtitle`, `company_contact_id`, `is_company`, `is_user`, `is_staff`, `login`, `password`, `last_datetime`, `sex`, `birth_day`, `birth_month`, `birth_year`, `about`, `photo`, `create_datetime`, `create_app_id`, `create_method`, `create_contact_id`, `locale`, `timezone`. Use matching string lengths/nullability and portable SQLAlchemy scalar types; keep auth fields infrastructure-private.

For example, the required profile/core columns are:

```python
class WaContactRow(Base):
    __tablename__ = "wa_contact"

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

- [ ] **Step 4: Implement mapper and repository**

`mappings.py`:

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

`repositories.py`:

```python
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate
from .mappings import contact_row_to_read
from .models import WaContactRow


class SQLAlchemyContactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, contact_id: int) -> ContactRead | None:
        row = await self._session.get(WaContactRow, contact_id)
        return None if row is None else contact_row_to_read(row)

    async def create(self, data: ContactCreate) -> ContactRead:
        values = data.model_dump()
        values["is_company"] = int(data.is_company)
        row = WaContactRow(
            **values,
            create_datetime=datetime.now(timezone.utc).replace(tzinfo=None),
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

- [ ] **Step 5: Implement Unit of Work and engine factory**

`unit_of_work.py`:

```python
from types import TracebackType
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from .repositories import SQLAlchemyContactRepository


class SQLAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.contacts: SQLAlchemyContactRepository

    async def __aenter__(self):
        self._session = self._session_factory()
        self.contacts = SQLAlchemyContactRepository(self._session)
        return self

    async def __aexit__(self, exc_type, exc, tb: TracebackType | None) -> None:
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

`factory.py`:

```python
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from gomazon_webasyst.composition.settings import Settings
from .unit_of_work import SQLAlchemyUnitOfWorkFactory


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.database_url, pool_pre_ping=True)


def create_uow_factory(engine: AsyncEngine) -> SQLAlchemyUnitOfWorkFactory:
    return SQLAlchemyUnitOfWorkFactory(async_sessionmaker(engine, expire_on_commit=False))
```

Run:

```bash
python -m pytest tests/integration/test_sqlalchemy_contact_repository.py tests/architecture/test_dependency_boundaries.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/gomazon_webasyst/infrastructure tests/persistence_contracts tests/integration/test_sqlalchemy_contact_repository.py
git commit -m "feat: add sqlalchemy contact persistence adapter"
```

---

### Task 5: Build the composition root and native FastAPI contact API

**Files:**
- Create: `src/gomazon_webasyst/composition/container.py`
- Create presentation package files from the File Map
- Create: `src/gomazon_webasyst/main.py`
- Create: `tests/integration/test_http_contacts.py`

**Interfaces:**
- Produces: `Container`, `create_container`, `create_app`.
- Produces: POST/GET/PATCH `/api/v1/contacts` native Python endpoints.
- Maps `ContactNotFound` to 404 only in presentation.

- [ ] **Step 1: Implement composition root**

`composition/container.py`:

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

- [ ] **Step 2: Implement presentation dependencies, error mapping, and router**

`presentation/http/dependencies.py`:

```python
from fastapi import Request
from gomazon_webasyst.composition.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container
```

`presentation/http/errors.py`:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from gomazon_webasyst.application.errors import ContactNotFound


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ContactNotFound)
    async def handle_contact_not_found(request: Request, exc: ContactNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
```

`presentation/http/contacts.py`:

```python
from typing import Annotated
from fastapi import APIRouter, Depends, Request, status

from gomazon_webasyst.application.contacts import CreateContact, GetContact, UpdateContact
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate
from .dependencies import get_container

router = APIRouter(prefix="/api/v1/contacts", tags=["contacts"])


def get_query(request: Request) -> GetContact:
    return get_container(request).get_contact


def get_creator(request: Request) -> CreateContact:
    return get_container(request).create_contact


def get_updater(request: Request) -> UpdateContact:
    return get_container(request).update_contact


@router.post("", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: ContactCreate,
    use_case: Annotated[CreateContact, Depends(get_creator)],
) -> ContactRead:
    return await use_case.execute(data)


@router.get("/{contact_id}", response_model=ContactRead)
async def get_contact(
    contact_id: int,
    use_case: Annotated[GetContact, Depends(get_query)],
) -> ContactRead:
    return await use_case.execute(contact_id)


@router.patch("/{contact_id}", response_model=ContactRead)
async def update_contact(
    contact_id: int,
    data: ContactUpdate,
    use_case: Annotated[UpdateContact, Depends(get_updater)],
) -> ContactRead:
    return await use_case.execute(contact_id, data)
```

- [ ] **Step 3: Implement ASGI app factory without import-time DB configuration**

`main.py`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

from gomazon_webasyst.composition.container import create_container
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.presentation.http.contacts import router as contacts_router
from gomazon_webasyst.presentation.http.errors import install_error_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()
    container = create_container(resolved)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = container
        try:
            yield
        finally:
            await container.close()

    app = FastAPI(title=resolved.app_name, lifespan=lifespan)
    app.include_router(contacts_router)
    install_error_handlers(app)
    return app
```

Do not create a module-level `app = create_app()` because `database_url` is intentionally required. Run production/dev ASGI with:

```bash
GOMAZON_DATABASE_URL='mysql+asyncmy://user:pass@host/webasyst' uvicorn gomazon_webasyst.main:create_app --factory
```

- [ ] **Step 4: Write complete HTTP integration test**

Create `tests/integration/test_http_contacts.py`:

```python
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.main import create_app


@pytest.mark.asyncio
async def test_contact_http_vertical_slice(tmp_path: Path) -> None:
    db_path = tmp_path / "contacts.db"
    app = create_app(Settings(database_url=f"sqlite+aiosqlite:///{db_path}"))

    async with app.router.lifespan_context(app):
        async with app.state.container.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/contacts",
                json={"name": "Alice", "firstname": "Alice"},
            )
            assert created.status_code == 201
            contact_id = created.json()["id"]

            loaded = await client.get(f"/api/v1/contacts/{contact_id}")
            assert loaded.status_code == 200
            assert loaded.json()["name"] == "Alice"

            updated = await client.patch(
                f"/api/v1/contacts/{contact_id}",
                json={"company": "Example Ltd"},
            )
            assert updated.status_code == 200
            assert updated.json()["company"] == "Example Ltd"

            missing = await client.get("/api/v1/contacts/999999")
            assert missing.status_code == 404
            assert missing.json() == {"detail": "contact 999999 not found"}
```

Run:

```bash
python -m pytest tests/integration/test_http_contacts.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/gomazon_webasyst/composition/container.py src/gomazon_webasyst/presentation src/gomazon_webasyst/main.py tests/integration/test_http_contacts.py
git commit -m "feat: expose native contact api"
```

---

### Task 6: Prove database selection and architecture replaceability

**Files:**
- Create: `tests/integration/test_persistence_factory.py`

**Interfaces:**
- Verifies: MySQL/MariaDB driver selection is configuration-only.
- Verifies: no live MySQL server is needed merely to compose the adapter.

- [ ] **Step 1: Add dialect-selection test**

Create `tests/integration/test_persistence_factory.py`:

```python
import pytest

from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.factory import create_engine


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url", "dialect"),
    [
        ("sqlite+aiosqlite:///:memory:", "sqlite"),
        ("mysql+asyncmy://user:pass@localhost/webasyst", "mysql"),
    ],
)
async def test_config_selects_async_relational_dialect(url: str, dialect: str) -> None:
    engine = create_engine(Settings(database_url=url))
    try:
        assert engine.dialect.name == dialect
        assert engine.dialect.is_async is True
    finally:
        await engine.dispose()
```

Run:

```bash
python -m pytest tests/integration/test_persistence_factory.py -v
```

Expected: PASS without opening a network connection.

- [ ] **Step 2: Run application-only tests to prove fake DI still works**

```bash
python -m pytest tests/unit/test_contact_use_cases.py -v
```

Expected: PASS without FastAPI or SQLAlchemy involvement in the use-case code.

- [ ] **Step 3: Run architecture guard**

```bash
python -m pytest tests/architecture/test_dependency_boundaries.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_persistence_factory.py
git commit -m "test: prove persistence selection through di"
```

---

### Task 7: Final verification and architecture synchronization

**Files:**
- Modify: `AGENTS.md` only when implementation introduced a boundary or decision not already represented by ADR-001..013.
- Modify: design spec only when implementation invalidated an accepted design statement.

**Interfaces:**
- Produces: a verified first architecture milestone.

- [ ] **Step 1: Run contract/unit tests**

```bash
python -m pytest tests/unit -v
```

Expected: PASS.

- [ ] **Step 2: Run persistence and HTTP integration tests**

```bash
python -m pytest tests/persistence_contracts tests/integration -v
```

Expected: PASS.

- [ ] **Step 3: Run architecture guard**

```bash
python -m pytest tests/architecture -v
```

Expected: PASS.

- [ ] **Step 4: Run complete suite**

```bash
python -m pytest -v
```

Expected: PASS.

- [ ] **Step 5: Verify dependency direction manually against imports**

The final tree must satisfy:

```text
contracts -> pydantic / stdlib
application -> contracts + application ports / stdlib
infrastructure -> contracts + application ports + sqlalchemy
presentation -> contracts + application + fastapi
composition -> application + infrastructure + settings
```

No route or use case may accept `AsyncSession`, `Engine`, ORM rows, or SQLAlchemy query objects.

- [ ] **Step 6: Synchronize `AGENTS.md` if reality differs from ADR-012/013**

Any new architectural decision found during implementation is added as a new numbered ADR; existing accepted history is not silently rewritten.

- [ ] **Step 7: Commit documentation changes when present**

```bash
git add AGENTS.md docs/superpowers/specs/2026-09-14-webasyst-python-rewrite-design.md
git commit -m "docs: synchronize implemented contact architecture"
```

Omit this commit if neither file changed.

---

## Acceptance Criteria

- Pydantic v2 defines `ContactCreate`, `ContactUpdate`, and `ContactRead`.
- Application contact code imports neither FastAPI, SQLAlchemy, nor DB drivers.
- `ContactRepository` and `UnitOfWork` are application-owned protocols.
- ORM instances and SQLAlchemy primitives remain infrastructure-private.
- The concrete adapter maps the existing `wa_contact` schema rather than redesigning it.
- Email/custom-field/auth concerns remain outside this slice by explicit ADR.
- Use cases pass against fake persistence through constructor DI.
- The SQLAlchemy repository passes the reusable contact repository contract.
- `mysql+asyncmy://...` can be selected via settings without changes to application code.
- POST/GET/PATCH native contact endpoints pass end-to-end against SQLite through the same SQLAlchemy adapter interface.
- Missing contacts are application errors translated to HTTP 404 in presentation.
- `AGENTS.md` contains every architectural decision introduced by implementation.
- Full pytest suite passes before completion is claimed.
