# Team users.invite — Implementation Plan

Status: implemented
Date: 2026-09-20

- [x] Source-characterize Webasyst 4.2.0 `team.users.invite`.
- [x] Separate code/email-link/phone-link request variants.
- [x] Preserve phone precedence and required POST email behavior.
- [x] Preserve repeated raw `groups[]` values and integer normalization separately.
- [x] Preserve PHP-truthy `add_users` and `manage_group.<id>`.
- [x] Preserve hook-before-validation for link flows and code-flow bypass.
- [x] Preserve link contact reuse, user/banned conflicts and code fresh-contact behavior.
- [x] Keep `wa_app_tokens` in a Team-private Core mapping.
- [x] Preserve token type, payload, three-day TTL, newest-five retention and non-atomic contact-before-token behavior.
- [x] Preserve send=false link and send=true no-link response shapes.
- [x] Model sent/soft-failure/hard-rejection mail outcomes.
- [x] Model disconnected and connected WAID outcomes.
- [x] Keep real mail and connected WAID adapters explicitly deferred.
- [x] Add open application API error codes while keeping framework errors closed.
- [x] Register `team.users.invite` POST-only.
- [x] Prove local/disconnected behavior through production ASGI.
- [x] Prove unavailable `send=true` capability boundary.
- [x] Pass architecture and full regression CI.

## Verification

Code verification head: `a009b1fbdd410b8573774e1caf768c1ab46f567c`, followed by production boundary test `e158c1a7d225d0a2cabebe7c795f6dfc394fc176`.

The green code head before documentation passed full CI with 876 tests and 11 warnings.

## Deferred

Real outbound email provider and connected Webasyst ID client are not production-wired in this slice.
