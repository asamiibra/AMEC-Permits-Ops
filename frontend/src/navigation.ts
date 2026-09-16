import { useSyncExternalStore } from "react";

const subscribe = (listener: () => void) => {
  window.addEventListener("popstate", listener);
  window.addEventListener("hashchange", listener);
  return () => {
    window.removeEventListener("popstate", listener);
    window.removeEventListener("hashchange", listener);
  };
};
const snapshot = () => window.location.pathname + window.location.search + window.location.hash;

/** One subscription contract for page, record and section navigation. */
export function useLocationPath() {
  return useSyncExternalStore(subscribe, snapshot);
}

export function navigateTo(route: string, replace = false) {
  const url = new URL(route, window.location.origin);
  if (url.origin !== window.location.origin) throw new Error("Application navigation must stay on the current origin.");
  window.history[replace ? "replaceState" : "pushState"]({}, "", url.pathname + url.search + url.hash);
  window.dispatchEvent(new PopStateEvent("popstate"));
}
