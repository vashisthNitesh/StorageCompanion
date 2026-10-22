import { defineStore } from "pinia";
import { ref, computed } from "vue";
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

const ROOT_CRUMB: Crumb = { id: null, name: "My files" };

async function decryptNodes(key: Uint8Array, items: any[]): Promise<FileNode[]> {
  return Promise.all(
    items.map(async (item) => ({
      ...item,
      name: await decryptName(key, item.encrypted_name, item.name_nonce),
    }))
  );
}

export const useFilesStore = defineStore("files", () => {
  const authStore = useAuthStore();

  const nodes = ref<FileNode[]>([]);
  const currentParentId = ref<string | null>(null);
  const breadcrumbs = ref<Crumb[]>([ROOT_CRUMB]);
  const viewMode = ref<"grid" | "list">(
    (typeof localStorage !== "undefined" && (localStorage.getItem("sc_view_mode") as "grid" | "list")) || "list"
  );
  const isLoading = ref(false);
  const loadError = ref("");

  // Search across every folder. Names are encrypted, so the whole tree is fetched and
  // decrypted in the browser once, then reused until something changes.
  const searchQuery = ref("");
  const isSearching = ref(false);
  const searchError = ref("");
  let allNodesIndex: FileNode[] | null = null;
  let indexPromise: Promise<FileNode[]> | null = null;

  let requestSeq = 0;

  function setViewMode(mode: "grid" | "list") {
    viewMode.value = mode;
    try {
      localStorage.setItem("sc_view_mode", mode);
    } catch {
      // storage unavailable
    }
  }

  function invalidateIndex() {
    allNodesIndex = null;
    indexPromise = null;
  }

  async function fetchNodes(parentId: string | null = currentParentId.value) {
    const key = authStore.masterKey;
    if (!key) return;
    const seq = ++requestSeq;
    isLoading.value = true;
    loadError.value = "";
    currentParentId.value = parentId;

    try {
      const endpoint = parentId ? `/api/v1/nodes?parent=${encodeURIComponent(parentId)}` : "/api/v1/nodes";
      const items = await apiRequest<any[]>(endpoint);
      const decrypted = await decryptNodes(key, items);
      if (seq === requestSeq) nodes.value = decrypted;
    } catch (err: any) {
      if (seq === requestSeq) loadError.value = err.message || "Couldn't load your files.";
    } finally {
      if (seq === requestSeq) isLoading.value = false;
    }
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
    return parts.length ? `My files / ${parts.join(" / ")}` : "My files";
  }

  const searchResults = ref<SearchResult[]>([]);
  const isSearchActive = computed(() => searchQuery.value.trim().length > 0);

  let searchSeq = 0;
  async function search(query: string) {
    searchQuery.value = query;
    const q = query.trim().toLowerCase();
    const seq = ++searchSeq;
    if (!q) {
      searchResults.value = [];
      searchError.value = "";
      isSearching.value = false;
      return;
    }
    isSearching.value = true;
    searchError.value = "";
    try {
      const index = await loadIndex();
      if (seq !== searchSeq) return;
      const byId = new Map(index.map((n) => [n.id, n]));
      const terms = q.split(/\s+/).filter(Boolean);
      searchResults.value = index
        .filter((n) => {
          const name = n.name.toLowerCase();
          return terms.every((t) => name.includes(t));
        })
        .slice(0, 200)
        .map((n) => ({ ...n, location: locationOf(n, byId) }));
    } catch (err: any) {
      if (seq === searchSeq) searchError.value = err.message || "Search failed. Please try again.";
    } finally {
      if (seq === searchSeq) isSearching.value = false;
    }
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

  /** Items to briefly highlight (new uploads, revealed search hits). */
  const highlightIds = ref<Set<string>>(new Set());
  function highlight(ids: string[]) {
    highlightIds.value = new Set([...highlightIds.value, ...ids]);
    setTimeout(() => {
      const next = new Set(highlightIds.value);
      ids.forEach((id) => next.delete(id));
      highlightIds.value = next;
    }, 2400);
  }

  /** Opens the folder containing `node` and highlights it. */
  async function revealNode(node: { id: string; parent: string | null }) {
    await openFolderFromSearch(node.parent);
    highlight([node.id]);
  }

  function clearSearch() {
    searchSeq++;
    searchQuery.value = "";
    searchResults.value = [];
    searchError.value = "";
    isSearching.value = false;
  }

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

  async function createFolder(folderName: string, parentId: string | null = currentParentId.value) {
    if (!authStore.masterKey) throw new Error("Unlock your vault first.");
    const { ciphertextBase64, nonceHex } = await encryptName(authStore.masterKey, folderName);
    const res = await apiRequest<FileNode>("/api/v1/nodes", {
      method: "POST",
      body: JSON.stringify({ parent: parentId, encrypted_name: ciphertextBase64, name_nonce: nonceHex }),
    });
    res.name = folderName;
    if (parentId === currentParentId.value) nodes.value = [res, ...nodes.value];
    invalidateIndex();
    return res;
  }

  async function renameNode(nodeId: string, newName: string) {
    if (!authStore.masterKey) throw new Error("Unlock your vault first.");
    const { ciphertextBase64, nonceHex } = await encryptName(authStore.masterKey, newName);
    await apiRequest(`/api/v1/nodes/${nodeId}`, {
      method: "PATCH",
      body: JSON.stringify({ encrypted_name: ciphertextBase64, name_nonce: nonceHex }),
    });
    const target = nodes.value.find((n) => n.id === nodeId);
    if (target) target.name = newName;
    const hit = searchResults.value.find((n) => n.id === nodeId);
    if (hit) hit.name = newName;
    invalidateIndex();
  }

  async function moveNode(nodeId: string, newParentId: string | null) {
    await apiRequest(`/api/v1/nodes/${nodeId}`, { method: "PATCH", body: JSON.stringify({ parent: newParentId }) });
    if (newParentId !== currentParentId.value) nodes.value = nodes.value.filter((n) => n.id !== nodeId);
    invalidateIndex();
  }

  function applyQuota(res: { quota?: any } | undefined) {
    if (res?.quota && authStore.user) authStore.user.quota = res.quota;
    else authStore.fetchProfile().catch(() => {});
  }

  async function trashNode(nodeId: string) {
    const res = await apiRequest<{ quota?: any }>(`/api/v1/nodes/${nodeId}`, { method: "DELETE" });
    nodes.value = nodes.value.filter((n) => n.id !== nodeId);
    searchResults.value = searchResults.value.filter((n) => n.id !== nodeId);
    invalidateIndex();
    applyQuota(res);
  }

  async function restoreNode(nodeId: string) {
    const res = await apiRequest<{ quota?: any }>(`/api/v1/nodes/${nodeId}/restore`, { method: "POST" });
    invalidateIndex();
    applyQuota(res);
  }

  async function permanentDeleteNode(nodeId: string) {
    const res = await apiRequest<{ quota?: any }>(`/api/v1/nodes/${nodeId}?permanent=true`, { method: "DELETE" });
    invalidateIndex();
    applyQuota(res);
  }

  async function fetchTrash(): Promise<FileNode[]> {
    if (!authStore.masterKey) return [];
    const items = await apiRequest<any[]>("/api/v1/nodes?trashed=true");
    return decryptNodes(authStore.masterKey, items);
  }

  /** All folders (for the Move dialog), excluding `excludeId` and everything inside it. */
  async function listFolders(excludeId?: string): Promise<{ id: string | null; name: string; depth: number }[]> {
    const index = await loadIndex();
    const folders = index.filter((n) => n.type === "folder");
    const children = new Map<string | null, FileNode[]>();
    for (const f of folders) {
      const list = children.get(f.parent) || [];
      list.push(f);
      children.set(f.parent, list);
    }
    const out: { id: string | null; name: string; depth: number }[] = [{ id: null, name: "My files", depth: 0 }];
    const walk = (parentId: string | null, depth: number) => {
      const list = (children.get(parentId) || []).sort((a, b) => a.name.localeCompare(b.name));
      for (const f of list) {
        if (f.id === excludeId) continue;
        out.push({ id: f.id, name: f.name, depth });
        walk(f.id, depth + 1);
      }
    };
    walk(null, 1);
    return out;
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

  function navigateToCrumb(index: number) {
    const target = breadcrumbs.value[index];
    if (!target) return;
    clearSearch();
    breadcrumbs.value = breadcrumbs.value.slice(0, index + 1);
    return fetchNodes(target.id);
  }

  function reset() {
    nodes.value = [];
    currentParentId.value = null;
    breadcrumbs.value = [ROOT_CRUMB];
    invalidateIndex();
    clearSearch();
  }

  return {
    nodes,
    currentParentId,
    breadcrumbs,
    viewMode,
    isLoading,
    loadError,
    searchQuery,
    searchResults,
    isSearching,
    isSearchActive,
    searchError,
    setViewMode,
    fetchNodes,
    search,
    clearSearch,
    createFolder,
    renameNode,
    moveNode,
    trashNode,
    restoreNode,
    permanentDeleteNode,
    fetchTrash,
    listFolders,
    openFolder,
    openFolderFromSearch,
    navigateToCrumb,
    invalidateIndex,
    reset,
    findNodes,
    highlightIds,
    highlight,
    revealNode,
  };
});
