import { apiRequest } from "../../lib/api";
import { unwrapKey, wrapKey } from "../../lib/crypto/keys";
import { encryptName, decryptName } from "../../lib/crypto/names";
import { generateRandomSalt } from "../../lib/crypto/kdf";
import { sha256Hex } from "../../lib/crypto/hkdf";
import { importFileKey } from "../../lib/crypto/content";
import { DecryptError, encryptedFileFrom, type EncryptedFile } from "../../lib/crypto/encryptedFile";
import { hexToUint8Array } from "../../lib/crypto/kdf";
import {
  SHARE_KDF_PARAMS,
  decodeLinkKey,
  encodeLinkKey,
  generateLinkKey,
  passwordLayer,
  shareWrappingKey,
} from "../../lib/crypto/shareKey";

export type ExpiryChoice = "1h" | "1d" | "7d" | "30d" | "never";
export type ShareStatus = "active" | "expired" | "revoked" | "limit_reached" | "unavailable";

export interface ShareLink {
  id: string;
  token: string;
  created_at: string;
  expires_at: string | null;
  max_downloads: number | null;
  download_count: number;
  allow_download: boolean;
  password_protected: boolean;
  revoked_at: string | null;
  last_accessed_at: string | null;
  owner_wrapped_link_key: string;
  status: ShareStatus;
}

export interface ShareOptions {
  expiresIn: ExpiryChoice;
  password?: string;
  maxDownloads?: number | null;
  allowDownload: boolean;
}

export function shareUrl(token: string, linkKey: Uint8Array): string {
  return `${window.location.origin}/s/${token}#${encodeLinkKey(linkKey)}`;
}

/** Rebuilds a link's full address from the owner's copy of the link key. */
export async function urlForLink(link: ShareLink, masterKey: Uint8Array): Promise<string> {
  return shareUrl(link.token, await unwrapKey(masterKey, link.owner_wrapped_link_key));
}

export function listShares(nodeId: string) {
  return apiRequest<ShareLink[]>(`/api/v1/nodes/${nodeId}/shares`);
}

export function revokeShare(linkId: string) {
  return apiRequest(`/api/v1/shares/${linkId}`, { method: "DELETE" });
}

/**
 * Creates a link in the browser: unwraps the file key with the vault key and re-wraps it with a
 * new link key (plus the password key, if any). The server never sees either key.
 */
export async function createShare(node: { id: string; name: string }, masterKey: Uint8Array, opts: ShareOptions) {
  const info = await apiRequest<{ wrapped_file_key: string; version_no: number }>(`/api/v1/nodes/${node.id}/download?purpose=share`);
  const fileKey = await unwrapKey(masterKey, info.wrapped_file_key);
  const linkKey = generateLinkKey();
  let password: { salt: string; kdf_params: typeof SHARE_KDF_PARAMS; auth_hash: string } | null = null;
  let passwordKey: Uint8Array | undefined;
  if (opts.password) {
    const salt = generateRandomSalt(16);
    const layer = await passwordLayer(opts.password, salt);
    passwordKey = layer.key;
    password = { salt, kdf_params: SHARE_KDF_PARAMS, auth_hash: await sha256Hex(hexToUint8Array(layer.proof)) };
  }
  const wrapping = await shareWrappingKey(linkKey, passwordKey);
  const name = await encryptName(wrapping, node.name);
  const link = await apiRequest<ShareLink>(`/api/v1/nodes/${node.id}/shares`, {
    method: "POST",
    body: JSON.stringify({
      expires_in: opts.expiresIn,
      max_downloads: opts.maxDownloads || null,
      allow_download: opts.allowDownload,
      version_no: info.version_no,
      wrapped_key: await wrapKey(wrapping, fileKey),
      encrypted_name: name.ciphertextBase64,
      name_nonce: name.nonceHex,
      owner_wrapped_link_key: await wrapKey(masterKey, linkKey),
      password,
    }),
  });
  return { link, url: shareUrl(link.token, linkKey) };
}

// --- Public page ----------------------------------------------------------------------

export interface PublicShareInfo {
  size_bytes: number;
  allow_download: boolean;
  password_protected: boolean;
  expires_at: string | null;
  downloads_left: number | null;
  password_salt?: string;
  password_kdf_params?: typeof SHARE_KDF_PARAMS;
  wrapped_key?: string;
  encrypted_name?: string;
  name_nonce?: string;
}

interface OpenedShare {
  grant: string;
  wrapped_key: string;
  encrypted_name: string;
  name_nonce: string;
  content_nonce: string;
  part_size: number;
  size_bytes: number;
  allow_download: boolean;
  content_url: string;
}

export class WrongShareKey extends Error {}

export { decodeLinkKey };

export function fetchShare(token: string) {
  return apiRequest<PublicShareInfo>(`/api/v1/s/${encodeURIComponent(token)}`);
}

/** Decrypts the file name with the link key (and password). Throws WrongShareKey if they don't fit. */
export async function unlockShare(wrapped: { wrapped_key: string; encrypted_name: string; name_nonce: string }, wrapping: Uint8Array) {
  let fileKey: Uint8Array;
  try {
    fileKey = await unwrapKey(wrapping, wrapped.wrapped_key);
  } catch {
    throw new WrongShareKey();
  }
  return { fileKey, name: await decryptName(wrapping, wrapped.encrypted_name, wrapped.name_nonce) };
}

/** Keys for a password-protected link: the combined wrapping key and the proof sent to open it. */
export async function passwordKeys(linkKey: Uint8Array, info: PublicShareInfo, password: string) {
  const layer = await passwordLayer(password, info.password_salt!, info.password_kdf_params ?? SHARE_KDF_PARAMS);
  return { wrapping: await shareWrappingKey(linkKey, layer.key), proof: layer.proof };
}

/** Counts one download, then returns a reader over the decrypted content. */
export async function openShare(token: string, wrapping: Uint8Array, proof = ""): Promise<{ name: string; file: EncryptedFile; allowDownload: boolean }> {
  const opened = await apiRequest<OpenedShare>(`/api/v1/s/${encodeURIComponent(token)}/open`, {
    method: "POST",
    body: JSON.stringify({ password_proof: proof || undefined }),
  });
  const { fileKey, name } = await unlockShare(opened, wrapping);
  let key: CryptoKey;
  try {
    key = await importFileKey(fileKey);
  } catch {
    throw new DecryptError();
  }
  const file = encryptedFileFrom(
    { download_url: opened.content_url, content_nonce: opened.content_nonce, size_bytes: opened.size_bytes, part_size: opened.part_size },
    key,
    { headers: { "X-Share-Grant": opened.grant } }
  );
  return { name, file, allowDownload: opened.allow_download };
}
