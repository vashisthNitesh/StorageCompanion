import { defineStore } from "pinia";
import { ref, computed, watch } from "vue";
import { apiRequest } from "../lib/api";
import { useAuthStore } from "./auth";
import { encryptName, decryptName } from "../lib/crypto/names";

export interface FileNode {
  id: string;
  parent: string | null;
  type: "file" | "folder";
  encrypted_name: string;
  name_nonce: string;
  name: string; // Decrypted client-side
  size_bytes: number;
  created_at: string;
  updated_at: string;
  trashed_at?: string | null;
}

export interface SearchResult extends FileNode {
  location: string;
}

export interface Crumb {
  id: string | null;
  name: string;
}

export type SortField = "name" | "modified" | "size";
export type SortDir = "asc" | "desc";
export interface ViewPrefs {
  view: "list" | "grid";
  sort: SortField;
  dir: SortDir;
}

const ROOT_CRUMB: Crumb = { id: null, name: "My files" };
const DEFAULT_PREFS: ViewPrefs = { view: "list", sort: "name", dir: "asc" };

/** Names that can't be decrypted are shown with a neutral placeholder, never raw ciphertext. */
const UNREADABLE = "[Encrypted File]";

async function decryptNodes(key: Uint8Array, items: any[]): Promise<FileNode[]> {
  return Promise.all(
    items.map(async (item) => {
      const name = await decryptName(key, item.encrypted_name, item.name_nonce);
      return { ...item, name: name === UNREADABLE ? "Unreadable name" : name };
    })
  );
}

export function compareNodes(field: SortField, dir: SortDir) {
  const sign = dir === "asc" ? 1 : -1;
  return (a: FileNode, b: FileNode) => {
    // Folders always first, like every desktop file manager.
    if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
    let r = 0;
    if (field === "name") r = a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: "base" });
    else if (field === "modified") r = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime();
    else r = (a.size_bytes || 0) - (b.size_bytes || 0);
    return r * sign || a.name.localeCompare(b.name);
  };
}

