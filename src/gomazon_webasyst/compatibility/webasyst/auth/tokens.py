from hashlib import md5

from gomazon_webasyst.contracts.auth import AuthIdentity


class LegacyCredentialVersionTokenFactory:
    def create(self, identity: AuthIdentity) -> str:
        created = identity.create_datetime.strftime("%Y-%m-%d %H:%M:%S")
        digest = md5(f"{created}{identity.login}{identity.password_hash}".encode()).hexdigest()
        return f"{digest[:15]}{identity.id}{digest[-15:]}"
