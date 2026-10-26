<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from "vue";
import { useRoute } from "vue-router";
import { Download, Eye, LockKeyhole, ShieldCheck, Clock, LinkIcon, Ban, TimerOff, FileX2, ArrowRight } from "lucide-vue-next";
import AppLogo from "../../components/AppLogo.vue";
import ThemeToggle from "../../components/ThemeToggle.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiFormField from "../../components/ui/UiFormField.vue";
import UiPasswordInput from "../../components/ui/UiPasswordInput.vue";
import UiProgress from "../../components/ui/UiProgress.vue";
import UiSpinner from "../../components/ui/UiSpinner.vue";
import { normalizeApiError } from "../../lib/errors";
import { formatBytes, formatDate } from "../../lib/format";
import { DecryptError, type EncryptedFile } from "../../lib/crypto/encryptedFile";
import type { FileNode } from "../../stores/files";
import { kindInfo, kindOf } from "../files/fileTypes";
import { previewKindOf, likelyUnsupported, mimeOf } from "../preview/previewTypes";
import ImageView from "../preview/views/ImageView.vue";
import MediaView from "../preview/views/MediaView.vue";
import PdfView from "../preview/views/PdfView.vue";
import DocxView from "../preview/views/DocxView.vue";
import SheetView from "../preview/views/SheetView.vue";
import TextView from "../preview/views/TextView.vue";
import type { ViewProblem } from "../preview/views/types";
import { WrongShareKey, decodeLinkKey, fetchShare, openShare, passwordKeys, unlockShare, type PublicShareInfo } from "./shareLinks";

// Public page for a shared file. Everything is decrypted here, in the visitor's browser,
// with the key after the # in the address (which is never sent to our servers).
const route = useRoute();
const token = String(route.params.token || "");

type Problem = { icon: unknown; title: string; text: string };
const PROBLEMS: Record<string, Problem> = {
  SHARE_NOT_FOUND: { icon: LinkIcon, title: "This link doesn't work", text: "It may have been mistyped or cut off. Ask the person who shared it to send it again." },
  SHARE_EXPIRED: { icon: Clock, title: "This link has expired", text: "Ask the person who shared it for a new link." },
  SHARE_REVOKED: { icon: Ban, title: "This link was turned off", text: "The owner stopped sharing this file." },
  SHARE_LIMIT_REACHED: { icon: TimerOff, title: "Download limit reached", text: "This link can't be opened any more times. Ask the owner for a new one." },
  SHARE_UNAVAILABLE: { icon: FileX2, title: "This file isn't available", text: "It was moved to the trash or replaced with a newer version." },
  MISSING_KEY: { icon: LinkIcon, title: "Part of the link is missing", text: "The link should end with # and a long code. Copy the whole link and try again." },
  WRONG_KEY: { icon: LinkIcon, title: "This link is damaged", text: "The file couldn't be decrypted with this link. Copy the whole link and try again." },
};

