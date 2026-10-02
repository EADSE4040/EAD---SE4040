# REST API contract

Base path: `/api`. JSON uses camelCase. Authenticated requests send `Authorization: Bearer TOKEN`. Error responses use Problem Details; validation failures include an `errors` object. All scheduling timestamps must contain an explicit UTC offset; replies use UTC. Clients display local time.

| Method / path | Role | Operation |
|---|---|---|
| POST /auth/register | Public | Pending NIC-based prosumer registration |
| POST /auth/login | Public | Active account authentication |
| GET, PUT /auth/me | Any active role | Read/update own profile |
| POST /auth/me/deactivate | Prosumer | Deactivate self |
| GET /users | Staff | Account list; operators see only prosumers |
| POST /users/staff | Backoffice | Create staff |
| POST /users/prosumers | Backoffice | Create active prosumer |
| PUT /users/{id} | Backoffice | Edit prosumer |
| POST /users/{id}/activate, deactivate | Backoffice | Account lifecycle |
| GET /stations | Any active role | Persisted nodes; optional latitude/longitude/radiusKm (default 25 km) nearby filtering |
| POST /stations | Backoffice | Register node |
| PUT /stations/{id} | Staff | Update specifications/schedule |
| DELETE /stations/{id} | Backoffice | Soft-delete from active listings; preserve history and reject active bookings |
| POST /stations/{id}/activate, deactivate | Backoffice | Node lifecycle |
| POST /stations/{id}/slots | Staff | Publish non-overlapping slot |
| GET /slots | Any active role | Future slots; optional stationId filter |
| PUT, DELETE /slots/{id} | Staff | Edit/archive unreserved slot |
| GET /reservations | Any active role | Paginated bookings with status/search/from/to filters; ownership enforced |
| GET /reservations/dashboard | Any active role | Pending, approved-future, completed and active-node counts |
| POST /reservations | Any active role | Create pending request; staff specify prosumerId |
| PUT /reservations/{id} | Owner or staff | Modify with notice |
| POST /reservations/{id}/cancel | Owner or staff | Cancel with notice |
| POST /reservations/{id}/approve, reject | Staff | Review pending booking |
| GET /reservations/{id}/qr | Owner or staff | Signed approved QR payload |
| POST /reservations/verify | Staff | Server verification of QR payload |
| POST /reservations/complete | Staff | Atomic physical-transfer completion |
| GET /health | Public | Actual MongoDB connectivity check |

Creation/update booking JSON: `slotId`, positive `energyKwh`, `direction` (`DropOff` or `Charging`), and staff-only target `prosumerId`. Summaries contain booking ID, prosumer/station IDs and names, slot ID, start/end, energy, direction, status and actual transfer details when completed.

QR verification JSON contains `qrCode`. Completion also contains `transferredKwh`. QR nonce and password hashes are never returned in booking/account lists.
