import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useAuthStore } from "../stores/auth";

const routes: RouteRecordRaw[] = [
  { path: "/", name: "landing", component: () => import("../pages/Landing.vue") },
  { path: "/pricing", name: "pricing", component: () => import("../pages/Pricing.vue") },
  { path: "/security", name: "security", component: () => import("../pages/Security.vue") },
  { path: "/legal", name: "legal", component: () => import("../pages/Legal.vue") },
  { path: "/login", name: "login", component: () => import("../features/auth/LoginView.vue"), meta: { guestOnly: true } },
  { path: "/register", name: "register", component: () => import("../features/auth/RegisterView.vue"), meta: { guestOnly: true } },
  {
    path: "/app",
    component: () => import("../layouts/AppLayout.vue"),
    meta: { requiresAuth: true },
    children: [
      { path: "", redirect: "/app/files" },
      { path: "files", name: "files", component: () => import("../features/files/FileManager.vue"), meta: { customer: true } },
      { path: "trash", name: "trash", component: () => import("../features/files/TrashView.vue"), meta: { customer: true } },
      { path: "billing", name: "billing", component: () => import("../features/billing/BillingView.vue"), meta: { customer: true } },
      { path: "settings", name: "settings", component: () => import("../features/settings/SettingsView.vue") },
      {
        path: "admin",
        name: "admin-dashboard",
        component: () => import("../features/admin/AdminDashboard.vue"),
        meta: { requiresAdmin: true },
      },
    ],
  },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, _from, saved) {
    if (saved) return saved;
    if (to.hash) return { el: to.hash, behavior: "smooth" };
    return { top: 0 };
  },
});

export function homeFor(isAdmin: boolean) {
  return isAdmin ? "/app/admin" : "/app/files";
}

router.beforeEach(async (to) => {
  const authStore = useAuthStore();
  if (!authStore.isInitialized) await authStore.initAuth();

  if (to.matched.some((r) => r.meta.requiresAuth)) {
    if (!authStore.isAuthenticated) return { name: "login", query: { redirect: to.fullPath } };
    if (to.meta.requiresAdmin && !authStore.isMasterAdmin) return "/app/files";
    // Administrators have no storage vault; send them to the console.
    if (to.meta.customer && authStore.isMasterAdmin) return "/app/admin";
    return true;
  }

  if (to.meta.guestOnly && authStore.isAuthenticated) return homeFor(authStore.isMasterAdmin);
  return true;
});
