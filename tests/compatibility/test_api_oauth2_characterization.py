"""Golden characterization excerpts from the supplied Webasyst Framework 4.2.0 source."""


DB_SCHEMA_SOURCE = r"""
'wa_api_auth_codes' => array(
    'code' => array('varchar', 32, 'null' => 0),
    'contact_id' => array('int', 11, 'null' => 0),
    'client_id' => array('varchar', 32, 'null' => 0),
    'scope' => array('text', 'null' => 0),
    'expires' => array('datetime', 'null' => 0),
    ':keys' => array('PRIMARY' => 'code'),
),
'wa_api_tokens' => array(
    'contact_id' => array('int', 11, 'null' => 0),
    'client_id' => array('varchar', 32, 'null' => 0),
    'token' => array('varchar', 32, 'null' => 0),
    'scope' => array('text', 'null' => 0),
    'create_datetime' => array('datetime', 'null' => 0),
    'last_use_datetime' => array('datetime'),
    'expires' => array('datetime'),
    ':keys' => array(
        'PRIMARY' => 'token',
        'contact_client' => array('contact_id', 'client_id', 'unique' => 1),
    ),
),
"""

AUTH_CODE_SOURCE = r"""
$code = md5(microtime(true).uniqid());
// + 3 min
$expires = date('Y-m-d H:i:s', time() + 180);
"""

TOKEN_MODEL_SOURCE = r"""
$row = $this->getByField(array('client_id' => $client_id, 'contact_id' => $contact_id));
if ($row) {
    if ($row['scope'] != $scope) {
        $this->updateById($row['token'], array('scope' => $scope));
    }
    return $row['token'];
} else {
    $token = $this->generateToken();
    $this->insert(array(
        'token' => $token,
        'client_id' => $client_id,
        'contact_id' => $contact_id,
        'scope' => $scope,
        'create_datetime' => date('Y-m-d H:i:s'),
        'expires' => null
    ));
    return $token;
}
"""

TOKEN_CONTROLLER_SOURCE = r"""
$row = $auth_codes_model->getById($code);
if ($row) {
    if ($row['client_id'] != waRequest::post('client_id')) {
        return;
    }
    if (strtotime($row['expires']) < time()) {
        return;
    }
    $token_model = new waApiTokensModel();
    $token = $token_model->getToken($row['client_id'], $row['contact_id'], $row['scope']);
    $this->response(array('access_token' => $token));
}
"""


def test_wa_api_auth_codes_schema_is_32_char_code_with_required_expiry() -> None:
    assert "'code' => array('varchar', 32, 'null' => 0)" in DB_SCHEMA_SOURCE
    assert "'expires' => array('datetime', 'null' => 0)" in DB_SCHEMA_SOURCE
    assert "'PRIMARY' => 'code'" in DB_SCHEMA_SOURCE


def test_wa_api_tokens_schema_keeps_nullable_usage_and_expiry_and_unique_subject_client() -> None:
    assert "'token' => array('varchar', 32, 'null' => 0)" in DB_SCHEMA_SOURCE
    assert "'last_use_datetime' => array('datetime')" in DB_SCHEMA_SOURCE
    assert "'expires' => array('datetime')" in DB_SCHEMA_SOURCE
    assert "'contact_client' => array('contact_id', 'client_id', 'unique' => 1)" in DB_SCHEMA_SOURCE


def test_webasyst_authorization_code_lifetime_is_exactly_180_seconds() -> None:
    assert "time() + 180" in AUTH_CODE_SOURCE


def test_webasyst_token_reuses_subject_client_token_and_updates_scope_without_rotation() -> None:
    assert "getByField(array('client_id' => $client_id, 'contact_id' => $contact_id))" in TOKEN_MODEL_SOURCE
    assert "updateById($row['token'], array('scope' => $scope))" in TOKEN_MODEL_SOURCE
    assert "return $row['token']" in TOKEN_MODEL_SOURCE
    assert "'expires' => null" in TOKEN_MODEL_SOURCE


def test_webasyst_successful_code_exchange_does_not_consume_authorization_code() -> None:
    assert "$auth_codes_model->getById($code)" in TOKEN_CONTROLLER_SOURCE
    assert "$token_model->getToken($row['client_id'], $row['contact_id'], $row['scope'])" in TOKEN_CONTROLLER_SOURCE
    assert "deleteById" not in TOKEN_CONTROLLER_SOURCE
    assert "deleteByField" not in TOKEN_CONTROLLER_SOURCE
