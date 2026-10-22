import { emitAppEvent } from "../lib/events";

/** Opens the app-wide file / folder pickers owned by AppLayout. */
export function useFilePicker() {
  return {
    pickFiles: () => emitAppEvent("upload-files"),
    pickFolder: () => emitAppEvent("upload-folder"),
  };
}
