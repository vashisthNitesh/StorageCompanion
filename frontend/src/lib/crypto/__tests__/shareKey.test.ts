import { describe, expect, it } from "vitest";
import { decodeLinkKey, encodeLinkKey, generateLinkKey, passwordLayer, shareWrappingKey } from "../shareKey";
import { generateFileKey, unwrapKey, wrapKey } from "../keys";
import { generateRandomSalt, uint8ArrayToHex } from "../kdf";

describe("share link keys", () => {
  it("round-trips the link key through a URL-safe fragment", () => {
    for (let i = 0; i < 20; i++) {
      const key = generateLinkKey();
      const text = encodeLinkKey(key);
      expect(text).toMatch(/^[A-Za-z0-9_-]{43}$/);
      expect(uint8ArrayToHex(decodeLinkKey(text)!)).toBe(uint8ArrayToHex(key));
    }
    expect(decodeLinkKey("too-short")).toBeNull();
    expect(decodeLinkKey("%%%")).toBeNull();
  });

  it("needs both the link key and the password when a password is set", async () => {
    const fileKey = generateFileKey();
    const linkKey = generateLinkKey();
    const salt = generateRandomSalt(16);
    const right = await passwordLayer("correct horse", salt);
    const wrapped = await wrapKey(await shareWrappingKey(linkKey, right.key), fileKey);

    const opened = await unwrapKey(await shareWrappingKey(linkKey, (await passwordLayer("correct horse", salt)).key), wrapped);
    expect(uint8ArrayToHex(opened)).toBe(uint8ArrayToHex(fileKey));

    const wrong = await passwordLayer("wrong horse", salt);
    await expect(unwrapKey(await shareWrappingKey(linkKey, wrong.key), wrapped)).rejects.toThrow();
    await expect(unwrapKey(linkKey, wrapped)).rejects.toThrow();
    await expect(unwrapKey(await shareWrappingKey(generateLinkKey(), right.key), wrapped)).rejects.toThrow();
  });

  it("derives a proof that differs from the wrapping key", async () => {
    const layer = await passwordLayer("pw", generateRandomSalt(16));
    expect(layer.proof).toMatch(/^[0-9a-f]{64}$/);
    expect(layer.proof).not.toBe(uint8ArrayToHex(layer.key));
  });
});
