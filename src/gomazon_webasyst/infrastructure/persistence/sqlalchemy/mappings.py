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
