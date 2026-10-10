# Verification evidence

## IIS configuration alignment - 10 October 2026

- Found that the development API on port 5080 used the configured MongoDB Atlas database while the IIS API on port 8080 still served the earlier database. The saved user1 demo credentials succeeded only on 5080; the reported QR booking was absent from IIS.
- Synchronized the existing IIS API pool's database and signing settings with the working source API configuration using `scripts/sync-iis-configuration.ps1`. A private backup is retained under `.tools/`; no database records were deleted or passwords reset.
- After synchronization, the user1 demo login returned HTTP 200 through IIS. The reported booking's current signed QR returned HTTP 200 when generated and verified on either endpoint, including cross-endpoint verification.
- Physical Samsung phone login with the existing user1 demo credentials succeeded after the sync. The native dashboard displayed Demo Consumer 1 and live counts (one pending, three approved upcoming, zero completed).
- This verifies API login and signed QR validation. Physical camera scanning and transfer completion are separate checks; a future booking cannot complete before its scheduled slot.

## Checks completed

- C# API and test-runner compilation succeeded; the final Release suite completed successfully.
- Final integration suite: 35 checks passed against a real isolated MongoDB replica set, including simultaneous requests for the final slot, nearby-node filtering and automatic expiry/capacity release.
- Final live HTTP suite: 38 assertions passed against the running Release API, covering role restrictions, pending activation, mutation responses, nearby filtering, QR tampering, invalidation after edits and immediate session revocation.
- Web production build passed; npm audit reported no known vulnerabilities in production or development dependencies.
- Backend dependency audit reported no known vulnerable packages, including transitive dependencies, after upgrading MongoDB.Driver.
- Android debug APK build and lint passed; zero lint errors, with three advisory dependency-update warnings.
- Browser verified staff login, live dashboard counts, navigation to each staff page, and an actual reservation form submission returning a summary.
- Unique web screenshots are saved under `docs/screenshots/`. Records shown are synthetic demonstration data, not real energy transactions.
- Local IIS API/web artifacts were published successfully; the official .NET 10.0.12 Hosting Bundle passed SHA512 and Microsoft Authenticode signature verification. Setup scripts passed PowerShell syntax checks.
- IIS installation and dedicated SolaraApi/SolaraWeb sites completed. Both return HTTP 200 with Microsoft-IIS/10.0 headers; browser staff login and dashboard were verified through IIS. All 38 live HTTP assertions also passed against the IIS API.
- MongoDB now runs as the automatic-start SolaraMongo Windows service. Database connection health was rechecked after service installation and API pool recovery.
- Actual IIS configuration, HTTP responses, MongoDB collection counts and indexes are captured under `docs/evidence`; screenshots clearly label generated database snapshots.
- Google APIs Android 15 emulator and signed acceleration driver installed. Native registration against IIS, pending-account login rejection, Backoffice web activation and subsequent Android login passed.
- Android session survived process restart and APK update. A read-only SQLite inspection confirmed encrypted session storage; evidence omits credentials and ciphertext.
- Android reservation creation (5 kWh), modification (6 kWh), cancellation and corresponding summaries were verified against the persisted IIS API records. Approved-status filtering, web approval of a separate native request and signed QR display passed.
- Device testing found that form errors could be hidden above the scroll position; the app now scrolls the error into view. System-bar icon contrast was also corrected. Updated APK build and lint passed.

## Remaining external verification

- Android camera scanning, completion and current OpenStreetMap/MapLibre device verification are the remaining integration checks.
- Maps now use MapLibre/OpenFreeMap with OpenStreetMap data; no Google API key is required. Previous Google Maps screenshots do not verify the replacement.
- The group has three confirmed members. Actual contribution details, submission ZIP owner and the accessible demo-video link are outstanding; confirm the group-size arrangement with the lecturer.

Passing code/build checks do not establish those external criteria or guarantee marks. The source and instructions are prepared to support their completion.

## OpenStreetMap migration — 9 October 2026

- Replaced Google Maps with MapLibre Native Android 13.5.2 (OpenGL) and OpenFreeMap Liberty/OpenStreetMap data. Google Maps SDK and key configuration are no longer used.
- Android `assembleDebug lintDebug` passed. Native station layers, marker details, location integration and lifecycle methods compile successfully.
- Device rendering verification remains pending: initial emulator startup failed due to insufficient host RAM; the reduced-memory retry has not become responsive. Previous Google Maps screenshots do not verify this replacement.
