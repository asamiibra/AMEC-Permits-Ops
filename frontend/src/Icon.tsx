import {
  ArrowRight,
  ArrowLeft,
  ArrowUpRight,
  BadgeCheck,
  Bell,
  BookOpen,
  CircleAlert,
  CircleCheck,
  Circle,
  CircleDollarSign,
  CircleHelp,
  ClipboardList,
  DraftingCompass,
  FileSignature,
  FileCheck2,
  HardHat,
  House,
  Landmark,
  Library,
  ListTodo,
  Minus,
  Plus,
  PackageCheck,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Target,
  TriangleAlert,
  UserRound,
  UsersRound,
  X,
  type LucideIcon,
  type LucideProps,
} from "lucide-react";

export type IconName =
  | "dashboard"
  | "work"
  | "briefcase"
  | "engineering"
  | "construction"
  | "completion"
  | "permit"
  | "contract"
  | "handover"
  | "authority"
  | "issues"
  | "notifications"
  | "settings"
  | "guide"
  | "shield"
  | "refresh"
  | "arrow-up-right"
  | "arrow-right"
  | "arrow-left"
  | "plus"
  | "close"
  | "empty"
  | "search"
  | "help"
  | "user"
  | "check"
  | "alert"
  | "minus"
  | "finance"
  | "library"
  | "sparkles"
  | "users"
  | "current";

const iconComponents: Record<IconName, LucideIcon> = {
  dashboard: House,
  work: ListTodo,
  briefcase: Target,
  engineering: DraftingCompass,
  construction: HardHat,
  completion: BadgeCheck,
  permit: FileCheck2,
  contract: FileSignature,
  handover: PackageCheck,
  authority: Landmark,
  issues: TriangleAlert,
  notifications: Bell,
  settings: Settings,
  guide: BookOpen,
  shield: ShieldCheck,
  refresh: RefreshCw,
  "arrow-up-right": ArrowUpRight,
  "arrow-right": ArrowRight,
  "arrow-left": ArrowLeft,
  plus: Plus,
  close: X,
  empty: ClipboardList,
  search: Search,
  help: CircleHelp,
  user: UserRound,
  check: CircleCheck,
  alert: CircleAlert,
  minus: Minus,
  finance: CircleDollarSign,
  library: Library,
  sparkles: Sparkles,
  users: UsersRound,
  current: Circle,
};

export function Icon({
  name,
  size = 16,
  label,
  className,
  ...props
}: { name: IconName; size?: number; label?: string; className?: string } & Omit<LucideProps, "name" | "size">) {
  const Component = iconComponents[name];
  return (
    <Component
      size={size}
      strokeWidth={1.8}
      focusable="false"
      aria-hidden={label ? undefined : true}
      aria-label={label}
      className={className}
      {...props}
    />
  );
}
