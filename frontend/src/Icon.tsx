import type { ReactNode, SVGProps } from "react";

export type IconName =
  | "dashboard"
  | "work"
  | "briefcase"
  | "engineering"
  | "construction"
  | "completion"
  | "permit"
  | "authority"
  | "issues"
  | "notifications"
  | "settings"
  | "guide"
  | "shield"
  | "refresh"
  | "arrow-up-right"
  | "plus"
  | "close"
  | "empty";

const paths: Record<IconName, ReactNode> = {
  dashboard: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
  work: <><path d="M4 5.5h16M4 12h16M4 18.5h10" /><path d="m17 17 2 2 3-4" /></>,
  briefcase: <><rect x="3" y="6" width="18" height="13" rx="2" /><path d="M8 6V4.5A1.5 1.5 0 0 1 9.5 3h5A1.5 1.5 0 0 1 16 4.5V6M3 11h18M10 11v2h4v-2" /></>,
  engineering: <><path d="m14.5 4.5 5 5M12 7l5 5M4 20l5.5-1.5L19 9a2.1 2.1 0 0 0-3-3l-9.5 9.5L5 20Z" /><path d="M4 4v4M2 6h4" /></>,
  construction: <><path d="M4 10h16M5 10v9M19 10v9M3 19h18" /><path d="M7 10V7h10v3M9 7V4h6v3" /></>,
  completion: <><circle cx="12" cy="12" r="9" /><path d="m8 12 2.5 2.5L16 9" /></>,
  permit: <><path d="M6 3h9l4 4v14H6z" /><path d="M15 3v5h4M9 12h6M9 16h6" /></>,
  authority: <><path d="M3 9h18L12 4 3 9Z" /><path d="M5 10v7M9 10v7M15 10v7M19 10v7M3 20h18" /></>,
  issues: <><path d="m12 3 9 17H3L12 3Z" /><path d="M12 9v5M12 17h.01" /></>,
  notifications: <><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></>,
  settings: <><path d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z" /><path d="m19.4 15 .1.1a2 2 0 1 1-2.8 2.8l-.1-.1a2 2 0 0 0-3.4 1.4v.2a2 2 0 1 1-4 0v-.2a2 2 0 0 0-3.4-1.4l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A2 2 0 0 0 1.7 12a2 2 0 0 1 0-4h.2a2 2 0 0 0 1.4-3.4l-.1-.1A2 2 0 1 1 6 1.7l.1.1A2 2 0 0 0 9.5.4V.2a2 2 0 1 1 4 0v.2a2 2 0 0 0 3.4 1.4l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1A2 2 0 0 0 21.1 8h.2a2 2 0 1 1 0 4h-.2a2 2 0 0 0-1.7 3Z" transform="translate(0 2) scale(.8)" /></>,
  guide: <><circle cx="12" cy="12" r="9" /><path d="M9.7 9a2.4 2.4 0 1 1 4.4 1.3c-.8 1-2.1 1.2-2.1 2.7M12 16h.01" /></>,
  shield: <><path d="M12 3 19 6v5c0 4.4-2.8 8-7 10-4.2-2-7-5.6-7-10V6l7-3Z" /><path d="m8.5 12 2.3 2.3 4.7-5" /></>,
  refresh: <><path d="M20 11a8 8 0 0 0-14.6-4L3 10" /><path d="M3 5v5h5M4 13a8 8 0 0 0 14.6 4L21 14" /><path d="M21 19v-5h-5" /></>,
  "arrow-up-right": <><path d="M7 17 17 7M8 7h9v9" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  close: <><path d="m6 6 12 12M18 6 6 18" /></>,
  empty: <><rect x="4" y="5" width="16" height="14" rx="2" /><path d="M8 9h8M8 13h5M8 16h3" /></>,
};

export function Icon({ name, size = 16, label, className, ...props }: { name: IconName; size?: number; label?: string; className?: string } & Omit<SVGProps<SVGSVGElement>, "name">) {
  if (name === "arrow-up-right") return "→";
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" focusable="false" className={className} aria-hidden={label ? undefined : true} aria-label={label} role={label ? "img" : undefined} {...props}>{paths[name]}</svg>;
}
