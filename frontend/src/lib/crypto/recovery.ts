// Curated representative BIP-39 English word list for 24-word recovery phrases
export const BIP39_WORDS: string[] = [
  "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract", "absurd", "abuse",
  "access", "accident", "account", "accuse", "achieve", "acid", "acoustic", "acquire", "across", "act",
  "action", "actor", "actress", "actual", "adapt", "add", "addict", "address", "adjust", "admit",
  "adult", "advance", "advice", "aerobic", "affair", "afford", "afraid", "again", "age", "agent",
  "agree", "ahead", "aim", "air", "airport", "aisle", "alarm", "album", "alcohol", "alert",
  "alien", "all", "alley", "allow", "almost", "alone", "alpha", "already", "also", "alter",
  "always", "amateur", "amazing", "among", "amount", "amused", "analyst", "anchor", "ancient", "anger",
  "angle", "angry", "animal", "ankle", "announce", "annual", "another", "answer", "antenna", "antique",
  "anxiety", "any", "apart", "apology", "appear", "apple", "approve", "april", "arch", "arctic",
  "area", "arena", "argue", "arm", "armed", "armor", "army", "around", "arrange", "arrest",
  "arrive", "arrow", "art", "artefact", "artist", "artwork", "ask", "aspect", "assault", "asset",
  "assist", "assume", "asthma", "athlete", "atom", "attack", "attend", "attitude", "attract", "auction",
  "audit", "august", "aunt", "author", "auto", "autumn", "average", "avocado", "avoid", "awake",
  "aware", "away", "awesome", "awful", "awkward", "axis", "baby", "bachelor", "bacon", "badge",
  "bag", "balance", "balcony", "ball", "bamboo", "banana", "banner", "bar", "barely", "bargain",
  "barrel", "base", "basic", "basket", "battle", "beach", "bean", "beauty", "because", "become",
  "beef", "before", "begin", "behave", "behind", "believe", "below", "belt", "bench", "benefit",
  "best", "betray", "better", "between", "beyond", "bicycle", "bid", "bike", "bind", "biology",
  "bird", "birth", "bitter", "black", "blade", "blame", "blanket", "blast", "bleak", "bless",
  "blind", "blood", "blossom", "blouse", "blue", "blur", "blush", "board", "boat", "body",
  "boil", "bomb", "bone", "bonus", "book", "boost", "border", "boring", "borrow", "boss",
  "bottom", "bounce", "box", "boy", "bracket", "brain", "brand", "brass", "brave", "bread",
  "breeze", "brick", "bridge", "brief", "bright", "bring", "brisk", "broccoli", "broken", "bronze",
  "brother", "brown", "brush", "bubble", "buddy", "budget", "buffalo", "build", "bulb", "bulk",
  "bullet", "bundle", "bunker", "burden", "burger", "burst", "bus", "business", "busy", "butter",
  "buyer", "buzz", "cabbage", "cabin", "cable", "cactus", "cage", "cake", "call", "calm"
];

/**
 * Generates a 24-word recovery phrase.
 */
export function generateRecoveryPhrase(): string[] {
  const words: string[] = [];
  const randomIndices = new Uint16Array(24);
  crypto.getRandomValues(randomIndices);
  for (let i = 0; i < 24; i++) {
    const idx = randomIndices[i] % BIP39_WORDS.length;
    words.push(BIP39_WORDS[idx]);
  }
  return words;
}

/**
 * Derives a 256-bit Recovery Key from a 24-word recovery phrase using PBKDF2-HMAC-SHA256.
 */
export async function deriveRecoveryKey(phrase: string[] | string): Promise<Uint8Array> {
  const phraseString = Array.isArray(phrase) ? phrase.join(" ").trim().toLowerCase() : phrase.trim().toLowerCase();
  const encoder = new TextEncoder();
  const passphraseBytes = encoder.encode(phraseString);
  const saltBytes = encoder.encode("speedcloud-mnemonic-salt");

  const importedKey = await crypto.subtle.importKey(
    "raw",
    passphraseBytes,
    { name: "PBKDF2" },
    false,
    ["deriveBits"]
  );

  const derivedBits = await crypto.subtle.deriveBits(
    {
      name: "PBKDF2",
      salt: saltBytes,
      iterations: 2048,
      hash: "SHA-256",
    },
    importedKey,
    256
  );

  return new Uint8Array(derivedBits);
}
