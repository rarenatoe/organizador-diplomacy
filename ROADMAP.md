# Roadmap & Future Features

This document consolidates the planned ideas and initiatives for future releases of the **Diplomacy Games Organizer**.

## 🤖 1. Improved Distribution Algorithms
- [ ] **Social Matchmaking:** Avoid seating players from the same club or close group together by assigning "negative weights" to pre-identified relationships.

## 🖥 2. Admin Tools & User Experience (UI/UX)
- [ ] **Data Reconciliation Dashboard (Player Directory):** Implement a dedicated route to handle unlinked local players asynchronously. To preserve a fast, non-blocking draft creation workflow, the system will allow unlinked players to be drafted immediately. Meanwhile, a background similarity checker will populate a "⚠️ Requires Attention" tab in the dashboard (e.g., *"Daniel Eil (Local) seems to match DaniVonKlaus (Notion). [Link]"*), allowing organizers to perform database maintenance at their own pace.
- [ ] **Drag & Drop for Tables:** Extend the state logic in `Svelte 5` to allow freely dragging and dropping players between tables and the waitlist, while maintaining backend mathematical reconciliation.
- [ ] **Individual Player Dashboards:** A profile view that groups and charts the player's history extracted from `NotionCache` across all seasons.