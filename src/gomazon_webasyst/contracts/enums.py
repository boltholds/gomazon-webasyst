from enum import StrEnum


class EnumStr(StrEnum):
    """String enum base used by serialized contract discriminators."""


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


class LegacyDispatchOutcomeKind(EnumStr):
    HANDLER = "handler"


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