const state = ref<"loading" | "problem" | "password" | "ready">("loading");
const problem = ref<Problem | null>(null);
const info = ref<PublicShareInfo | null>(null);
const name = ref("");
const linkKey = decodeLinkKey((route.hash || window.location.hash).replace(/^#/, ""));

// Password links
const password = ref("");
const passwordError = ref("");
const unlocking = ref(false);
let wrapping: Uint8Array | null = linkKey;
let proof = "";

// Opening counts one download; the reader is reused for preview and download.
const file = shallowRef<EncryptedFile | null>(null);
const allowDownload = ref(true);
const opening = ref(false);
const actionError = ref("");
const showPreview = ref(false);
const viewProblem = ref<ViewProblem | null>(null);
const progress = ref<number | null>(null);
const downloadProgress = ref<number | null>(null);

const node = computed<FileNode>(() => ({
  id: `share-${token}`,
  parent: null,
  type: "file",
  encrypted_name: "",
  name_nonce: "",
  name: name.value || "Shared file",
  size_bytes: info.value?.size_bytes ?? 0,
  created_at: "",
  updated_at: "",
}));
const kind = computed(() => (name.value ? previewKindOf(node.value) : null));
const canPreview = computed(() => !!kind.value && !likelyUnsupported(kind.value, name.value));

function fail(err: unknown) {
  const n = normalizeApiError(err);
  if (err instanceof WrongShareKey || err instanceof DecryptError) problem.value = PROBLEMS.WRONG_KEY;
  else problem.value = (n.code && PROBLEMS[n.code]) || { icon: LinkIcon, title: "Couldn't open this link", text: n.message };
  state.value = "problem";
}

onMounted(async () => {
  if (!linkKey) {
    problem.value = PROBLEMS.MISSING_KEY;
    state.value = "problem";
    return;
  }
  try {
    info.value = await fetchShare(token);
    allowDownload.value = info.value.allow_download;
    if (info.value.password_protected) {
      state.value = "password";
      return;
    }
    name.value = (await unlockShare(info.value as Required<PublicShareInfo>, linkKey)).name;
    state.value = "ready";
  } catch (err) {
    fail(err);
  }
});

async function submitPassword() {
  if (!password.value || !info.value || !linkKey) {
    passwordError.value = "Enter the password.";
    return;
  }
  unlocking.value = true;
  passwordError.value = "";
  try {
    const keys = await passwordKeys(linkKey, info.value, password.value);
    wrapping = keys.wrapping;
    proof = keys.proof;
    await ensureOpen();
    state.value = "ready";
  } catch (err) {
    const n = normalizeApiError(err);
    if (n.code === "SHARE_WRONG_PASSWORD") passwordError.value = "That password isn't right.";
    else if (n.code === "SHARE_PASSWORD_LOCKED") passwordError.value = "Too many wrong passwords. Try again in 15 minutes.";
    else fail(err);
  } finally {
    unlocking.value = false;
  }
}

async function ensureOpen() {
  if (file.value) return file.value;
  opening.value = true;
  try {
    const opened = await openShare(token, wrapping!, proof);
    name.value = opened.name;
    allowDownload.value = opened.allowDownload;
    file.value = opened.file;
    if (info.value && info.value.downloads_left !== null) info.value = { ...info.value, downloads_left: Math.max(0, info.value.downloads_left - 1) };
    return opened.file;
  } finally {
    opening.value = false;
  }
}

async function preview() {
  actionError.value = "";
  try {
    await ensureOpen();
    viewProblem.value = null;
    showPreview.value = true;
  } catch (err) {
    fail(err);
  }
}

async function download() {
  actionError.value = "";
  try {
    const f = await ensureOpen();
    downloadProgress.value = 0;
    const blob = await f.readAll((p) => (downloadProgress.value = Math.round(p * 100)));
    const url = URL.createObjectURL(new Blob([blob], { type: mimeOf(name.value) || "application/octet-stream" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = name.value;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30_000);
  } catch (err) {
    const n = normalizeApiError(err);
    if (n.code && PROBLEMS[n.code]) fail(err);
    else actionError.value = err instanceof DecryptError ? "The file couldn't be decrypted. It may be damaged." : `Download failed. ${n.message}`;
  } finally {
    downloadProgress.value = null;
  }
}

function onViewProblem(p: ViewProblem) {
  viewProblem.value = p;
  progress.value = null;
}
</script>

<template>
  <div class="flex min-h-[100dvh] flex-col bg-canvas">
    <header class="border-b border-line bg-surface/80 backdrop-blur">
      <div class="mx-auto flex h-14 max-w-5xl items-center justify-between px-4 sm:px-6">
        <router-link to="/" aria-label="SmartSpace home"><AppLogo size="sm" /></router-link>
        <div class="flex items-center gap-1">
          <ThemeToggle />
          <UiButton variant="ghost" size="sm" to="/" :icon-right="ArrowRight" class="hidden sm:inline-flex">Get SmartSpace</UiButton>
        </div>
      </div>
    </header>

    <main class="mx-auto flex w-full max-w-5xl flex-1 flex-col items-center px-4 py-10 sm:px-6 sm:py-14">
      <section class="w-full max-w-md rounded-2xl border border-line bg-surface p-6 shadow-sm sm:p-8" aria-live="polite">
        <div v-if="state === 'loading'" class="flex justify-center py-8"><UiSpinner /></div>

        <div v-else-if="state === 'problem' && problem" class="text-center">
          <span class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-warning-soft text-warning">
            <component :is="problem.icon" :size="22" :stroke-width="1.75" aria-hidden="true" />
          </span>
          <h1 class="mt-4 text-xl font-semibold text-fg">{{ problem.title }}</h1>
          <p class="mt-2 text-base text-fg-muted">{{ problem.text }}</p>
        </div>

        <form v-else-if="state === 'password'" novalidate class="space-y-4" @submit.prevent="submitPassword">
          <div class="text-center">
            <span class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary-soft text-primary">
              <LockKeyhole :size="22" :stroke-width="1.75" aria-hidden="true" />
            </span>
            <h1 class="mt-4 text-xl font-semibold text-fg">This file is password protected</h1>
            <p class="mt-1 text-base text-fg-muted">{{ formatBytes(info?.size_bytes) }} · Enter the password the owner gave you.</p>
          </div>
          <UiFormField label="Password" :error="passwordError">
            <UiPasswordInput v-model="password" autocomplete="off" autofocus />
          </UiFormField>
          <UiButton type="submit" variant="primary" size="lg" block :loading="unlocking">Open file</UiButton>
        </form>

        <div v-else-if="state === 'ready'">
          <div class="flex items-center gap-3">
            <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl" :class="kindInfo(kindOf(node)).tint">
              <component :is="kindInfo(kindOf(node)).icon" :size="24" :stroke-width="1.75" aria-hidden="true" />
            </span>
            <div class="min-w-0">
              <h1 class="break-words text-lg font-semibold text-fg">{{ name }}</h1>
              <p class="text-sm text-fg-muted">{{ formatBytes(info?.size_bytes) }}</p>
            </div>
          </div>
          <div class="mt-6 grid gap-2" :class="allowDownload && canPreview ? 'sm:grid-cols-2' : ''">
            <UiButton v-if="canPreview" size="lg" :icon="Eye" :loading="opening && !downloadProgress" @click="preview">Preview</UiButton>
            <UiButton v-if="allowDownload" variant="primary" size="lg" :icon="Download" :loading="downloadProgress !== null" @click="download">
              {{ downloadProgress !== null ? `Downloading ${downloadProgress}%` : "Download" }}
            </UiButton>
          </div>
          <p v-if="!allowDownload && !canPreview" class="mt-4 text-base text-fg-muted">The owner shared this file as view-only, and it can't be previewed in the browser.</p>
          <UiProgress v-if="downloadProgress !== null" class="mt-3" :value="downloadProgress" label="Download progress" size="sm" />
          <p v-if="actionError" class="mt-3 text-sm text-danger" role="alert">{{ actionError }}</p>
          <ul class="mt-6 space-y-1.5 border-t border-line pt-4 text-sm text-fg-muted">
            <li class="flex items-center gap-2"><ShieldCheck :size="15" class="text-success" aria-hidden="true" />End-to-end encrypted. Decrypted in your browser.</li>
            <li v-if="info?.expires_at" class="flex items-center gap-2"><Clock :size="15" aria-hidden="true" />Link expires {{ formatDate(info.expires_at, { hour: "numeric", minute: "2-digit" }) }}</li>
            <li v-if="info && info.downloads_left !== null" class="flex items-center gap-2"><TimerOff :size="15" aria-hidden="true" />{{ info.downloads_left }} {{ info.downloads_left === 1 ? "open" : "opens" }} left</li>
          </ul>
        </div>
      </section>

      <!-- Inline preview -->
      <section v-if="showPreview && file && kind" data-theme="dark" class="relative mt-6 h-[70vh] w-full overflow-hidden rounded-2xl border border-line bg-[rgb(8_11_18)] text-fg" aria-label="Preview">
        <UiProgress v-if="progress !== null" :value="progress * 100" label="Opening file" class="absolute inset-x-0 top-0 z-10 [&_*]:rounded-none" size="sm" />
        <div v-if="viewProblem" class="flex h-full items-center justify-center p-6 text-center text-base text-fg-muted">
          {{ viewProblem.kind === "too-large" ? "This file is too large to preview." : viewProblem.kind === "damaged" ? "This file couldn't be decrypted." : "This file can't be previewed." }}
        </div>
        <template v-else>
          <ImageView v-if="kind === 'image'" :node="node" :file="file" @progress="progress = $event" @problem="onViewProblem" />
          <MediaView v-else-if="kind === 'video' || kind === 'audio'" :node="node" :file="file" :kind="kind" @progress="progress = $event" @problem="onViewProblem" />
          <PdfView v-else-if="kind === 'pdf'" :file="file" @progress="progress = $event" @problem="onViewProblem" />
          <DocxView v-else-if="kind === 'docx'" :file="file" @progress="progress = $event" @problem="onViewProblem" />
          <SheetView v-else-if="kind === 'sheet'" :node="node" :file="file" @progress="progress = $event" @problem="onViewProblem" />
          <TextView v-else-if="kind === 'text'" :node="node" :file="file" @progress="progress = $event" @problem="onViewProblem" />
        </template>
      </section>
    </main>

    <footer class="py-6 text-center text-sm text-fg-subtle">
      Shared with <router-link to="/" class="font-medium text-fg-muted hover:text-fg">SmartSpace</router-link>, private cloud storage encrypted on your device.
    </footer>
  </div>
</template>
