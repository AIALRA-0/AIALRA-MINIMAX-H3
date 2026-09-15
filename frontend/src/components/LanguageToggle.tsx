"use client";

import { Languages } from "lucide-react";
import { useLocale } from "@/lib/i18n";

export function LanguageToggle({ compact = false }: { compact?: boolean }) {
  const { locale, setLocale, t } = useLocale();
  const next = locale === "zh-CN" ? "en" : "zh-CN";
  const title = locale === "zh-CN" ? t("language.switchToEnglish") : t("language.switchToChinese");

  return (
    <button
      type="button"
      onClick={() => setLocale(next)}
      title={title}
      aria-label={title}
      className="inline-flex items-center gap-1.5 rounded-lg border border-studio-border px-2.5 py-1.5 text-xs font-medium text-studio-muted transition-colors hover:border-studio-accent/40 hover:bg-studio-panelHover hover:text-studio-text"
    >
      <Languages className="h-3.5 w-3.5" />
      {!compact && <span>{locale === "zh-CN" ? "中 / EN" : "EN / 中"}</span>}
    </button>
  );
}
