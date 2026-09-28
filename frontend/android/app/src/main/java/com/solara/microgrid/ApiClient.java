package com.solara.microgrid;

import android.app.Activity;
import org.json.JSONObject;
import org.json.JSONTokener;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** REST-only network client. No MongoDB access or business rule implementation belongs on the device. */
public final class ApiClient {
    public interface Callback { void done(Object value, String error, int status); }
    private final Activity activity;
    private final ExecutorService executor=Executors.newSingleThreadExecutor();
    public String baseUrl, token="";
    public ApiClient(Activity activity,String baseUrl) { this.activity=activity; this.baseUrl=baseUrl; }
    public void call(String method,String path,JSONObject body,Callback callback) {
        executor.execute(() -> {
            HttpURLConnection connection=null; Object result=null; String error=null; int status=0;
            try {
                connection=(HttpURLConnection)new URL(baseUrl+path).openConnection();
                connection.setConnectTimeout(15000); connection.setReadTimeout(15000); connection.setRequestMethod(method);
                connection.setRequestProperty("Accept","application/json");
                if (!token.isEmpty()) connection.setRequestProperty("Authorization","Bearer "+token);
                if (body!=null) {
                    connection.setDoOutput(true); connection.setRequestProperty("Content-Type","application/json");
                    try (var out=connection.getOutputStream()) { out.write(body.toString().getBytes(StandardCharsets.UTF_8)); }
                }
                status=connection.getResponseCode();
                var stream=status>=400 ? connection.getErrorStream() : connection.getInputStream();
                String text=""; if (stream!=null) { try(var in=stream; var buffer=new ByteArrayOutputStream()) { byte[] chunk=new byte[4096]; int count; while((count=in.read(chunk))!=-1) buffer.write(chunk,0,count); text=buffer.toString("UTF-8"); } }
                if (!text.isBlank()) result=new JSONTokener(text).nextValue();
                if (status>=400) {
                    error=result instanceof JSONObject ? ((JSONObject)result).optString("title","Request failed") : "Request failed ("+status+")";
                    if (result instanceof JSONObject && ((JSONObject)result).has("errors")) error=((JSONObject)result).getJSONObject("errors").toString();
                    if (status==401) error="Your session expired. Please sign in again.";
                }
            } catch(Exception e) { error="Could not reach the server. Check your connection and API address."; }
            finally { if(connection!=null) connection.disconnect(); }
            Object value=result; String message=error; int code=status;
            activity.runOnUiThread(() -> { if(!activity.isDestroyed()) callback.done(value,message,code); });
        });
    }
    public void close() { executor.shutdownNow(); }
}
