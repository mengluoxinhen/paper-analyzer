<template>
  <div class="chat">
    <!-- Session Sidebar -->
    <div class="chat-session-bar" v-if="showSessions">
      <div class="session-bar-header">
        <span>对话历史</span>
        <button class="session-new-btn" @click="handleNewSession" title="新建对话">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>
      </div>
      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: currentSessionId === s.id }"
          @click="switchSession(s.id)"
        >
          <div class="session-item-main">
            <div class="session-title">{{ s.title || '新对话' }}</div>
            <div class="session-preview">{{ s.preview || '暂无消息' }}</div>
          </div>
          <button class="session-del-btn" @click.stop="handleDeleteSession(s.id)" title="删除">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div v-if="sessions.length === 0" class="session-empty">暂无对话记录</div>
      </div>
    </div>

    <!-- Main Chat Area -->
    <div class="chat-main">
      <div class="chat-header">
        <div class="chat-header-left">
          <button class="sidebar-toggle" @click="showSessions = !showSessions" :title="showSessions ? '收起侧栏' : '展开侧栏'">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="15" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          <h4>论文对话</h4>
        </div>
        <span class="chat-model">AI Assistant</span>
      </div>

      <div class="chat-body" ref="chatBody">
        <div v-if="summarizing && !currentSessionId" class="summary-block">
          <div class="summary-header">📝 AI 正在分析论文...</div>
          <div class="summary-card streaming-card">
            <div class="streaming-text" v-html="renderMsg(summaryStream)"></div>
            <span class="typing-cursor"></span>
          </div>
        </div><div v-else-if="summary && !currentSessionId" class="summary-block">
          <div class="summary-header"><span>📝 论文总结</span><span v-if="summary.paper_type" class="paper-type-badge">{{ summary.paper_type }}</span><div class="summary-actions"><button class="action-btn" @click="copySummary" title="复制 Markdown"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button><button class="action-btn" @click="downloadSummary" title="下载 Markdown"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg></button><button class="action-btn" @click="$emit('regenerate')" title="重新生成总结"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg></button></div></div>

          <div class="summary-card">
            <div class="summary-label">研究概述</div>
            <div v-if="summary.problem" class="summary-text" v-html="renderMsg(summary.problem)"></div>
            <div v-else class="summary-text empty-hint">未提取到相关内容</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">核心创新点</div>
            <div v-if="summary.innovation" class="summary-text" v-html="renderMsg(summary.innovation)"></div>
            <div v-else class="summary-text empty-hint">未提取到相关内容</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">结论</div>
            <div v-if="summary.conclusion" class="summary-text" v-html="renderMsg(summary.conclusion)"></div>
            <div v-else class="summary-text empty-hint">未提取到相关内容</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">条件与方法</div>
            <div v-if="summary.conditions" class="conditions-table" v-html="renderTable(summary.conditions)"></div>
            <div v-else class="summary-text empty-hint">未提取到相关内容</div>
          </div>
        </div>

        

        <div
          v-if="(summary || summarizing) && !currentSessionId"
          class="summary-ask-hint"
        >
          <div class="hint-text">💡 点击上方 <strong>"+"</strong> 开启新对话，进行多轮问答</div>
        </div>

        <div
          v-if="currentSessionId && !summary && !summarizing"
          class="chat-divider"
        >— 对话 —</div>

        <div v-for="msg in messages" :key="msg._id" class="chat-message" :class="msg.role">
          <div class="msg-avatar"><span>{{ msg.role === 'user' ? '你' : 'AI' }}</span></div>
          <div class="msg-bubble">
            <div class="msg-content" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>

        <div v-if="streamLoading" class="chat-message assistant">
          <div class="msg-avatar"><span>AI</span></div>
          <div class="msg-bubble">
            <div class="msg-content" v-html="renderMarkdown(streamText)"></div>
            <span class="typing-cursor"></span>
          </div>
        </div>

        <div v-if="currentSessionId && messages.length === 0 && !streamLoading" class="chat-empty">
          <div class="empty-text">开始提问吧</div>
        </div>
      </div>

      <div class="chat-footer">
        <div class="chat-input-wrapper" :class="{ disabled: !currentSessionId && (!summary || summarizing) }">
          <input
            v-model="input"
            :placeholder="currentSessionId ? '输入问题...' : '先开启新对话以开始提问...'"
            @keydown.enter.exact="sendMessage"
            :disabled="(!currentSessionId && (!summary || summarizing)) || streamLoading"
            class="chat-input"
          />
          <button
            class="chat-send-btn"
            @click="sendMessage"
            :disabled="!input.trim() || (!currentSessionId && (!summary || summarizing)) || streamLoading"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { renderMarkdown } from "../../utils/marked-setup.js";
