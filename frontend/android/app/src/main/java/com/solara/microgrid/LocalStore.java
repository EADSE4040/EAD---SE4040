package com.solara.microgrid;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * Native SQLite persistence. Access tokens are encrypted with a non-exportable Android Keystore
 * key.
 */
public final class LocalStore extends SQLiteOpenHelper {
  // Open the versioned SQLite database used for sessions and reference data.
  public LocalStore(Context context) {
    super(context, "solara.db", null, 1);
  }

  // Create the local key-value cache schema on first launch.
  @Override
  public void onCreate(SQLiteDatabase db) {
    db.execSQL(
        "CREATE TABLE cache (name TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at INTEGER NOT"
            + " NULL)");
  }

  // Reserve the schema migration hook; version one has no older schema to migrate.
  @Override
  public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {}

  // Insert or replace a cached value together with its update time.
  public void put(String name, String value) {
    ContentValues row = new ContentValues();
    row.put("name", name);
    row.put("value", value);
    row.put("updated_at", System.currentTimeMillis());
    getWritableDatabase().insertWithOnConflict("cache", null, row, SQLiteDatabase.CONFLICT_REPLACE);
  }

  // Read a cache entry using a parameterized SQLite query.
  public String get(String name) {
    try (Cursor c =
        getReadableDatabase()
            .query(
                "cache", new String[] {"value"}, "name=?", new String[] {name}, null, null, null)) {
      return c.moveToFirst() ? c.getString(0) : null;
    }
  }

  // Remove cached account and reference data when the user signs out.
  public void clearSession() {
    getWritableDatabase().delete("cache", null, null);
  }

  // Retrieve or create a non-exportable AES key in Android Keystore.
  private SecretKey key() throws Exception {
    KeyStore store = KeyStore.getInstance("AndroidKeyStore");
    store.load(null);
    if (!store.containsAlias("solara.session")) {
      KeyGenerator generator =
          KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
      generator.init(
          new KeyGenParameterSpec.Builder(
                  "solara.session", KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
              .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
              .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
              .build());
      generator.generateKey();
    }
    return (SecretKey) store.getKey("solara.session", null);
  }

  // Encrypt session JSON with AES-GCM before writing it to SQLite.
  public void saveSession(String json) throws Exception {
    Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
    cipher.init(Cipher.ENCRYPT_MODE, key());
    put(
        "session",
        Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP)
            + ":"
            + Base64.encodeToString(
                cipher.doFinal(json.getBytes(StandardCharsets.UTF_8)), Base64.NO_WRAP));
  }

  // Decrypt the saved session and discard invalid or unreadable data.
  public String readSession() {
    try {
      String encrypted = get("session");
      if (encrypted == null) return null;
      String[] parts = encrypted.split(":");
      Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
      cipher.init(
          Cipher.DECRYPT_MODE,
          key(),
          new GCMParameterSpec(128, Base64.decode(parts[0], Base64.NO_WRAP)));
      return new String(
          cipher.doFinal(Base64.decode(parts[1], Base64.NO_WRAP)), StandardCharsets.UTF_8);
    } catch (Exception e) {
      clearSession();
      return null;
    }
  }
}
