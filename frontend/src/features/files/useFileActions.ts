import { useFilesStore, type FileNode } from "../../stores/files";
import { toast } from "../../lib/toast";
import { reportError } from "../../lib/reportError";
import { useFileDownload } from "./useFileDownload";

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** File operations with optimistic UI, undo toasts and designed error handling. */
export function useFileActions() {
  const files = useFilesStore();
  const { downloadFile } = useFileDownload();

  function fail(err: unknown, retry?: () => void) {
    const n = reportError(err, { retry });
    if (n.kind === "not_found") void files.fetchNodes();
  }

  async function download(nodes: FileNode[]) {
    for (const node of nodes.filter((n) => n.type === "file")) await downloadFile(node);
  }

  /** `rethrow` lets a dialog show the error inline instead of a toast. */
  async function rename(node: FileNode, name: string, { undoable = true, rethrow = false } = {}) {
    const previous = node.name;
    if (previous === name) return true;
    try {
      await files.renameNode(node.id, name);
      if (undoable) toast.undoable(`Renamed to “${name}”`, () => void rename({ ...node, name }, previous, { undoable: false }));
      return true;
    } catch (err) {
      if (rethrow) throw err;
      fail(err, () => void rename(node, name, { undoable }));
      return false;
    }
  }

  async function trash(nodes: FileNode[]) {
    const results = await Promise.allSettled(nodes.map((n) => files.trashNode(n)));
    const done = nodes.filter((_, i) => results[i].status === "fulfilled");
    const failed = results.find((r): r is PromiseRejectedResult => r.status === "rejected");
    if (done.length) {
      const label = done.length === 1 ? `“${done[0].name}” moved to trash` : `${plural(done.length, "item")} moved to trash`;
      toast.undoable(label, () => void restore(done));
    }
    if (failed) fail(failed.reason, () => void trash(nodes.filter((n) => !done.includes(n))));
    return done;
  }

  async function restore(nodes: FileNode[]) {
    const results = await Promise.allSettled(nodes.map((n) => files.restoreNode(n)));
    const failed = results.find((r): r is PromiseRejectedResult => r.status === "rejected");
    if (failed) fail(failed.reason);
  }

  async function move(nodes: FileNode[], destination: { id: string | null; name: string }, { undoable = true } = {}) {
    const origins = nodes.map((n) => ({ node: n, from: n.parent }));
    const results = await Promise.allSettled(nodes.map((n) => files.moveNode(n, destination.id)));
    const moved = origins.filter((_, i) => results[i].status === "fulfilled");
    const failed = results.find((r): r is PromiseRejectedResult => r.status === "rejected");
    if (moved.length && undoable) {
      const label = moved.length === 1 ? `Moved “${moved[0].node.name}” to ${destination.name}` : `Moved ${plural(moved.length, "item")} to ${destination.name}`;
      toast.undoable(label, () => {
        for (const m of moved) void files.moveNode({ ...m.node, parent: destination.id }, m.from).catch((e) => fail(e));
      });
    }
    if (failed) fail(failed.reason);
    return moved.length;
  }

  return { download, rename, trash, restore, move };
}
