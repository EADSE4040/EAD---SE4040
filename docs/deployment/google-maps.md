# Google Maps setup for this Android application

Checked against Google's official pricing on 28 September 2026: the basic Maps SDK SKU has unlimited free usage. A billing-enabled Google Cloud project and API key are still required. This application uses basic native maps and stored station coordinates; it does not require Places, Routes, Geocoding, Street View or cloud map styling.

1. Open Google Cloud Console using the team's account and create/select the project.
2. Complete Google's billing setup yourself, then enable **Maps SDK for Android**.
3. Create an API key. Set application restrictions to **Android apps**.
4. Add package name `com.solara.microgrid` and the signing certificate SHA-1 below.
5. Set API restrictions to **Maps SDK for Android** only.
6. Put the key in the ignored file `frontend/android/maps.properties` as `MAPS_API_KEY=your_actual_key`. Do not paste the key into chat or commit it.
7. Rebuild/install the debug APK. Open Nearby nodes, grant location access, verify real tiles and station markers, then select a marker for details.

Current workspace debug certificate SHA-1:

```text
17:02:42:76:04:78:4C:54:34:EB:91:CE:F8:DA:8B:B8:6C:91:F6:28
```

This fingerprint is public certificate metadata, not a private key. A different computer/debug keystore or release signing key needs its own authorized fingerprint. Regenerate it with Gradle `signingReport` when the signing certificate changes.

Google account sign-in, billing enrollment and key issuance must be completed by the account owner. Without the key, the app displays an explicit configuration message; this is not evidence that Google Maps integration was exercised successfully.

Sources: [Google Maps pricing](https://developers.google.com/maps/billing-and-pricing/pricing), [Android SDK usage and billing](https://developers.google.com/maps/documentation/android-sdk/usage-and-billing), [API key restrictions](https://developers.google.com/maps/api-security-best-practices).
