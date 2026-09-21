# Team users.invite — Design

Status: implemented
Date: 2026-09-20
Authoritative source: Webasyst Framework 4.2.0 release commit `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`

## Goal

Migrate `team.users.invite` through the installed Team runtime while preserving distinct code, email-link and phone-link behavior without coupling application code to SQLAlchemy, HTTP form details, outbound mail, or Webasyst ID clients.

## Request boundary

Compatibility parses POST into `TeamInvitationCodeRequest`, `TeamInvitationEmailLinkRequest`, or `TeamInvitationPhoneLinkRequest`. The exact value `type=code` selects code flow. In link mode a PHP-truthy phone has precedence over email/send; otherwise email is a required POST parameter and PHP-falsy absence is a framework `invalid_param` before application execution.

The common Python API transport preserves repeated form pairs, but the Team compatibility parser recreates the shapes PHP would expose in `$_POST`: repeated unbracketed scalar parameters resolve to the last value, while `groups[]` remains an array. Repeated unbracketed `groups` therefore collapses to its final scalar before `TYPE_ARRAY_TRIM`-style normalization. Raw trimmed group strings remain available to `team.invite_user`; integer ids are normalized separately for rights and token data using legacy `wa_is_int` semantics, including ASCII-only digit recognition.

## Authorization and hook ordering

The actor needs PHP-truthy Team `add_users`. Scalar dotted rights preserve ordinary `.all` fallback and non-zero negative values remain truthy.

Requested integer groups enter token data only when `manage_group.<id>` is truthy. Group existence is not separately validated.

Email/phone link flows publish `team.invite_user` before channel validation. Truthy handler results are stringified and newline-joined into a `general` error. Code flow skips both hook and channel validation.

Channel validation is source-derived rather than approximated. Phone validation uses the exact simple Webasyst character class and rejects empty values. Email validation mirrors `waEmailValidator`: its RFC-oriented regex behavior, IDNA domain normalization and explicit `<script` malware-substring rejection are preserved, including domain-literal addresses accepted by the legacy validator.

## Contact lifecycle

Email/phone link flows reuse an existing `is_user=0` contact by exact legacy channel lookup. Existing users return `user_in_team`; banned `is_user=-1` contacts with login return `contact_banned`. Otherwise Team creates an invite contact with `create_app_id=team`, `create_method=invite`, and the API actor as creator.

Code flow does not reuse an existing contact by email/phone; it creates a fresh contact.


For any freshly created invite contact, persistence and event ordering are explicit: the contact plus email/phone channel data are committed first, then synchronous `contacts.save` is published, and only after the event returns may invitation-token creation begin. Event handlers therefore observe the persisted contact/channel state and no invitation token yet. Reused existing contacts do not publish this save event.

## Token lifecycle

Team invitation infrastructure owns a private SQLAlchemy Core mapping of legacy `wa_app_tokens`; the table is intentionally absent from shared ORM metadata.

- link token type: `user_invite`;
- code token type: `waid_invite`;
- persisted token lifetime: three days from token creation;
- payload always includes `full_access:false`;
- `groups` is emitted only when the original group request was non-empty and contains only manageable integer ids;
- newest five tokens are retained per contact/app/type.

Contact creation and token creation remain separate committed operations, preserving the source-like non-atomic case where a token collision can leave the newly created contact.

Invitation links reproduce `waAppTokensModel::getLink()` at the compatibility edge: the absolute public root hostname is IDNA-decoded before `link.php/<urlencoded-token>/` is constructed.

## Result shapes

Link without mail sending returns `contact_id`, `invitation_link`, and `invitation_expire`.

Email link with `send=true` returns `contact_id` and `invitation_expire` after an accepted delivery result; it intentionally omits the link.

The link-flow response expiry is deliberately not copied from the persisted token row. Legacy `teamUsersInviteMethod::execute()` assigns `time() + 259200` only after create/send succeeds, so the compatibility API method owns an injected response clock and computes that value at projection time. The persisted token still expires three days from its own earlier creation time. Connected WAID code expiry remains the remote value returned by Webasyst ID.

Disconnected code flow returns only `contact_id`.

Connected WAID behavior is modeled behind a port: remote success returns code/expiry; remote failure deletes the local token and returns `token_not_created` with remote details.

## External capabilities

The mail port distinguishes sent, soft-failure, and hard rejection. Sent and soft-failure are successful because legacy ignores a false mailer send result. Hard/template rejection maps to `email_send_fail`.

Production currently has no real outbound mail provider and wires that absence as an explicit hard-unavailable adapter. Production WAID is explicitly disconnected. Concrete mail and connected-WAID adapters are later slices and are not included in the parity claim.

## API errors

Framework errors stay a closed enum. Method-specific legacy error codes use open validated `ApiApplicationErrorCode` values, allowing `user_in_team`, `contact_banned`, `email_send_fail`, and literal `Access denied` without widening the framework domain.

Source HTTP statuses are preserved: access denied 403, contact conflicts 409, token-not-created 500, remaining invitation errors 400.

## Acceptance

Local/disconnected production behavior is proven through `/api.php/team.users.invite` using the real API token pipeline, installed Team runtime, ACL tables and legacy persistence. Tests cover PHP scalar-vs-array POST normalization, ASCII `wa_is_int`, source email/phone validation, rights filtering, contact reuse, fresh code contact creation, committed `contacts.save`-before-token ordering, token data, response-time expiry, IDNA link roots, conflict mapping, unavailable send boundary and POST-only enforcement.
