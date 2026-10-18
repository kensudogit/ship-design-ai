import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "船舶基本設計AI（教育用）",
  description: "船級承認用途ではない幾何評価のデモ",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
