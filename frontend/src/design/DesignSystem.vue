<script setup lang="ts">
// Dev-only catalogue of every UI primitive in every state (route: /_design).
import { ref } from "vue";
import {
  Upload,
  FolderPlus,
  FolderUp,
  Download,
  Pencil,
  Trash2,
  Settings,
  Plus,
  Inbox,
  Mail,
  Moon,
  Sun,
  Monitor,
  List,
  LayoutGrid,
} from "lucide-vue-next";
import UiButton from "../components/ui/UiButton.vue";
import UiSplitButton from "../components/ui/UiSplitButton.vue";
import UiInput from "../components/ui/UiInput.vue";
import UiPasswordInput from "../components/ui/UiPasswordInput.vue";
import UiTextarea from "../components/ui/UiTextarea.vue";
import UiSearchInput from "../components/ui/UiSearchInput.vue";
import UiFormField from "../components/ui/UiFormField.vue";
import UiSelect from "../components/ui/UiSelect.vue";
import UiDropdownMenu from "../components/ui/UiDropdownMenu.vue";
import UiContextMenu from "../components/ui/UiContextMenu.vue";
import UiCheckbox from "../components/ui/UiCheckbox.vue";
import UiRadioGroup from "../components/ui/UiRadioGroup.vue";
import UiSwitch from "../components/ui/UiSwitch.vue";
import UiSegmented from "../components/ui/UiSegmented.vue";
import UiModal from "../components/ui/UiModal.vue";
import UiDrawer from "../components/ui/UiDrawer.vue";
import UiTooltip from "../components/ui/UiTooltip.vue";
import UiBadge from "../components/ui/UiBadge.vue";
import UiAvatar from "../components/ui/UiAvatar.vue";
import UiProgress from "../components/ui/UiProgress.vue";
import UiProgressCircle from "../components/ui/UiProgressCircle.vue";
import UiSkeleton from "../components/ui/UiSkeleton.vue";
import UiEmptyState from "../components/ui/UiEmptyState.vue";
import UiBanner from "../components/ui/UiBanner.vue";
import UiTabs from "../components/ui/UiTabs.vue";
import UiBreadcrumbs from "../components/ui/UiBreadcrumbs.vue";
import UiPagination from "../components/ui/UiPagination.vue";
import UiKbd from "../components/ui/UiKbd.vue";
import UiCard from "../components/ui/UiCard.vue";
import UiAlert from "../components/ui/UiAlert.vue";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import type { MenuEntry } from "../components/ui/menuTypes";
import { toast } from "../lib/toast";
import { confirmDialog } from "../lib/confirm";
import { useThemeStore, type ThemePreference } from "../stores/theme";
import { GST_STATES } from "../lib/gstStates";

const theme = useThemeStore();
const text = ref("Quarterly report");
const pw = ref("hunter2-correct-horse");
const area = ref("");
const search = ref("");
const select = ref("name");
const state = ref("");
const checked = ref(true);
const indeterminate = ref<boolean | "indeterminate">("indeterminate");
const radio = ref("monthly");
const sw = ref(true);
const seg = ref<"list" | "grid">("list");
const interval = ref<"monthly" | "yearly">("yearly");
const modal = ref(false);
const drawer = ref(false);
const tab = ref("one");
const page = ref(2);

const menu: MenuEntry[] = [
  { label: "Download", icon: Download, shortcut: "D", onSelect: () => toast.info("Download") },
  { label: "Rename", icon: Pencil, shortcut: "F2", onSelect: () => toast.info("Rename") },
  { label: "Disabled item", icon: Settings, disabled: true, onSelect: () => {} },
  { separator: true },
  { label: "Move to trash", icon: Trash2, danger: true, shortcut: "Del", onSelect: () => toast.undoable("Moved to trash", () => toast.info("Restored")) },
];
const uploadMenu: MenuEntry[] = [
  { label: "Upload files", icon: Upload, onSelect: () => {} },
  { label: "Upload folder", icon: FolderUp, onSelect: () => {} },
  { separator: true },
  { label: "New folder", icon: FolderPlus, shortcut: "N", onSelect: () => {} },
];
const themes: { value: ThemePreference; label: string; icon: any }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

async function askConfirm(type = false) {
  const ok = await confirmDialog({
    title: type ? "Delete 3 files forever?" : "Move 3 files to trash?",
    body: type ? "These files will be permanently deleted. This can't be undone." : "You can restore them from Trash.",
    confirmLabel: type ? "Delete 3 files" : "Move to trash",
    danger: true,
    typeToConfirm: type ? "delete" : undefined,
    action: () => new Promise((r) => setTimeout(r, 900)),
  });
  toast.info(ok ? "Confirmed" : "Cancelled");
}

