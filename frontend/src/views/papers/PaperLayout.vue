<template>
  <div class="paper-layout">
    <aside class="paper-sidebar">
      <div class="kb-selector">
        <div class="kb-selector-inner">
          <select v-model="kbStore.currentId" class="kb-select" @change="onKbChange">
            <option v-for="kb in kbStore.list" :key="kb.id" :value="kb.id">{{ kb.name }}</option>
          </select>
          <button class="kb-add-btn" @click="showKbDialog = true">+</button>
        </div>
      </div>
      <PaperLibrary
        :kbId="kbStore.currentId"
        ref="libraryRef"
        :papers="store.list"
        :loading="store.loading"
        :currentId="store.currentPaper ? store.currentPaper.id : null"
        :parseProgressMap="parseProgressMap"
        @select="handleSelect"
        @delete="handleDelete"
        @upload="handleUpload"
        @search="handleSearch"
        @open-settings="settingsVisible = true"
      />
    </aside>
    <main class="paper-main" :style="mainPanelStyle">
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
    <div
      class="resize-handle"
      @mousedown="startResize"
      :class="{ active: resizing }"
    ></div>
    <aside class="paper-chat-panel" :style="chatPanelStyle">
      <PaperChat
        v-if="store.currentPaper"
        :key="store.currentPaper.id"
        :paperId="store.currentPaper.id"
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
    <div class="kb-dialog-overlay" v-if="showKbDialog" @click.self="showKbDialog = false">
      <div class="kb-dialog">
        <h4>管理知识库</h4>
        <div class="kb-list">
          <div v-for="kb in kbStore.list" :key="kb.id" class="kb-item" :class="{ active: kb.id === kbStore.currentId }" @click="kbStore.select(kb.id); showKbDialog = false">
            <div class="kb-item-info">
              <span class="kb-item-name">{{ kb.is_shared ? '共享库' : kb.name }}</span>
              <span class="kb-item-count">{{ kb.paper_count }} 篇</span>
            </div>
            <div class="kb-item-actions" v-if="!kb.is_shared">
              <button class="kb-action-btn" @click.stop="startRenameKb(kb)">&#9998;</button>
              <button class="kb-action-btn danger" @click.stop="handleDeleteKb(kb)">&#10005;</button>
            </div>
          </div>
        </div>
        <div class="kb-create-row">
          <input v-model="newKbName" placeholder="新知识库名称..." class="kb-create-input" @keydown.enter="handleCreateKb" />
          <button class="kb-create-btn" @click="handleCreateKb" :disabled="!newKbName.trim()">创建</button>
        </div>
        <div v-if="editingKbId" class="kb-rename-row">
          <input v-model="editingKbName" placeholder="新名称..." class="kb-rename-input" @keydown.enter="confirmRenameKb" @keydown.escape="cancelRenameKb" />
          <button class="kb-create-btn" @click="confirmRenameKb">确认</button>
          <button class="kb-cancel-btn" @click="cancelRenameKb">取消</button>
        </div>
        <button class="kb-close-btn" @click="showKbDialog = false">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from "vue";
import { ElMessage } from "element-plus";
import { useKnowledgeBaseStore } from "../../stores/knowledgeBase";
import { usePapersStore } from "../../stores/papers";
import { uploadPaper } from "../../api/papers";
import PaperLibrary from "./PaperLibrary.vue";
import PaperReader from "./PaperReader.vue";
import PaperChat from "./PaperChat.vue";
import SettingsDialog from "../settings/SettingsDialog.vue";

const store = usePapersStore();
const kbStore = useKnowledgeBaseStore();
const settingsVisible = ref(false);
const showKbDialog = ref(false);
const newKbName = ref("");
const editingKbId = ref(null);
const editingKbName = ref("");
const chatWidth = ref(520);
const resizing = ref(false);
const MIN_CHAT = 400;
const MAX_CHAT = 720;
const MIN_MAIN = 100;
const libraryRef = ref(null);
const summarizing = ref(false);
const summaryStreamText = ref('');

