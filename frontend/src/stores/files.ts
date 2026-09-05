import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { apiRequest } from "../lib/api";
import { useAuthStore } from "./auth";
import { encryptName, decryptName } from "../lib/crypto/names";
import { cacheNodes, searchLocalNodes, type CachedMetadataNode } from "../lib/db";

export interface FileNode {
  id: string;
  parent: string | null;
  type: "file" | "folder";
  encrypted_name: string;
  name_nonce: string;
  name: string; // Decrypted client-side!
  size_bytes: number;
  thumbnail_object_key?: string;
  thumbnail_nonce?: string;
  created_at: string;
  updated_at: string;
  trashed_at?: string | null;
}

export const useFilesStore = defineStore("files", () => {
  const authStore = useAuthStore();
  const rawNodes = ref<FileNode[]>([]);
  const currentParentId = ref<string | null>(null);
  const breadcrumbs = ref<{ id: string | null; name: string }[]>([
    { id: null, name: "My Files" },
  ]);
  const selectedNodeIds = ref<Set<string>>(new Set());
  const viewMode = ref<"grid" | "list">("grid");
  const searchQuery = ref<string>("");
  const searchResults = ref<CachedMetadataNode[]>([]);
  const isLoading = ref<boolean>(false);
  const filterMode = ref<"files" | "recent" | "starred" | "trash">("files");

  const nodes = computed(() => {
    return rawNodes.value;
  });

  async function fetchNodes(parentId: string | null = currentParentId.value) {
    if (!authStore.masterKey) return;
    isLoading.value = true;
    currentParentId.value = parentId;

    try {
      let endpoint = "/api/v1/nodes";
      if (filterMode.value === "trash") {
        endpoint += "?trashed=true";
      } else if (parentId) {
        endpoint += `?parent=${parentId}`;
      }

      const res = await apiRequest<{ results: any[] } | any[]>(endpoint);
      const items = Array.isArray(res) ? res : res.results || [];

      // Decrypt all file and folder names in parallel using the user's Master Key
      const decryptedNodes: FileNode[] = await Promise.all(
        items.map(async (item: any) => {
          let decrypted = "[Encrypted]";
          if (authStore.masterKey) {
            decrypted = await decryptName(
              authStore.masterKey,
              item.encrypted_name,
              item.name_nonce
            );
          }
          return {
            ...item,
            name: decrypted,
          };
        })
      );

      rawNodes.value = decryptedNodes;

      // Update local IndexedDB search index
      const cacheEntries: CachedMetadataNode[] = decryptedNodes.map((n) => ({
        id: n.id,
        parentId: n.parent,
        name: n.name,
        type: n.type,
        sizeBytes: n.size_bytes,
        updatedAt: n.updated_at,
      }));
      await cacheNodes(cacheEntries);
    } finally {
      isLoading.value = false;
    }
  }

  async function createFolder(folderName: string, parentId: string | null = currentParentId.value) {
    if (!authStore.masterKey) throw new Error("Vault is locked");

    const { ciphertextBase64, nonceHex } = await encryptName(
      authStore.masterKey,
      folderName
    );

    const res = await apiRequest<FileNode>("/api/v1/nodes", {
      method: "POST",
      body: JSON.stringify({
        parent: parentId,
        encrypted_name: ciphertextBase64,
        name_nonce: nonceHex,
      }),
    });

    res.name = folderName;
    rawNodes.value.unshift(res);
    return res;
  }

  async function renameNode(nodeId: string, newName: string) {
    if (!authStore.masterKey) throw new Error("Vault is locked");

    const { ciphertextBase64, nonceHex } = await encryptName(
      authStore.masterKey,
      newName
    );

    await apiRequest(`/api/v1/nodes/${nodeId}`, {
      method: "PATCH",
      body: JSON.stringify({
        encrypted_name: ciphertextBase64,
        name_nonce: nonceHex,
      }),
    });

    const target = rawNodes.value.find((n) => n.id === nodeId);
    if (target) {
      target.name = newName;
    }
  }

  async function moveNode(nodeId: string, newParentId: string | null) {
    await apiRequest(`/api/v1/nodes/${nodeId}`, {
      method: "PATCH",
      body: JSON.stringify({ parent: newParentId }),
    });
    // Remove from current view
    rawNodes.value = rawNodes.value.filter((n) => n.id !== nodeId);
  }

  async function trashNode(nodeId: string) {
    await apiRequest(`/api/v1/nodes/${nodeId}`, { method: "DELETE" });
    rawNodes.value = rawNodes.value.filter((n) => n.id !== nodeId);
    selectedNodeIds.value.delete(nodeId);
  }

  async function restoreNode(nodeId: string) {
    await apiRequest(`/api/v1/nodes/${nodeId}/restore`, { method: "POST" });
    rawNodes.value = rawNodes.value.filter((n) => n.id !== nodeId);
  }

  function navigateToFolder(folderId: string | null, folderName: string) {
    if (folderId === null) {
      breadcrumbs.value = [{ id: null, name: "My Files" }];
    } else {
      breadcrumbs.value.push({ id: folderId, name: folderName });
    }
    fetchNodes(folderId);
  }

  function navigateUp(index: number) {
    breadcrumbs.value = breadcrumbs.value.slice(0, index + 1);
    const target = breadcrumbs.value[index];
    fetchNodes(target.id);
  }

  async function performSearch(query: string) {
    searchQuery.value = query;
    if (!query.trim()) {
      searchResults.value = [];
      return;
    }
    searchResults.value = await searchLocalNodes(query);
  }

  function toggleSelect(nodeId: string, multi: boolean = false) {
    if (!multi) {
      if (selectedNodeIds.value.has(nodeId) && selectedNodeIds.value.size === 1) {
        selectedNodeIds.value.clear();
      } else {
        selectedNodeIds.value = new Set([nodeId]);
      }
    } else {
      if (selectedNodeIds.value.has(nodeId)) {
        selectedNodeIds.value.delete(nodeId);
      } else {
        selectedNodeIds.value.add(nodeId);
      }
    }
  }

  function clearSelection() {
    selectedNodeIds.value.clear();
  }

  return {
    rawNodes,
    nodes,
    currentParentId,
    breadcrumbs,
    selectedNodeIds,
    viewMode,
    searchQuery,
    searchResults,
    isLoading,
    filterMode,
    fetchNodes,
    createFolder,
    renameNode,
    moveNode,
    trashNode,
    restoreNode,
    navigateToFolder,
    navigateUp,
    performSearch,
    toggleSelect,
    clearSelection,
  };
});
