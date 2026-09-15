from enum import StrEnum


class EnumStr(StrEnum):
    """String enum base used by serialized contract discriminators."""


class LegacyRouteRuleKind(EnumStr):
    APP = "app"
    REDIRECT = "redirect"
    DISPATCH = "dispatch"


class DispatchSeedKind(EnumStr):
    EMPTY = "empty"
    MODULE = "module"
    ACTION_ONLY = "action_only"
    ACTION = "action"
    PLUGIN = "plugin"
    PLUGIN_ACTION_ONLY = "plugin_action_only"
    PLUGIN_MODULE = "plugin_module"
    PLUGIN_ACTION = "plugin_action"


class AppRouteConstraintKind(EnumStr):
    ANY = "any"
    MODULE = "module"


class SettlementKind(EnumStr):
    APP = "app"
    REDIRECT = "redirect"


class DispatchNamespaceKind(EnumStr):
    APP = "app"
    PLUGIN = "plugin"


class DispatchRequestKind(EnumStr):
    DEFAULT = "default"
    ACTION = "action"


class DispatchTargetKind(EnumStr):
    CONTROLLER = "controller"
    SINGLE_ACTION = "single_action"
    MULTI_ACTION = "multi_action"


class HandlerRegistryLookupKind(EnumStr):
    REGISTERED = "registered"
    MISSING = "missing"


class PluginRegistryLookupKind(EnumStr):
    AVAILABLE = "available"
    MISSING = "missing"


class LegacyDispatchOutcomeKind(EnumStr):
    HANDLER = "handler"


class ContactResolutionKind(EnumStr):
    RESOLVED = "resolved"
    MISSING = "missing"


class IdentityResolutionKind(EnumStr):
    RESOLVED = "resolved"
    ERROR = "error"


class IdentityResolutionErrorType(EnumStr):
    NOT_FOUND = "not_found"
    REJECTED_BY_POLICY = "rejected_by_policy"
    UNSUPPORTED_SCHEME = "unsupported_scheme"


class PasswordVerificationKind(EnumStr):
    ACCEPTED = "accepted"
    ERROR = "error"


class PasswordVerificationErrorType(EnumStr):
    INVALID = "invalid"
    UNSUPPORTED_SCHEME = "unsupported_scheme"


class SubjectResolutionKind(EnumStr):
    RESOLVED = "resolved"
    ERROR = "error"


class SubjectResolutionErrorType(EnumStr):
    NOT_FOUND = "not_found"
    DISABLED = "disabled"


class SessionResolutionKind(EnumStr):
    RESOLVED = "resolved"
    ERROR = "error"


class SessionResolutionErrorType(EnumStr):
    NOT_FOUND = "not_found"
    EXPIRED = "expired"
    REVOKED = "revoked"
    CREDENTIALS_CHANGED = "credentials_changed"
    SUBJECT_UNAVAILABLE = "subject_unavailable"
    SUBJECT_DISABLED = "subject_disabled"


class AuthenticationResultKind(EnumStr):
    SUCCEEDED = "succeeded"
    REJECTED = "rejected"


class AuthenticationRejectType(EnumStr):
    INVALID_CREDENTIALS = "invalid_credentials"
    SUBJECT_DISABLED = "subject_disabled"
    POLICY_REJECTED = "policy_rejected"
    SESSION_UNAVAILABLE = "session_unavailable"


class LoginPolicyDecisionKind(EnumStr):
    CONTRIBUTE = "contribute"
    SKIP = "skip"
    REJECT = "reject"


class LoginPolicyRejectType(EnumStr):
    INVALID_IDENTIFIER = "invalid_identifier"


class LoginPlanKind(EnumStr):
    PLANNED = "planned"
    ERROR = "error"


class LoginPlanErrorType(EnumStr):
    EMPTY_IDENTIFIER = "empty_identifier"
    REJECTED_BY_POLICY = "rejected_by_policy"


class IdentityKeyResolutionKind(EnumStr):
    RESOLVED = "resolved"
    NOT_FOUND = "not_found"


class SessionCreationKind(EnumStr):
    CREATED = "created"
    ERROR = "error"


class SessionCreationErrorType(EnumStr):
    COLLISION = "collision"


class SessionStateResolutionKind(EnumStr):
    RESOLVED = "resolved"
    ERROR = "error"


class SessionStateErrorType(EnumStr):
    NOT_FOUND = "not_found"
    EXPIRED = "expired"


class SessionRevocationKind(EnumStr):
    REVOKED = "revoked"
    ALREADY_MISSING = "already_missing"


class RegistryWriteKind(EnumStr):
    WRITTEN = "written"


