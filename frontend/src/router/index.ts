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

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore();
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: "login", query: { redirect: to.fullPath } });
  } else {
    next();
  }
});
