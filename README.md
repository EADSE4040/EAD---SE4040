# Solara — Smart Solar Microgrid Trading System

Repository: https://github.com/EADSE4040/EAD---SE4040

C#/.NET 10 REST API with MongoDB, a React + Bootstrap 5 staff portal, and a pure native Java Android application with SQLite. All authoritative business logic is in the central API.

## Layout

```text
backend/SolarTrading.Api/       API, services, MongoDB persistence
backend/SolarTrading.Tests/     Real-MongoDB transaction and business-rule checks
frontend/web/                  React staff portal
frontend/android/              Native Android application
docs/                          Design, verification, deployment and submission evidence
scripts/                       Local configuration, build and IIS publish helpers
```

## Requirements

- .NET 10 SDK (a runtime alone is insufficient).
- MongoDB 8.0+ configured as a replica set, including for local development.
- Node.js 22.12+ or a compatible newer version and npm.
- Android Studio or Java 17, Android SDK 36, and Gradle wrapper.
- Google Maps Android API key, restricted to this application's package and signing certificate.
- Windows IIS and .NET 10 Hosting Bundle for the assessed deployment.

The workspace-local `.tools/` directory is ignored; downloaded SDKs, database files and development credentials are never submitted to GitHub.

## Run locally

1. Start a MongoDB replica set. See [deployment instructions](docs/deployment/iis.md) and use a separate database for testing.
2. Run `powershell -ExecutionPolicy Bypass -File scripts/configure-local.ps1`. This creates ignored local configuration and random secrets. Administrator credentials are saved privately in `.tools/dev-credentials.json`.
3. Run `dotnet run --project backend/SolarTrading.Api`. When using the downloaded portable SDK, use `.tools/dotnet/dotnet.exe` instead of `dotnet`.
4. In `frontend/web`, run `npm ci` then `npm run dev`. Open `http://127.0.0.1:5173` and sign in with the administrator created at startup.
5. Create Grid Operator accounts, nodes and future slots through the portal. Prosumers register in Android; Backoffice activates them in the portal.
6. Open `frontend/android` in Android Studio. Copy `maps.properties.example` to `maps.properties`, enter your restricted key, and build/run. The default API is `http://10.0.2.2:5080/api` for the emulator. Change it in Connection settings for a physical device or IIS. Release builds require HTTPS.

Both clients expose meaningful API errors. Android encrypts its SQLite session with Android Keystore; raw passwords are never persisted locally. Cached station data is labelled offline and never authorizes bookings or transfers.

## Business rules

- New reservations must start in the future, at most seven days from the server's current UTC time; exactly seven days is accepted.
- Modification and cancellation require at least twelve hours' notice; exactly twelve hours is accepted.
- Pending and approved bookings hold capacity. Transactions protect energy and battery limits against concurrent requests.
- A modified booking becomes pending and invalidates its old QR code.
- Backoffice alone activates/reactivates accounts. Grid Operators and Backoffice review reservations.
- Nodes with pending/approved bookings cannot deactivate. Slots with held bookings cannot be edited or archived. Archival preserves booking history.
- QR dispatch is signed with a dedicated server secret. Transfer completion requires the current approved QR, a scheduled time window and positive actual energy no larger than the reservation. Completion is single-use.
- Elapsed active reservations are marked expired and their capacity released by a periodic worker.
- Generation capacity is measured in kW; traded energy in kWh. This resolves the brief's ambiguous `kW/h` notation and should be confirmed with the lecturer.

## Verification

```powershell
dotnet build backend/SolarTrading.Tests/SolarTrading.Tests.csproj
$env:MONGO_TEST_URL='mongodb://127.0.0.1:27018/?replicaSet=rs0'
dotnet run --project backend/SolarTrading.Tests
cd frontend/web
npm ci
npm run build
cd ../android
./gradlew.bat assembleDebug lintDebug
```

The test runner creates and drops only a randomly named test database. The `--init` option initializes the development replica set at `127.0.0.1:27018`; do not use this operation against an unrelated instance.

For IIS release output, run `scripts/publish.ps1 -ApiUrl https://YOUR_API_HOST/api`, then follow [IIS deployment](docs/deployment/iis.md). This command generates artifacts; it does not configure IIS or deploy them automatically.

## Assessment and submission

Read [assignment checklist](docs/planning/assignment-checklist.md), [system design](docs/design.md), and [submission checklist](docs/submission.md). A passing build is not proof of IIS hosting, device features, or viva readiness.

Individual contributions: **awaiting the four members' names, IT numbers and actual contribution details**. Record each person's real work and commits; do not fabricate ownership.

Demo video (maximum five minutes): **awaiting recording and upload by the team**.

AI disclosure: this repository includes AI-assisted planning and implementation at the user's request. The assignment brief restricts AI to planning. This disclosure must accurately reflect how the work was produced; the team must resolve compliance with its lecturer before submission.

## References

- [ASP.NET Core authentication](https://learn.microsoft.com/en-us/aspnet/core/security/authentication/?view=aspnetcore-10.0)
- [ASP.NET Core on IIS](https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/iis/?view=aspnetcore-10.0)
- [MongoDB atomicity and transactions](https://www.mongodb.com/docs/manual/core/write-operations-atomicity/)
- [MongoDB C# driver](https://www.mongodb.com/docs/drivers/csharp/current/)
- [SQLiteOpenHelper](https://developer.android.com/reference/android/database/sqlite/SQLiteOpenHelper)
- [Google Maps SDK for Android](https://developers.google.com/maps/documentation/android-sdk/overview)
- [ZXing Android Embedded](https://github.com/journeyapps/zxing-android-embedded)
- [React](https://react.dev/)
- [Bootstrap 5](https://getbootstrap.com/docs/5.3/getting-started/introduction/)
