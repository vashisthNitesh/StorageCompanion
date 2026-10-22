import { createApp } from "vue";
import { createPinia } from "pinia";
import "./stores/theme";
import App from "./App.vue";
import { router } from "./router";
import "./style.css";

// Older versions cached upload state (including unencrypted file keys) and file names in
// IndexedDB. Nothing reads it any more, so remove it from the browser.
try {
  indexedDB?.deleteDatabase("SpeedCloudDB");
} catch {
  // IndexedDB unavailable (private mode); nothing to clean up.
}

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount("#app");
