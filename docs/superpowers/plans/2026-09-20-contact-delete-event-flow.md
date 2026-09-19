# Contact Delete Event Flow — Implementation Plan

Status: implemented
Date: 2026-09-20

- [x] Characterize exact `waContactModel::delete()` sequence.
- [x] Characterize `deleteById()` no-missing-result behavior.
- [x] Characterize verification asset address cleanup.
- [x] Characterize category counter recalculation quirk.
- [x] Add immutable `ContactDeletionBatch`.
- [x] Add typed `ContactsDeleteEventPayload`.
- [x] Extend contact persistence port with batch deletion.
- [x] Publish `contacts.delete` before destructive UoW.
- [x] Implement core legacy cleanup tables/order in SQLAlchemy adapter.
- [x] Preserve source company-reference clearing.
- [x] Preserve source category-counter zero-member quirk.
- [x] Wire DeleteContacts to the shared runtime EventPublisher.
- [x] Add native DELETE contact route.
- [x] Unit-test event-before-cleanup ordering.
- [x] Test publisher failure prevents destructive UoW.
- [x] Integration-test legacy cleanup persistence.
- [x] Integration-test real DeleteContacts -> Team nested event -> cleanup.
- [x] Integration-test production HTTP deletion path.
- [x] Add executable source-characterization fixture.
- [x] Update ADR/architecture record.
- [x] Run final full CI and record exact count.


## Verification record

Final code head before completion-documentation commits: `6c855fff631016dc0a90b776b0bc89b376ff018a`.

GitHub Actions completed successfully on that head:

- source-tree compile passed;
- `820 passed, 9 warnings`;
- exact Webasyst 4.2.0 contact-delete characterization passed;
- contact delete publishes `contacts.delete` before destructive UoW entry;
- immutable deletion scope/order/duplicates are pinned;
- legacy cleanup persistence across core contact-owned tables passed;
- Team relay is reached from the real DeleteContacts use case;
- nested Team consumer observes the contact still present during event dispatch;
- contact is absent after cleanup commit;
- native production DELETE route executes the real deletion path;
- architecture guards for EventPublisher and immutable destructive scope passed.
