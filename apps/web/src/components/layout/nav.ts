import {
  BarChart3,
  BookOpen,
  Database,
  Home,
  Layers,
  Settings,
  type LucideIcon,
} from "lucide-react";

/** 主导航项（侧边栏与移动端抽屉共用） */
export const NAV_ITEMS: { to: string; label: string; icon: LucideIcon }[] = [
  { to: "/", label: "Home", icon: Home },
  { to: "/library", label: "Library", icon: BookOpen },
  { to: "/knowledge-base", label: "Knowledge Base", icon: Database },
  { to: "/datasources", label: "Datasources", icon: Layers },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/settings", label: "Settings", icon: Settings },
];
