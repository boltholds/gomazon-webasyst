from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.mappings import contact_row_to_read
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaContactRow


def test_wa_contact_mapping_contains_legacy_columns() -> None:
    assert set(WaContactRow.__table__.columns.keys()) == {
        "id", "name", "firstname", "middlename", "lastname", "title",
        "company", "jobtitle", "company_contact_id", "is_company", "is_user",
        "is_staff", "login", "password", "last_datetime", "sex", "birth_day",
        "birth_month", "birth_year", "about", "photo", "create_datetime",
        "create_app_id", "create_method", "create_contact_id", "locale", "timezone",
    }
    assert WaContactRow.__table__.c.name.nullable is False
    assert WaContactRow.__table__.c.login.nullable is True


def test_wa_contact_mapping_can_create_table_and_map_profile() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        row = WaContactRow(
            name="Alice",
            firstname="Alice",
            create_datetime=datetime(2026, 9, 14, 12, 0, 0),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        contract = contact_row_to_read(row)
    assert contract.id == row.id
    assert contract.name == "Alice"
    assert contract.firstname == "Alice"
    assert contract.is_company is False
