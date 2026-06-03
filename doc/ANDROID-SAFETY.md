# PTorrent Android Safety — HAL Boundary and System Partition Protection

**Version:** 2.0  
**Date:** 2026-06-03  
**License:** GNU GPL v3

---

## HAL Boundary Policy

PTorrent accesses hardware and OS services exclusively through Android's
**Hardware Abstraction Layer (HAL)** and official Android APIs. The Python
engine never touches hardware, credential, or auth paths directly.

This is not just a security best practice — it is the architecture.
Going through HAL means:

- Credentials go through `EncryptedSharedPreferences` and Android `KeyStore`
- Biometrics go through `BiometricPrompt`, never raw sensor data
- Network state goes through `ConnectivityManager`, never `/sys/` or `/proc/`
- Device identity goes through `Build.*` and `Settings.Secure`, never `/efs/`

**Why this matters when ADB is enabled:**

A phone plugged in with ADB debugging enabled is an open port. Any code with
filesystem access — a malicious `.ptorrent` file, a compromised skill, or
a rogue evaluation job — could potentially read:

```
/data/misc/adb/adb_keys          → grants full device access over USB
/data/system/password.key         → PIN hash for offline brute-force
/data/system/pattern.key          → lock pattern hash
/data/system/locksettings.db      → full lock screen credential store
/data/misc/keystore/              → Android Keystore key material
/data/misc/wifi/                  → saved WiFi passwords
/efs/                             → Samsung IMEI / SIM lock (Samsung devices)
```

PTorrent's Python sandbox (`skills/sandbox.py`) blocks all of these paths
at the `builtins.open` level, before any skill code can reach them.
The block fires regardless of root status, regardless of what the
`.ptorrent` file requests, and cannot be bypassed by skill code.

**The same policy applies to all future ports:**

| Platform | Auth/credential layer | PTorrent uses |
|---|---|---|
| Android | Android HAL / KeyStore | `EncryptedSharedPreferences`, `BiometricPrompt` |
| iOS | Secure Enclave / Keychain | `SecItemAdd` / `LocalAuthentication` framework |
| Desktop (Linux) | libsecret / GNOME Keyring | `secret-tool` / `python3-keyring` |
| Desktop (macOS) | Keychain Services | `keyring` Python library |
| Desktop (Windows) | DPAPI / Credential Manager | `keyring` Python library |

---

## What PTorrent NEVER Does

PTorrent is a sandboxed Android application. It runs in the standard Android
application sandbox and has no access to system partitions. It cannot:

- Write to `/system/build.prop` — soft brick risk
- Write to `/system/` — system partition
- Write to `/vbmeta` — Verified Boot Metadata (device will not boot if corrupted)
- Write to `/boot` — kernel partition
- Write to `/vendor` — vendor partition
- Write to `/proc/sys` — kernel parameters
- Spawn shell processes (`subprocess` is explicitly blocked in the Python sandbox)
- Access other apps' data (`/data/data/` outside its own package)

These restrictions are enforced at two layers:

1. **Android sandbox** — the OS prevents writes to system partitions without root
2. **Python sandbox** (`skills/sandbox.py`) — blocks `subprocess`, `ctypes`,
   system path writes, and sensitive reads at the Python level, regardless of
   whether the device is rooted

---

## VBMeta — The Brick You Don't Want

Android Verified Boot (AVB) chains cryptographic hashes from every system
partition up to a root in VBMeta. If VBMeta is modified incorrectly:

- The device will not boot
- The only recovery is fastboot or a manufacturer flash tool
- Factory reset does not help if VBMeta is corrupted

**PTorrent does not touch VBMeta under any circumstances.**

If you are running a custom ROM or unlocking your bootloader alongside PTorrent
development, you are responsible for your own VBMeta management. PTorrent's
data directory is `/sdcard/Android/data/com.ptolemy.seeder/files/`. Nothing
PTorrent does will ever affect VBMeta.

If you need to disable AVB verification for custom ROM work:

```bash
fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img
```

This is your operation, not PTorrent's.

