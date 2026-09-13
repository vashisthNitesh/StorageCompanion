import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useAuthStore } from "../stores/auth";

const routes: RouteRecordRaw[] = [
  // Public Marketing Site
  {
    path: "/",
    name: "landing",
    component: () => import("../pages/Landing.vue"),
  },
  {
    path: "/pricing",
    name: "pricing",
    component: () => import("../pages/Pricing.vue"),
  },
  {
    path: "/security",
    name: "security",
    component: () => import("../pages/Security.vue"),
  },
  {
    path: "/legal",
    name: "legal",
    component: () => import("../pages/Legal.vue"),
  },
  // Auth
  {
    path: "/login",
    name: "login",
    component: () => import("../features/auth/LoginView.vue"),
  },
  {
    path: "/register",
    name: "register",
    component: () => import("../features/auth/RegisterView.vue"),
  },
  // Public Link Decrypt View (Zero-knowledge fragment key)
  {
    path: "/s/:token",
    name: "public-share",
    component: () => import("../features/sharing/PublicShareView.vue"),
  },
  // Authenticated Application
  {
    path: "/app",
    component: () => import("../layouts/AppLayout.vue"),
    meta: { requiresAuth: true },
    children: [
      {
        path: "",
        redirect: "/app/files",
      },
      {
        path: "files",
        name: "files",
        component: () => import("../features/files/FileManager.vue"),
      },
      {
        path: "shared",
        name: "shared",
        component: () => import("../features/sharing/SharedFilesView.vue"),
      },
      {
        path: "billing",
        name: "billing",
        component: () => import("../features/billing/BillingView.vue"),
      },
      {
        path: "settings",
        name: "settings",
        component: () => import("../features/settings/SettingsView.vue"),
      },
      {
        path: "admin",
        name: "admin-dashboard",
        component: () => import("../features/admin/AdminDashboard.vue"),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
    ],
  },
  {
    path: "/:pathMatch(.*)*",
    redirect: "/",
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();

  // Initialize auth session before making route decisions
  if (!authStore.isInitialized) {
    await authStore.initAuth();
  }

  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      next({ name: "login", query: { redirect: to.fullPath } });
      return;
    }

    // Admin Route Protection: only master admin can access /app/admin
    if (to.meta.requiresAdmin && !authStore.isMasterAdmin) {
      next({ path: "/app/files" });
      return;
    }

    // Superadmin restriction: redirect away from customer vault/billing pages to admin dashboard
    if (authStore.isMasterAdmin && (to.path === "/app" || to.path === "/app/files" || to.path === "/app/shared" || to.path === "/app/billing")) {
      next({ path: "/app/admin" });
      return;
    }

    // Strict Subscription Gating (NO FREE TIER)
    // If authenticated but unpaid (and not an admin), only allow billing and settings pages
    if (!authStore.hasActiveSubscription && !authStore.isMasterAdmin) {
      if (to.path === "/app/billing" || to.path === "/app/settings") {
        next();
      } else {
        next({ path: "/app/billing", query: { gate: "required" } });
      }
      return;
    }

    next();
  } else {
    // If already logged in, redirect away from auth pages
    if (authStore.isAuthenticated && (to.name === "login" || to.name === "register")) {
      if (authStore.hasActiveSubscription || authStore.isMasterAdmin) {
        next({ path: authStore.isMasterAdmin ? "/app/admin" : "/app/files" });
      } else {
        next({ path: "/app/billing" });
      }
      return;
    }

    next();
  }
});