import { getChatSessions, createChatSession, deleteChatSession, getChatMessages, sendChatMessage } from "../../api/chat.js";

const props = defineProps({
  paperId: [Number, String],
  conversations: Array,
  summary: Object,
  summarizing: Boolean,
  summaryStream: String,
});
const emit = defineEmits(["regenerate"]);

const input = ref("");
const streamText = ref("");
const streamLoading = ref(false);
const chatBody = ref(null);
const messages = ref([]);
const showSessions = ref(false);
const sessions = ref([]);
const currentSessionId = ref(null);

watch(() => props.summaryStream, () => { scrollToBottom(); });

// Load sessions when paperId changes
watch(() => props.paperId, async (newId) => {
  currentSessionId.value = null;
  messages.value = [];
  if (newId) {
    await loadSessions();
  }
}, { immediate: true });

async function loadSessions() {
  try {
    const res = await getChatSessions(props.paperId);
    sessions.value = res.data.sessions || [];
  } catch { /* ignore */ }
}

async function handleNewSession() {
  try {
    const res = await createChatSession("", props.paperId);
    const newSession = res.data;
    sessions.value.unshift(newSession);
    currentSessionId.value = newSession.id;
    messages.value = [];
  } catch (e) {
    ElMessage.error("创建会话失败");
  }
}

async function switchSession(sessionId) {
  currentSessionId.value = sessionId;
  streamText.value = "";
  streamLoading.value = false;
  try {
    const res = await getChatMessages(sessionId);
    messages.value = (res.data || []).map(m => ({ _id: m.id || Date.now() + Math.random(), role: m.role, content: m.content }));

    await nextTick();
    scrollToBottom();
  } catch {
    messages.value = [];
  }
}

async function handleDeleteSession(sessionId) {
  try {
    await deleteChatSession(sessionId);
    sessions.value = sessions.value.filter(s => s.id !== sessionId);
    if (currentSessionId.value === sessionId) {
      currentSessionId.value = null;
      messages.value = [];
    }
  } catch {
    ElMessage.error("删除会话失败");
  }
}

async function sendMessage() {
  if (!input.value.trim() || streamLoading.value) return;
  // Auto-create session if not yet created
  if (!currentSessionId.value) {
    await handleNewSession();
    if (!currentSessionId.value) return;
  }

  const userMsg = input.value.trim();
  input.value = "";
  messages.value.push({ _id: Date.now(), role: "user", content: userMsg });
  await nextTick();
  scrollToBottom();

  streamText.value = "";
  streamLoading.value = true;

  sendChatMessage(
    currentSessionId.value,
    userMsg,
    (token) => {
      streamText.value += token;
      scrollToBottom();
    },
    async () => {
      const fullText = streamText.value;
      
      messages.value.push({ _id: Date.now() + 1, role: "assistant", content: fullText });
      await nextTick();
      streamLoading.value = false;
      streamText.value = "";
      await loadSessions();
      await nextTick();
      scrollToBottom();
    },
    (err) => {
      streamLoading.value = false;
      messages.value.push({ _id: Date.now() + 1, role: "assistant", content: "❌ 错误: " + err });
      streamText.value = "";
      scrollToBottom();
    }
  );
}

function scrollToBottom() {
  nextTick(() => {
    const el = chatBody.value;
    if (el) el.scrollTop = el.scrollHeight;
  });
}

function renderMsg(text) {
  if (!text) return "";
  return renderMarkdown(text);
}

