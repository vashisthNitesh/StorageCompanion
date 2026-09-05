# SpeedCloud Cryptographic Specification (Zero-Knowledge Architecture)

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

### 2.4 Recovery Phrase & Recovery Key
- At signup, a 24-word BIP-39 mnemonic phrase is generated.
- The phrase derives a 256-bit Recovery Key via PBKDF2-HMAC-SHA512 (2048 iterations).
- The Master Key is wrapped with this Recovery Key:
  `recovery_wrapped_master_key = AES_GCM_Encrypt(RecoveryKey, IV_12bytes, MasterKey)`.
- If the user forgets their password, providing the 24 words allows un-wrapping the Master Key, entering a new password, and re-wrapping with a new KEK.

---

## 3. Content Encryption & Direct-to-R2 Uploads

### 3.1 Chunking
- Files are chunked client-side:
  - Files ≤ 5 GB: **8 MB** chunk size.
  - Files > 5 GB: **16 MB** chunk size.

### 3.2 AES-256-GCM Chunk Encryption
Each chunk $i$ ($i \in [1, N]$) is encrypted independently:
$$\text{ChunkNonce}_i = \text{BaseNonce}_{12\text{ bytes}} \oplus \text{BigEndian}(i)$$
- **Nonce Invariant**: A nonce is **never** reused across chunks under the same File Key.
- Chunk bytes are encrypted in a dedicated Web Worker (`encrypt.worker.ts`) using the Web Cryptography API (`SubtleCrypto.encrypt`).

### 3.3 Zero App Server Transit
- The encrypted chunks are uploaded directly from browser to Cloudflare R2 / S3 via presigned PUT URLs.
- The Gunicorn/Django backend and Nginx reverse proxy never receive or process file bytes.

---

## 4. Metadata & Name Encryption

- File and folder names are encrypted in the browser using AES-256-GCM with the Master Key.
- Database records only contain `encrypted_name` (ciphertext base64) and `name_nonce` (12 bytes base64).
- The database knows only:
  - Node hierarchy (`id`, `parent_id`, `type`)
  - Timestamps (`created_at`, `updated_at`, `trashed_at`)
  - Encrypted file sizes in bytes

---

## 5. Sharing Cryptography

### 5.1 Public Share Links
- The client generates a random 256-bit `LinkKey`.
- The `FileKey` is encrypted with the `LinkKey`:
  `wrapped_key = AES_GCM_Encrypt(LinkKey, IV, FileKey)`.
- The URL issued is formatted as:
  `https://speedcloud.app/s/<token>#<LinkKeyBase64Url>`
- **Crucial Security Property**: Everything after the `#` fragment is **never** sent to the server in HTTP requests (RFC 3986 §3.5). The server hosts the encrypted payload and token, but cannot decrypt without the fragment key.
- Optional Password Protection: Password hashed client-side or checked on server; unlocks access to the encrypted blob only after authentication.

### 5.2 User-to-User Sharing
- Each user possesses an X25519 keypair.
- When User A shares with User B:
  1. User A fetches User B's public key from `/api/v1/users/{email}/public-key`.
  2. User A performs Diffie-Hellman key exchange ($X25519(sk_A, pk_B)$) to derive a shared secret.
  3. User A wraps the `FileKey` using HKDF + AES-256-GCM with the shared secret.
  4. User B uses their private key ($X25519(sk_B, pk_A)$) to unwrap the `FileKey`.

---

## 6. What an Attacker with Full Database Access Can and Cannot Learn

| Data Element | Attacker Visibility |
|---|---|
| User email & subscription tier | **Visible** |
| Password | **Protected** (Argon2id server-side hash) |
| Master Key | **Unreadable** (Wrapped with client KEK) |
| Recovery Key | **Unreadable** (Held offline by user) |
| File Contents | **Unreadable** (AES-256-GCM ciphertext) |
| File & Folder Names | **Unreadable** (AES-256-GCM ciphertext) |
| Number of files & folder structure | Visible (Node parent/child links) |
| File sizes & timestamps | Visible |
| Share link access counts | Visible |