// paperId → { progress: number, message: string }
const parseProgressMap = reactive({});

const chatPanelStyle = computed(() => ({ width: chatWidth.value + 'px', minWidth: chatWidth.value + 'px', flexShrink: '0' }));
const mainPanelStyle = computed(() => ({ minWidth: '0' }));

function onKbChange() {
  if (kbStore.currentId) {
    store.setKbId(kbStore.currentId);
    store.currentPaper = null;
    store.currentSummary = null;
    store.fetchList();
  }
}


async function handleCreateKb() {
  const name = newKbName.value.trim();
  if (!name) return;
  try { await kbStore.create(name, ""); newKbName.value = ""; store.setKbId(kbStore.currentId); store.fetchList(); } catch(e) {}
}
function startRenameKb(kb) { editingKbId.value = kb.id; editingKbName.value = kb.name; }
async function confirmRenameKb() {
  if (!editingKbName.value.trim()) return;
  try { await kbStore.update(editingKbId.value, { name: editingKbName.value.trim() }); editingKbId.value = null; editingKbName.value = ''; } catch(e) {}
}
function cancelRenameKb() { editingKbId.value = null; editingKbName.value = ''; }
async function handleDeleteKb(kb) {
  if (!confirm('确定删除知识库"' + kb.name + '"吗？所有论文将被永久删除。')) return;
  try { await kbStore.remove(kb.id); if (kbStore.currentId) { store.setKbId(kbStore.currentId); store.currentPaper = null; store.currentSummary = null; store.fetchList(); } } catch(e) {}
}

function startResize(e) {
  resizing.value = true;
  const startX = e.clientX;
  const startWidth = chatWidth.value;
  const onMove = (ev) => {
    const delta = startX - ev.clientX;
    const next = Math.min(MAX_CHAT, Math.max(MIN_CHAT, startWidth + delta));
    const containerWidth = document.querySelector('.paper-layout')?.clientWidth || 1400;
    const mainNext = containerWidth - 260 - 8 - 12 * 5 - next;
    if (mainNext < MIN_MAIN) return;
    chatWidth.value = next;
  };
  const onUp = () => {
    resizing.value = false;
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  };
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
  document.body.style.cursor = 'col-resize';
  document.body.style.userSelect = 'none';
}

onMounted(async () => { await kbStore.fetchList(); kbStore.restoreSelection(); if (kbStore.currentId) { store.setKbId(kbStore.currentId); store.fetchList(); } });

