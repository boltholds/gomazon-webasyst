# Team users.invite — Implementation Plan

Status: implemented
Date: 2026-09-20

- [x] Source-characterize Webasyst 4.2.0 `team.users.invite`.
- [x] Separate code/email-link/phone-link request variants.
- [x] Preserve phone precedence and required POST email behavior.
- [x] Preserve repeated raw `groups[]` values and integer normalization separately.
- [x] Recreate PHP scalar POST last-value semantics without collapsing bracket-array groups.
- [x] Preserve ASCII-only legacy `wa_is_int` recognition.
- [x] Replace approximate email validation with source-derived `waEmailValidator` regex/IDNA/malware semantics.
- [x] Preserve PHP-truthy `add_users` and `manage_group.<id>`.
- [x] Preserve hook-before-validation for link flows and code-flow bypass.
- [x] Preserve link contact reuse, user/banned conflicts and code fresh-contact behavior.
- [x] Keep `wa_app_tokens` in a Team-private Core mapping.
- [x] Preserve token type, payload, three-day TTL, newest-five retention and non-atomic contact-before-token behavior.
- [x] Keep persisted token expiry distinct from link API response-time `time()+3d` expiry.
- [x] Preserve IDNA-decoded absolute root behavior in invitation links.
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

Post-audit code verification head: `ee76902a0c7a048ed4ff5c9ba3599e947e3cb9b2`.

That head passed full GitHub Actions CI with **885 tests and 11 warnings**. The audit added source-backed regressions for PHP scalar POST normalization, the exact Webasyst email validator surface, response-time invitation expiry, IDNA-decoded link roots, and ASCII-only `wa_is_int`.

## Deferred

Real outbound email provider and connected Webasyst ID client are not production-wired in this slice.
