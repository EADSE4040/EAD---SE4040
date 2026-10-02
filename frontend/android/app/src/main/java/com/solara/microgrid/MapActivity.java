package com.solara.microgrid;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.location.Location;
import android.location.LocationManager;
import android.location.LocationListener;
import android.os.Handler;
import android.os.Looper;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import android.os.Bundle;
import android.widget.*;
import com.google.android.gms.maps.*;
import com.google.android.gms.maps.model.*;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Google Maps plots live station coordinates; cached SQLite reference data is explicitly labelled
 * offline.
 */
public final class MapActivity extends Activity implements OnMapReadyCallback {
  private MapView mapView;
  private GoogleMap map;
  private ApiClient api;
  private LocalStore store;
  private TextView status;
  private JSONArray nodes = new JSONArray();
  private final ExecutorService cacheWorker = Executors.newSingleThreadExecutor();
  private final Handler handler = new Handler(Looper.getMainLooper());
  private LocationManager locationManager;
  private LocationListener locationListener;
  private Location currentLocation;
  private int requestVersion;
  private boolean offline;
  private final Runnable locationTimeout = () -> {
    stopLocation();
    if (currentLocation == null) status.setText(R.string.map_location_unavailable);
  };

  // Build the map screen and start loading persisted station coordinates.
  @Override
  public void onCreate(Bundle state) {
    super.onCreate(state);
    getWindow().getDecorView().setSystemUiVisibility(
        android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
            | android.view.View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
    LinearLayout root = new LinearLayout(this);
    root.setOrientation(LinearLayout.VERTICAL);
    root.setOnApplyWindowInsetsListener(
        (v, insets) -> {
          v.setPadding(
              insets.getSystemWindowInsetLeft(),
              insets.getSystemWindowInsetTop(),
              insets.getSystemWindowInsetRight(),
              insets.getSystemWindowInsetBottom());
          return insets;
        });
    Button back = new Button(this);
    back.setText(R.string.map_back);
    back.setOnClickListener(v -> finish());
    root.addView(back);
    Button refresh = new Button(this);
    refresh.setText(R.string.map_refresh);
    refresh.setOnClickListener(v -> {
      if (map != null) {
        loadStations(currentLocation == null ? "/stations" : nearbyPath(currentLocation));
        locate();
      }
    });
    root.addView(refresh);
    status = new TextView(this);
    status.setPadding(25, 15, 25, 15);
    status.setText(R.string.map_loading);
    status.setTextColor(Color.rgb(32, 93, 70));
    root.addView(status);
    setContentView(root);
    root.requestApplyInsets();
    if (!"true".equals(BuildConfig.MAPS_CONFIGURED)) {
      status.setText(R.string.map_key_missing);
      return;
    }
    store = new LocalStore(this);
    api = new ApiClient(this, getIntent().getStringExtra("api"));
    api.token = getIntent().getStringExtra("token");
    mapView = new MapView(this);
    root.addView(mapView, new LinearLayout.LayoutParams(-1, 0, 1));
    mapView.onCreate(state);
    mapView.getMapAsync(this);
    loadStations("/stations");
  }

  // Ignore superseded responses and keep SQLite I/O off the map rendering thread.
  private void loadStations(String path) {
    final int version = ++requestVersion;
    status.setText(R.string.map_loading);
    api.call("GET", path, null, (value, error, code) -> {
      if (version != requestVersion) return;
      if (code == 401) {
        nodes = new JSONArray();
        plot();
        status.setText(R.string.map_session_expired);
        return;
      }
      cacheWorker.execute(() -> {
        JSONArray result = new JSONArray();
        boolean cached = error != null;
        try {
          if (error == null) {
            result = (JSONArray) value;
            store.put("map:" + path, result.toString());
          } else {
            String saved = store.get("map:" + path);
            if (saved != null) result = new JSONArray(saved);
          }
        } catch (Exception ignored) {
          if (value instanceof JSONArray) result = (JSONArray) value;
        }
        final JSONArray stations = result;
        runOnUiThread(() -> {
          if (isDestroyed() || version != requestVersion) return;
          nodes = stations;
          offline = cached;
          plot();
          if (error != null && nodes.length() == 0) status.setText(error);
        });
      });
    });
  }

  // Ask the server to calculate nearby stations using the current device coordinates.
  private String nearbyPath(Location location) {
    return "/stations?latitude=" + location.getLatitude()
        + "&longitude=" + location.getLongitude() + "&radiusKm=25";
  }

  // Configure the map and request location permission before nearby filtering.
  @Override
  public void onMapReady(GoogleMap googleMap) {
    map = googleMap;
    map.getUiSettings().setZoomControlsEnabled(true);
    plot();
    if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
            == PackageManager.PERMISSION_GRANTED
        || checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
            == PackageManager.PERMISSION_GRANTED) locate();
    else
      requestPermissions(
          new String[] {
            Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION
          },
          42);
  }

