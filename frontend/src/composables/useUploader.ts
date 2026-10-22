import { useAuthStore } from "../stores/auth";
import { useBillingStore } from "../stores/billing";
import { useFilesStore, type FileNode } from "../stores/files";
import { useUploadStore, type UploadRequest } from "../stores/upload";
import { emitAppEvent } from "../lib/events";
import { COPY } from "../lib/errors";
import { toast } from "../lib/toast";
import { reportError } from "../lib/reportError";
import { formatBytes, splitFileName } from "../lib/format";
import { askConflict, type ConflictChoice } from "../lib/conflictPrompt";

type FileWithPath = File & { webkitRelativePath?: string };

function uniqueName(name: string, taken: Set<string>): string {
  const { stem, ext } = splitFileName(name);
  for (let i = 1; ; i++) {
    const candidate = `${stem} (${i})${ext}`;
    if (!taken.has(candidate.toLowerCase())) return candidate;
  }
}

/** Single entry point for uploads from anywhere (sidebar, toolbar, drop, shortcuts), with pre-flight checks. */
export function useUploader() {
  const authStore = useAuthStore();
  const billing = useBillingStore();
  const files = useFilesStore();
  const uploadStore = useUploadStore();

  function ensureCanUpload(): boolean {
    if (authStore.canUpload) return true;
    const ended = !!authStore.user?.subscription?.plan_code && !authStore.user?.subscription?.can_upload;
    emitAppEvent("plan-picker", { reason: ended ? COPY.planEnded : COPY.planRequired });
    return false;
  }

  async function children(parentId: string | null): Promise<FileNode[]> {
    if (parentId === files.currentParentId && files.loaded) return files.nodes;
    const all = await files.folderTree().catch(() => []);
    // folderTree only has folders; files in other folders are checked by the server-side name anyway.
    return all.filter((f) => f.parent === parentId);
  }

  async function folderName(parentId: string | null): Promise<string> {
    if (!parentId) return "My files";
    if (parentId === files.currentParentId) return files.breadcrumbs.at(-1)?.name ?? "this folder";
    const tree = await files.folderTree().catch(() => []);
    return tree.find((f) => f.id === parentId)?.name ?? "this folder";
  }

  async function upload(input: FileList | File[], parentId: string | null = files.currentParentId) {
    if (!ensureCanUpload()) return;
    let list = Array.from(input as ArrayLike<FileWithPath>);
    if (!list.length) return;

    // 1. Empty files can't be uploaded (often a download that hasn't finished).
    const empty = list.filter((f) => f.size === 0);
    if (empty.length) {
      toast.info(empty.length === 1 ? `Skipped “${empty[0].name}” because it's empty.` : `Skipped ${empty.length} empty files.`);
      list = list.filter((f) => f.size > 0);
    }

    // 2. Per-file size limit of the current plan.
    await billing.ensurePlans().catch(() => {});
    const plan = billing.plans.find((p) => p.code === authStore.user?.subscription?.plan_code);
    if (plan) {
      const tooBig = list.filter((f) => f.size > plan.max_file_size);
      if (tooBig.length) {
        const limit = formatBytes(plan.max_file_size, 0);
        const what = tooBig.length === 1 ? `“${tooBig[0].name}” is` : `${tooBig.length} files are`;
        toast.error(`${what} larger than your plan allows (max ${limit} per file).`, {
          action: { label: "Upgrade", onClick: () => emitAppEvent("plan-picker", { reason: `Your plan allows files up to ${limit}.` }) },
        });
        list = list.filter((f) => f.size <= plan.max_file_size);
      }
    }
    if (!list.length) return;

    // 3. Remaining storage.
    const quota = authStore.user?.quota;
    if (quota?.bytes_limit) {
      const needed = list.reduce((s, f) => s + f.size, 0);
      const left = Math.max(0, quota.bytes_limit - quota.bytes_used);
      if (needed > left) {
        emitAppEvent("plan-picker", {
          reason: `These files need ${formatBytes(needed)}, but you have ${formatBytes(left)} left on your plan. Upgrade for more space.`,
        });
        return;
      }
    }

    const target = { id: parentId, name: await folderName(parentId) };

    try {
      const requests: UploadRequest[] = [];
      const loose = list.filter((f) => !f.webkitRelativePath?.includes("/"));
      const nested = list.filter((f) => f.webkitRelativePath?.includes("/"));

      // 4. Name conflicts for loose files in the target folder.
      if (loose.length) {
        const siblings = await children(parentId);
        const byName = new Map(siblings.filter((n) => n.type === "file").map((n) => [n.name.toLowerCase(), n]));
        const taken = new Set(siblings.map((n) => n.name.toLowerCase()));
        const conflicts = loose.filter((f) => byName.has(f.name.toLowerCase()));
        let remembered: ConflictChoice | null = null;
        for (const file of loose) {
          const existing = byName.get(file.name.toLowerCase());
          if (!existing) {
            requests.push({ file, parentId });
            taken.add(file.name.toLowerCase());
            continue;
          }
          let choice: ConflictChoice | null = remembered;
          if (!choice) {
            const answer = await askConflict(file.name, target.name, conflicts.length - conflicts.indexOf(file));
            if (!answer) return; // cancelled the whole upload
            choice = answer.choice;
            if (answer.applyToAll) remembered = choice;
          }
          if (choice === "replace") requests.push({ file, parentId, nodeId: existing.id, keepName: existing.name, name: existing.name });
          else if (choice === "keep-both") {
            const name = uniqueName(file.name, taken);
            taken.add(name.toLowerCase());
            requests.push({ file, parentId, name });
          }
        }
      }

      // 5. Folder uploads: recreate the structure, merging into folders that already exist.
      if (nested.length) {
        const tree = await files.folderTree().catch(() => [] as FileNode[]);
        const folderIds = new Map<string, string | null>();
        const ensureFolder = async (path: string): Promise<string | null> => {
          if (!path) return parentId;
          if (folderIds.has(path)) return folderIds.get(path)!;
          const parts = path.split("/");
          const parent = await ensureFolder(parts.slice(0, -1).join("/"));
          const name = parts[parts.length - 1];
          const existing = tree.find((f) => f.parent === parent && f.name.toLowerCase() === name.toLowerCase());
          const id = existing ? existing.id : (await files.createFolder(name, parent)).id;
          folderIds.set(path, id);
          return id;
        };
        for (const file of nested) {
          const parts = file.webkitRelativePath!.split("/");
          requests.push({ file, parentId: await ensureFolder(parts.slice(0, -1).join("/")), group: parts[0] });
        }
      }

      uploadStore.enqueueBatch(requests, target);
    } catch (err) {
      reportError(err, { retry: () => void upload(input, parentId) });
    }
  }

  return { ensureCanUpload, upload };
}
