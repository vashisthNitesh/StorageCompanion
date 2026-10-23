/** Why a file can't be shown; the viewer swaps in a fallback with a Download button. */
export type ViewProblem =
  | { kind: "unsupported" }
  | { kind: "too-large" }
  | { kind: "damaged" }
  | { kind: "locked" }
  | { kind: "failed"; message: string };

/** Largest files each viewer will load into memory. */
export const LIMITS = {
  image: 200 * 1024 * 1024,
  pdf: 200 * 1024 * 1024,
  docx: 50 * 1024 * 1024,
  sheet: 30 * 1024 * 1024,
  /** Videos without the streaming worker are decrypted into memory first. */
  mediaInMemory: 500 * 1024 * 1024,
};
