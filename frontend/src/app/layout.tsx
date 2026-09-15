import type { Metadata } from "next";
import "./globals.css";
import { LocaleProvider } from "@/lib/i18n";

export const metadata: Metadata = {
  title: "AI Movie Studio 2",
  description: "Professional AI Filmmaking Workstation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="bg-studio-bg text-studio-text antialiased">
        <LocaleProvider>{children}</LocaleProvider>
      </body>
    </html>
  );
}
