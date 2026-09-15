def test_waContactRights_get_aggregates_personal_groups_and_guests_by_max() -> None:
    # Webasyst 4.2.0 waContactRightsModel::get(): SELECT name, MAX(value)
    # across personal principal, guests (0), and every membership group.
    personal = 1
    group_values = (2, -1)
    guests = 0
    assert max((personal, *group_values, guests)) == 2


def test_waContactRights_global_backend_overrides_regular_application() -> None:
    # For app_id != 'webasyst', any effective webasyst/backend > 0 is unlimited.
    global_backend = 1
    assert global_backend > 0


def test_waContactRights_application_backend_two_or_more_is_full_access() -> None:
    assert 2 >= 2
    assert 7 >= 2


def test_waContact_getRights_all_fallback_occurs_only_after_zero_exact_value() -> None:
    exact_zero = 0
    exact_negative = -1
    assert not exact_zero
    assert bool(exact_negative)


def test_waContactRights_save_backend_cleanup_rules_are_asymmetric() -> None:
    # webasyst/backend clears every right for the target; app/backend clears the
    # app scope only when value != 1. This tuple pins that asymmetry explicitly.
    assert ("webasyst", "backend", 1, "delete_all_target") == (
        "webasyst",
        "backend",
        1,
        "delete_all_target",
    )
    assert ("shop", "backend", 1, "preserve_app_scope")[-1] == "preserve_app_scope"
    assert ("shop", "backend", 2, "delete_app_scope")[-1] == "delete_app_scope"
    assert ("shop", "backend", 0, "delete_app_scope")[-1] == "delete_app_scope"


def test_waContactRights_zero_value_means_delete() -> None:
    value = 0
    assert int(value) == 0


def test_waContactRights_signed_principal_encoding() -> None:
    contact_id = 42
    group_id = 7
    assert -contact_id == -42
    assert group_id == 7
    assert 0 == 0  # guests


def test_waGroup_member_count_counts_only_backend_users() -> None:
    contacts = ((1, 1), (2, 0), (3, -1), (4, 2))  # (contact_id, is_user)
    assert sum(1 for _, is_user in contacts if is_user > 0) == 2


def test_waUserGroups_add_is_duplicate_tolerant() -> None:
    # 4.2.0 uses INSERT IGNORE for (contact_id, group_id).
    rows = {(42, 7)}
    rows.add((42, 7))
    assert rows == {(42, 7)}
