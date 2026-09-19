from sqlalchemy import Integer, String, column, table


WA_VERIFICATION_CHANNEL_ASSETS = table(
    "wa_verification_channel_assets",
    column("address", String),
)

WA_CONTACT_SETTINGS = table(
    "wa_contact_settings",
    column("contact_id", Integer),
)

WA_APP_TOKENS = table(
    "wa_app_tokens",
    column("contact_id", Integer),
)

WA_CONTACT_DATA_TEXT = table(
    "wa_contact_data_text",
    column("contact_id", Integer),
)

WA_CONTACT_CATEGORIES = table(
    "wa_contact_categories",
    column("contact_id", Integer),
    column("category_id", Integer),
)

WA_CONTACT_CATEGORY = table(
    "wa_contact_category",
    column("id", Integer),
    column("cnt", Integer),
)

WA_CONTACT_EVENTS = table(
    "wa_contact_events",
    column("contact_id", Integer),
)
