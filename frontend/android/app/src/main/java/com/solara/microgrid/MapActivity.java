package com.solara.microgrid;

import static org.maplibre.android.style.layers.PropertyFactory.*;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.PointF;
import android.graphics.RectF;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.*;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONArray;
import org.json.JSONObject;
import org.maplibre.android.MapLibre;
import org.maplibre.android.camera.CameraUpdateFactory;
import org.maplibre.android.geometry.*;
import org.maplibre.android.location.LocationComponentActivationOptions;
import org.maplibre.android.maps.*;
import org.maplibre.android.style.layers.CircleLayer;
import org.maplibre.android.style.sources.GeoJsonSource;
import org.maplibre.geojson.Feature;
import org.maplibre.geojson.FeatureCollection;
import org.maplibre.geojson.Point;

/**
 * MapLibre with OpenStreetMap data plots live station coordinates; cached SQLite reference data is
 * explicitly labelled offline.
 */
public final class MapActivity extends Activity implements OnMapReadyCallback {
  private MapView mapView;
  private MapLibreMap map;
  private Style mapStyle;
  private boolean mapLoadFailed;
  private static final String STATIONS_SOURCE = "solara-stations";
  private static final String STATIONS_LAYER = "solara-station-markers";
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
  private final Runnable locationTimeout =
      () -> {
        stopLocation();
        if (currentLocation == null) status.setText(R.string.map_location_unavailable);
      };

