<template>
  <div class="chat">
    <div class="chat-header">
      <h4>论文对话</h4>
      <span class="chat-model">AI Assistant</span>
    </div>

    <div class="chat-body" ref="chatBody">
            <div v-if="summary" class="summary-block">
        <div class="summary-header"><span>📝 论文总结</span><div class="summary-actions"><button class="action-btn" @click="copySummary" title="复制 Markdown"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button><button class="action-btn" @click="downloadSummary" title="下载 Markdown"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg></button><button class="action-btn" @click="$emit('regenerate')" title="重新生成总结"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg></button></div></div>

        <div class="summary-card">
          <div class="summary-label">解决的问题</div>
          <div v-if="summary.problem" class="summary-text" v-html="renderMsg(summary.problem)"></div>
          <div v-else class="summary-text empty-hint">未提取到相关内容</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">结论</div>
          <div v-if="summary.conclusion" class="summary-text" v-html="renderMsg(summary.conclusion)"></div>
          <div v-else class="summary-text empty-hint">未提取到相关内容</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">工况</div>
          <div v-if="summary.conditions" class="conditions-table" v-html="renderTable(summary.conditions)"></div>
          <div v-else class="summary-text empty-hint">未提取到相关内容</div>
        </div>
      </div>

      <div v-else-if="summarizing" class="summary-block">
        <div class="summary-header">📝 AI 正在分析论文...</div>
        <div class="summary-card streaming-card">
          <div class="streaming-text" v-html="renderMsg(summaryStream)"></div>
          <span class="typing-cursor"></span>
        </div>
      </div>

      <div class="chat-divider" v-if="summary && !summarizing">— 对话 —</div>

      <div v-for="(msg, idx) in messages" :key="idx" class="chat-message" :class="msg.role">
        <div class="msg-avatar"><span>{{ msg.role === 'user' ? '你' : 'AI' }}</span></div>
        <div class="msg-bubble">
          <div class="msg-content" v-html="renderMsg(msg.content)"></div>
        </div>
      </div>

      <div v-if="streamLoading" class="chat-message assistant">
        <div class="msg-avatar"><span>AI</span></div>
        <div class="msg-bubble">
          <div class="msg-content" v-html="renderMsg(streamText)"></div>
          <span class="typing-cursor"></span>
        </div>
      </div>

      <div v-if="!summarizing && !summary && messages.length === 0 && !streamLoading" class="chat-empty">
        <div class="empty-text">选择论文后将自动生成总结</div>
      </div>
    </div>

    <div class="chat-footer">
      <div class="chat-input-wrapper" :class="{ disabled: !summary || summarizing }">
        <input v-model="input" placeholder="总结生成后可输入问题..." @keydown.enter.exact="sendMessage" :disabled="!summary || summarizing || streamLoading" class="chat-input" />
        <button class="chat-send-btn" @click="sendMessage" :disabled="!input.trim() || !summary || summarizing || streamLoading">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from "vue";
import { renderMarkdown } from "../../utils/marked-setup.js";

const props = defineProps({

  paperId: Number,
  conversations: Array,
  summary: Object,
  summarizing: Boolean,
  summaryStream: String,
});
const emit = defineEmits(['regenerate']);

const input = ref("");
const streamText = ref("");
const streamLoading = ref(false);
const chatBody = ref(null);
const messages = ref([]);

watch(() => props.conversations, (val) => {
  if (val) { messages.value = val.map(c => ({ role: c.role, content: c.content })); scrollToBottom(); }
}, { immediate: true, deep: true });

watch(() => props.summaryStream, () => { scrollToBottom(); });


function buildSummaryMd() {
  if (!props.summary) return "";
  const parts = [];
  parts.push("# 论文总结");
  parts.push("");
  parts.push("## 解决的问题");
  parts.push(props.summary.problem || "未提取到相关内容");
  parts.push("");
  parts.push("## 结论");
  parts.push(props.summary.conclusion || "未提取到相关内容");
  parts.push("");
  parts.push("## 工况");
  parts.push(props.summary.conditions || "未提取到相关内容");
  return parts.join("\n");
}

