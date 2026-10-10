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
- Internet access for the OpenFreeMap basemap; no maps API key or billing account is required.
- Windows IIS and .NET 10 Hosting Bundle for the assessed deployment.

The workspace-local `.tools/` directory is ignored; downloaded SDKs, database files and development credentials are never submitted to GitHub.

## Run locally

For this already-provisioned workspace, `powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1` starts or reuses the local MongoDB, API and web services. For a fresh machine, install the prerequisites and follow the steps below.

1. Start a MongoDB replica set. See [deployment instructions](docs/deployment/iis.md) and use a separate database for testing.
2. Run `powershell -ExecutionPolicy Bypass -File scripts/configure-local.ps1`. This creates ignored local configuration and random secrets. Administrator credentials are saved privately in `.tools/dev-credentials.json`.
3. Run `dotnet run --project backend/SolarTrading.Api`. When using the downloaded portable SDK, use `.tools/dotnet/dotnet.exe` instead of `dotnet`.
4. In `frontend/web`, run `npm ci` then `npm run dev`. Open `http://127.0.0.1:5173` and sign in with the administrator created at startup.
5. Create Grid Operator accounts, nodes and future slots through the portal. Prosumers register in Android; Backoffice activates them in the portal.
6. Open `frontend/android` in Android Studio, or run `powershell -ExecutionPolicy Bypass -File scripts/run-android.ps1` to start the configured emulator, build with the workspace Java 17 installation, install the current debug APK and open it. Maps use MapLibre with OpenStreetMap data from OpenFreeMap automatically; see [map configuration](docs/deployment/openstreetmap.md). The default emulator API is the IIS deployment at `http://10.0.2.2:8080/api`; change it in Connection settings when using the local development API or a physical device. Release builds require HTTPS.

Both clients expose meaningful API errors. Android encrypts its SQLite session with Android Keystore; raw passwords are never persisted locally. Cached station data is labelled offline and never authorizes bookings or transfers.

### Physical Android phone over USB

Install the debug APK, enable USB debugging and authorize this laptop on the phone. Keep IIS and MongoDB running. Run `powershell -ExecutionPolicy Bypass -File scripts/connect-android-usb.ps1` to forward IIS port 8080 and configure the current debug app with `http://127.0.0.1:8080/api`.

Run `powershell -ExecutionPolicy Bypass -File scripts/enable-usb-demo-autostart.ps1` once to start the USB reconnect watcher now and at this Windows user's future sign-ins. It restores the forwarding rule after a cable reconnect or ADB restart. Logs are private under `.tools/usb-demo-watcher.log`. With several physical phones attached, run `scripts/start-usb-demo.ps1 -Stop`, then `scripts/start-usb-demo.ps1 -Serial DEVICE_SERIAL` to select one. Use `scripts/enable-usb-demo-autostart.ps1 -Disable` to remove autostart and stop the watcher.

The app's **Test connection** checks the API and database without submitting a transaction. Its visible Back button and Android back gesture return detail/form screens to their parent. USB forwarding requires the cable, an authorized phone and a running laptop server; it does not provide access from other phones or over the internet. Release builds require HTTPS.

If the development API's database or signing configuration changes, run `scripts/sync-iis-configuration.ps1` from administrator Windows PowerShell to update the existing `SolaraApi` IIS pool from the private source configuration. It preserves a private rollback backup, recycles only that pool, checks API/database health, and restores the old settings if health fails. Both clients must use a backend with the same database and signing configuration; pulling source files alone does not update IIS settings. Regenerate transaction QR codes after changing signing keys.

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

For this Windows PC, run `scripts/prepare-iis.ps1` to build the loopback deployment and download/verify Microsoft's Hosting Bundle. Then run `scripts/setup-iis.ps1` from **administrator Windows PowerShell**. It creates dedicated `SolaraApi` and `SolaraWeb` sites at `http://127.0.0.1:8080` and `http://127.0.0.1:8081`, preserving existing sites. Keep the local MongoDB running. Use `http://10.0.2.2:8080/api` in an Android emulator debug build; release and device-network deployments require the HTTPS configuration above.

## Assessment and submission

Read [assignment checklist](docs/planning/assignment-checklist.md), [system design](docs/design.md), and [submission checklist](docs/submission.md). A passing build is not proof of IIS hosting, device features, or viva readiness.

Use the [five-minute demonstration guide](docs/demo-guide.md) after deployment and device verification. The professional report is generated from `docs/report.md` and the verification record. `artifacts/Solara-SE4040-Report.pdf` includes figures, screenshots, references and a source-text appendix. The matching Markdown edition is `artifacts/report-with-source.md`.

Confirmed three-member group: Kojithan P.Y (IT22264220), Baskaran V (IT22172600), Nishara T (IT22223876). The team declares equal contribution: one third (33 1/3%) per member. See [contribution record](docs/contributions.md).

Demo video (maximum five minutes): **deferred at the team's request; not included in this submission package**.

AI disclosure: this repository includes AI-assisted planning and implementation at the user's request. The assignment brief restricts AI to planning. This disclosure must accurately reflect how the work was produced; the team must resolve compliance with its lecturer before submission.

## References

- [ASP.NET Core authentication](https://learn.microsoft.com/en-us/aspnet/core/security/authentication/?view=aspnetcore-10.0)
- [ASP.NET Core on IIS](https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/iis/?view=aspnetcore-10.0)
- [MongoDB atomicity and transactions](https://www.mongodb.com/docs/manual/core/write-operations-atomicity/)
- [MongoDB C# driver](https://www.mongodb.com/docs/drivers/csharp/current/)
- [SQLiteOpenHelper](https://developer.android.com/reference/android/database/sqlite/SQLiteOpenHelper)
- [MapLibre Native for Android](https://maplibre.org/maplibre-native/android/examples/)
- [OpenFreeMap](https://openfreemap.org/)
- [ZXing Android Embedded](https://github.com/journeyapps/zxing-android-embedded)
- [React](https://react.dev/)
- [Bootstrap 5](https://getbootstrap.com/docs/5.3/getting-started/introduction/)