---

## Safe ADB Operations with PTorrent

### SAFE — operations within PTorrent's storage boundary

```bash
# Pull a trained bin checkpoint off the device
adb pull /sdcard/Android/data/com.ptolemy.seeder/files/monad_physics.bin .

# Push a new .ptorrent job to the device inbox
adb push my_evaluation.ptorrent \
    /sdcard/Android/data/com.ptolemy.seeder/files/inbox/

# Pull the chain JSON to inspect on desktop
adb pull /sdcard/Android/data/com.ptolemy.seeder/files/ptorrent_chain.json .

# Pull a completed evaluation result
adb pull /sdcard/Android/data/com.ptolemy.seeder/files/sparc_evaluated.peval .
```

### NEVER — operations that risk system integrity

```bash
# NEVER — writes to system partition
adb push anything /system/
adb push anything /system/build.prop

# NEVER — VBMeta modification without full understanding
adb push anything /vbmeta

# NEVER — root shell system writes
adb shell su -c 'cp file /system/build.prop'
```

`adb shell setprop` modifies runtime properties only — they do not survive
reboot and do not touch build.prop. This is safe for temporary debugging but
is not a substitute for proper build.prop management.

---

## Rooted Devices

On a rooted device, PTorrent's Python sandbox still blocks:
- All `subprocess` imports
- All writes outside the allowed roots
- All reads from sensitive kernel paths

Root access does not bypass the Python sandbox. The sandbox installs at the
builtins level before any skill code runs — it cannot be circumvented by a
skill importing a module.

If you are a developer testing PTorrent on a rooted device:

- The sandbox can be disabled for testing via `skills.sandbox.uninstall()`
- Never disable the sandbox when running untrusted `.ptorrent` files
- Report any `.ptorrent` that attempts system writes immediately — flag it on
  the chain using `chain.flag()` and contact the ANNOUNCE ORCID

---

## Resource Safety

Long-running evaluations can:
- Fill your storage partition if output bounds are not set
- Cause thermal throttling or automatic shutdown
- Drain the battery if not charging

All `.ptorrent` files with significant resource requirements must include a
`resources` block. PTorrent's pre-flight check enforces these before the job
starts. See `spec/ptorrent-format-v1.md` for the `resources` field reference.

If a job fills your `/sdcard` partition:
1. The Android system may become unstable if `/data` is also affected
2. PTorrent writes output only to its own files directory — it cannot fill `/data`
3. But if `/sdcard` is a FUSE mount to `/data/media`, a large output can affect
   available space for app data

PTorrent will refuse to start any job if free storage is less than 1.2× the
declared `storage_gb` requirement.

---

## Malicious `.ptorrent` Files

The PTorrent chain tracks all published files with ORCID attribution. Before
any `.ptorrent` executes, the APK checks for `FLAG` transactions on the chain.

If you receive a `.ptorrent` that:
- Attempts to access system paths (blocked by sandbox, logged)
- Imports `subprocess` or `ctypes` (blocked by sandbox, logged)
- Attempts writes outside app storage (blocked by sandbox, logged)

Do the following:
1. Note the ORCID on the `ANNOUNCE` transaction for that file
2. Run `chain.flag(file_hash, "attempted_system_write", detail, evidence, peer_id)`
3. Contact the ORCID holder directly
4. Report to the PTorrent issue tracker: https://github.com/michaelrendier/PTorrent

The sandbox exception message includes the blocked path. Include this in the
`detail` parameter of `chain.flag()` and in your issue report.

---

## Summary

| Operation | PTorrent does it? | Risk |
|-----------|------------------|------|
| Write to app files directory | Yes | Low — sandboxed |
| Read from public URLs | Yes | Low — rate-limited, robots.txt checked |
| Write to /system | Never | Soft brick |
| Write to /vbmeta | Never | Hard brick |
| Spawn shell processes | Never | Blocked by Python sandbox |
| Modify build.prop | Never | Blocked by Android sandbox + Python sandbox |
| Access other apps' data | Never | Blocked by Android sandbox |