async function handleSelect(paper) {
  store.currentPaper = await store.fetchPaper(paper.id);
  summaryStreamText.value = '';
  await store.fetchSummary(paper.id);
  if (store.currentSummary) return;
  if (store.currentPaper.status === 'parsed' && store.currentPaper.md_content) {
    summarizing.value = true;
    try {
      await streamSummarize(store.currentPaper.id);
    } finally {
      summarizing.value = false;
    }
  } else if (store.currentPaper.status === 'parse_failed') {
    store.currentSummary = { problem: 'MinerU PDF 解析失败，请检查 API Token 是否正确配置', conclusion: '', conditions: '', full_text: '' };
  } else if (store.currentPaper.status === 'parsing') {
    store.currentSummary = { problem: 'MinerU 正在解析 PDF，请稍候...', conclusion: '', conditions: '', full_text: '' };
  } else {
    store.currentSummary = { problem: '请先触发 MinerU 解析以生成总结', conclusion: '', conditions: '', full_text: '' };
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

async function handleDelete(id) {
  await store.removePaper(id);
  ElMessage.success("论文已删除");
}

async function handleUpload(title, pdfFile, folderId) {
  try {
    const res = await uploadPaper(title, pdfFile, folderId, kbStore.currentId);
    ElMessage.success("上传成功");
    await store.fetchList();

    // Auto-trigger MinerU parsing with progress tracking
    const paperId = res.data.id;
    parseProgressMap[paperId] = { progress: 0, message: '准备解析...' };
    try {
      await triggerParse(paperId);
    } catch {
      delete parseProgressMap[paperId];
    }
    await store.fetchList();
    // 解析完成后自动加载论文并触发总结
    store.currentPaper = await store.fetchPaper(paperId);
    if (store.currentPaper.status === "parsed" && store.currentPaper.md_content) {
      summarizing.value = true;
      try { await streamSummarize(paperId); } finally { summarizing.value = false; }
    }
  } catch (e) {
    ElMessage.error("上传失败：" + (e?.response?.data?.detail || e.message));
  }
}

async function triggerParse(paperId) {
  try {
    const response = await fetch("/api/papers/" + paperId + "/parse", { method: "POST" });
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
            delete parseProgressMap[paperId];
            return;
          }
          try {
            const event = JSON.parse(data);
            if (event.stage === "error") {
              delete parseProgressMap[paperId];
              throw new Error(event.message);
            }
            if (parseProgressMap[paperId]) {
              parseProgressMap[paperId].progress = event.progress || parseProgressMap[paperId].progress;
              parseProgressMap[paperId].message = event.message || parseProgressMap[paperId].message;
            }
            if (event.stage === "done") {
              setTimeout(() => { delete parseProgressMap[paperId]; }, 2000);
            }
          } catch (e) {
            if (e.message && !e.message.includes("JSON")) {
              delete parseProgressMap[paperId];
              ElMessage.error("MinerU 解析失败: " + e.message);
              throw e;
            }
          }
        }
      }
    }
  } catch (e) {
    delete parseProgressMap[paperId];
    if (e.message && !e.message.includes("JSON")) {
      ElMessage.error("MinerU 解析失败: " + e.message);
    }
    await store.fetchList();
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
            await store.fetchSummary(paperId);
            summaryStreamText.value = '';
            return;
          }
          let decoded = data; try { decoded = JSON.parse(data); } catch(_) {}
          if (decoded.startsWith("__CACHED__")) {
            try {
              const cached = JSON.parse(decoded.slice(10));
              store.currentSummary = cached;
            } catch(e) { /* ignore */ }
            summaryStreamText.value = '';
            summarizing.value = false;
            return;
          }
          summaryStreamText.value += decoded;
        }
      }
    }
  } catch {
    summarizing.value = false;
  }
}
</script>

<style scoped>

