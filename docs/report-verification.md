| Check | Result and scope |
|---|---|
| Backend integration suite | 35 checks passed on 30 September 2026 against an isolated MongoDB replica-set database. Includes concurrency, time boundaries, QR replay and expiry. |
| Live IIS HTTP suite | 47 assertions passed on 30 September 2026. Includes activation, roles, booking workflow, signed QR validation, session revocation and protected node deletion. |
| Web production build | Passed after the node deletion action was added. |
| Android build and lint | Debug build and lint passed. Final device observations are recorded separately. |
| IIS deployment | Updated API and web artifacts published to the existing local IIS sites; live HTTP assertions ran against port 8080. |
| Existing mobile evidence | Registration, activation, session restoration, reservation creation/modification/cancellation and QR display were captured in the earlier device verification. |
| Maps and camera completion | Current end-to-end device verification in progress; no pass is inferred from build success. |
