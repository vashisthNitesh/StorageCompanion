/* Logging that is silent in production builds (the build also strips console calls). */
const enabled = import.meta.env.DEV;

export const logger = {
  debug: (...args: unknown[]) => enabled && console.debug(...args),
  warn: (...args: unknown[]) => enabled && console.warn(...args),
  error: (...args: unknown[]) => enabled && console.error(...args),
};
