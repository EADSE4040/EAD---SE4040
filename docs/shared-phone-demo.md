# Two phones using one local backend

A transaction QR is signed by its issuing API. A separate laptop/backend can use a
different QR key or database and cannot verify that QR. Both the prosumer and
operator must use the same deployment. Do not copy signing keys between separate
servers to work around this; connect both clients to one API.

1. Connect the laptop and both phones to the same Wi-Fi/hotspot.
2. Start MongoDB and the local application with `scripts/start-local.ps1`.
3. Find the laptop's Wi-Fi IPv4 address using `ipconfig`.
4. In an Administrator PowerShell at the repository root, run:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-shared-backend.ps1 -Address <laptop-Wi-Fi-IPv4>
   ```

   This restarts only this project's API on loopback plus the selected interface
   and adds a firewall rule restricted to that interface/address, the local subnet,
   TCP port 5080 and the project's dotnet executable.
5. Install the newly built `frontend/android/app/build/outputs/apk/debug/app-debug.apk`
   on each phone. In Solara's **Connection settings**, save
   `http://<laptop-Wi-Fi-IPv4>:5080/api`, then use **Test connection**.
   Changing the address signs the user out; sign in with an account belonging to
   this backend. The prosumer and operator need their respective roles.
6. Open an approved booking's QR on the prosumer phone and scan it on the operator
   phone. Both screens display the API address. A USB-connected phone may instead
   use `http://127.0.0.1:5080/api` with `adb reverse tcp:5080 tcp:5080`; it still
   reaches the same API.

The laptop and backend must remain on. If the Wi-Fi IP changes, rerun the sharing
script with the new address and update the phones. A router that isolates Wi-Fi
clients can prevent access; use a shared hotspot that allows devices to communicate.
This HTTP setup is for debug builds on the local network. Release builds require HTTPS.

Signature errors can also occur after the server signing key changes or if the
payload is edited. Reload the QR from the current issuing server. Verification
does not bypass approval, expiry, the transfer window or protection against reuse.

Every main app screen has a visible Back button. Detail/form screens return to
their parent; Back on Home or Sign in closes the activity. The map and QR camera
also have visible Back controls; cancelling the camera leaves the previous screen intact.
