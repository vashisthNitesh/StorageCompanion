// Tiny typed event bus for app-wide UI requests (open the plan picker, refresh a list…).
type Events = {
  "plan-picker": { reason?: string; planCode?: string };
  "command-palette": undefined;
  "shortcuts-help": undefined;
};
type Handler<K extends keyof Events> = (payload: Events[K]) => void;
const handlers = new Map<keyof Events, Set<(payload: unknown) => void>>();

export function onAppEvent<K extends keyof Events>(name: K, handler: Handler<K>): () => void {
  if (!handlers.has(name)) handlers.set(name, new Set());
  const set = handlers.get(name)!;
  const fn = handler as (payload: unknown) => void;
  set.add(fn);
  return () => set.delete(fn);
}

export function emitAppEvent<K extends keyof Events>(name: K, ...payload: Events[K] extends undefined ? [] : [Events[K]]) {
  handlers.get(name)?.forEach((h) => h(payload[0]));
}