  // Start nearby lookup only when a location permission was granted.
  @Override
  public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grants) {
    super.onRequestPermissionsResult(requestCode, permissions, grants);
    if (requestCode == 42
        && grants.length > 0
        && (grants[0] == PackageManager.PERMISSION_GRANTED
            || (grants.length > 1 && grants[1] == PackageManager.PERMISSION_GRANTED))) locate();
    else if (requestCode == 42) status.setText(R.string.map_location_unavailable);
  }

  // Use a recent cached fix immediately, then request a bounded fresh location update.
  private void locate() {
    if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED
        && checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
      status.setText(R.string.map_location_unavailable);
      return;
    }
    try {
      map.setMyLocationEnabled(true);
      stopLocation();
      locationManager = (LocationManager) getSystemService(LOCATION_SERVICE);
      Location best = null;
      for (String provider : locationManager.getProviders(true)) {
        Location candidate = locationManager.getLastKnownLocation(provider);
        if (candidate != null && (best == null || candidate.getTime() > best.getTime())) best = candidate;
      }
      if (best != null && System.currentTimeMillis() - best.getTime() < 300000) useLocation(best);
      locationListener = new LocationListener() {
        // Stop the temporary subscription after receiving a usable device position.
        @Override public void onLocationChanged(Location location) {
          useLocation(location);
          stopLocation();
        }
        // Older Android versions require these callbacks even when no UI action is needed.
        @Override public void onStatusChanged(String provider, int state, Bundle extras) {}
        // Keep the existing station view when a provider becomes available.
        @Override public void onProviderEnabled(String provider) {}
        // Explain why nearby filtering cannot be refreshed when location is disabled.
        @Override public void onProviderDisabled(String provider) {
          if (currentLocation == null) status.setText(R.string.map_location_unavailable);
        }
      };
      boolean listening = false;
      for (String provider : new String[] {LocationManager.NETWORK_PROVIDER, LocationManager.GPS_PROVIDER}) {
        if (locationManager.isProviderEnabled(provider)) {
          locationManager.requestLocationUpdates(provider, 1000, 0, locationListener, Looper.getMainLooper());
          listening = true;
        }
      }
      if (listening) handler.postDelayed(locationTimeout, 15000);
      else if (currentLocation == null) status.setText(R.string.map_location_unavailable);
    } catch (SecurityException | IllegalArgumentException e) {
      stopLocation();
      status.setText(R.string.map_location_unavailable);
    }
  }

  // Reload only when a new location changes the nearby search area.
  private void useLocation(Location location) {
    boolean changed = currentLocation == null || currentLocation.distanceTo(location) > 100;
    currentLocation = location;
    if (changed) loadStations(nearbyPath(location));
  }

  // Release location callbacks on timeout and when this screen leaves the foreground.
  private void stopLocation() {
    handler.removeCallbacks(locationTimeout);
    if (locationManager != null && locationListener != null) locationManager.removeUpdates(locationListener);
    locationListener = null;
  }

  // Display server station coordinates and open station details from marker selections.
  private void plot() {
    if (map == null) return;
    map.clear();
    status.setText(offline ? R.string.map_cached
        : nodes.length() == 0 ? R.string.map_no_nodes
        : currentLocation == null ? R.string.map_all_nodes : R.string.map_ready);
    if (nodes.length() == 0) {
      if (currentLocation != null) map.moveCamera(CameraUpdateFactory.newLatLngZoom(
          new LatLng(currentLocation.getLatitude(), currentLocation.getLongitude()), 12));
      return;
    }
    LatLngBounds.Builder bounds = new LatLngBounds.Builder();
    for (int i = 0; i < nodes.length(); i++) {
      JSONObject n = nodes.optJSONObject(i);
      LatLng point = new LatLng(n.optDouble("latitude"), n.optDouble("longitude"));
      bounds.include(point);
      Marker marker =
          map.addMarker(
              new MarkerOptions()
                  .position(point)
                  .title(n.optString("name"))
                  .snippet(
                      n.optDouble("capacityKw")
                          + " kW · "
                          + n.optInt("batterySlots")
                          + " battery slots"));
      if (marker != null) marker.setTag(n);
    }
    if (currentLocation != null) bounds.include(new LatLng(currentLocation.getLatitude(), currentLocation.getLongitude()));
    final LatLngBounds cameraBounds = bounds.build();
    mapView.post(() -> {
      if (isDestroyed() || mapView.getWidth() == 0 || mapView.getHeight() == 0) return;
      if (cameraBounds.southwest.equals(cameraBounds.northeast))
        map.moveCamera(CameraUpdateFactory.newLatLngZoom(cameraBounds.getCenter(), 13));
      else map.moveCamera(CameraUpdateFactory.newLatLngBounds(cameraBounds, 80));
    });
    map.setOnInfoWindowClickListener(
        marker -> {
          JSONObject n = (JSONObject) marker.getTag();
          if (n != null)
            new android.app.AlertDialog.Builder(this)
                .setTitle(n.optString("name"))
                .setMessage(
                    n.optString("address")
                        + "\n\n"
                        + n.optDouble("capacityKw")
                        + " kW generation capacity\n"
                        + n.optInt("batterySlots")
                        + " battery slots\n"
                        + n.optString("schedule"))
                .setPositiveButton("Done", null)
                .show();
        });
  }

  // Resume the map renderer with the activity lifecycle.
  @Override
  protected void onResume() {
    super.onResume();
    if (mapView != null) mapView.onResume();
  }

  // Pause rendering and release temporary location subscriptions.
  @Override
  protected void onPause() {
    if (mapView != null) mapView.onPause();
    stopLocation();
    super.onPause();
  }

  // Forward the visible lifecycle state to the map renderer.
  @Override
  protected void onStart() {
    super.onStart();
    if (mapView != null) mapView.onStart();
  }

  // Stop the map renderer while the activity is not visible.
  @Override
  protected void onStop() {
    if (mapView != null) mapView.onStop();
    super.onStop();
  }

  // Release network, database and rendering resources owned by this activity.
  @Override
  protected void onDestroy() {
    if (mapView != null) mapView.onDestroy();
    if (api != null) api.close();
    requestVersion++;
    stopLocation();
    if (store != null) cacheWorker.execute(() -> store.close());
    cacheWorker.shutdown();
    super.onDestroy();
  }

  // Forward memory pressure so Google Maps can release cached resources.
  @Override
  public void onLowMemory() {
    super.onLowMemory();
    if (mapView != null) mapView.onLowMemory();
  }

  // Preserve map state across Android activity recreation.
  @Override
  protected void onSaveInstanceState(Bundle state) {
    super.onSaveInstanceState(state);
    if (mapView != null) mapView.onSaveInstanceState(state);
  }
}
