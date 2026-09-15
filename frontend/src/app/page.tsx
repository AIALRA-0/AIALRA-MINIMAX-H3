"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Film, ArrowRight, Image as ImageIcon, Camera, Video, Music, Clapperboard, Sparkles } from "lucide-react";
import { useAuth } from "@/lib/useAuth";
import { AuthModal } from "@/components/AuthModal";
import { UserMenu } from "@/components/UserMenu";
import { LanguageToggle } from "@/components/LanguageToggle";
import { useLocale } from "@/lib/i18n";

export default function HomePage() {
  const { locale, t } = useLocale();
  const { user, loading } = useAuth();
  const router = useRouter();
  const [authMode, setAuthMode] = useState<"signin" | "signup" | null>(null);

  useEffect(() => {
    if (!loading && user) {
      router.replace("/projects");
    }
  }, [user, loading, router]);

  const handleAuthSuccess = () => {
    setAuthMode(null);
    router.push("/projects");
  };

  const features = locale === "zh-CN" ? [
    { icon: ImageIcon, title: "素材生成", desc: "使用本地 FLUX.2 Klein 生成角色、场景、道具与车辆" },
    { icon: Clapperboard, title: "分镜搭建", desc: "组织镜头、绑定素材，并用可复现参数生成分镜画面" },
    { icon: Camera, title: "3D 镜头导演", desc: "通过三维预演、镜头路径与运动提示设计画面" },
    { icon: Video, title: "H3 视频生成", desc: "本地 MiniMax H3 文生视频、图生视频、首尾帧与参考生成" },
    { icon: Music, title: "原生音频", desc: "保留 MiniMax H3 视频原生音频并支持多轨时间线" },
    { icon: Sparkles, title: "抽帧、超分与导出", desc: "智能筛选关键帧，使用 SeedVR2 生成 2× 母版并完成剪辑导出" },
  ] : [
    { icon: ImageIcon, title: "Asset Generation", desc: "Create characters, locations, props, and vehicles with local FLUX.2 Klein" },
    { icon: Clapperboard, title: "Storyboard Builder", desc: "Compose shots, bind assets, and generate frames with reproducible settings" },
    { icon: Camera, title: "3D Camera Director", desc: "Design shots with previs, camera paths, and motion prompts" },
    { icon: Video, title: "H3 Video Generation", desc: "Local MiniMax H3 text, image, first-last-frame, and reference generation" },
    { icon: Music, title: "Native Audio", desc: "Keep MiniMax H3 native video audio and arrange it on multiple tracks" },
    { icon: Sparkles, title: "Frames, Upscale & Export", desc: "Rank keyframes, make a SeedVR2 2× master, edit, and export" },
  ];

  return (
    <div className="min-h-screen flex flex-col items-center px-8 py-16 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-studio-bg pointer-events-none" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-studio-accent/10 rounded-full blur-[120px] pointer-events-none" />

      {/* Top-right auth area */}
      <div className="absolute top-6 right-8 z-20 flex items-center gap-2">
        <LanguageToggle />
        {loading ? (
          <div className="w-8 h-8 rounded-full bg-studio-border animate-pulse" />
        ) : user ? (
          <UserMenu />
        ) : (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setAuthMode("signin")}
              className="px-4 py-1.5 rounded-lg text-sm text-studio-text hover:text-white border border-studio-border hover:border-studio-accent/30 transition-colors"
            >
              {t("home.signIn")}
            </button>
            <button
              onClick={() => setAuthMode("signup")}
              className="px-4 py-1.5 rounded-lg text-sm bg-studio-accent hover:bg-studio-accentHover text-white font-medium transition-colors"
            >
              {t("home.signUp")}
            </button>
          </div>
        )}
      </div>

      <div className="max-w-5xl w-full relative z-10">
        <div className="text-center mb-12 animate-fade-in">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-studio-accent/10 border border-studio-accent/20 mb-6">
            <Film className="w-8 h-8 text-studio-accent" />
          </div>
          <h1 className="text-5xl font-bold mb-4">
            <span className="gradient-text">AI Movie Studio 2</span>
          </h1>
          <p className="text-studio-muted text-lg max-w-2xl mx-auto leading-relaxed">
            {t("home.tagline")}
          </p>
        </div>

        <div className="flex justify-center gap-4 mb-12 animate-fade-in" style={{ animationDelay: "0.05s" }}>
          {user ? (
            <>
              <Link
                href="/projects"
                className="inline-flex items-center gap-2 px-8 py-3.5 bg-studio-accent hover:bg-studio-accentHover text-white rounded-xl font-medium transition-all hover:scale-[1.02] shadow-lg shadow-studio-accent/20"
              >
                {t("home.openProjects")}
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/project/default"
                className="inline-flex items-center gap-2 px-8 py-3.5 bg-studio-panel hover:bg-studio-border border border-studio-border text-studio-text rounded-xl font-medium transition-all hover:scale-[1.02]"
              >
                {t("home.quickStart")}
                <ArrowRight className="w-4 h-4" />
              </Link>
            </>
          ) : (
            <>
              <button
                onClick={() => setAuthMode("signup")}
                className="inline-flex items-center gap-2 px-8 py-3.5 bg-studio-accent hover:bg-studio-accentHover text-white rounded-xl font-medium transition-all hover:scale-[1.02] shadow-lg shadow-studio-accent/20"
              >
                {t("home.getStarted")}
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => setAuthMode("signin")}
                className="inline-flex items-center gap-2 px-8 py-3.5 bg-studio-panel hover:bg-studio-border border border-studio-border text-studio-text rounded-xl font-medium transition-all hover:scale-[1.02]"
              >
                {t("home.signIn")}
                <ArrowRight className="w-4 h-4" />
              </button>
            </>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 animate-fade-in" style={{ animationDelay: "0.1s" }}>
          {features.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <div
                key={i}
                className="group p-5 bg-studio-panel/50 hover:bg-studio-panel rounded-xl border border-studio-border hover:border-studio-accent/30 transition-all hover:translate-y-[-2px]"
              >
                <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-studio-accent/10 mb-3 group-hover:bg-studio-accent/20 transition-colors">
                  <Icon className="w-5 h-5 text-studio-accent" />
                </div>
                <h3 className="text-sm font-semibold mb-1">{feature.title}</h3>
                <p className="text-xs text-studio-muted leading-relaxed">{feature.desc}</p>
              </div>
            );
          })}
        </div>

        <div className="text-center mt-16 text-xs text-studio-muted/50">
          {t("home.footer")}
        </div>
      </div>

      {authMode && (
        <AuthModal
          mode={authMode}
          onClose={() => setAuthMode(null)}
          onSuccess={handleAuthSuccess}
        />
      )}
    </div>
  );
}
