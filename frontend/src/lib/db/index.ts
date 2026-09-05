// IndexedDB wrapper for upload chunk resume state and client-side metadata index
const DB_NAME = "SpeedCloudDB";
const DB_VERSION = 1;

let dbPromise: Promise<IDBDatabase> | null = null;

function getDB(): Promise<IDBDatabase> {
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = (event: any) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains("uploads")) {
          db.createObjectStore("uploads", { keyPath: "uploadSessionId" });
        }
        if (!db.objectStoreNames.contains("metadata_cache")) {
          db.createObjectStore("metadata_cache", { keyPath: "id" });
        }
      };

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
  return dbPromise;
}

export interface StoredUpload {
  uploadSessionId: string;
  s3UploadId: string;
  fileKeyHex: string;
  baseNonceHex: string;
  wrappedFileKey: string;
  fileName: string;
  fileSize: number;
  partSize: number;
  totalParts: number;
  completedParts: { part_number: number; etag: string }[];
  status: "uploading" | "paused" | "error" | "completed";
}

export async function saveUploadState(upload: StoredUpload): Promise<void> {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("uploads", "readwrite");
    const store = tx.objectStore("uploads");
    const req = store.put(upload);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

export async function getUploadState(uploadSessionId: string): Promise<StoredUpload | null> {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("uploads", "readonly");
    const store = tx.objectStore("uploads");
    const req = store.get(uploadSessionId);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}

export async function removeUploadState(uploadSessionId: string): Promise<void> {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("uploads", "readwrite");
    const store = tx.objectStore("uploads");
    const req = store.delete(uploadSessionId);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

export interface CachedMetadataNode {
  id: string;
  parentId: string | null;
  name: string;
  type: "file" | "folder";
  sizeBytes: number;
  updatedAt: string;
}

export async function cacheNodes(nodes: CachedMetadataNode[]): Promise<void> {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("metadata_cache", "readwrite");
    const store = tx.objectStore("metadata_cache");
    nodes.forEach((node) => store.put(node));
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function searchLocalNodes(query: string): Promise<CachedMetadataNode[]> {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("metadata_cache", "readonly");
    const store = tx.objectStore("metadata_cache");
    const req = store.getAll();
    req.onsuccess = () => {
      const all: CachedMetadataNode[] = req.result || [];
      const lower = query.toLowerCase().trim();
      const matches = all.filter((n) => n.name.toLowerCase().includes(lower));
      resolve(matches);
    };
    req.onerror = () => reject(req.error);
  });
}
