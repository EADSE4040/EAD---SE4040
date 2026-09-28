# Five-minute demonstration guide

Record the final running application after IIS and Android device checks pass. Use synthetic accounts and future test slots, and show the deployed API address in each client. Keep credentials, JWTs, QR signing keys and Maps API keys out of the recording.

| Time | Demonstration |
|---|---|
| 0:00–0:30 | Show the repository's `backend/` and `frontend/` folders, IIS sites and healthy API response. Explain that the API owns the business rules and MongoDB stores shared records. |
| 0:30–1:15 | Register a prosumer with a unique synthetic NIC in Android. Show pending activation, then activate through the Backoffice portal and log in on Android. |
| 1:15–2:00 | Show a node and available energy slot in web. On Android, open nearby stations, select a map marker for details and create a reservation. Show its server-returned summary and pending counts. |
| 2:00–2:45 | Use Grid Operator or Backoffice to approve. Show the approved booking and QR in Android. Demonstrate an editable future booking or cancellation and its summary. Explain the seven-day and twelve-hour limits. |
| 2:45–3:30 | With a separate approved reservation whose transfer window is currently open, scan its QR using the operator's camera. Confirm measured energy, complete once and demonstrate that the completed QR cannot be used again. |
| 3:30–4:15 | Show current/history filters and profile editing. Restart Android to demonstrate SQLite persistence; identify the offline reference-data label if demonstrating offline behavior. |
| 4:15–5:00 | Show account deactivation and revoked-session behavior, integration-test results, diagrams and the three members' actual contributions. Finish within five minutes. |

Prepare the transfer-window fixture through normal authorized API/UI actions; do not change the computer clock or bypass verification rules. Rehearse the camera and Maps sections on the actual device before recording. Upload the video to a location the examiner can access, verify its link while signed out, and replace the pending link in README.

For the viva, each member should explain the work they actually performed, one design decision, one failure they diagnosed and how they verified the fix. Practice navigating from a UI action through its API endpoint, service rules and persisted MongoDB records.
