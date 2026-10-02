# 1. Project overview

Solara is a client-server application for coordinating energy drop-off and charging reservations at solar microgrid nodes. Backoffice staff maintain accounts and infrastructure through a web portal. Grid operators manage trading availability, review bookings and record completed transfers. Prosumers use a native Android application to register, reserve energy slots and review their transactions.

The system records planned and completed transfers; it does not control physical inverters, meters or batteries. The operator enters the measured energy after a physical transfer. Demonstration records and screenshots use synthetic data.

## 1.1 Objectives and scope

The implementation provides a central C# REST API, a MongoDB database, a React staff portal and a native Java Android application. Both clients obtain authoritative decisions from the API. Android stores encrypted session information and cached reference data locally in SQLite.

The assessed deployment uses Windows IIS for the API and web application. Local emulator traffic reaches IIS through the Android host alias. Deployment beyond the local demonstration requires HTTPS, appropriate host bindings and production credentials.

## 1.2 Roles and responsibilities

| Role | Access and responsibilities |
|---|---|
| Backoffice | Create staff accounts; manage and activate prosumers; maintain nodes; publish slots; review reservations. |
| Grid Operator | Maintain operational schedules and slots; monitor reservations; approve or reject requests; scan and verify QR codes; record completed energy transfers. |
| Prosumer | Register with NIC; maintain personal details; request deactivation; reserve, modify or cancel slots; view history, approved QR codes and nearby nodes. |

# 2. Requirements and business rules

| Requirement | Implementation |
|---|---|
| NIC identity | The normalized NIC is the MongoDB primary identifier for a prosumer. Staff accounts use generated identifiers. |
| Account activation | Mobile registrations start as Pending. Only Backoffice may activate or reactivate an account. |
| Booking window | A new reservation must start in the future and no later than seven days from the server time. The seven-day boundary is inclusive. |
| Modification and cancellation | Pending or approved reservations may change only with at least twelve hours of notice. The twelve-hour boundary is inclusive. |
| Capacity protection | Pending and approved reservations hold both energy and booking capacity. MongoDB transactions prevent concurrent overbooking. |
| Node removal | Deactivation and soft deletion are rejected while active reservations exist. Historical records are retained. |
| Slot removal | An unreserved slot can be archived. Reserved slots cannot be edited or removed. |
| QR dispatch | Only an approved booking receives a signed transaction payload. Editing a booking invalidates its earlier QR and returns it to Pending. |
| Transfer completion | The server verifies signature, current approval, scheduled time and measured energy. A reservation can complete only once. |

Generation capacity is expressed in kW and traded energy in kWh. This distinguishes power from energy; the assignment uses the ambiguous notation kW/h. The implementation also interprets deletion as removal from active listings while preserving booking history. These interpretations should be confirmed during assessment.

# 3. System architecture

The web portal and Android application communicate with the API through REST requests. Controllers map HTTP requests to account, grid and reservation services. Those services enforce ownership, roles, account status, time limits, capacity and state transitions. Neither client connects directly to MongoDB.

[diagram:architecture]

SQLite is a local session and reference cache, not an alternative source of booking authority. A cached station can be displayed when connectivity fails, but reserving capacity, approving requests and completing transfers require a successful server response.

## 3.1 Use cases

[diagram:use-cases]

## 3.2 Reservation data flow

A reservation request first passes identity and ownership checks. The service verifies the booking window and claims capacity within a transaction. The same transaction saves the reservation and audit record. Approval produces a new QR nonce. Completion checks the current record before changing status and releasing its held capacity.

[diagram:data-flow]

# 4. Database design

| Collection | Identifier | Stored data and references |
|---|---|---|
| Users | NIC for prosumers; generated ID for staff | Name, normalized email, contact details, password hash, role, status, token version and creation time. |
| SolarStationInfo | Node ID | Name, address, latitude, longitude, generation capacity, battery slots, schedule, active state and revision. |
| EnergyBookingSlots | Slot ID | Station ID, UTC start/end, capacity, maximum bookings, reserved energy/count and active state. |
| EnergyReservations | Reservation ID | Prosumer, station and slot IDs; scheduled interval; direction; energy; status; QR nonce; completion details. |
| AuditLog | Event ID | Actor, action, entity identifier and UTC timestamp. |

[diagram:database-model]

The unique email index prevents duplicate accounts, while MongoDB identifier uniqueness enforces NIC identity. Query indexes support station/time and prosumer/status/time lookups. MongoDB runs as a replica set because reservation operations require transactions across several collections.

A revision update on the node serializes conflicting scheduling and deactivation operations. This prevents a reservation from being accepted while another transaction removes the same node from service.

# 5. Application implementation

## 5.1 Staff web portal

The React portal provides role-specific navigation, dashboard counts, user activation, node management, slot scheduling and reservation administration. Bootstrap supplies the responsive layout. Forms send requests to the API and display the returned result or an actionable validation error. Node deletion removes a node from active listings; Backoffice can restore it without breaking historical references.

## 5.2 Native Android application

