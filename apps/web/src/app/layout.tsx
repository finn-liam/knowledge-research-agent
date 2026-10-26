import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

/** Inter 仅覆盖拉丁字母与数字（variable 子集，display=swap），中文继续走系统栈 */
const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Knowledge Research Agent",
  description: "Your AI-powered assistant for enterprise knowledge research and analysis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={inter.variable}>
      <body>{children}</body>
    </html>
  );
}
