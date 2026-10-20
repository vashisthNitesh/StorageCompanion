// Loads Google Identity Services on demand and renders Google's own sign-in button,
// which opens the Google account chooser.

const GIS_SRC = "https://accounts.google.com/gsi/client";
let loader: Promise<any> | null = null;

export function loadGoogleIdentity(): Promise<any> {
  const w = window as any;
  if (w.google?.accounts?.id) return Promise.resolve(w.google);
  if (loader) return loader;

  loader = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = GIS_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => (w.google?.accounts?.id ? resolve(w.google) : reject(new Error("Google sign-in failed to load.")));
    script.onerror = () => {
      loader = null;
      reject(new Error("Google sign-in could not be loaded. Check your connection or disable blockers for this site."));
    };
    document.head.appendChild(script);
  });
  return loader;
}

export interface GoogleButtonOptions {
  clientId: string;
  container: HTMLElement;
  text?: "signin_with" | "signup_with" | "continue_with";
  onCredential: (credential: string) => void;
}

export async function renderGoogleButton(opts: GoogleButtonOptions): Promise<void> {
  const google = await loadGoogleIdentity();
  google.accounts.id.initialize({
    client_id: opts.clientId,
    callback: (response: { credential?: string }) => {
      if (response?.credential) opts.onCredential(response.credential);
    },
    ux_mode: "popup",
    auto_select: false,
    cancel_on_tap_outside: true,
    itp_support: true,
  });
  const width = Math.min(400, Math.max(200, Math.floor(opts.container.clientWidth || 320)));
  opts.container.innerHTML = "";
  google.accounts.id.renderButton(opts.container, {
    type: "standard",
    theme: "outline",
    size: "large",
    shape: "rectangular",
    text: opts.text || "continue_with",
    logo_alignment: "left",
    width,
  });
}
