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

1. Enable IIS with management tools and static content support.
2. Install the .NET 10 Hosting Bundle. If IIS was enabled after installing the bundle, repair/reinstall the bundle so the ASP.NET Core module is registered.
3. Publish with `scripts/publish.ps1 -ApiUrl https://YOUR_API_HOST/api`.
4. Copy `artifacts/publish/api` into the API site's physical directory. Create a dedicated application pool using No Managed Code and 64-bit execution.
5. Configure separate high-entropy `Jwt__Key` and `Qr__Key`, `Mongo__ConnectionString`, `Mongo__Database`, JWT issuer/audience and `Cors__Origins__0` for the deployed web origin. Use secured deployment configuration, never committed secrets.
6. Set `Bootstrap__Email` and a strong `Bootstrap__Password` only for first start, then remove them after the initial administrator is created.
7. Bind the API site to HTTPS with a valid trusted certificate. Give its application-pool identity only the file permissions it needs. Use persistent environment/secrets configuration managed on the server.
8. Host `artifacts/publish/web` as an IIS static site with the supplied `web.config`. The web build must contain the real HTTPS API URL; changing runtime environment variables does not rewrite compiled frontend assets.
9. Verify `/api/health`, staff login, role authorization and a booking mutation from the web site and Android device. Ensure the actual IIS binding is reachable from the device network.
10. Configure Android's API address and restricted Google Maps key; generate a release signing key owned by the team before release distribution.

## Evidence required

Capture actual IIS site/app-pool configuration, a healthy API response, successful operations from both clients, and a MongoDB collection view. These are outstanding until exercised on a configured IIS host; local Kestrel testing does not prove IIS deployment.