/* KB Dialog */
.kb-dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); backdrop-filter: blur(4px); z-index: 2000; display: flex; align-items: center; justify-content: center; }
.kb-dialog { background: var(--bg-card); border-radius: var(--radius-xl); box-shadow: var(--shadow-lg); padding: 24px; width: 400px; max-width: 90vw; }
.kb-dialog h4 { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
.kb-list { max-height: 240px; overflow-y: auto; margin-bottom: 12px; }
.kb-item { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-radius: var(--radius-md); cursor: pointer; transition: background var(--transition-fast); }
.kb-item:hover { background: var(--bg-hover); }
.kb-item.active { background: var(--accent-light); }
.kb-item-info { display: flex; flex-direction: column; }
.kb-item-name { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.kb-item-count { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; }
.kb-item-actions { display: flex; gap: 4px; opacity: 0; transition: opacity var(--transition-fast); }
.kb-item:hover .kb-item-actions { opacity: 1; }
.kb-action-btn { width: 26px; height: 26px; border: none; border-radius: var(--radius-sm); background: var(--bg-hover); cursor: pointer; display: flex; align-items: center; justify-content: center; color: var(--text-secondary); font-size: 14px; }
.kb-action-btn:hover { color: var(--accent); background: var(--accent-light); }
.kb-action-btn.danger:hover { color: #ef4444; background: #fee2e2; }
.kb-create-row { display: flex; gap: 8px; margin-bottom: 8px; }
.kb-create-input { flex: 1; padding: 6px 10px; border: 1px solid var(--border-light); border-radius: var(--radius-sm); font-size: 12px; font-family: var(--font-sans); outline: none; background: var(--bg-hover); }
.kb-create-input:focus { border-color: var(--accent); }
.kb-create-btn { padding: 6px 14px; border: none; border-radius: var(--radius-sm); background: var(--accent); color: #fff; font-size: 12px; cursor: pointer; font-family: var(--font-sans); }
.kb-create-btn:disabled { background: var(--border-light); color: var(--text-tertiary); cursor: not-allowed; }
.kb-create-btn:hover:not(:disabled) { background: var(--accent-hover); }
.kb-cancel-btn { padding: 6px 14px; border: 1px solid var(--border-light); border-radius: var(--radius-sm); background: var(--bg-card); color: var(--text-secondary); font-size: 12px; cursor: pointer; font-family: var(--font-sans); }
.kb-close-btn { display: block; width: 100%; margin-top: 12px; padding: 8px; border: 1px solid var(--border-light); border-radius: var(--radius-md); background: var(--bg-card); color: var(--text-secondary); font-size: 13px; cursor: pointer; font-family: var(--font-sans); }
.kb-close-btn:hover { background: var(--bg-hover); }
.kb-rename-row { display: flex; gap: 8px; margin-bottom: 8px; }
.kb-rename-input { flex: 1; padding: 6px 10px; border: 1px solid var(--accent); border-radius: var(--radius-sm); font-size: 12px; font-family: var(--font-sans); outline: none; background: var(--bg-card); }

/* KB Selector */
.kb-selector { padding: 8px 12px; border-bottom: 1px solid var(--border-light); flex-shrink: 0; }
.kb-selector-inner { display: flex; gap: 4px; align-items: center; }
.kb-select { flex: 1; min-width: 0; padding: 5px 8px; border: 1px solid var(--border-light); border-radius: var(--radius-sm); background: var(--bg-hover); font-size: 12px; color: var(--text-primary); outline: none; cursor: pointer; font-family: var(--font-sans); }
.kb-select:focus { border-color: var(--accent); }
.kb-add-btn { width: 28px; height: 28px; border: 1px solid var(--border-light); border-radius: var(--radius-sm); background: var(--bg-hover); cursor: pointer; display: flex; align-items: center; justify-content: center; color: var(--text-secondary); flex-shrink: 0; font-size: 16px; }
.kb-add-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }

.paper-layout { display: flex; height: 100vh; overflow: hidden; gap: 12px; padding: 12px; background: var(--bg-primary); }
.paper-sidebar { width: 260px; min-width: 260px; flex-shrink: 0; background: var(--bg-card); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); display: flex; flex-direction: column; overflow: hidden; transition: box-shadow var(--transition-base); }
.paper-sidebar:hover { box-shadow: var(--shadow-md); }
.paper-main { flex: 1; min-width: 0; background: var(--bg-card); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); overflow: hidden; display: flex; flex-direction: column; transition: box-shadow var(--transition-base); }
.paper-main:hover { box-shadow: var(--shadow-md); }
.paper-chat-panel { flex-shrink: 0; background: var(--bg-card); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); display: flex; flex-direction: column; overflow: hidden; transition: box-shadow var(--transition-base); }
.paper-chat-panel:hover { box-shadow: var(--shadow-md); }

.resize-handle { width: 8px; cursor: col-resize; flex-shrink: 0; position: relative; z-index: 1; display: flex; align-items: center; justify-content: center; }
.resize-handle::after { content: ""; width: 4px; height: 40px; border-radius: 2px; background: var(--border-light); transition: background 0.15s, height 0.15s; }
.resize-handle:hover::after, .resize-handle.active::after { background: var(--accent); height: 60px; }

.main-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; height: 100%; padding: 40px; text-align: center; }
.chat-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px; text-align: center; }
.empty-icon { font-size: 48px; margin-bottom: var(--space-lg); opacity: 0.7; }
.empty-title { font-size: var(--font-size-lg); font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-xs); }
.empty-desc { font-size: var(--font-size-sm); color: var(--text-tertiary); max-width: 240px; line-height: 1.6; }
</style>
