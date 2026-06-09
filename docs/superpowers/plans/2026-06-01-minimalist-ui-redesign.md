# 极简风格 UI 改造实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** 将论文分析工具前端从 Element Plus 默认风格改造为 Apple/Linear/Notion 极简风格

**Architecture:** 纯 CSS 变量驱动设计系统，保留 Element Plus 组件功能逻辑但完全覆盖其默认样式。不引入新依赖。

**Tech Stack:** Vue 3 + Element Plus + SCSS (已安装)

---

### Task 1: 更新 index.html 标题

**Files:**
- Modify: C:\myweb\frontend\index.html

<title>frontend</title> → <title>PaperMind</title>

### Task 2: 全局样式系统 (App.vue)

**Files:**
- Modify: C:\myweb\frontend\src\App.vue

完整替换为包含 CSS 变量设计系统、滚动条样式、Element Plus 主题覆盖的新版本。
详见紧随其后的 apply_patch 内容。

### Task 3: PaperLayout.vue

**Files:**
- Modify: C:\myweb\frontend\src\views\papers\PaperLayout.vue

三面板卡片化布局，gap 间距代替硬边框，自定义空状态。

### Task 4: PaperLibrary.vue

**Files:**
- Modify: C:\myweb\frontend\src\views\papers\PaperLibrary.vue

圆形渐变色图标、pill 形搜索框、列表项 hover 动画、删除按钮优化、上传弹窗美化。

### Task 5: PaperReader.vue

**Files:**
- Modify: C:\myweb\frontend\src\views\papers\PaperReader.vue

隐式拖拽手柄、总结内容卡片化、Markdown 排版向 Notion 看齐。

### Task 6: PaperChat.vue

**Files:**
- Modify: C:\myweb\frontend\src\views\papers\PaperChat.vue

ChatGPT 风格气泡、首字母头像、自定义输入框、打字光标动画、欢迎引导。

### Task 7: 验证

启动开发服务器 
pm run dev，在浏览器检查视觉效果。