  // Build the map screen and start loading persisted station coordinates.
  @Override
  public void onCreate(Bundle state) {
    super.onCreate(state);
    getWindow()
        .getDecorView()
        .setSystemUiVisibility(
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
    refresh.setOnClickListener(
        v -> {
          if (map != null) {
            loadStations(currentLocation == null ? "/stations" : nearbyPath(currentLocation));
            if (mapLoadFailed) loadMapStyle();
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
    store = new LocalStore(this);
    api = new ApiClient(this, getIntent().getStringExtra("api"));
    api.token = getIntent().getStringExtra("token");
    MapLibre.getInstance(this);
    mapView = new MapView(this);
    mapView.addOnDidFailLoadingMapListener(
        error -> {
          mapLoadFailed = true;
          if (!isDestroyed()) status.setText(R.string.map_tiles_unavailable);
        });
    root.addView(mapView, new LinearLayout.LayoutParams(-1, 0, 1));
    mapView.onCreate(state);
    mapView.getMapAsync(this);
    loadStations("/stations");
  }

  // Ignore superseded responses and keep SQLite I/O off the map rendering thread.
  private void loadStations(String path) {
    final int version = ++requestVersion;
    status.setText(R.string.map_loading);
    api.call(
        "GET",
        path,
        null,
        (value, error, code) -> {
          if (isDestroyed() || version != requestVersion) return;
          if (code == 401) {
            nodes = new JSONArray();
            plot();
            status.setText(R.string.map_session_expired);
            return;
          }
          cacheWorker.execute(
              () -> {
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
                runOnUiThread(
                    () -> {
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
    return "/stations?latitude="
        + location.getLatitude()
        + "&longitude="
        + location.getLongitude()
        + "&radiusKm=25";
  }

  // Configure the map and request location permission before nearby filtering.
  @Override
  public void onMapReady(MapLibreMap readyMap) {
    map = readyMap;
    map.getUiSettings().setAttributionEnabled(true);
    map.addOnMapClickListener(
        point -> {
          if (mapStyle == null) return false;
          PointF pixel = map.getProjection().toScreenLocation(point);
          float radius = 24 * getResources().getDisplayMetrics().density;
          List<Feature> hits =
              map.queryRenderedFeatures(
                  new RectF(pixel.x - radius, pixel.y - radius, pixel.x + radius, pixel.y + radius),
                  STATIONS_LAYER);
          if (hits.isEmpty()) return false;
          try {
            showStation(new JSONObject(hits.get(0).getStringProperty("station")));
            return true;
          } catch (org.json.JSONException error) {
            return false;
          }
        });
    loadMapStyle();
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

  // Load a key-free basemap and keep its attribution controls visible.
  private void loadMapStyle() {
    mapLoadFailed = false;
    mapStyle = null;
    map.setStyle(
        getString(R.string.map_style_url),
        style -> {
          if (isDestroyed()) return;
          mapStyle = style;
          mapLoadFailed = false;
          style.addSource(
              new GeoJsonSource(
                  STATIONS_SOURCE, FeatureCollection.fromFeatures(new ArrayList<Feature>())));
          style.addLayer(
              new CircleLayer(STATIONS_LAYER, STATIONS_SOURCE)
                  .withProperties(
                      circleRadius(10f), circleColor(Color.rgb(32, 93, 70)),
                      circleStrokeColor(Color.WHITE), circleStrokeWidth(2f)));
          showLocation();
          plot();
        });
  }

  // Draw the existing Android location fix without starting a second location subscription.
  private void showLocation() {
    if (mapStyle == null || currentLocation == null) return;
    if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
            != PackageManager.PERMISSION_GRANTED
        && checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
            != PackageManager.PERMISSION_GRANTED) return;
    org.maplibre.android.location.LocationComponent component = map.getLocationComponent();
    if (!component.isLocationComponentActivated()) {
      component.activateLocationComponent(
          LocationComponentActivationOptions.builder(this, mapStyle)
              .useDefaultLocationEngine(false)
              .build());
    }
    component.setLocationComponentEnabled(true);
    component.forceLocationUpdate(currentLocation);
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
    if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
            != PackageManager.PERMISSION_GRANTED
        && checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
            != PackageManager.PERMISSION_GRANTED) {
      status.setText(R.string.map_location_unavailable);
      return;
    }
    try {
      stopLocation();
      locationManager = (LocationManager) getSystemService(LOCATION_SERVICE);
      Location best = null;
      for (String provider : locationManager.getProviders(true)) {
        Location candidate = locationManager.getLastKnownLocation(provider);
        if (candidate != null && (best == null || candidate.getTime() > best.getTime()))
          best = candidate;
      }
      if (best != null && System.currentTimeMillis() - best.getTime() < 300000) useLocation(best);
      locationListener =
          new LocationListener() {
            // Stop the temporary subscription after receiving a usable device position.
            @Override
            public void onLocationChanged(Location location) {
              useLocation(location);
              stopLocation();
            }

            // Older Android versions require these callbacks even when no UI action is needed.
            @Override
            public void onStatusChanged(String provider, int state, Bundle extras) {}

            // Keep the existing station view when a provider becomes available.
            @Override
            public void onProviderEnabled(String provider) {}

            // Explain why nearby filtering cannot be refreshed when location is disabled.
            @Override
            public void onProviderDisabled(String provider) {
              if (currentLocation == null) status.setText(R.string.map_location_unavailable);
            }
          };
      boolean listening = false;
      for (String provider :
          new String[] {LocationManager.NETWORK_PROVIDER, LocationManager.GPS_PROVIDER}) {
        if (locationManager.isProviderEnabled(provider)) {
          locationManager.requestLocationUpdates(
              provider, 1000, 0, locationListener, Looper.getMainLooper());
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
    showLocation();
    if (changed) loadStations(nearbyPath(location));
  }

  // Release location callbacks on timeout and when this screen leaves the foreground.
  private void stopLocation() {
    handler.removeCallbacks(locationTimeout);
    if (locationManager != null && locationListener != null)
      locationManager.removeUpdates(locationListener);
    locationListener = null;
  }

  // Display server coordinates as native map layers and fit all visible stations.
  private void plot() {
    if (mapStyle == null) {
      if (mapLoadFailed) status.setText(R.string.map_tiles_unavailable);
      return;
    }
    List<Feature> features = new ArrayList<>();
    List<LatLng> points = new ArrayList<>();
    for (int i = 0; i < nodes.length(); i++) {
      JSONObject node = nodes.optJSONObject(i);
      if (node == null) continue;
      double latitude = node.optDouble("latitude", Double.NaN);
      double longitude = node.optDouble("longitude", Double.NaN);
      if (!Double.isFinite(latitude)
          || !Double.isFinite(longitude)
          || Math.abs(latitude) > 90
          || Math.abs(longitude) > 180) continue;
      points.add(new LatLng(latitude, longitude));
      Feature feature = Feature.fromGeometry(Point.fromLngLat(longitude, latitude));
      feature.addStringProperty("station", node.toString());
      features.add(feature);
    }
    GeoJsonSource source = mapStyle.getSourceAs(STATIONS_SOURCE);
    if (source != null) source.setGeoJson(FeatureCollection.fromFeatures(features));
    status.setText(
        offline
            ? R.string.map_cached
            : features.isEmpty()
                ? R.string.map_no_nodes
                : currentLocation == null ? R.string.map_all_nodes : R.string.map_ready);
    if (currentLocation != null)
      points.add(new LatLng(currentLocation.getLatitude(), currentLocation.getLongitude()));
    if (points.isEmpty()) return;
    mapView.post(
        () -> {
          if (isDestroyed() || mapView.getWidth() == 0 || mapView.getHeight() == 0) return;
          boolean samePoint = true;
          for (LatLng point : points) if (!point.equals(points.get(0))) samePoint = false;
          if (samePoint) map.moveCamera(CameraUpdateFactory.newLatLngZoom(points.get(0), 13));
          else {
            LatLngBounds.Builder bounds = new LatLngBounds.Builder();
            for (LatLng point : points) bounds.include(point);
            map.moveCamera(CameraUpdateFactory.newLatLngBounds(bounds.build(), 80));
          }
        });
  }

  // Open station details directly when its marker is selected.
  private void showStation(JSONObject node) {
    new android.app.AlertDialog.Builder(this)
        .setTitle(node.optString("name"))
        .setMessage(
            node.optString("address")
                + "\n\n"
                + node.optDouble("capacityKw")
                + " kW generation capacity\n"
                + node.optInt("batterySlots")
                + " battery slots\n"
                + node.optString("schedule"))
        .setPositiveButton("Done", null)
        .show();
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

  // Forward memory pressure so MapLibre can release cached resources.
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
