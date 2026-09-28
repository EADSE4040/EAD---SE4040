# Verification evidence

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

## Remaining external verification

- IIS is not installed on this Windows 11 Home PC and the current process is not an administrator. Local publish files and an administrator setup script are prepared; installation, site health and both-client reachability still need verification after setup.
- No Android device/emulator is currently connected. Runtime SQLite, camera scanning, permission behavior, maps and end-to-end mobile interaction need device testing.
- Google Maps needs a valid Android-restricted API key in ignored `frontend/android/maps.properties` before rebuilding.
- The group has three confirmed members. Actual contribution details, submission ZIP owner and the accessible demo-video link are outstanding; confirm the group-size arrangement with the lecturer.

Passing code/build checks do not establish those external criteria or guarantee marks. The source and instructions are prepared to support their completion.
