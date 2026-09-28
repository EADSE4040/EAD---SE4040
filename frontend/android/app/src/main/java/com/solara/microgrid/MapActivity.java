package com.solara.microgrid;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationManager;
import android.os.Bundle;
import android.graphics.Color;
import android.view.WindowInsets;
import android.widget.*;
import com.google.android.gms.maps.*;
import com.google.android.gms.maps.model.*;
import org.json.JSONArray;
import org.json.JSONObject;

/** Google Maps plots live station coordinates; cached SQLite reference data is explicitly labelled offline. */
public final class MapActivity extends Activity implements OnMapReadyCallback {
    private MapView mapView; private GoogleMap map; private ApiClient api; private LocalStore store; private TextView status;
    private JSONArray nodes=new JSONArray();
    @Override public void onCreate(Bundle state){super.onCreate(state);LinearLayout root=new LinearLayout(this);root.setOrientation(1);root.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());return insets;});Button back=new Button(this);back.setText("‹ Back to Solara");back.setOnClickListener(v->finish());root.addView(back);status=new TextView(this);status.setPadding(25,15,25,15);status.setText("Loading nearby grid nodes…");status.setTextColor(Color.rgb(32,93,70));root.addView(status);setContentView(root);root.requestApplyInsets();
        if(!"true".equals(BuildConfig.MAPS_CONFIGURED)){status.setText("Google Maps needs an API key. Add your Android-restricted key to maps.properties and rebuild the app.");return;}
        store=new LocalStore(this);api=new ApiClient(this,getIntent().getStringExtra("api"));api.token=getIntent().getStringExtra("token");mapView=new MapView(this);root.addView(mapView,new LinearLayout.LayoutParams(-1,0,1));mapView.onCreate(state);mapView.getMapAsync(this);
        api.call("GET","/stations",null,(value,error,code)->{if(error==null){nodes=(JSONArray)value;store.put("stations",nodes.toString());status.setText("Nearby microgrid nodes · tap a marker for details");}else{try{nodes=new JSONArray(store.get("stations"));status.setText("Offline: displaying cached stations. Availability may have changed.");}catch(Exception e){status.setText(error);}}plot();});
    }
    @Override public void onMapReady(GoogleMap googleMap){map=googleMap;map.getUiSettings().setZoomControlsEnabled(true);plot();if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED||checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)==PackageManager.PERMISSION_GRANTED)locate();else requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION},42);}
    @Override public void onRequestPermissionsResult(int requestCode,String[] permissions,int[] grants){super.onRequestPermissionsResult(requestCode,permissions,grants);if(requestCode==42 && grants.length>0 && (grants[0]==PackageManager.PERMISSION_GRANTED || (grants.length>1&&grants[1]==PackageManager.PERMISSION_GRANTED)))locate();}
    private void locate(){try{map.setMyLocationEnabled(true);LocationManager manager=(LocationManager)getSystemService(LOCATION_SERVICE);Location best=null;for(String provider:manager.getProviders(true)){Location l=manager.getLastKnownLocation(provider);if(l!=null&&(best==null||l.getTime()>best.getTime()))best=l;}if(best!=null)map.animateCamera(CameraUpdateFactory.newLatLngZoom(new LatLng(best.getLatitude(),best.getLongitude()),12));}catch(SecurityException e){status.setText("Location permission unavailable; all active grid nodes remain visible.");}}
    private void plot(){if(map==null||nodes.length()==0)return;map.clear();LatLngBounds.Builder bounds=new LatLngBounds.Builder();for(int i=0;i<nodes.length();i++){JSONObject n=nodes.optJSONObject(i);LatLng point=new LatLng(n.optDouble("latitude"),n.optDouble("longitude"));bounds.include(point);Marker marker=map.addMarker(new MarkerOptions().position(point).title(n.optString("name")).snippet(n.optDouble("capacityKw")+" kW · "+n.optInt("batterySlots")+" battery slots"));if(marker!=null)marker.setTag(n);}mapView.post(()->map.moveCamera(CameraUpdateFactory.newLatLngBounds(bounds.build(),80)));map.setOnInfoWindowClickListener(marker->{JSONObject n=(JSONObject)marker.getTag();if(n!=null)new android.app.AlertDialog.Builder(this).setTitle(n.optString("name")).setMessage(n.optString("address")+"\n\n"+n.optDouble("capacityKw")+" kW generation capacity\n"+n.optInt("batterySlots")+" battery slots\n"+n.optString("schedule")).setPositiveButton("Done",null).show();});}
    @Override protected void onResume(){super.onResume();if(mapView!=null)mapView.onResume();}
    @Override protected void onPause(){if(mapView!=null)mapView.onPause();super.onPause();}
    @Override protected void onStart(){super.onStart();if(mapView!=null)mapView.onStart();}
    @Override protected void onStop(){if(mapView!=null)mapView.onStop();super.onStop();}
    @Override protected void onDestroy(){if(mapView!=null)mapView.onDestroy();if(api!=null)api.close();if(store!=null)store.close();super.onDestroy();}
    @Override public void onLowMemory(){super.onLowMemory();if(mapView!=null)mapView.onLowMemory();}
    @Override protected void onSaveInstanceState(Bundle state){super.onSaveInstanceState(state);if(mapView!=null)mapView.onSaveInstanceState(state);}
}