function loadingToast() {
  const id = toast.loading("Uploading 3 files…");
  setTimeout(() => toast.success("3 files uploaded to Projects", { id, action: { label: "View", onClick: () => {} } }), 1500);
}
</script>

<template>
  <div class="min-h-screen bg-canvas">
    <div class="mx-auto max-w-5xl space-y-10 px-4 py-10 sm:px-8">
      <UiPageHeader title="Design system" description="Every component in every state. Dev only.">
        <template #actions>
          <UiSegmented v-model="theme.preference" :options="themes" label="Theme" />
        </template>
      </UiPageHeader>

      <UiCard title="Buttons">
        <div class="space-y-4">
          <div v-for="v in (['primary', 'secondary', 'ghost', 'danger', 'danger-ghost', 'link'] as const)" :key="v" class="flex flex-wrap items-center gap-3">
            <span class="w-24 text-sm text-fg-subtle">{{ v }}</span>
            <UiButton :variant="v" size="sm" :icon="Plus">Small</UiButton>
            <UiButton :variant="v">Default</UiButton>
            <UiButton :variant="v" size="lg">Large</UiButton>
            <UiButton :variant="v" loading>Loading</UiButton>
            <UiButton :variant="v" disabled tooltip="Choose a plan to upload">Disabled</UiButton>
            <UiButton :variant="v" icon-only :icon="Settings" aria-label="Settings" />
          </div>
          <div class="flex flex-wrap items-center gap-3">
            <UiSplitButton label="Upload" :icon="Upload" :items="uploadMenu" />
            <UiButton variant="secondary" :icon="FolderPlus" tooltip="New folder" shortcut="N">New folder</UiButton>
            <UiKbd>⌘K</UiKbd>
          </div>
        </div>
      </UiCard>

      <UiCard title="Form controls">
        <div class="grid gap-5 sm:grid-cols-2">
          <UiFormField label="Name" hint="Shown on invoices." required>
            <UiInput v-model="text" />
          </UiFormField>
          <UiFormField label="Email" error="Enter a valid email address, like name@example.com.">
            <UiInput model-value="nitesh@" :icon="Mail" />
          </UiFormField>
          <UiFormField label="Password">
            <UiPasswordInput v-model="pw" />
          </UiFormField>
          <UiFormField label="Disabled">
            <UiInput model-value="Can't edit" disabled />
          </UiFormField>
          <UiFormField label="Notes" optional :counter="{ value: area.length, max: 140 }">
            <UiTextarea v-model="area" :rows="3" />
          </UiFormField>
          <UiFormField label="Search">
            <UiSearchInput v-model="search" placeholder="Search files" shortcut />
          </UiFormField>
          <UiFormField label="Sort by">
            <UiSelect
              v-model="select"
              :options="[
                { value: 'name', label: 'Name' },
                { value: 'modified', label: 'Last modified' },
                { value: 'size', label: 'Size' },
              ]"
            />
          </UiFormField>
          <UiFormField label="State (searchable)" hint="Used to calculate CGST/SGST or IGST on your invoice.">
            <UiSelect v-model="state" :options="GST_STATES.map((s) => ({ value: s.code, label: s.name }))" placeholder="Search for your state" />
          </UiFormField>
        </div>
        <div class="mt-6 grid gap-5 sm:grid-cols-3">
          <div class="space-y-3">
            <UiCheckbox v-model="checked" label="Checked" />
            <UiCheckbox v-model="indeterminate" label="Indeterminate" />
            <UiCheckbox :model-value="false" label="Disabled" disabled />
            <UiCheckbox :model-value="false" label="Invalid" invalid description="Required to continue." />
          </div>
          <UiRadioGroup
            v-model="radio"
            aria-label="Billing"
            :options="[
              { value: 'monthly', label: 'Monthly' },
              { value: 'yearly', label: 'Yearly', description: 'Two months free' },
              { value: 'x', label: 'Disabled', disabled: true },
            ]"
          />
          <div class="space-y-3">
            <UiSwitch v-model="sw" label="Switch" description="With a description" />
            <UiSegmented
              v-model="seg"
              label="View"
              :options="[
                { value: 'list', label: 'List', icon: List },
                { value: 'grid', label: 'Grid', icon: LayoutGrid },
              ]"
            />
            <UiSegmented
              v-model="interval"
              label="Billing period"
              :options="[
                { value: 'monthly', label: 'Monthly' },
                { value: 'yearly', label: 'Yearly', badge: 'Save 17%' },
              ]"
            />
          </div>
        </div>
      </UiCard>

      <UiCard title="Menus, overlays and feedback">
        <div class="flex flex-wrap items-center gap-3">
          <UiDropdownMenu :items="menu"><UiButton>Dropdown menu</UiButton></UiDropdownMenu>
          <UiContextMenu :items="menu">
            <div class="rounded border border-dashed border-line-strong px-4 py-2 text-sm text-fg-muted">Right-click me</div>
          </UiContextMenu>
          <UiTooltip content="Tooltip with shortcut" shortcut="U"><UiButton>Hover me</UiButton></UiTooltip>
          <UiButton @click="modal = true">Modal</UiButton>
          <UiButton @click="drawer = true">Drawer</UiButton>
          <UiButton @click="askConfirm()">Confirm</UiButton>
          <UiButton variant="danger" @click="askConfirm(true)">Type-to-confirm</UiButton>
        </div>
        <div class="mt-4 flex flex-wrap items-center gap-3">
          <UiButton @click="toast.success('Folder created')">Success toast</UiButton>
          <UiButton @click="toast.error('Something went wrong on our side. Please try again.', { retry: () => {} })">Error toast</UiButton>
          <UiButton @click="toast.info('You\'re offline')">Info toast</UiButton>
          <UiButton @click="toast.undoable('“Notes.txt” moved to trash', () => {})">Undo toast</UiButton>
          <UiButton @click="loadingToast">Loading → success</UiButton>
        </div>
      </UiCard>

      <UiCard title="Display">
        <div class="space-y-6">
          <div class="flex flex-wrap items-center gap-2">
            <UiBadge>Neutral</UiBadge>
            <UiBadge tone="primary">Primary</UiBadge>
            <UiBadge tone="success" dot>Paid</UiBadge>
            <UiBadge tone="warning">Expiring</UiBadge>
            <UiBadge tone="danger">Failed</UiBadge>
            <UiBadge tone="info">Info</UiBadge>
            <UiAvatar name="Nitesh Vashisth" email="nitesh@example.com" />
            <UiAvatar email="asha@example.com" size="lg" />
          </div>
          <div class="grid gap-3 sm:grid-cols-2">
            <UiProgress :value="32" label="Storage" />
            <UiProgress :value="84" tone="warning" label="Storage" />
            <UiProgress :value="97" tone="danger" label="Storage" />
            <UiProgress :value="null" label="Indeterminate" />
          </div>
          <div class="flex items-center gap-3 text-primary"><UiProgressCircle :value="66" label="Upload progress" /> <span class="text-sm text-fg-muted">66%</span></div>
          <div class="space-y-2">
            <UiSkeleton class="h-4 w-1/3" />
            <UiSkeleton class="h-4 w-2/3" />
            <UiSkeleton class="h-10 w-full" />
          </div>
          <UiBreadcrumbs
            :items="[
              { key: 'root', label: 'My files' },
              { key: 'a', label: 'Clients' },
              { key: 'b', label: 'Mehta wedding' },
              { key: 'c', label: 'Ceremony' },
              { key: 'd', label: 'Edited' },
            ]"
          />
          <UiTabs
            v-model="tab"
            label="Example"
            :tabs="[
              { value: 'one', label: 'Overview' },
              { value: 'two', label: 'Customers' },
              { value: 'three', label: 'Files' },
            ]"
          />
          <UiPagination v-model="page" :total="132" :page-size="20" />
          <UiBanner tone="info" dismissible>You don't have a plan yet. <a class="font-medium underline" href="#">Choose a plan</a></UiBanner>
          <UiBanner tone="warning">Your plan ends on 12 Mar. Extend now to keep uploading.</UiBanner>
          <UiAlert>Email or password is incorrect.</UiAlert>
          <UiAlert tone="success">Password updated.</UiAlert>
          <div class="rounded-lg border border-line">
            <UiEmptyState :icon="Inbox" title="Trash is empty" description="Items you delete appear here.">
              <UiButton variant="primary" :icon="Upload">Upload files</UiButton>
            </UiEmptyState>
          </div>
        </div>
      </UiCard>
    </div>

    <UiModal v-model:open="modal" title="New folder" description="Folders help you organise your files.">
      <UiFormField label="Folder name"><UiInput model-value="Untitled folder" autofocus /></UiFormField>
      <template #footer>
        <UiButton @click="modal = false">Cancel</UiButton>
        <UiButton variant="primary" @click="modal = false">Create folder</UiButton>
      </template>
    </UiModal>
    <UiDrawer v-model:open="drawer" title="Quarterly report.pdf" description="PDF · 2.4 MB">
      <p class="text-base text-fg-muted">Drawer content.</p>
    </UiDrawer>
  </div>
</template>