function renderTable(text) {
  if (!text) return "";
  return renderMarkdown(text);
}

function buildSummaryMd() {
  if (!props.summary) return "";
  const parts = [];
  if (props.summary.problem) parts.push("## 研究概述\n\n" + props.summary.problem);
  if (props.summary.conclusion) parts.push("## 结论\n\n" + props.summary.conclusion);
  if (props.summary.innovation) parts.push("## 核心创新点\n\n" + props.summary.innovation);
  if (props.summary.conditions) parts.push("## 条件与方法\n\n" + props.summary.conditions);
  return parts.join("\n\n");
}

function copySummary() {
  const md = buildSummaryMd();
  if (!md) return;
  navigator.clipboard.writeText(md).then(() => ElMessage.success("已复制到剪贴板"));
}

function downloadSummary() {
  const md = buildSummaryMd();
  if (!md) return;
  const blob = new Blob([md], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "summary.md";
  a.click();
  URL.revokeObjectURL(url);
}
</script>

<style scoped>
.chat { display: flex; height: 100%; overflow: hidden; }
.chat-session-bar { width: 200px; min-width: 200px; border-right: 1px solid var(--border-light); display: flex; flex-direction: column; background: var(--bg-primary); }
.session-bar-header { display: flex; align-items: center; justify-content: space-between; padding: var(--space-md) var(--space-md); font-size: 12px; font-weight: 600; color: var(--text-secondary); border-bottom: 1px solid var(--border-light); }
.session-new-btn { width: 24px; height: 24px; border-radius: var(--radius-sm); border: 1px solid var(--border-light); background: var(--bg-card); color: var(--text-secondary); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.15s; }
.session-new-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }
.session-list { flex: 1; overflow-y: auto; padding: 4px; }
.session-item { display: flex; align-items: center; gap: 4px; padding: 8px 10px; border-radius: var(--radius-md); cursor: pointer; transition: all 0.1s; margin-bottom: 2px; }
.session-item:hover { background: var(--bg-hover); }
.session-item.active { background: var(--accent-light); }
.session-item-main { flex: 1; min-width: 0; }
.session-title { font-size: 13px; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500; }
.session-item.active .session-title { color: var(--accent); }
.session-preview { font-size: 11px; color: var(--text-tertiary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px; }
.session-del-btn { width: 20px; height: 20px; border-radius: 50%; border: none; background: transparent; color: var(--text-tertiary); cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; opacity: 0; transition: all 0.1s; }
.session-item:hover .session-del-btn { opacity: 1; }
.session-del-btn:hover { background: rgba(239,68,68,0.1); color: #ef4444; }
.session-empty { text-align: center; padding: 20px 10px; font-size: 12px; color: var(--text-tertiary); }

.chat-main { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; }

.chat-header { display: flex; align-items: center; justify-content: space-between; padding: var(--space-md) var(--space-lg); border-bottom: 1px solid var(--border-light); flex-shrink: 0; }
.chat-header-left { display: flex; align-items: center; gap: 8px; }
.sidebar-toggle { width: 28px; height: 28px; border: none; background: transparent; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center; justify-content: center; border-radius: var(--radius-sm); }
.sidebar-toggle:hover { background: var(--bg-hover); color: var(--accent); }
.chat-header h4 { font-size: var(--font-size-md); font-weight: 600; margin: 0; color: var(--text-primary); }
.chat-model { font-size: 11px; color: var(--text-tertiary); background: var(--bg-hover); padding: 2px 10px; border-radius: var(--radius-full); }

.chat-body { flex: 1; overflow-y: auto; padding: var(--space-lg); }

.chat-divider { text-align: center; color: var(--text-tertiary); font-size: 12px; margin: 16px 0; }

.chat-empty { display: flex; align-items: center; justify-content: center; height: 100%; }
.empty-text { font-size: var(--font-size-sm); color: var(--text-tertiary); }

.summary-ask-hint { margin-top: 24px; text-align: center; }
.hint-text { font-size: 13px; color: var(--text-secondary); background: var(--accent-light); padding: 10px 16px; border-radius: var(--radius-md); display: inline-block; }
.hint-text strong { color: var(--accent); }

.chat-message { display: flex; gap: var(--space-md); margin-bottom: 16px; animation: msgIn 0.25s ease; }
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
.msg-content :deep(h2) { font-size: 1.15em; font-weight: 700; margin: 14px 0 6px; color: var(--text-primary); border-bottom: 1px solid var(--border-light); padding-bottom: 4px; }
.msg-content :deep(h3) { font-size: 1.05em; font-weight: 600; margin: 12px 0 4px; color: var(--text-primary); }
.msg-content :deep(h4) { font-size: 1em; font-weight: 600; margin: 10px 0 4px; }
.msg-content :deep(p) { margin: 4px 0; }
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

.summary-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.summary-actions { display: flex; gap: 4px; }
.action-btn { width: 28px; height: 28px; border-radius: 50%; border: 1px solid var(--border-light); background: var(--bg-card); color: var(--text-secondary); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all var(--transition-fast); }
.action-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }

.summary-block { margin-bottom: 16px; }
.summary-card { background: var(--bg-hover); border-radius: var(--radius-md); padding: var(--space-md); margin-bottom: 10px; }
.summary-label { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
.summary-text :deep(h2) { font-size: 1.15em; font-weight: 700; margin: 10px 0 4px; border-bottom: 1px solid var(--border-light); padding-bottom: 3px; }
.summary-text :deep(h3) { font-size: 1.05em; font-weight: 600; margin: 8px 0 3px; }
.summary-text { font-size: var(--font-size-sm); color: var(--text-primary); line-height: 1.7; }
.empty-hint { color: var(--text-tertiary); font-style: italic; }
.streaming-card { border: 1px dashed var(--border-light); }
.streaming-text :deep(h2) { font-size: 1.15em; font-weight: 700; margin: 10px 0 4px; border-bottom: 1px solid var(--border-light); padding-bottom: 3px; }
.streaming-text :deep(h3) { font-size: 1.05em; font-weight: 600; margin: 8px 0 3px; }
.streaming-text { font-size: var(--font-size-sm); color: var(--text-secondary); line-height: 1.7; }

.msg-content :deep(.math-inline) { font-family: var(--font-mono); background: rgba(91,95,227,0.06); padding: 1px 4px; border-radius: 3px; font-style: italic; color: var(--accent); }
.msg-content :deep(.math-block) { display: block; text-align: center; font-family: var(--font-mono); background: rgba(91,95,227,0.04); padding: var(--space-md); border-radius: var(--radius-sm); margin: 8px 0; font-style: italic; color: var(--accent); }
.summary-text :deep(.math-inline) { font-family: var(--font-mono); background: rgba(91,95,227,0.06); padding: 1px 4px; border-radius: 3px; font-style: italic; color: var(--accent); }
.streaming-text :deep(.math-inline) { font-family: var(--font-mono); background: rgba(91,95,227,0.06); padding: 1px 4px; border-radius: 3px; font-style: italic; color: var(--accent); }
.conditions-table { font-size: var(--font-size-sm); color: var(--text-primary); line-height: 1.7; }
.conditions-table :deep(table) { border-collapse: collapse; width: 100%; margin: 6px 0; font-size: 13px; }
.conditions-table :deep(th) { background: rgba(91,95,227,0.08); padding: 8px 12px; border: 1px solid var(--border-light); font-weight: 600; text-align: left; }
.conditions-table :deep(td) { padding: 6px 12px; border: 1px solid var(--border-light); }
.conditions-table :deep(tr:nth-child(even)) { background: rgba(0,0,0,0.02); }
.conditions-table :deep(.math-inline) { font-family: var(--font-mono); background: rgba(91,95,227,0.06); padding: 1px 4px; border-radius: 3px; font-style: italic; color: var(--accent); }

.paper-type-badge { font-size: 11px; background: var(--accent-light); color: var(--accent); padding: 2px 10px; border-radius: var(--radius-full); font-weight: 500; margin-left: 8px; }
</style>

