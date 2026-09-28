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
  public LocalStore(Context context) {
    super(context, "solara.db", null, 1);
  }

  @Override
  public void onCreate(SQLiteDatabase db) {
    db.execSQL(
        "CREATE TABLE cache (name TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at INTEGER NOT"
            + " NULL)");
  }

  @Override
  public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {}

  public void put(String name, String value) {
    ContentValues row = new ContentValues();
    row.put("name", name);
    row.put("value", value);
    row.put("updated_at", System.currentTimeMillis());
    getWritableDatabase().insertWithOnConflict("cache", null, row, SQLiteDatabase.CONFLICT_REPLACE);
  }

  public String get(String name) {
    try (Cursor c =
        getReadableDatabase()
            .query(
                "cache", new String[] {"value"}, "name=?", new String[] {name}, null, null, null)) {
      return c.moveToFirst() ? c.getString(0) : null;
    }
  }

  public void clearSession() {
    getWritableDatabase().delete("cache", null, null);
  }

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
