package com.ptolemy.seeder;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.KeyStore;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * KeyManager — AES-256-GCM encrypted API key store backed by Android Keystore.
 *
 * Key never leaves the Keystore TEE. IV is 12 bytes, rotated on every write.
 * Custom keys live under the "custom" JSON object.
 *
 * Built-in slots: anthropic, openai, nist_nvd, github, smtp_pass
 */
public class KeyManager {

    private static final String KEYSTORE_ALIAS = "ptorrent_user_keys_v1";
    private static final String ANDROID_KEYSTORE = "AndroidKeyStore";
    private static final String TRANSFORM = "AES/GCM/NoPadding";
    private static final int GCM_TAG_BITS = 128;
    private static final int IV_BYTES = 12;
    private static final String ENC_FILE = "keys.enc";
    private static final String IV_FILE  = "keys.iv";

    private static KeyManager sInstance;
    private final Context mCtx;

    private KeyManager(Context ctx) {
        mCtx = ctx.getApplicationContext();
    }

    public static synchronized KeyManager getInstance(Context ctx) {
        if (sInstance == null) sInstance = new KeyManager(ctx);
        return sInstance;
    }

    // ── Public API ────────────────────────────────────────────────────────────

    /** Returns the value for a built-in or custom slot, or null if not set. */
    public String get(String slot) {
        try {
            JSONObject store = load();
            if (isCustom(slot, store)) {
                JSONObject custom = store.optJSONObject("custom");
                return custom != null ? custom.optString(slot, null) : null;
            }
            String val = store.optString(slot, null);
            return (val == null || val.isEmpty()) ? null : val;
        } catch (Exception e) {
            return null;
        }
    }

    /** Saves a value into the store. Creates the slot if it doesn't exist. */
    public void set(String slot, String value) throws GeneralSecurityException, IOException, JSONException {
        JSONObject store = loadOrEmpty();
        String[] builtIns = {"anthropic", "openai", "nist_nvd", "github", "smtp_pass"};
        boolean isBuiltIn = false;
        for (String b : builtIns) { if (b.equals(slot)) { isBuiltIn = true; break; } }

        if (isBuiltIn) {
            store.put(slot, value);
        } else {
            JSONObject custom = store.optJSONObject("custom");
            if (custom == null) custom = new JSONObject();
            custom.put(slot, value);
            store.put("custom", custom);
        }
        save(store);
    }

    /** Removes a slot. No-op if it doesn't exist. */
    public void delete(String slot) throws GeneralSecurityException, IOException, JSONException {
        JSONObject store = loadOrEmpty();
        if (store.has(slot)) {
            store.remove(slot);
        } else {
            JSONObject custom = store.optJSONObject("custom");
            if (custom != null) custom.remove(slot);
        }
        save(store);
    }

    /** Returns key names only — never values. */
    public List<String> list() {
        List<String> names = new ArrayList<>();
        try {
            JSONObject store = load();
            Iterator<String> keys = store.keys();
            while (keys.hasNext()) {
                String k = keys.next();
                if ("custom".equals(k)) {
                    JSONObject custom = store.optJSONObject("custom");
                    if (custom != null) {
                        Iterator<String> ck = custom.keys();
                        while (ck.hasNext()) names.add(ck.next());
                    }
                } else {
                    names.add(k);
                }
            }
        } catch (Exception ignored) {}
        return names;
    }

    /** Wipes all keys. Caller must show confirmation dialog before calling. */
    public void clear() throws GeneralSecurityException, IOException, JSONException {
        save(new JSONObject());
    }

    /** True if the slot has a non-null, non-empty value. */
    public boolean isSet(String slot) {
        return get(slot) != null;
    }

    // ── Crypto ────────────────────────────────────────────────────────────────

    private SecretKey getOrCreateKey() throws GeneralSecurityException {
        KeyStore ks = KeyStore.getInstance(ANDROID_KEYSTORE);
        try { ks.load(null); } catch (Exception e) { throw new GeneralSecurityException(e); }

        if (ks.containsAlias(KEYSTORE_ALIAS)) {
            KeyStore.SecretKeyEntry entry = (KeyStore.SecretKeyEntry)
                    ks.getEntry(KEYSTORE_ALIAS, null);
            return entry.getSecretKey();
        }

        KeyGenerator kg = KeyGenerator.getInstance(
                KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE);
        kg.init(new KeyGenParameterSpec.Builder(
                KEYSTORE_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build());
        return kg.generateKey();
    }

    private void save(JSONObject store) throws GeneralSecurityException, IOException, JSONException {
        SecretKey key = getOrCreateKey();
        Cipher cipher = Cipher.getInstance(TRANSFORM);
        cipher.init(Cipher.ENCRYPT_MODE, key);
        byte[] iv = cipher.getIV();
        byte[] plain = store.toString().getBytes(StandardCharsets.UTF_8);
        byte[] enc = cipher.doFinal(plain);

        File dir = mCtx.getFilesDir();
        writeBytes(new File(dir, ENC_FILE), enc);
        writeBytes(new File(dir, IV_FILE), iv);
    }

    private JSONObject load() throws GeneralSecurityException, IOException, JSONException {
        File dir = mCtx.getFilesDir();
        File encFile = new File(dir, ENC_FILE);
        File ivFile  = new File(dir, IV_FILE);
        if (!encFile.exists() || !ivFile.exists()) return new JSONObject();

        byte[] enc = readBytes(encFile);
        byte[] iv  = readBytes(ivFile);

        SecretKey key = getOrCreateKey();
        Cipher cipher = Cipher.getInstance(TRANSFORM);
        cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(GCM_TAG_BITS, iv));
        byte[] plain = cipher.doFinal(enc);
        return new JSONObject(new String(plain, StandardCharsets.UTF_8));
    }

    private JSONObject loadOrEmpty() {
        try { return load(); } catch (Exception e) { return new JSONObject(); }
    }

    private boolean isCustom(String slot, JSONObject store) {
        // A slot is "custom" if it's not a top-level key in the store
        // (meaning it would live under "custom" object)
        String[] builtIns = {"anthropic", "openai", "nist_nvd", "github", "smtp_pass"};
        for (String b : builtIns) { if (b.equals(slot)) return false; }
        return true;
    }

    // ── File helpers ──────────────────────────────────────────────────────────

    private static void writeBytes(File f, byte[] data) throws IOException {
        try (FileOutputStream fos = new FileOutputStream(f)) { fos.write(data); }
    }

    private static byte[] readBytes(File f) throws IOException {
        try (FileInputStream fis = new FileInputStream(f)) {
            byte[] buf = new byte[(int) f.length()];
            //noinspection ResultOfMethodCallIgnored
            fis.read(buf);
            return buf;
        }
    }
}