The Android client uses Java activities and native views. Registration collects NIC and profile information, followed by a pending-activation confirmation. An activated user can sign in, update their profile and manage reservations. Successful create, modify and cancel operations show the resulting reservation summary.

The booking view offers status filtering, text search and paging. The dashboard displays API-provided pending and approved-future counts. The operator view adds camera scanning and transfer completion controls.

## 5.3 Maps and local persistence

Google Maps plots the coordinates stored for active stations. A device location is sent to the API, which filters stations within 25 km. A recent cached location may be used immediately; a bounded location subscription requests a fresh fix. Without location access, all active stations remain available. Selecting a station opens its address, capacity, battery slots and operating schedule.

Map requests carry a screen-local sequence number so an older all-station response cannot replace a newer nearby result. SQLite cache access runs on a worker thread, separate from map rendering. Cached responses are scoped to the requested area and labelled offline. The refresh control retries network and location retrieval.

## 5.4 Reservation lifecycle

A reservation starts as Pending. Staff may approve or reject it. Approval enables QR dispatch. An eligible modification returns it to Pending and invalidates its previous QR. Cancellation, rejection, completion and expiry end the active reservation. A background service expires elapsed pending or approved reservations and releases held capacity.

# 6. Security and error handling

Passwords are processed by ASP.NET's salted password hasher. JWTs include an expiry and are checked against the account's current status and token version. Deactivation therefore revokes existing sessions. Role restrictions and ownership checks apply on the server even when a client hides an unavailable action.

QR payloads are signed with a dedicated HMAC secret. The signature alone is insufficient: verification checks the stored reservation and nonce. Completion runs within a transaction and rejects replay, premature use and measured energy exceeding the reservation.

Android encrypts session JSON with AES-GCM using a non-exportable Android Keystore key before saving it to SQLite. Raw passwords are not stored locally. Release builds require HTTPS; cleartext transport is restricted to the debug configuration. Secrets, local credentials and the Maps key are excluded from source and the submission archive.

# 7. Verification and results

Verification combines database integration tests, live HTTP checks, client builds and device observations. Automated checks use synthetic records. Integration tests create an isolated, randomly named database and remove that database when finished. Existing operational data is not used to establish test outcomes.

[verification]

## 7.1 Evidence limitations

Build success confirms compilation, not complete device behavior. A screenshot confirms a displayed state at the time of capture. Camera verification using an emulator image feed exercises the scanner pipeline, but does not establish performance on every physical device. Any remaining unverified behavior is identified in the accompanying verification record.

# 8. Deployment and operation

The backend requires .NET 10 and MongoDB configured as a replica set. The web client is built with Node.js and npm. Android requires Java 17, SDK 36 and the Gradle wrapper. The Maps SDK key is supplied through the ignored maps.properties file and restricted to the application package and signing certificate.

The repository includes scripts for local configuration, builds, IIS publishing and Android installation. The local assessed endpoints are http://127.0.0.1:8080/api for the service and http://127.0.0.1:8081 for the web portal. The emulator uses http://10.0.2.2:8080/api. See docs/deployment/iis.md for the complete IIS procedure and docs/deployment/google-maps.md for key setup.

Before a demonstration, confirm MongoDB and IIS are running, sign in from both clients and create slots with future timestamps. Old demonstration slots may have expired. Real deployments also require HTTPS certificates, restricted database access, backups and operational monitoring.

# 9. Engineering challenges and decisions

## 9.1 Concurrent reservations

Independent checks of available capacity can accept two requests for the final slot. The solution combines capacity claims, reservation writes and audit entries in a MongoDB transaction. The integration suite races ten requests for a single available booking and verifies that only one succeeds.

## 9.2 Time boundaries and stale QR codes

Client clocks cannot safely enforce booking windows. The service uses UTC server time and inclusive boundary checks. Tests use a controlled clock to verify exact seven-day and twelve-hour cases. A reservation revision requires new approval and a new QR nonce, preventing an old screenshot from authorizing a changed booking.

## 9.3 Device rendering and asynchronous responses

Earlier emulator captures showed a non-responsive Maps screen. The map flow also used only last-known location and could allow a stale response to replace nearby results. The revised implementation separates cache I/O from rendering, bounds location subscriptions and ignores superseded responses. Device evidence is recorded separately from these code changes because a successful build alone cannot establish rendering stability.

## 9.4 Reproducible deployment

The initial environment required SDKs, MongoDB and IIS provisioning. Workspace-local tools simplified setup without adding binaries or credentials to source control. Deployment scripts and explicit endpoint configuration make the same service accessible to the browser and emulator. Environment-specific paths and secrets remain outside the submission.

# 10. Team contribution and development statement

[contributions]

# 11. Delivery status

The submission archive is named IT22264220.zip and contains source files, supporting documentation, the PDF report and an opening-screen screenshot. The demonstration video is deferred at the team's request and is not included. Lecturer confirmation of group size and AI-use compliance remains an external assessment requirement. Each member must attend and prepare for the individual viva.

# Appendix A. Application screens

[screenshots]

# Appendix B. References

[references]

# Appendix C. Source listing

[source]
