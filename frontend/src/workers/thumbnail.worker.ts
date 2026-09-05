import { encryptChunk } from "../lib/crypto/content";
import { generateRandomBytes } from "../lib/crypto/keys";

self.onmessage = async (e: MessageEvent) => {
  const { id, fileKeyBytes, imageBitmap } = e.data;

  try {
    const canvas = new OffscreenCanvas(256, 256);
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Could not create canvas context");

    const scale = Math.min(256 / imageBitmap.width, 256 / imageBitmap.height);
    const w = imageBitmap.width * scale;
    const h = imageBitmap.height * scale;
    const x = (256 - w) / 2;
    const y = (256 - h) / 2;

    ctx.drawImage(imageBitmap, x, y, w, h);
    const blob = await canvas.convertToBlob({ type: "image/jpeg", quality: 0.8 });
    const arrayBuffer = await blob.arrayBuffer();
    const thumbnailBytes = new Uint8Array(arrayBuffer);

    const thumbnailNonce = generateRandomBytes(12);
    const encryptedThumbnail = await encryptChunk(fileKeyBytes, thumbnailBytes, thumbnailNonce, 0);

    (self as any).postMessage(
      {
        id,
        success: true,
        encryptedThumbnail,
        thumbnailNonce,
      },
      [encryptedThumbnail.buffer]
    );
  } catch (error: any) {
    (self as any).postMessage({ id, success: false, error: error.message });
  }
};