class RegistryCheckKind(EnumStr):
    ACTIVE = "active"
    MISSING = "missing"


class RegistryTouchKind(EnumStr):
    TOUCHED = "touched"
    MISSING = "missing"


class RegistryRevocationKind(EnumStr):
    REVOKED = "revoked"
    ALREADY_MISSING = "already_missing"


class LogoutStatus(EnumStr):
    REVOKED = "revoked"
    ALREADY_MISSING = "already_missing"


class PersistentCredentialDispositionKind(EnumStr):
    REFRESH = "refresh"
    CLEAR = "clear"
    KEEP = "keep"


class PersistentStrategyResultKind(EnumStr):
    RESOLVED = "resolved"
    NOT_APPLICABLE = "not_applicable"
    REJECTED = "rejected"


class PersistentCredentialResolutionKind(EnumStr):
    RESOLVED = "resolved"
    REJECTED = "rejected"


class PersistentCredentialRejectReason(EnumStr):
    MALFORMED = "malformed"
    UNSUPPORTED = "unsupported"
    INVALID = "invalid"
    SUBJECT_NOT_FOUND = "subject_not_found"
    SUBJECT_DISABLED = "subject_disabled"


class PersistentCredentialIssueKind(EnumStr):
    ISSUED = "issued"
    REJECTED = "rejected"


class PersistentCredentialIssueRejectReason(EnumStr):
    SUBJECT_NOT_FOUND = "subject_not_found"
    SUBJECT_DISABLED = "subject_disabled"


class BackendSessionEstablishmentKind(EnumStr):
    ESTABLISHED = "established"
    REJECTED = "rejected"


class BackendSessionEstablishmentRejectReason(EnumStr):
    SESSION_UNAVAILABLE = "session_unavailable"


class PersistentLoginResultKind(EnumStr):
    RESTORED = "restored"
    REJECTED = "rejected"


class PersistentLoginRejectReason(EnumStr):
    CREDENTIAL_REJECTED = "credential_rejected"
    SESSION_UNAVAILABLE = "session_unavailable"


class GroupType(EnumStr):
    GROUP = "group"
    LOCATION = "location"


class GroupResolutionKind(EnumStr):
    RESOLVED = "resolved"
    MISSING = "missing"


class AppAccessKind(EnumStr):
    NONE = "none"
    LIMITED = "limited"
    FULL = "full"
    GLOBAL_ADMIN = "global_admin"


class EffectiveRightKind(EnumStr):
    FINITE = "finite"
    UNLIMITED = "unlimited"


class UnlimitedRightReason(EnumStr):
    GLOBAL_ADMIN = "global_admin"
    APP_FULL_ACCESS = "app_full_access"


class RightsSnapshotKind(EnumStr):
    FINITE = "finite"
    UNLIMITED = "unlimited"


class AppAccessMode(EnumStr):
    NONE = "none"
    LIMITED = "limited"
    FULL = "full"


class GlobalAdminMode(EnumStr):
    ENABLED = "enabled"
    DISABLED = "disabled"


class RightsMutationRejectReason(EnumStr):
    ZERO_VALUE = "zero_value"
    RESERVED_RIGHT = "reserved_right"
    GLOBAL_CONTROL_APP = "global_control_app"


class AccessReadResultKind(EnumStr):
    RESOLVED = "resolved"
    REJECTED = "rejected"


class AccessReadRejectReason(EnumStr):
    SUBJECT_NOT_FOUND = "subject_not_found"
    SUBJECT_NOT_USER = "subject_not_user"
    GROUP_NOT_FOUND = "group_not_found"


class AccessAdministrationDenyReason(EnumStr):
    ACTOR_NOT_FOUND = "actor_not_found"
    ACTOR_NOT_USER = "actor_not_user"
    NOT_GLOBAL_ADMIN = "not_global_admin"


class AccessMutationResultKind(EnumStr):
    GROUP_CREATED = "group_created"
    GROUP_UPDATED = "group_updated"
    GROUP_DELETED = "group_deleted"
    MEMBERSHIP_ADDED = "membership_added"
    MEMBERSHIP_ALREADY_PRESENT = "membership_already_present"
    MEMBERSHIP_REMOVED = "membership_removed"
    MEMBERSHIP_ALREADY_ABSENT = "membership_already_absent"
    MEMBERS_REPLACED = "members_replaced"
    REJECTED = "rejected"


class AccessMutationRejectReason(EnumStr):
    ACCESS_DENIED = "access_denied"
    GROUP_NOT_FOUND = "group_not_found"
    CONTACT_NOT_FOUND = "contact_not_found"
    CONTACT_NOT_USER = "contact_not_user"
