import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemeMode = "light" | "dark";
export type ReportLang = "zh" | "en";

interface UserState {
  username: string;
  theme: ThemeMode;
  reportLang: ReportLang;
  recentLimit: number;
  setUsername: (name: string) => void;
  setTheme: (t: ThemeMode) => void;
  setReportLang: (l: ReportLang) => void;
  setRecentLimit: (n: number) => void;
  resetPrefs: () => void;
}

const DEFAULTS = {
  username: "YC",
  theme: "light" as ThemeMode,
  reportLang: "zh" as ReportLang,
  recentLimit: 8,
};

/** 用户偏好：localStorage 持久化（用户名/主题/报告语言/历史条数） */
export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      ...DEFAULTS,
      setUsername: (username) => set({ username: username.trim() || DEFAULTS.username }),
      setTheme: (theme) => set({ theme }),
      setReportLang: (reportLang) => set({ reportLang }),
      setRecentLimit: (recentLimit) => set({ recentLimit }),
      resetPrefs: () => set({ ...DEFAULTS }),
    }),
    { name: "kra-user-prefs" },
  ),
);

/** 头像缩写：取名称前两位 */
export function userInitials(name: string): string {
  const trimmed = name.trim();
  return (trimmed.slice(0, 2) || "YC").toUpperCase();
}
