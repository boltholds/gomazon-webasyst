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
- [ ] Add executable source-characterization fixture.
- [ ] Update ADR/architecture record.
- [ ] Run final full CI and record exact count.
