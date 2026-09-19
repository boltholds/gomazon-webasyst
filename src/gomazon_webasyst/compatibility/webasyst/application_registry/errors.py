class LegacyPhpConfigError(ValueError):
    """Base error for restricted legacy PHP configuration parsing."""


class LegacyPhpConfigSyntaxError(LegacyPhpConfigError):
    """The supported declarative PHP subset is syntactically malformed."""


class LegacyPhpConfigUnsupportedExpression(LegacyPhpConfigError):
    """The configuration requires PHP execution or unsupported expression semantics."""


class LegacyPhpConfigLimitError(LegacyPhpConfigError):
    """A configured parser safety budget was exceeded."""
