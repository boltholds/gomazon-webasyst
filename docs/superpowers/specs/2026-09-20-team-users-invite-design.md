# Team users.invite — Design

Status: implemented
Date: 2026-09-20
Authoritative source: Webasyst Framework 4.2.0 release commit `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`

## Goal

Migrate `team.users.invite` through the installed Team runtime while preserving distinct code, email-link and phone-link behavior without coupling application code to SQLAlchemy, HTTP form details, outbound mail, or Webasyst ID clients.

## Request boundary

Compatibility parses POST into `TeamInvitationCodeRequest`, `TeamInvitationEmailLinkRequest`, or `TeamInvitationPhoneLinkRequest`. The exact value `type=code` selects code flow. In link mode a PHP-truthy phone has precedence over email/send; otherwise email is a required POST parameter and PHP-falsy absence is a framework `invalid_param` before application execution.

Repeated form values are preserved by the common legacy API transport, so `groups[]` reaches Team as an immutable tuple. Raw trimmed group strings remain available to `team.invite_user`; integer-like ids are normalized separately for rights and token data.

## Authorization and hook ordering

The actor needs PHP-truthy Team `add_users`. Scalar dotted rights preserve ordinary `.all` fallback and non-zero negative values remain truthy.

Requested integer groups enter token data only when `manage_group.<id>` is truthy. Group existence is not separately validated.

Email/phone link flows publish `team.invite_user` before channel validation. Truthy handler results are stringified and newline-joined into a `general` error. Code flow skips both hook and channel validation.

## Contact lifecycle

Email/phone link flows reuse an existing `is_user=0` contact by exact legacy channel lookup. Existing users return `user_in_team`; banned `is_user=-1` contacts with login return `contact_banned`. Otherwise Team creates an invite contact with `create_app_id=team`, `create_method=invite`, and the API actor as creator.

Code flow does not reuse an existing contact by email/phone; it creates a fresh contact.

## Token lifecycle

Team invitation infrastructure owns a private SQLAlchemy Core mapping of legacy `wa_app_tokens`; the table is intentionally absent from shared ORM metadata.

- link token type: `user_invite`;
- code token type: `waid_invite`;
- lifetime: three days;
- payload always includes `full_access:false`;
- `groups` is emitted only when the original group request was non-empty and contains only manageable integer ids;
- newest five tokens are retained per contact/app/type.

Contact creation and token creation remain separate committed operations, preserving the source-like non-atomic case where a token collision can leave the newly created contact.

## Result shapes

Link without mail sending returns `contact_id`, `invitation_link`, and `invitation_expire`.

Email link with `send=true` returns `contact_id` and `invitation_expire` after an accepted delivery result; it intentionally omits the link.

Disconnected code flow returns only `contact_id`.

Connected WAID behavior is modeled behind a port: remote success returns code/expiry; remote failure deletes the local token and returns `token_not_created` with remote details.

## External capabilities

The mail port distinguishes sent, soft-failure, and hard rejection. Sent and soft-failure are successful because legacy ignores a false mailer send result. Hard/template rejection maps to `email_send_fail`.

Production currently has no real outbound mail provider and wires that absence as an explicit hard-unavailable adapter. Production WAID is explicitly disconnected. Concrete mail and connected-WAID adapters are later slices and are not included in the parity claim.

## API errors

Framework errors stay a closed enum. Method-specific legacy error codes use open validated `ApiApplicationErrorCode` values, allowing `user_in_team`, `contact_banned`, `email_send_fail`, and literal `Access denied` without widening the framework domain.

Source HTTP statuses are preserved: access denied 403, contact conflicts 409, token-not-created 500, remaining invitation errors 400.

## Acceptance

Local/disconnected production behavior is proven through `/api.php/team.users.invite` using the real API token pipeline, installed Team runtime, ACL tables and legacy persistence. Tests cover repeated groups, rights filtering, contact reuse, fresh code contact creation, token data, conflict mapping, unavailable send boundary and POST-only enforcement.