export const useFilesStore = defineStore("files", () => {
  const authStore = useAuthStore();

  const nodes = ref<FileNode[]>([]);
  const currentParentId = ref<string | null>(null);
  const breadcrumbs = ref<Crumb[]>([ROOT_CRUMB]);
  const isLoading = ref(false);
  const loaded = ref(false);
  const loadError = ref<unknown>(null);

  // --- View preferences, persisted per user ------------------------------------
  const prefs = ref<ViewPrefs>({ ...DEFAULT_PREFS });
  const prefsKey = computed(() => (authStore.user ? `sc_files_prefs_${authStore.user.id}` : null));
  watch(
    prefsKey,
    (key) => {
      if (!key) return;
      try {
        const saved = JSON.parse(localStorage.getItem(key) || "null");
        prefs.value = { ...DEFAULT_PREFS, ...(saved ?? {}) };
      } catch {
        prefs.value = { ...DEFAULT_PREFS };
      }
    },
    { immediate: true }
  );
  watch(
    prefs,
    (p) => {
      if (!prefsKey.value) return;
      try {
        localStorage.setItem(prefsKey.value, JSON.stringify(p));
      } catch {}
    },
    { deep: true }
  );

  // --- Search index (names are encrypted, so the tree is decrypted in the browser) ---
  const searchQuery = ref("");
  const isSearching = ref(false);
  const searchError = ref<unknown>(null);
  const searchResults = ref<SearchResult[]>([]);
  const isSearchActive = computed(() => searchQuery.value.trim().length > 0);
  let allNodesIndex: FileNode[] | null = null;
  let indexPromise: Promise<FileNode[]> | null = null;
  let requestSeq = 0;
  let searchSeq = 0;

  function invalidateIndex() {
    allNodesIndex = null;
    indexPromise = null;
  }

  async function loadIndex(): Promise<FileNode[]> {
    if (allNodesIndex) return allNodesIndex;
    if (!indexPromise) {
      const key = authStore.masterKey;
      if (!key) return [];
      indexPromise = apiRequest<any[]>("/api/v1/nodes?all=true", { timeoutMs: 45_000 })
        .then((items) => decryptNodes(key, items))
        .then((decrypted) => (allNodesIndex = decrypted))
        .catch((err) => {
          indexPromise = null;
          throw err;
        });
    }
    return indexPromise;
  }

  function locationOf(node: FileNode, byId: Map<string, FileNode>): string {
    const parts: string[] = [];
    let parentId = node.parent;
    let guard = 0;
    while (parentId && guard++ < 50) {
      const parent = byId.get(parentId);
      if (!parent) break;
      parts.unshift(parent.name);
      parentId = parent.parent;
    }
    return ["My files", ...parts].join(" / ");
  }

  async function fetchNodes(parentId: string | null = currentParentId.value) {
    const key = authStore.masterKey;
    if (!key) return;
    const seq = ++requestSeq;
    isLoading.value = true;
    loadError.value = null;
    if (parentId !== currentParentId.value) nodes.value = [];
    currentParentId.value = parentId;
    try {
      const endpoint = parentId ? `/api/v1/nodes?parent=${encodeURIComponent(parentId)}` : "/api/v1/nodes";
      const decrypted = await decryptNodes(key, await apiRequest<any[]>(endpoint));
      if (seq === requestSeq) {
        nodes.value = decrypted;
        loaded.value = true;
      }
    } catch (err) {
      if (seq === requestSeq) loadError.value = err;
    } finally {
      if (seq === requestSeq) isLoading.value = false;
    }
  }

  async function search(query: string) {
    searchQuery.value = query;
    const q = query.trim().toLowerCase();
    const seq = ++searchSeq;
    if (!q) {
      searchResults.value = [];
      searchError.value = null;
      isSearching.value = false;
      return;
    }
    isSearching.value = true;
    searchError.value = null;
    try {
      const index = await loadIndex();
      if (seq !== searchSeq) return;
      const byId = new Map(index.map((n) => [n.id, n]));
      const terms = q.split(/\s+/).filter(Boolean);
      searchResults.value = index
        .filter((n) => terms.every((t) => n.name.toLowerCase().includes(t)))
        .slice(0, 500)
        .map((n) => ({ ...n, location: locationOf(n, byId) }));
    } catch (err) {
      if (seq === searchSeq) searchError.value = err;
    } finally {
      if (seq === searchSeq) isSearching.value = false;
    }
  }

  function clearSearch() {
    searchSeq++;
    searchQuery.value = "";
    searchResults.value = [];
    searchError.value = null;
    isSearching.value = false;
  }

  /** Name lookup for the command palette; doesn't change the visible search. */
  async function findNodes(query: string, limit = 8): Promise<SearchResult[]> {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const index = await loadIndex();
    const byId = new Map(index.map((n) => [n.id, n]));
    const terms = q.split(/\s+/);
    return index
      .filter((n) => terms.every((t) => n.name.toLowerCase().includes(t)))
      .sort((a, b) => (a.type === b.type ? 0 : a.type === "folder" ? -1 : 1))
      .slice(0, limit)
      .map((n) => ({ ...n, location: locationOf(n, byId) }));
  }

  /** Most recently changed files across all folders. */
  async function recentFiles(limit = 100): Promise<SearchResult[]> {
    const index = await loadIndex();
    const byId = new Map(index.map((n) => [n.id, n]));
    return index
      .filter((n) => n.type === "file")
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, limit)
      .map((n) => ({ ...n, location: locationOf(n, byId) }));
  }

  // --- Highlighting (new uploads, revealed items) -------------------------------
  const highlightIds = ref<Set<string>>(new Set());
  function highlight(ids: string[]) {
    highlightIds.value = new Set([...highlightIds.value, ...ids]);
    setTimeout(() => {
      const next = new Set(highlightIds.value);
      ids.forEach((id) => next.delete(id));
      highlightIds.value = next;
    }, 2400);
  }

  // --- Navigation -----------------------------------------------------------------
  async function folderPath(folderId: string): Promise<Crumb[]> {
    const index = await loadIndex();
    const byId = new Map(index.map((n) => [n.id, n]));
    const path: Crumb[] = [];
    let current = byId.get(folderId);
    let guard = 0;
    while (current && guard++ < 50) {
      path.unshift({ id: current.id, name: current.name });
      current = current.parent ? byId.get(current.parent) : undefined;
    }
    return [ROOT_CRUMB, ...path];
  }

  function openFolder(folderId: string | null, folderName?: string) {
    clearSearch();
    if (folderId === null) {
      breadcrumbs.value = [ROOT_CRUMB];
    } else {
      const existing = breadcrumbs.value.findIndex((c) => c.id === folderId);
      if (existing >= 0) breadcrumbs.value = breadcrumbs.value.slice(0, existing + 1);
      else breadcrumbs.value = [...breadcrumbs.value, { id: folderId, name: folderName || "Folder" }];
    }
    return fetchNodes(folderId);
  }

  async function openFolderFromSearch(folderId: string | null) {
    clearSearch();
    breadcrumbs.value = folderId ? await folderPath(folderId).catch(() => [ROOT_CRUMB]) : [ROOT_CRUMB];
    return fetchNodes(folderId);
  }

  async function revealNode(node: { id: string; parent: string | null }) {
    await openFolderFromSearch(node.parent);
    highlight([node.id]);
  }

  function navigateToCrumb(index: number) {
    const target = breadcrumbs.value[index];
    if (!target) return;
    clearSearch();
    breadcrumbs.value = breadcrumbs.value.slice(0, index + 1);
    return fetchNodes(target.id);
  }

  // --- Mutations (optimistic; callers handle errors and undo) ----------------------
  function nameExists(name: string, parentId: string | null, exceptId?: string): boolean {
    const lower = name.trim().toLowerCase();
    const siblings = parentId === currentParentId.value ? nodes.value : (allNodesIndex ?? []).filter((n) => n.parent === parentId);
    return siblings.some((n) => n.id !== exceptId && n.name.toLowerCase() === lower);
  }

  async function createFolder(folderName: string, parentId: string | null = currentParentId.value) {
    if (!authStore.masterKey) throw new Error("vault_locked");
    const { ciphertextBase64, nonceHex } = await encryptName(authStore.masterKey, folderName);
    const res = await apiRequest<FileNode>("/api/v1/nodes", {
      method: "POST",
      body: JSON.stringify({ parent: parentId, encrypted_name: ciphertextBase64, name_nonce: nonceHex }),
    });
    res.name = folderName;
    if (parentId === currentParentId.value) {
      nodes.value = [res, ...nodes.value];
      highlight([res.id]);
    }
    invalidateIndex();
    return res;
  }

  function patchLocal(id: string, patch: Partial<FileNode>) {
    nodes.value = nodes.value.map((n) => (n.id === id ? { ...n, ...patch } : n));
    searchResults.value = searchResults.value.map((n) => (n.id === id ? { ...n, ...patch } : n));
  }

  async function renameNode(nodeId: string, newName: string) {
    if (!authStore.masterKey) throw new Error("vault_locked");
    const before = nodes.value.find((n) => n.id === nodeId) ?? searchResults.value.find((n) => n.id === nodeId);
    patchLocal(nodeId, { name: newName });
    try {
      const { ciphertextBase64, nonceHex } = await encryptName(authStore.masterKey, newName);
      await apiRequest(`/api/v1/nodes/${nodeId}`, {
        method: "PATCH",
        body: JSON.stringify({ encrypted_name: ciphertextBase64, name_nonce: nonceHex }),
      });
      invalidateIndex();
    } catch (err) {
      if (before) patchLocal(nodeId, { name: before.name });
      throw err;
    }
  }

  async function moveNode(node: FileNode, newParentId: string | null) {
    const wasVisible = nodes.value.some((n) => n.id === node.id);
    if (newParentId !== currentParentId.value) nodes.value = nodes.value.filter((n) => n.id !== node.id);
    try {
      await apiRequest(`/api/v1/nodes/${node.id}`, { method: "PATCH", body: JSON.stringify({ parent: newParentId }) });
      invalidateIndex();
      if (newParentId === currentParentId.value && !wasVisible) {
        nodes.value = [...nodes.value, { ...node, parent: newParentId }];
        highlight([node.id]);
      }
    } catch (err) {
      if (wasVisible && !nodes.value.some((n) => n.id === node.id)) nodes.value = [...nodes.value, node];
      throw err;
    }
  }

  function applyQuota(res: { quota?: any } | undefined) {
    if (res?.quota && authStore.user) authStore.user.quota = res.quota;
    else authStore.fetchProfile().catch(() => {});
  }

  async function trashNode(node: FileNode) {
    nodes.value = nodes.value.filter((n) => n.id !== node.id);
    searchResults.value = searchResults.value.filter((n) => n.id !== node.id);
    try {
      applyQuota(await apiRequest<{ quota?: any }>(`/api/v1/nodes/${node.id}`, { method: "DELETE" }));
      invalidateIndex();
    } catch (err) {
      if (node.parent === currentParentId.value) nodes.value = [...nodes.value, node];
      throw err;
    }
  }

  async function restoreNode(node: FileNode) {
    applyQuota(await apiRequest<{ quota?: any }>(`/api/v1/nodes/${node.id}/restore`, { method: "POST" }));
    invalidateIndex();
    if (node.parent === currentParentId.value && !nodes.value.some((n) => n.id === node.id)) {
      nodes.value = [...nodes.value, { ...node, trashed_at: null }];
      highlight([node.id]);
    }
  }

  async function permanentDeleteNode(nodeId: string) {
    applyQuota(await apiRequest<{ quota?: any }>(`/api/v1/nodes/${nodeId}?permanent=true`, { method: "DELETE" }));
    invalidateIndex();
  }

  async function fetchTrash(): Promise<FileNode[]> {
    if (!authStore.masterKey) return [];
    return decryptNodes(authStore.masterKey, await apiRequest<any[]>("/api/v1/nodes?trashed=true"));
  }

  /** Called by the upload store when a file finishes; updates the list in place. */
  function upsertUploaded(node: FileNode) {
    invalidateIndex();
    if (node.parent !== currentParentId.value) return;
    const exists = nodes.value.some((n) => n.id === node.id);
    nodes.value = exists ? nodes.value.map((n) => (n.id === node.id ? { ...n, ...node } : n)) : [...nodes.value, node];
    highlight([node.id]);
  }

  /** Folder tree for the Move dialog. */
  async function folderTree(): Promise<FileNode[]> {
    return (await loadIndex()).filter((n) => n.type === "folder");
  }

  function reset() {
    nodes.value = [];
    loaded.value = false;
    currentParentId.value = null;
    breadcrumbs.value = [ROOT_CRUMB];
    invalidateIndex();
    clearSearch();
  }

  return {
    nodes,
    currentParentId,
    breadcrumbs,
    isLoading,
    loaded,
    loadError,
    prefs,
    searchQuery,
    searchResults,
    isSearching,
    isSearchActive,
    searchError,
    highlightIds,
    fetchNodes,
    search,
    clearSearch,
    findNodes,
    recentFiles,
    highlight,
    openFolder,
    openFolderFromSearch,
    revealNode,
    navigateToCrumb,
    nameExists,
    createFolder,
    renameNode,
    moveNode,
    trashNode,
    restoreNode,
    permanentDeleteNode,
    fetchTrash,
    upsertUploaded,
    folderTree,
    invalidateIndex,
    reset,
  };
});
