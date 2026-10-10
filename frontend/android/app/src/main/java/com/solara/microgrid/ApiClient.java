package com.solara.microgrid;

import android.app.Activity;
import java.io.ByteArrayOutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.SocketTimeoutException;
import java.net.UnknownHostException;
import javax.net.ssl.SSLException;
import android.util.Log;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONObject;
import org.json.JSONTokener;

/**
 * REST-only network client. No MongoDB access or business rule implementation belongs on the
 * device.
 */
public final class ApiClient {
  public interface Callback {
    // Receive the parsed response, user-facing error and HTTP status on the UI thread.
    void done(Object value, String error, int status);
  }

  private final Activity activity;
  private final ExecutorService executor = Executors.newSingleThreadExecutor();
  public String baseUrl, token = "";

  // Bind asynchronous REST requests to the owning activity and API address.
  public ApiClient(Activity activity, String baseUrl) {
    this.activity = activity;
    this.baseUrl = baseUrl;
  }

  // Run HTTP I/O on a worker and deliver a parsed response on the UI thread.
  public void call(String method, String path, JSONObject body, Callback callback) {
    executor.execute(
        () -> {
          HttpURLConnection connection = null;
          Object result = null;
          String error = null;
          int status = 0;
          try {
            connection = (HttpURLConnection) new URL(baseUrl + path).openConnection();
            connection.setConnectTimeout(15000);
            connection.setReadTimeout(15000);
            connection.setRequestMethod(method);
            connection.setRequestProperty("Accept", "application/json");
            if (!token.isEmpty()) connection.setRequestProperty("Authorization", "Bearer " + token);
            if (body != null) {
              connection.setDoOutput(true);
              connection.setRequestProperty("Content-Type", "application/json");
              try (var out = connection.getOutputStream()) {
                out.write(body.toString().getBytes(StandardCharsets.UTF_8));
              }
            }
            status = connection.getResponseCode();
            var stream = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
            String text = "";
            if (stream != null) {
              try (var in = stream;
                  var buffer = new ByteArrayOutputStream()) {
                byte[] chunk = new byte[4096];
                int count;
                while ((count = in.read(chunk)) != -1) buffer.write(chunk, 0, count);
                text = buffer.toString("UTF-8");
              }
            }
            if (!text.isBlank()) result = new JSONTokener(text).nextValue();
            if (status >= 400) {
              error =
                  result instanceof JSONObject
                      ? ((JSONObject) result).optString("title", "Request failed")
                      : "Request failed (" + status + ")";
              if (result instanceof JSONObject && ((JSONObject) result).has("errors"))
                error = ((JSONObject) result).getJSONObject("errors").toString();
              if (status == 401) error = "Your session expired. Please sign in again.";
            }
          } catch (Exception e) {
            // Log the exception type only; never log credentials, tokens or request bodies.
            Log.w("SolaraApi", "Request failed: " + e.getClass().getSimpleName());
            if (e instanceof SocketTimeoutException) {
              error = "The server took too long to respond. Check the connection and try again.";
            } else if (e instanceof UnknownHostException) {
              error = "The server address could not be found. Check Connection settings and your network.";
            } else if (e instanceof SSLException) {
              error = "The secure connection failed. Check the server's HTTPS certificate.";
            } else if (status > 0) {
              error = "The server returned an unreadable response. Check the API address in Connection settings.";
            } else if (baseUrl.startsWith("http://127.0.0.1:") || baseUrl.startsWith("http://localhost:")) {
              error = "USB server connection is unavailable. Keep the phone connected and the laptop's USB demo helper running. Then use Test connection.";
            } else if (baseUrl.startsWith("http://10.0.2.2:")) {
              error = "This address is for an Android emulator. For a USB-connected phone, select the laptop connection in Connection settings.";
            } else {
              error = "Could not reach the server. Check your network and the API address in Connection settings.";
            }
          } finally {
            if (connection != null) connection.disconnect();
          }
          Object value = result;
          String message = error;
          int code = status;
          activity.runOnUiThread(
              () -> {
                if (!activity.isDestroyed()) callback.done(value, message, code);
              });
        });
  }

  // Cancel queued network work when the owning activity is destroyed.
  public void close() {
    executor.shutdownNow();
  }
}
