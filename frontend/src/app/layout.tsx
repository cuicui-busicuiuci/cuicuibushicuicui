import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "A股量化投研系统",
  description: "A股选股软件 - 行情/新闻/因子/策略/回测/模拟交易",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className="dark">
      <body className="min-h-screen bg-[#020617] text-[#F8FAFC] antialiased">{children}</body>
    </html>
  );
}
