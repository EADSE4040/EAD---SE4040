# SE4040 assignment planning checklist

This is an AI-assisted planning starting point. The team must critically evaluate and refine it, implement the assessed system independently, and disclose planning assistance in its own report. This checklist is not evidence of implementation or a guarantee of marks.

## Repository layout

- `backend/`: central C# Web API and its tests.
- `frontend/web/`: web UI for Backoffice and Grid Operator roles.
- `frontend/android/`: pure native Android app with SQLite for prosumers and operators.
- `docs/`: team-authored design decisions, deployment instructions, screenshots, and submission evidence.

The local parent directory is the Git repository root. Its name is not included as an extra directory in the GitHub file tree.

## Group assessment: 35 marks

- [ ] Service architecture (8): C# API hosted on Windows IIS; stable MongoDB access; both clients reach the service; authoritative business logic stays in the API.
- [ ] Database modelling (4): user details, SolarStationInfo, EnergyBookingSlots, and energy reservations; required fields, consistent references, and sample data.
- [ ] Client architecture (12): native Android with SQLite; web UI; reliable API calls and graceful error handling.
- [ ] UI and experience (6): consistent complete Android and web screens; Bootstrap 5 or Tailwind CSS on web; complete home page.
- [ ] Documentation (5): unique screenshots of every UI, high-level/use-case/DFD diagrams, references, individual contributions, challenges, source code as text, and reproducible deployment steps.

## Individual assessment: 65 marks

- [ ] Web features (18): role-specific login, user management, nodes and slots, reservation creation/update/cancellation.
- [ ] Mobile accounts (9): role-specific home screens, NIC-based registration, actionable pending activation in web, profile editing, deactivation.
- [ ] Mobile reservations (9): create/update/cancel requests and a summary after each action.
- [ ] Booking views (10): current/pending bookings, history, filters, pending reservation dashboard, approved future reservation counts from the API.
- [ ] Operator and maps (7): QR scan verified by server, completion of energy transfer, nearby stations from stored coordinates, station details on selection.
- [ ] Integrations (12): both clients use the hosted API; SQLite login/reference persistence; Google Maps; QR scanning and server verification.

## API business-rule verification plan

- [ ] Create reservations only within the seven-day window; agree exact boundary semantics.
- [ ] Updates and cancellations require at least twelve hours' notice; test before, at, and after the boundary.
- [ ] Reject node deactivation when active reservations exist.
- [ ] Only Backoffice can reactivate deactivated prosumers.
- [ ] Enforce role permissions and reservation ownership on the server.
- [ ] Prevent overbooking, including simultaneous requests for the final available slot.
- [ ] Only approved valid reservations receive usable transaction QR codes.
- [ ] Verify QR data against server records and prevent repeated completion.
- [ ] Verify inactive-account restrictions and accurate dashboard counts.
- [ ] Verify API failures, expired authentication, connectivity loss, and SQLite persistence after app restart.

## Decisions requiring clarification

- Confirm who activates new accounts and approves bookings.
- Reconcile station/slot deletion in the rubric with node deactivation constraints in the specification.
- Confirm the intended energy/capacity units; the brief uses `kW/h`.
- Agree reservation status transitions, timezone, and exact seven-day booking boundary.

## Suggested implementation order

1. Team agrees roles, data model, states, API contract, and ownership of work.
2. Team establishes IIS hosting and connectivity from both clients early.
3. Team implements registration to activation to booking to approval to QR to operator completion.
4. Team completes editing/cancellation, node/slot management, dashboards, history/search, maps, and SQLite.
5. Team verifies all rules and integrations and captures evidence from the final application.
6. Each member writes their contribution and rehearses explaining and modifying their work.

## Submission gates

- [ ] Header comment block on every `.cs` file.
- [ ] Inline comments at the beginning of every method, as required by the brief.
- [ ] Unique application screenshots, including the opening screen.
- [ ] Report includes all UI screenshots, diagrams, database design, source code pasted as text, references, repository link, contributions, and challenges.
- [ ] README includes repository link, clear individual contributions, and a working video link of no more than five minutes.
- [ ] AI planning assistance is disclosed and reflected on in the team's own words.
- [ ] Meaningful descriptive Git history reflects actual work by each member.
- [ ] Single ZIP contains all required project files and report; ZIP filename includes the required IT number.
- [ ] Submission completed by 30 September 2026, 11:59 PM.
- [ ] Every member attends the compulsory viva and can explain their own implementation.

