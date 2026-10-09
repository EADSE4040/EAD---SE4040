# Android maps: OpenStreetMap with MapLibre

The app uses MapLibre Native Android 13.5.2 with OpenFreeMap's Liberty style. Map data comes from OpenStreetMap. No registration, API key, Google Play Services or billing account is needed for maps.

## Configuration

Build and run Android normally. The HTTPS style URL is configured in `frontend/android/app/src/main/res/values/strings.xml` as `map_style_url`: `https://tiles.openfreemap.org/styles/liberty`.

For a different provider or your own hosting, replace this resource with a compatible MapLibre style URL and retain the required attribution. OpenFreeMap's public service is free but offers no uptime SLA. Internet access is required for uncached styles and tiles; SQLite caches station reference data, not an offline basemap.

The OpenGL SDK variant supports existing emulators and devices without requiring Vulkan. MapLibre attribution stays enabled and obtains OpenStreetMap/OpenMapTiles credit from the provider style. The app does not pre-download tiles from OpenStreetMap's community tile server. Legacy `maps.properties` files are ignored and unused.

## Verify on a device

1. Open nearby stations while signed in. Check roads, labels, attribution and green station markers.
2. Tap a marker to see its address, generation capacity, battery slots and schedule.
3. Grant precise or approximate location: the app sends coordinates to its own API for stations within 25 km and displays the current position.
4. Deny location: all active stations remain available. Enable permission and tap Refresh to retry.
5. Disconnect the API after loading stations: cached reference data is labelled offline. An expired session clears station markers.
6. If the basemap fails, check connectivity and tap Refresh to retry its style request.

## Assessment note

The assignment checklist explicitly names Google Maps. The user requested this replacement; lecturer acceptance of OpenStreetMap/MapLibre is still unconfirmed. Do not describe this implementation as Google Maps or use previous Google Maps screenshots as evidence of this integration.

## Sources

- [MapLibre Android quickstart](https://maplibre.org/maplibre-native/android/examples/getting-started/)
- [MapLibre rendering backends](https://maplibre.org/maplibre-native/android/examples/data/rendering-engine/)
- [OpenFreeMap service, attribution and SLA](https://openfreemap.org/)
- [OpenFreeMap quickstart](https://openfreemap.org/quick_start/)
