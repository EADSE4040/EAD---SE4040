# IIS deployment and local MongoDB

## MongoDB

Transactions need a replica set. For isolated development, create a writable database directory, then start a local instance bound to localhost:

```powershell
mongod --dbpath PATH_TO_LOCAL_DATA --bind_ip 127.0.0.1 --port 27018 --replSet rs0
```

Initialize using `mongosh`:

```javascript
rs.initiate({_id:'rs0', members:[{_id:0,host:'127.0.0.1:27018'}]})
```

Alternatively, the C# test runner's `--init` command performs exactly this local initialization. Wait for the member to become primary before running the API or tests. Production MongoDB must use authentication, restricted network access and appropriate replica-set resilience. Use the connection string supplied by the actual deployment; do not expose MongoDB to either client.

## Windows IIS prerequisites

### Prepared setup for this PC

IIS and the .NET 10 Hosting Bundle are installed on this Windows 11 Home PC. Both dedicated sites return HTTP 200 and the API reports its MongoDB connection as healthy. Installation used an administrator PowerShell process through Windows UAC. The steps below reproduce the initial installation.

1. In the repository, run `powershell -ExecutionPolicy Bypass -File scripts/prepare-iis.ps1`. This publishes into `artifacts/iis-local` and downloads the .NET 10.0.12 Hosting Bundle from Microsoft's release metadata, checking its SHA512 hash and Microsoft Authenticode signature.
2. Keep the local MongoDB replica set running using `scripts/start-local.ps1`.
3. In **administrator Windows PowerShell**, run:

```powershell
& 'C:\Users\Koji\Desktop\EAD - SE4040\scripts\setup-iis.ps1'
```

The script enables IIS through DISM, installs the Hosting Bundle after IIS, creates separate No Managed Code application pools, stores secrets in administrator-managed IIS pool configuration, grants read/execute permissions to the published files, and checks both sites. Anonymous IIS file access uses the application pool identity. It stops on existing site/pool names or occupied ports. If Windows requests a reboot, restart and rerun the setup script. IIS settings captured from the running server are in `docs/evidence/iis-configuration.json`.

The portal is `http://127.0.0.1:8081` and health is `http://127.0.0.1:8080/api/health`. An emulator debug build uses `http://10.0.2.2:8080/api`. These loopback HTTP bindings support local assessment testing; use trusted HTTPS and network-reachable bindings for release/physical-device deployment.

MongoDB is now installed as the automatic-start `SolaraMongo` Windows service under LocalService, using the existing replica-set data and binding only to `127.0.0.1:27018`. `scripts/install-mongodb-service.ps1` performs that administrator setup. Data and service logs have dedicated write permissions. Restarting the IIS API pool after database recovery resolves a previously failed application startup. Keep the workspace at its current path because the service and IIS sites reference it.

### HTTPS deployment

1. Enable IIS with management tools and static content support.
2. Install the .NET 10 Hosting Bundle. If IIS was enabled after installing the bundle, repair/reinstall the bundle so the ASP.NET Core module is registered.
3. Publish with `scripts/publish.ps1 -ApiUrl https://YOUR_API_HOST/api`.
4. Copy `artifacts/publish/api` into the API site's physical directory. Create a dedicated application pool using No Managed Code and 64-bit execution.
5. Configure separate high-entropy `Jwt__Key` and `Qr__Key`, `Mongo__ConnectionString`, `Mongo__Database`, JWT issuer/audience and `Cors__Origins__0` for the deployed web origin. Use secured deployment configuration, never committed secrets.
6. Set `Bootstrap__Email` and a strong `Bootstrap__Password` only for first start, then remove them after the initial administrator is created.
7. Bind the API site to HTTPS with a valid trusted certificate. Give its application-pool identity only the file permissions it needs. Use persistent environment/secrets configuration managed on the server.
8. Host `artifacts/publish/web` as an IIS static site with the supplied `web.config`. The web build must contain the real HTTPS API URL; changing runtime environment variables does not rewrite compiled frontend assets.
9. Verify `/api/health`, staff login, role authorization and a booking mutation from the web site and Android device. Ensure the actual IIS binding is reachable from the device network.
10. Configure Android's API address and verify the [OpenStreetMap basemap](openstreetmap.md); generate a release signing key owned by the team before release distribution.

## Evidence required

Capture actual IIS site/app-pool configuration, a healthy API response, successful operations from both clients, and a MongoDB collection view. These are outstanding until exercised on a configured IIS host; local Kestrel testing does not prove IIS deployment.