async function copySummary() {
  const md = buildSummaryMd();
  try { await navigator.clipboard.writeText(md); } catch { /* fallback */ }
}

function downloadSummary() {
  const md = buildSummaryMd();
  const blob = new Blob([md], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "summary.md"; a.click();
  URL.revokeObjectURL(url);
}

function renderMsg(text) { return renderMarkdown(text); }
function renderTable(text) { return renderMarkdown(text); }

function scrollToBottom() {
  nextTick(() => { if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight; });
}

async function sendMessage() {
  const text = input.value.trim();
  if (!text || streamLoading.value || !props.summary) return;
  messages.value.push({ role: "user", content: text });
  input.value = ""; streamText.value = ""; streamLoading.value = true;
  scrollToBottom();
  try {
    const response = await fetch("/api/papers/" + props.paperId + "/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
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
          if (data === "[DONE]") { streamLoading.value = false; streamText.value = ""; return; }
          streamText.value += data;
          scrollToBottom();
        }
      }
    }
  } catch { streamLoading.value = false; }
}
</script>

<style scoped>
.chat { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.chat-header { display: flex; justify-content: space-between; align-items: center; padding: var(--space-lg) var(--space-xl); flex-shrink: 0; border-bottom: 1px solid var(--border-light); }
.chat-header h4 { font-size: var(--font-size-md); font-weight: 600; color: var(--text-primary); }
.chat-model { font-size: 11px; color: var(--text-tertiary); background: var(--bg-hover); padding: 2px 8px; border-radius: var(--radius-full); }

.chat-body { flex: 1; overflow-y: auto; padding: var(--space-lg) var(--space-xl); }

.summary-block { }
.summary-header { font-size: var(--font-size-sm); font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-md); }
.summary-card { padding: var(--space-md); border-radius: var(--radius-md); background: var(--bg-hover); border: 1px solid var(--border-light); margin-bottom: var(--space-sm); }
.summary-label { font-size: 11px; font-weight: 600; color: var(--accent); text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 4px; }
.summary-text { font-size: 14px; line-height: 1.6; color: var(--text-primary); margin: 0; }
.empty-hint { color: var(--text-tertiary); font-style: italic; }
.summary-text :deep(ol), .summary-text :deep(ul) { padding-left: 1.4em; margin: 6px 0; }
.summary-text :deep(li) { margin: 4px 0; }

.streaming-card { background: var(--bg-card); border-color: var(--accent); }
.streaming-text { font-size: 14px; line-height: 1.6; color: var(--text-primary); }
.streaming-text :deep(p) { margin: 4px 0; }

.conditions-table :deep(table) { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 4px; }
.conditions-table :deep(th) { background: rgba(91,95,227,0.06); padding: 4px 8px; text-align: left; font-weight: 600; color: var(--text-primary); border-bottom: 1px solid var(--border-light); }
.conditions-table :deep(td) { padding: 4px 8px; border-bottom: 1px solid var(--border-light); color: var(--text-primary); }

.chat-divider { text-align: center; font-size: 11px; color: var(--text-tertiary); margin: var(--space-sm) 0; }
.chat-empty { display: flex; align-items: center; justify-content: center; flex: 1; }
.empty-text { font-size: var(--font-size-sm); color: var(--text-tertiary); }

