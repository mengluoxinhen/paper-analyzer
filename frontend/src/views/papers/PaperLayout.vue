<template>
  <div class="paper-layout">
    <aside class="paper-sidebar">
      <PaperLibrary
        ref="libraryRef"
        :papers="store.list"
        :loading="store.loading"
        :currentId="store.currentPaper ? store.currentPaper.id : null"
        @select="handleSelect"
        @delete="handleDelete"
        @upload="handleUpload"
        @search="handleSearch"
        @open-settings="settingsVisible = true"
      />
    </aside>
    <main class="paper-main">
      <PaperReader
        v-if="store.currentPaper"
        :paper="store.currentPaper"
        @tagCreated="libraryRef?.loadTags()"
      />
      <div v-else class="main-empty">
        <div class="empty-icon">📄</div>
        <div class="empty-title">选择一篇论文开始阅读</div>
        <div class="empty-desc">从左侧论文库选择一篇论文，或上传新的论文</div>
      </div>
    </main>
    <aside class="paper-chat-panel">
      <PaperChat
        v-if="store.currentPaper"
        :paperId="store.currentPaper.id"
        :conversations="store.conversations"
        :summary="store.currentSummary"
        :summarizing="summarizing"
        :summaryStream="summaryStreamText"
        @regenerate="handleRegenerate"
      />
      <div v-else class="chat-empty">
        <div class="empty-icon">💬</div>
        <div class="empty-title">论文对话</div>
        <div class="empty-desc">选择论文后可向 AI 提问</div>
      </div>
    </aside>
    <SettingsDialog v-model:visible="settingsVisible" />
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { usePapersStore } from "../../stores/papers";
import { uploadPaper } from "../../api/papers";
import PaperLibrary from "./PaperLibrary.vue";
import PaperReader from "./PaperReader.vue";
import PaperChat from "./PaperChat.vue";
import SettingsDialog from "../settings/SettingsDialog.vue";

const store = usePapersStore();
const settingsVisible = ref(false);
const libraryRef = ref(null);
const summarizing = ref(false);
const summaryStreamText = ref('');

onMounted(() => { store.fetchList(); });

async function handleSelect(paper) {
  store.currentPaper = await store.fetchPaper(paper.id);
  store.conversations = [];
  summaryStreamText.value = '';
  await store.fetchConversations(paper.id);
  // 先尝试获取已有总结，有则直接复用
  await store.fetchSummary(paper.id);
  if (store.currentSummary) return;
  // 没有总结且论文有内容，自动生成
  if (store.currentPaper.status === 'parsed' && store.currentPaper.md_content) {
    summarizing.value = true;
    try {
      await streamSummarize(store.currentPaper.id);
    } finally {
      summarizing.value = false;
    }
  } else if (store.currentPaper.status === 'parse_failed') {
    store.currentSummary = { problem: 'MinerU PDF 解析失败，请检查 API Token 是否正确配置', conclusion: '', conditions: '', full_text: '' };
  } else {
    store.currentSummary = { problem: '请上传对应的 MD 文件以生成总结', conclusion: '', conditions: '', full_text: '' };
  }
}


async function handleRegenerate() {
  if (!store.currentPaper) return;
  store.currentSummary = null;
  summarizing.value = true;
  summaryStreamText.value = '';
  try {
    await streamSummarize(store.currentPaper.id);
  } finally {
    summarizing.value = false;
  }
}

async function handleDelete(paper) {
  await store.removePaper(paper.id);
  ElMessage.success("论文已删除");
}

async function handleUpload({ title, pdfFile, mdFile, folderId }) {
  try {
    await uploadPaper(title, pdfFile, mdFile, folderId);
    ElMessage.success("上传成功");
    await store.fetchList();
  } catch (e) {
    ElMessage.error("上传失败: " + (e.response ? e.response.data.detail : e.message));
  }
}

function handleSearch(params) { store.fetchList(params || {}); }

async function streamSummarize(paperId) {
  try {
    summaryStreamText.value = '';
    const response = await fetch("/api/papers/" + paperId + "/summarize", { method: "POST" });
    if (!response.ok) {
      const err = await response.text();
      throw new Error(err);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") {
            // Streaming finished, fetch the parsed summary
            await store.fetchSummary(paperId);
            summaryStreamText.value = '';
            return;
          }
          if (data.startsWith("__CACHED__")) {
            // Already cached, use directly
            try {
              const cached = JSON.parse(data.slice(10));
              store.currentSummary = cached;
            } catch(e) { /* ignore */ }
            summaryStreamText.value = '';
            summarizing.value = false;
            return;
          }
          summaryStreamText.value += data;
        }
      }
    }
  } catch {
    summarizing.value = false;
  }
}
</script>

<style scoped>
.paper-layout { display: flex; height: 100vh; overflow: hidden; gap: 12px; padding: 12px; background: var(--bg-primary); }
.paper-sidebar { width: 260px; min-width: 260px; flex-shrink: 0; background: var(--bg-card); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); display: flex; flex-direction: column; overflow: hidden; transition: box-shadow var(--transition-base); }
.paper-sidebar:hover { box-shadow: var(--shadow-md); }
.paper-main { flex: 1; min-width: 0; background: var(--bg-card); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); overflow: hidden; transition: box-shadow var(--transition-base); }
.paper-main:hover { box-shadow: var(--shadow-md); }
.paper-chat-panel { width: 380px; min-width: 380px; flex-shrink: 0; background: var(--bg-card); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); display: flex; flex-direction: column; overflow: hidden; transition: box-shadow var(--transition-base); }
.paper-chat-panel:hover { box-shadow: var(--shadow-md); }

.main-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; height: 100%; padding: 40px; text-align: center; }
.chat-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px; text-align: center; }
.empty-icon { font-size: 48px; margin-bottom: var(--space-lg); opacity: 0.7; }
.empty-title { font-size: var(--font-size-lg); font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-xs); }
.empty-desc { font-size: var(--font-size-sm); color: var(--text-tertiary); max-width: 240px; line-height: 1.6; }
</style>
