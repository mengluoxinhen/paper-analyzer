<template>
  <router-view />
</template>

<style>
/* ===== CSS 变量设计系统 ===== */
:root {
  --bg-primary: #f5f5f7;
  --bg-card: #ffffff;
  --bg-hover: #f8f8fa;
  --bg-active: #f0f0f5;
  --bg-glass: rgba(255, 255, 255, 0.72);

  --text-primary: #1d1d1f;
  --text-secondary: #86868b;
  --text-tertiary: #aeaeb2;
  --text-link: #5b5fe3;

  --border-light: rgba(0, 0, 0, 0.04);
  --border-medium: rgba(0, 0, 0, 0.08);

  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.08);
  --shadow-card: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.06);

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 20px;
  --radius-full: 9999px;

  --accent: #5b5fe3;
  --accent-light: #eeeffc;
  --accent-hover: #4a4ed0;

  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
  --font-mono: "SF Mono", "Fira Code", "Fira Mono", "Roboto Mono", Menlo, monospace;
  --font-size-sm: 12px;
  --font-size-base: 14px;
  --font-size-md: 15px;
  --font-size-lg: 17px;
  --font-size-xl: 20px;

  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --space-lg: 16px;
  --space-xl: 20px;
  --space-2xl: 24px;

  --transition-fast: 0.15s ease;
  --transition-base: 0.2s ease;
  --transition-slow: 0.3s ease;
}

/* ===== 全局 Reset ===== */
*,
*::before,
*::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: var(--font-sans);
  font-size: var(--font-size-md);
  color: var(--text-primary);
  background: var(--bg-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ===== 滚动条 ===== */
::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
  border-radius: var(--radius-full);
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}

/* ===== 选择文本 ===== */
::selection {
  background: var(--accent-light);
  color: var(--accent);
}

/* ===== Element Plus 全局覆盖 ===== */
:root {
  --el-color-primary: var(--accent);
  --el-color-primary-light-3: var(--accent-light);
  --el-color-primary-light-5: var(--accent-light);
  --el-color-primary-light-7: #eeeffc;
  --el-color-primary-light-8: #f5f5ff;
  --el-color-primary-light-9: #fafaff;
  --el-bg-color: var(--bg-card);
  --el-bg-color-overlay: var(--bg-card);
  --el-border-color: var(--border-light);
  --el-border-color-light: var(--border-light);
  --el-border-radius-base: var(--radius-md);
  --el-text-color-primary: var(--text-primary);
  --el-text-color-regular: var(--text-secondary);
  --el-font-size-base: var(--font-size-base);
  --el-font-family: var(--font-sans);
  --el-border-radius-small: var(--radius-sm);
  --el-box-shadow-light: var(--shadow-md);
  --el-box-shadow: var(--shadow-lg);
  --el-bg-color-page: var(--bg-primary);
  --el-fill-color-blank: var(--bg-card);
  --el-fill-color-light: var(--bg-hover);
  --el-input-bg-color: var(--bg-hover);
  --el-input-border-color: var(--border-light);
  --el-dialog-bg-color: var(--bg-card);
  --el-dialog-border-radius: var(--radius-xl);
  --el-dialog-box-shadow: var(--shadow-lg);
  --el-popover-bg-color: var(--bg-card);
  --el-popover-border-radius: var(--radius-lg);
}

/* Element Plus 按钮 */
.el-button--primary {
  --el-button-bg-color: var(--accent);
  --el-button-border-color: var(--accent);
  --el-button-hover-bg-color: var(--accent-hover);
  --el-button-hover-border-color: var(--accent-hover);
  --el-button-active-bg-color: var(--accent-hover);
  border-radius: var(--radius-md);
  font-weight: 500;
  transition: all var(--transition-base);
}
.el-button--primary:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.el-button--small {
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
}

.el-button--default {
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
}

/* 输入框 */
.el-input__wrapper {
  border-radius: var(--radius-md) !important;
  box-shadow: none !important;
  border: 1px solid var(--border-light);
  background: var(--bg-hover);
  transition: all var(--transition-base);
}
.el-input__wrapper:hover {
  border-color: var(--border-medium);
  background: var(--bg-card);
}
.el-input__wrapper.is-focus {
  border-color: var(--accent);
  background: var(--bg-card);
  box-shadow: 0 0 0 3px rgba(91, 95, 227, 0.1) !important;
}

/* 弹窗遮盖 */
.el-overlay {
  background-color: rgba(0, 0, 0, 0.3) !important;
  backdrop-filter: blur(8px);
}

.el-dialog {
  border-radius: var(--radius-xl) !important;
  box-shadow: var(--shadow-lg) !important;
}

.el-dialog__header {
  padding: var(--space-xl) var(--space-xl) 0 var(--space-xl);
  margin: 0;
}
.el-dialog__headerbtn {
  top: var(--space-xl);
  right: var(--space-xl);
}
.el-dialog__body {
  padding: var(--space-lg) var(--space-xl);
}
.el-dialog__footer {
  padding: 0 var(--space-xl) var(--space-xl) var(--space-xl);
}

/* 空状态 */
.el-empty__description {
  margin-top: var(--space-md);
  color: var(--text-tertiary);
}

/* Upload */
.el-upload-dragger {
  border-radius: var(--radius-lg) !important;
  border: 1.5px dashed var(--border-medium) !important;
  background: var(--bg-hover) !important;
  transition: all var(--transition-base);
}
.el-upload-dragger:hover {
  border-color: var(--accent) !important;
  background: var(--accent-light) !important;
}

/* Popconfirm */
.el-popconfirm {
  border-radius: var(--radius-lg) !important;
  padding: var(--space-md) !important;
}
.el-popconfirm__action {
  text-align: right;
  margin-top: var(--space-sm);
}
</style>