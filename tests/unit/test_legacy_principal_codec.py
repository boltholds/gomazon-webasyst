from gomazon_webasyst.application.access_values import GroupId, GroupTarget, GuestsTarget, UserTarget
from gomazon_webasyst.compatibility.webasyst.access_control.principals import (
    LegacyPrincipalId,
    WebasystPrincipalCodec,
)


def test_codec_encodes_typed_targets_to_legacy_signed_ids() -> None:
    codec = WebasystPrincipalCodec()

    assert codec.encode(UserTarget(42)) == LegacyPrincipalId(-42)
    assert codec.encode(GroupTarget(GroupId(7))) == LegacyPrincipalId(7)
    assert codec.encode(GuestsTarget()) == LegacyPrincipalId(0)


def test_codec_decodes_every_legacy_principal_without_optional_miss() -> None:
    codec = WebasystPrincipalCodec()

    assert codec.decode(LegacyPrincipalId(-42)) == UserTarget(42)
    assert codec.decode(LegacyPrincipalId(7)) == GroupTarget(GroupId(7))
    assert codec.decode(LegacyPrincipalId(0)) == GuestsTarget()
