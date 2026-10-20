# SmartSpace Cryptographic Specification

This document formally specifies the end-to-end client-side encryption architecture of SpeedCloud / CloudVault.

---

## 1. Threat Model & Security Invariants

SpeedCloud is designed under a **Zero-Knowledge** operational model:
- **Untrusted Infrastructure**: The storage servers, databases, backend API processes, network transit, and S3/R2 storage buckets are assumed to be accessible to adversaries or subpoenaed.
- **Client Security Boundary**: Decryption keys exist exclusively in the client device's volatile memory.
- **Zero Operator Access**: Even with full root access to the database and R2 buckets, an attacker **cannot** read file contents, file names, or folder names.

---

## 2. Key Hierarchy & Derivation

```
User Password (client input)
    │
    ├─► Argon2id(pwd, salt_auth) ────────► Server Password Hash (Stored in DB for authentication only)
    │
    └─► Argon2id(pwd, salt_kdf, params) ──► Key Encryption Key (KEK, 256 bits, RAM only)
                                                │
                                                ▼
                                         AES-256-KW / GCM
                                                │
                                                ▼
                                      Master Key (256 bits, CSPRNG)
                                      ├── Wrapped with KEK ───────────► DB (wrapped_master_key)
                                      └── Wrapped with Recovery Key ──► DB (recovery_wrapped_master_key)
                                                │
                   ┌────────────────────────────┼───────────────────────────┐
                   ▼                            ▼                           ▼
        File Key (256-bit CSPRNG)       Folder/File Names              User X25519 Keypair
        ├── Wrapped with Master Key     AES-256-GCM                   ├── Public Key (DB)
        └── Encrypts Chunks (AES-GCM)   Nonce: 12-byte random         └── Private Key (wrapped with Master Key)
```

### 2.1 Key Derivation Functions (KDF)
- **Library**: `hash-wasm` (WebAssembly-based Argon2id in the browser).
- **Parameters**:
  - Memory: `65536 KiB` (64 MB)
  - Time (iterations): `3`
  - Parallelism: `4`
  - Output length: `32 bytes` (256 bits)
  - Salt: 16 bytes cryptographic random, hex-encoded, generated on registration.
- **Strict Separation**: The password string is hashed with standard password authentication routines for server verification, but is *separately* derived through client Argon2id to produce the `KEK`. The KEK is never transmitted over the network.

### 2.2 Master Key
- 256-bit cryptographically secure pseudorandom number (`crypto.getRandomValues(new Uint8Array(32))`).
- Wrapped using AES-256-GCM with the KEK:
  `wrapped_master_key = AES_GCM_Encrypt(KEK, IV_12bytes, MasterKey)`.
- Stored as base64 in `User.wrapped_master_key`.

### 2.3 File Key
- Fresh 256-bit CSPRNG key per uploaded file.
- Wrapped with the user's Master Key:
  `wrapped_file_key = AES_GCM_Encrypt(MasterKey, IV_12bytes, FileKey)`.
- Stored in `FileVersion.wrapped_file_key`.

### 2.4 Recovery-wrapped Master Key
- At signup the browser also wraps the Master Key with a key derived from a random 24-word phrase
  (`recovery_wrapped_master_key`). The phrase is not shown to the user and there is no recovery
  flow yet, so a forgotten password currently means the vault cannot be opened.

### 2.5 Google sign-in accounts
- Accounts created with Google sign-in have no password, so their Master Key is derived on the
  server: `HMAC-SHA256(VAULT_KEY_SECRET, "storage_companion:vault:{user_id}:{google_sub}")`.
- The key is returned to the browser after sign-in (and from `GET /auth/vault/google-key` for new
  tabs). Files are still encrypted at rest, but the operator could derive this key, so these vaults
  are not zero-knowledge. `VAULT_KEY_SECRET` must never change.
- Password accounts never receive a key from the server, even if they later sign in with Google.

---

## 3. Content Encryption & Uploads

### 3.1 Chunking
- New uploads use **20 MB** parts (**32 MB** for files over 50 GB). The part size is stored on each
  `FileVersion` (`part_size`); older rows fall back to 8 MB (16 MB above 5 GB).

### 3.2 AES-256-GCM Chunk Encryption
Each part $i$ ($i \in [1, N]$) is encrypted independently with the File Key:
$$\text{ChunkNonce}_i = \text{BaseNonce}_{12\text{ bytes}} \oplus \text{BigEndian}(i)$$
- A nonce is never reused under the same File Key. Every encrypted part is exactly
  `plaintext + 16` bytes (GCM tag).

### 3.3 Upload relay
- The browser sends each encrypted part to `POST /api/v1/uploads/{id}/parts/{n}`; the server
  forwards it to SpaceByte with a presigned URL that never leaves the server.
- The server only ever sees ciphertext. It checks that every part has exactly the size implied by
  the declared file size, so the quota charged always equals the bytes stored.

---

## 4. Metadata & Name Encryption

- File and folder names are encrypted in the browser using AES-256-GCM with the Master Key.
- Database records only contain `encrypted_name` (ciphertext base64) and `name_nonce`.
- The database knows only:
  - Node hierarchy (`id`, `parent_id`, `type`)
  - Timestamps (`created_at`, `updated_at`, `trashed_at`)
  - File sizes in bytes

---

## 5. What an Attacker with Full Database Access Can and Cannot Learn

| Data Element | Attacker Visibility |
|---|---|
| User email & subscription tier | **Visible** |
| Password | **Protected** (Argon2id server-side hash) |
| Master Key (password accounts) | **Unreadable** (wrapped with client KEK) |
| Master Key (Google accounts) | **Derivable** with `VAULT_KEY_SECRET` (not stored in the database) |
| File Contents | **Unreadable** (AES-256-GCM ciphertext) |
| File & Folder Names | **Unreadable** (AES-256-GCM ciphertext) |
| Number of files & folder structure | Visible (Node parent/child links) |
| File sizes & timestamps | Visible |
