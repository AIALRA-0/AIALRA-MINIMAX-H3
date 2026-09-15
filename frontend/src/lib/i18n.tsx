"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type Locale = "zh-CN" | "en";

const STORAGE_KEY = "aialra-h3:locale:v1";

const messages: Record<string, Record<Locale, string>> = {
  "language.chinese": { "zh-CN": "中文", en: "Chinese" },
  "language.english": { "zh-CN": "英文", en: "English" },
  "language.switchToEnglish": { "zh-CN": "切换到英文", en: "Switch to English" },
  "language.switchToChinese": { "zh-CN": "切换到中文", en: "Switch to Chinese" },
  "status.connected": { "zh-CN": "已连接", en: "Connected" },
  "status.offline": { "zh-CN": "离线", en: "Offline" },
  "nav.timeline": { "zh-CN": "时间线", en: "Timeline" },
  "nav.previs": { "zh-CN": "预演", en: "Previs" },
  "nav.inspector": { "zh-CN": "检查器", en: "Inspector" },
  "nav.settings": { "zh-CN": "设置与 API 密钥", en: "Settings & API Keys" },
  "nav.import": { "zh-CN": "导入剧本", en: "Import Screenplay" },
  "nav.restore": { "zh-CN": "恢复", en: "Restore" },
  "common.cancel": { "zh-CN": "取消", en: "Cancel" },
  "common.create": { "zh-CN": "创建", en: "Create" },
  "common.creating": { "zh-CN": "创建中…", en: "Creating…" },
  "common.delete": { "zh-CN": "删除", en: "Delete" },
  "common.loading": { "zh-CN": "加载中…", en: "Loading…" },
  "home.tagline": {
    "zh-CN": "面向本地模型的 AI 影视工作台，可生成素材、搭建分镜、导演镜头、制作视频并完成时间线剪辑",
    en: "A local-first AI filmmaking workstation for assets, storyboards, camera direction, video generation, and timeline editing",
  },
  "home.openProjects": { "zh-CN": "打开项目", en: "View Projects" },
  "home.quickStart": { "zh-CN": "快速开始", en: "Quick Start" },
  "home.getStarted": { "zh-CN": "开始使用", en: "Get Started" },
  "home.signIn": { "zh-CN": "登录", en: "Sign In" },
  "home.signUp": { "zh-CN": "注册", en: "Sign Up" },
  "home.footer": { "zh-CN": "本地 ComfyUI · MiniMax H3 · FLUX.2 Klein · SeedVR2", en: "Local ComfyUI · MiniMax H3 · FLUX.2 Klein · SeedVR2" },
  "projects.title": { "zh-CN": "项目", en: "Projects" },
  "projects.subtitle": { "zh-CN": "管理你的 AI 短剧与电影项目", en: "Manage your AI movie projects" },
  "projects.new": { "zh-CN": "新建项目", en: "New Project" },
  "projects.createTitle": { "zh-CN": "创建新项目", en: "Create New Project" },
  "projects.name": { "zh-CN": "名称", en: "Name" },
  "projects.namePlaceholder": { "zh-CN": "我的短剧项目", en: "My AI drama" },
  "projects.description": { "zh-CN": "描述，可选", en: "Description, optional" },
  "projects.descriptionPlaceholder": { "zh-CN": "一句话描述项目…", en: "A short description…" },
  "projects.empty": { "zh-CN": "还没有项目", en: "No projects yet" },
  "projects.emptyHint": { "zh-CN": "点击“新建项目”开始", en: "Click “New Project” to get started" },
  "projects.loading": { "zh-CN": "正在加载项目…", en: "Loading projects…" },
  "projects.nameRequired": { "zh-CN": "请输入项目名称", en: "Project name is required" },
  "projects.loadFailed": { "zh-CN": "项目加载失败", en: "Failed to load projects" },
  "projects.createFailed": { "zh-CN": "项目创建失败", en: "Failed to create project" },
  "projects.deleteFailed": { "zh-CN": "项目删除失败", en: "Failed to delete project" },
  "projects.deleteConfirm": { "zh-CN": "确定删除项目“{name}”吗，此操作无法撤销", en: "Delete project “{name}”? This cannot be undone" },
  "projects.deleteTitle": { "zh-CN": "删除项目", en: "Delete project" },
  "workspace.noFrame": { "zh-CN": "暂无画面", en: "No frame" },
  "workspace.noShots": { "zh-CN": "还没有镜头", en: "No shots yet" },
  "inspector.shot": { "zh-CN": "镜头", en: "Shot" },
  "inspector.camera": { "zh-CN": "视频", en: "Video" },
  "inspector.audio": { "zh-CN": "音频", en: "Audio" },
  "inspector.generate": { "zh-CN": "素材", en: "Assets" },
  "inspector.selectShot": { "zh-CN": "选择一个镜头以查看详情", en: "Select a shot to inspect it" },
  "pipeline.extract": { "zh-CN": "智能抽帧", en: "Rank keyframes" },
  "pipeline.extracting": { "zh-CN": "抽帧中…", en: "Extracting…" },
  "pipeline.upscale": { "zh-CN": "SeedVR2 生成 2× 母版", en: "SeedVR2 2× master" },
  "pipeline.submitting": { "zh-CN": "正在提交 SeedVR2…", en: "Submitting SeedVR2…" },
  "pipeline.rendering": { "zh-CN": "SeedVR2 正在渲染…", en: "SeedVR2 is rendering…" },
  "pipeline.ready": { "zh-CN": "2× 母版已完成", en: "2× master ready" },
  "pipeline.score": { "zh-CN": "评分 {score}", en: "Score {score}" },
  "pipeline.extractFailed": { "zh-CN": "抽帧失败", en: "Keyframe extraction failed" },
  "pipeline.upscaleFailed": { "zh-CN": "超分失败", en: "Upscale failed" },
  "pipeline.statusFailed": { "zh-CN": "超分状态查询失败", en: "Upscale status failed" },
  "studio.freestyle": { "zh-CN": "自由生成", en: "Freestyle Generation" },
  "studio.videoModel": { "zh-CN": "视频模型", en: "Video Model" },
  "studio.prompt": { "zh-CN": "提示词", en: "Prompt" },
  "studio.duration": { "zh-CN": "时长", en: "Duration" },
  "studio.resolution": { "zh-CN": "分辨率", en: "Resolution" },
  "studio.advanced": { "zh-CN": "高级设置", en: "Advanced Settings" },
  "studio.generateTake": { "zh-CN": "生成镜头", en: "Generate Take" },
  "studio.generateLongTake": { "zh-CN": "生成长镜头", en: "Generate Long Take" },
  "studio.takes": { "zh-CN": "候选镜头", en: "Takes" },
  "studio.noTakes": { "zh-CN": "还没有候选镜头", en: "No takes yet" },
  "studio.noShot": { "zh-CN": "未选择镜头，生成时会自动新建镜头", en: "No shot selected — a new shot will be created on generate" },
  "studio.max": { "zh-CN": "最长 {seconds} 秒", en: "Max {seconds}s" },
  "studio.references": { "zh-CN": "参考素材", en: "References" },
  "studio.frames": { "zh-CN": "首尾帧", en: "Frames" },
  "studio.imageAudio": { "zh-CN": "图片与音频", en: "Image + Audio" },
  "studio.promptHistory": { "zh-CN": "历史", en: "History" },
  "studio.promptPlaceholder": { "zh-CN": "描述画面运动、场景、角色动作、对白和环境声音…", en: "Describe video motion, scene, action, dialogue, and ambient sound…" },
  "studio.longPromptPlaceholder": { "zh-CN": "描述全局场景、情绪和视觉风格，各段动作写在下方关键帧提示词中…", en: "Describe the global scene, mood, and visual style; put segment actions in the keyframe prompts below…" },
  "studio.globalPrompt": { "zh-CN": "全局场景提示词", en: "Global Scene Prompt" },
  "studio.aspectRatio": { "zh-CN": "画面比例", en: "Aspect Ratio" },
  "studio.negativePrompt": { "zh-CN": "反向提示词，可选", en: "Negative Prompt, optional" },
  "studio.seed": { "zh-CN": "随机种子，可选", en: "Seed, optional" },
  "studio.random": { "zh-CN": "随机", en: "Random" },
  "studio.reset": { "zh-CN": "重置", en: "Reset" },
  "asset.title": { "zh-CN": "素材生成", en: "Asset Generation" },
  "asset.subtitle": { "zh-CN": "使用本地 FLUX.2 Klein 生成角色、场景、道具与车辆", en: "Generate characters, locations, props, and vehicles with local FLUX.2 Klein" },
  "asset.model": { "zh-CN": "模型", en: "Model" },
  "asset.local": { "zh-CN": "本地 ComfyUI", en: "Local ComfyUI" },
  "asset.reference": { "zh-CN": "参考素材", en: "Reference Asset" },
  "asset.originalPrompt": { "zh-CN": "原始提示词", en: "Original Prompt" },
  "asset.promptPlaceholder": { "zh-CN": "描述要生成的角色、场景或道具…", en: "Describe the asset to generate…" },
  "asset.saveAs": { "zh-CN": "保存名称，可选", en: "Save as, optional" },
  "asset.namePlaceholder": { "zh-CN": "素材名称…", en: "Asset name…" },
  "asset.type": { "zh-CN": "类型", en: "Type" },
  "asset.generate": { "zh-CN": "生成素材", en: "Generate Asset" },
  "asset.promptRequired": { "zh-CN": "请输入提示词", en: "Please enter a prompt" },
  "mode.t2v": { "zh-CN": "文生视频", en: "Text to Video" },
  "mode.i2v": { "zh-CN": "图生视频", en: "Image to Video" },
  "mode.flf2v": { "zh-CN": "首尾帧", en: "First / Last" },
  "mode.r2v": { "zh-CN": "参考生视频", en: "Reference to Video" },
  "mode.ia2v": { "zh-CN": "图音生视频", en: "Image + Audio" },
  "pipeline.openMaster": { "zh-CN": "打开标准化 15 秒 2× 母版", en: "Open normalized 15 s 2× master" },
};

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, values?: Record<string, string | number>) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("zh-CN");

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "zh-CN" || saved === "en") setLocaleState(saved);
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const t = useCallback((key: string, values: Record<string, string | number> = {}) => {
    let text = messages[key]?.[locale] ?? messages[key]?.["zh-CN"] ?? key;
    for (const [name, value] of Object.entries(values)) {
      text = text.replaceAll(`{${name}}`, String(value));
    }
    return text;
  }, [locale]);

  const value = useMemo(() => ({ locale, setLocale, t }), [locale, setLocale, t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useLocale() {
  const value = useContext(I18nContext);
  if (!value) throw new Error("useLocale must be used inside LocaleProvider");
  return value;
}
