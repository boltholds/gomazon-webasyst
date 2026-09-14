class ContactNotFound(LookupError):
    def __init__(self, contact_id: int) -> None:
        self.contact_id = contact_id
        super().__init__(f"contact {contact_id} not found")
