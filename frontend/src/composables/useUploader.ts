import { useAuthStore } from "../stores/auth";
import { useFilesStore } from "../stores/files";
import { useUploadStore } from "../stores/upload";
import { emitAppEvent } from "../lib/events";
import { COPY } from "../lib/errors";

/** Single entry point for starting uploads from anywhere (sidebar, toolbar, drop, shortcuts). */
export function useUploader() {
  const authStore = useAuthStore();
  const filesStore = useFilesStore();
  const uploadStore = useUploadStore();

  function ensureCanUpload(): boolean {
    if (authStore.canUpload) return true;
    const ended = !!authStore.user?.subscription?.plan_code && !authStore.user?.subscription?.can_upload;
    emitAppEvent("plan-picker", { reason: ended ? COPY.planEnded : COPY.planRequired });
    return false;
  }

  function upload(files: FileList | File[], parentId: string | null = filesStore.currentParentId) {
    if (!ensureCanUpload()) return;
    void uploadStore.uploadFiles(files, parentId);
  }

  return { ensureCanUpload, upload };
}