.chat-message { display: flex; gap: var(--space-md); animation: msgIn 0.25s ease; }
@keyframes msgIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.chat-message.user { flex-direction: row-reverse; }
.msg-avatar { width: 30px; height: 30px; border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; flex-shrink: 0; }
.chat-message.user .msg-avatar { background: linear-gradient(135deg, var(--accent), #818cf8); color: #fff; }
.chat-message.assistant .msg-avatar { background: var(--bg-hover); color: var(--accent); border: 1px solid var(--border-light); }
.msg-bubble { max-width: 82%; }
.msg-content { padding: var(--space-md) var(--space-lg); border-radius: var(--radius-lg); font-size: var(--font-size-sm); line-height: 1.7; word-break: break-word; }
.chat-message.user .msg-content { background: var(--accent-light); color: var(--text-primary); border-bottom-right-radius: var(--radius-sm); }
.chat-message.assistant .msg-content { background: var(--bg-hover); color: var(--text-primary); border-bottom-left-radius: var(--radius-sm); border: 1px solid var(--border-light); }
.msg-content :deep(p) { margin: 4px 0; }
.msg-content :deep(p:first-child) { margin-top: 0; }
.msg-content :deep(p:last-child) { margin-bottom: 0; }
.msg-content :deep(pre) { background: rgba(0,0,0,0.04); padding: var(--space-md); border-radius: var(--radius-sm); overflow-x: auto; font-size: 12px; margin: 6px 0; }
.msg-content :deep(code) { font-family: var(--font-mono); font-size: 12px; background: rgba(0,0,0,0.05); padding: 1px 5px; border-radius: 3px; }
.msg-content :deep(pre code) { background: none; padding: 0; }
.msg-content :deep(ul), .msg-content :deep(ol) { padding-left: 1.2em; margin: 4px 0; }
.msg-content :deep(li) { margin: 2px 0; }

.typing-cursor { display: inline-block; width: 6px; height: 15px; background: var(--accent); margin-left: 2px; vertical-align: text-bottom; border-radius: 1px; animation: blink 0.8s infinite; }
@keyframes blink { 0%,50% { opacity:1; } 51%,100% { opacity:0; } }

.chat-footer { padding: var(--space-md) var(--space-lg); border-top: 1px solid var(--border-light); flex-shrink: 0; }
.chat-input-wrapper { display: flex; align-items: center; background: var(--bg-primary); border-radius: var(--radius-full); padding: 2px 2px 2px 16px; border: 1px solid var(--border-light); transition: all var(--transition-base); }
.chat-input-wrapper:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(91,95,227,0.1); background: var(--bg-card); }
.chat-input-wrapper.disabled { opacity: 0.6; pointer-events: none; }
.chat-input { flex: 1; border: none; outline: none; background: transparent; font-family: var(--font-sans); font-size: var(--font-size-sm); color: var(--text-primary); padding: 8px 0; }
.chat-input::placeholder { color: var(--text-tertiary); }
.chat-send-btn { width: 34px; height: 34px; border-radius: 50%; border: none; background: var(--accent); color: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all var(--transition-fast); flex-shrink: 0; }
.chat-send-btn:hover:not(:disabled) { background: var(--accent-hover); transform: scale(1.05); }
.chat-send-btn:disabled { background: var(--border-light); color: var(--text-tertiary); cursor: not-allowed; }

.summary-header { display: flex; align-items: center; justify-content: space-between; }
.summary-actions { display: flex; gap: 4px; }
.action-btn { width: 28px; height: 28px; border-radius: 50%; border: 1px solid var(--border-light); background: var(--bg-card); color: var(--text-secondary); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all var(--transition-fast); }
.action-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }

.msg-content :deep(.math-inline) { font-family: var(--font-mono); background: rgba(91,95,227,0.06); padding: 1px 4px; border-radius: 3px; font-style: italic; color: var(--accent); }
.msg-content :deep(.math-block) { display: block; text-align: center; font-family: var(--font-mono); background: rgba(91,95,227,0.04); padding: var(--space-md); border-radius: var(--radius-sm); margin: 8px 0; font-style: italic; color: var(--accent); }
.summary-text :deep(.math-inline) { font-family: var(--font-mono); background: rgba(91,95,227,0.06); padding: 1px 4px; border-radius: 3px; font-style: italic; color: var(--accent); }
.streaming-text :deep(.math-inline) { font-family: var(--font-mono); background: rgba(91,95,227,0.06); padding: 1px 4px; border-radius: 3px; font-style: italic; color: var(--accent); }
.conditions-table :deep(.math-inline) { font-family: var(--font-mono); background: rgba(91,95,227,0.06); padding: 1px 4px; border-radius: 3px; font-style: italic; color: var(--accent); }
</style>