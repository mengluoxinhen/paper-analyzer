<template>
  <div class="global-qa">
    <!-- Session Sidebar -->
    <div class="qa-session-bar" v-if="showSessions">
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
      <div class="qa-nav-bottom">
        <button class="rebuild-btn" @click="handleRebuild" :disabled="rebuilding">
          <svg v-if="!rebuilding" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
          <span>{{ rebuilding ? '重构中...' : '重建索引' }}</span>
        </button>
      </div>
    </div>

    <!-- Main Chat Area -->
    <div class="qa-main">
      <div class="qa-header">
        <div class="qa-header-left">
          <button class="back-btn" @click="$router.push('/papers')" title="返回论文库">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <button class="sidebar-toggle" @click="showSessions = !showSessions" :title="showSessions ? '收起侧栏' : '展开侧栏'">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="15" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          <h3>全局问答</h3>
        </div>
        <span class="qa-subtitle">基于所有已解析论文的知识库</span>
        <div class="qa-header-right">
          <button class="debug-btn" :class="{ active: showRaw }" @click="showRaw = !showRaw">
            {{ showRaw ? '📝 原始' : '👁 渲染' }}
          </button>
        </div>
      </div>

      <div class="qa-body" ref="chatBody">
        <div v-if="!currentSessionId && messages.length === 0 && !streamLoading" class="qa-welcome">
          <div class="welcome-icon">💬</div>
          <div class="welcome-title">向论文知识库提问</div>
          <div class="welcome-desc">点击左上角 "+" 开启新对话，系统会从所有已解析的论文中检索相关内容，综合后给出回答</div>
          <div class="welcome-hints">
            <span class="hint-label">试试这些问题：</span>
            <button v-for="hint in hints" :key="hint" class="hint-btn" @click="askHint(hint)">{{ hint }}</button>
          </div>
        </div>

        <div v-for="(msg, idx) in messages" :key="idx" class="qa-message" :class="msg.role">
          <div class="msg-avatar"><span>{{ msg.role === 'user' ? '你' : 'AI' }}</span></div>
          <div class="msg-body">
            <div class="msg-content">
              <pre v-if="showRaw" class="raw-md">{{ msg.content }}</pre>
              <span v-else v-html="renderMarkdown(msg.content)"></span>
            </div>
          </div>
        </div>

        <div v-if="streamLoading" class="qa-message assistant">
          <div class="msg-avatar"><span>AI</span></div>
          <div class="msg-body">
            <div class="msg-content">
              <pre v-if="showRaw" class="raw-md">{{ streamText }}</pre>
              <span v-else v-html="renderMarkdown(streamText)"></span>
            </div>
            <span class="typing-cursor"></span>
          </div>
        </div>
      </div>

      <div class="qa-footer">
        <div class="qa-input-wrapper">
          <textarea
            ref="inputEl"
            v-model="input"
            :placeholder="currentSessionId ? '输入你的问题...' : '点击左上角 + 开启新对话'"
            @keydown.enter.exact.prevent="sendMessage"
            @keydown.shift.enter="input += '\n'"
            :disabled="streamLoading"
            rows="1"
            class="qa-input"
          ></textarea>
          <button class="qa-send-btn" @click="sendMessage" :disabled="!input.trim() || streamLoading">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from "vue";
import { useKnowledgeBaseStore } from "../stores/knowledgeBase";
import { ElMessage } from "element-plus";
import { renderMarkdown } from "../utils/marked-setup.js";
import { rebuildIndex } from "../api/qa.js";
import { getChatSessions, createChatSession, deleteChatSession, getChatMessages, sendChatMessage } from "../api/chat.js";

const kbStore = useKnowledgeBaseStore();
const messages = ref([]);
const input = ref("");
const streamText = ref("");
const streamLoading = ref(false);
const chatBody = ref(null);
const inputEl = ref(null);
const showRaw = ref(false);
const rebuilding = ref(false);
const showSessions = ref(false);
const sessions = ref([]);
const currentSessionId = ref(null);

const hints = [
  "这些论文主要研究了哪些问题？",
  "对比一下不同论文的研究方法",
  "有哪些论文涉及CFD仿真分析？",
];

onMounted(() => { loadSessions(); });

async function loadSessions() {
  try {
    const res = await getChatSessions(null, kbStore.currentId); // null = global sessions
    sessions.value = res.data.sessions || [];
  } catch { /* ignore */ }
}

async function handleNewSession() {
  try {
    const res = await createChatSession("", null, kbStore.currentId);
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
    messages.value = (res.data || []).map(m => ({ role: m.role, content: m.content }));
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

function askHint(hint) {
  input.value = hint;
  sendMessage();
}

async function sendMessage() {
  if (!input.value.trim() || streamLoading.value) return;
  if (!currentSessionId.value) {
    await handleNewSession();
    if (!currentSessionId.value) return;
  }

  const userMsg = input.value.trim();
  input.value = "";
  messages.value.push({ role: "user", content: userMsg });
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
      streamLoading.value = false;
      messages.value.push({ role: "assistant", content: streamText.value });
      streamText.value = "";
      await loadSessions();
      scrollToBottom();
    },
    (err) => {
      streamLoading.value = false;
      messages.value.push({ role: "assistant", content: "❌ 错误: " + err });
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

async function handleRebuild() {
  rebuilding.value = true;
  try {
    if (!kbStore.currentId) {
      ElMessage.warning("请先选择知识库");
      rebuilding.value = false;
      return;
    }
    const res = await rebuildIndex(kbStore.currentId);
    ElMessage.success(res.data.message || "索引重建完成");
  } catch {
    ElMessage.error("索引重建失败");
  } finally {
    rebuilding.value = false;
  }
}
</script>

<style scoped>
.global-qa { display: flex; height: 100vh; overflow: hidden; background: var(--bg-primary); }

.qa-session-bar { width: 220px; min-width: 220px; background: var(--bg-card); border-right: 1px solid var(--border-light); display: flex; flex-direction: column; }
.session-bar-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 12px; font-size: 13px; font-weight: 600; color: var(--text-secondary); border-bottom: 1px solid var(--border-light); }
.session-new-btn { width: 26px; height: 26px; border-radius: var(--radius-sm); border: 1px solid var(--border-light); background: var(--bg-primary); color: var(--text-secondary); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.15s; }
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

.qa-nav-bottom { padding: 10px; border-top: 1px solid var(--border-light); }
.rebuild-btn { display: flex; align-items: center; gap: 6px; padding: 6px 12px; border: 1px solid var(--border-light); border-radius: var(--radius-md); background: var(--bg-primary); color: var(--text-secondary); font-size: 12px; cursor: pointer; width: 100%; justify-content: center; transition: all 0.15s; }
.rebuild-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }
.rebuild-btn:disabled { opacity: 0.6; cursor: not-allowed; }

/* Main */
.qa-main { flex: 1; display: flex; flex-direction: column; min-width: 0; background: var(--bg-card); }

.qa-header { display: flex; align-items: center; gap: 12px; padding: 12px 20px; border-bottom: 1px solid var(--border-light); flex-shrink: 0; }
.qa-header-left { display: flex; align-items: center; gap: 8px; }
.sidebar-toggle { width: 28px; height: 28px; border: none; background: transparent; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center; justify-content: center; border-radius: var(--radius-sm); }
.sidebar-toggle:hover { background: var(--bg-hover); color: var(--accent); }
.back-btn { width: 32px; height: 32px; border-radius: var(--radius-sm); border: 1px solid var(--border-light); background: var(--bg-primary); color: var(--text-secondary); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.15s; flex-shrink: 0; }
.back-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }
.qa-header h3 { font-size: 16px; font-weight: 600; color: var(--text-primary); margin: 0; }
.qa-subtitle { font-size: 12px; color: var(--text-tertiary); background: var(--bg-hover); padding: 2px 10px; border-radius: var(--radius-full); flex-shrink: 0; }
.qa-header-right { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.debug-btn { padding: 4px 12px; border: 1px solid var(--border-light); border-radius: var(--radius-full); background: var(--bg-primary); color: var(--text-secondary); font-size: 12px; cursor: pointer; transition: all 0.15s; }
.debug-btn:hover, .debug-btn.active { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }

.qa-body { flex: 1; overflow-y: auto; padding: 20px 24px; }

.qa-welcome { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; }
.welcome-icon { font-size: 48px; margin-bottom: var(--space-lg); opacity: 0.7; }
.welcome-title { font-size: var(--font-size-lg); font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-xs); }
.welcome-desc { font-size: var(--font-size-sm); color: var(--text-tertiary); max-width: 400px; line-height: 1.6; margin-bottom: var(--space-lg); }
.welcome-hints { display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 8px; }
.hint-label { font-size: 13px; color: var(--text-secondary); }
.hint-btn { padding: 6px 14px; border: 1px solid var(--border-light); border-radius: var(--radius-full); background: var(--bg-primary); color: var(--text-secondary); font-size: 13px; cursor: pointer; transition: all 0.15s; }
.hint-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }

.qa-message { display: flex; gap: var(--space-md); margin-bottom: 20px; animation: msgIn 0.25s ease; }
@keyframes msgIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.qa-message.user { flex-direction: row-reverse; }
.msg-avatar { width: 30px; height: 30px; border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; flex-shrink: 0; }
.qa-message.user .msg-avatar { background: linear-gradient(135deg, var(--accent), #818cf8); color: #fff; }
.qa-message.assistant .msg-avatar { background: var(--bg-hover); color: var(--accent); border: 1px solid var(--border-light); }
.msg-body { max-width: 82%; min-width: 0; }
.msg-content { padding: var(--space-md) var(--space-lg); border-radius: var(--radius-lg); font-size: var(--font-size-sm); line-height: 1.7; word-break: break-word; }
.qa-message.user .msg-content { background: var(--accent-light); color: var(--text-primary); border-bottom-right-radius: var(--radius-sm); }
.qa-message.assistant .msg-content { background: var(--bg-hover); color: var(--text-primary); border-bottom-left-radius: var(--radius-sm); border: 1px solid var(--border-light); }
.msg-content :deep(p) { margin: 4px 0; }
.msg-content :deep(p:first-child) { margin-top: 0; }
.msg-content :deep(p:last-child) { margin-bottom: 0; }
.msg-content :deep(pre) { background: rgba(0,0,0,0.04); padding: var(--space-md); border-radius: var(--radius-sm); overflow-x: auto; font-size: 12px; margin: 6px 0; }
.msg-content :deep(code) { font-family: var(--font-mono); font-size: 12px; background: rgba(0,0,0,0.05); padding: 1px 5px; border-radius: 3px; }
.msg-content :deep(pre code) { background: none; padding: 0; }
.msg-content :deep(h1), .msg-content :deep(h2), .msg-content :deep(h3), .msg-content :deep(h4) { margin: 12px 0 6px; font-weight: 600; color: var(--text-primary); line-height: 1.4; }
.msg-content :deep(h1) { font-size: 18px; }
.msg-content :deep(h2) { font-size: 16px; padding-bottom: 4px; border-bottom: 1px solid var(--border-light); }
.msg-content :deep(h3) { font-size: 14px; }
.msg-content :deep(h4) { font-size: 13px; }
.msg-content :deep(blockquote) { margin: 8px 0; padding: 6px 12px; border-left: 3px solid var(--accent); background: var(--accent-light); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; color: var(--text-secondary); }
.msg-content :deep(a) { color: var(--accent); text-decoration: underline; }
.msg-content :deep(hr) { border: none; border-top: 1px solid var(--border-light); margin: 12px 0; }
.msg-content :deep(ul), .msg-content :deep(ol) { padding-left: 1.2em; margin: 4px 0; }
.msg-content :deep(li) { margin: 2px 0; }
.msg-content :deep(table) { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 12px; }
.msg-content :deep(th), .msg-content :deep(td) { border: 1px solid var(--border-light); padding: 6px 10px; text-align: left; }
.msg-content :deep(th) { background: var(--bg-hover); font-weight: 600; }
.msg-content :deep(.math-inline) { font-family: var(--font-mono); background: rgba(91,95,227,0.06); padding: 1px 4px; border-radius: 3px; font-style: italic; color: var(--accent); }
.msg-content :deep(.math-block) { display: block; text-align: center; font-family: var(--font-mono); background: rgba(91,95,227,0.04); padding: var(--space-md); border-radius: var(--radius-sm); margin: 8px 0; font-style: italic; color: var(--accent); }

.typing-cursor { display: inline-block; width: 6px; height: 15px; background: var(--accent); margin-left: 2px; vertical-align: text-bottom; border-radius: 1px; animation: blink 0.8s infinite; }
@keyframes blink { 0%,50% { opacity:1; } 51%,100% { opacity:0; } }

.raw-md { white-space: pre-wrap; word-break: break-word; font-family: var(--font-mono); font-size: 12px; line-height: 1.5; color: var(--text-secondary); background: var(--bg-hover); padding: 12px; border-radius: var(--radius-sm); margin: 0; }

.qa-footer { padding: 16px 24px; border-top: 1px solid var(--border-light); flex-shrink: 0; background: var(--bg-card); }
.qa-input-wrapper { display: flex; align-items: flex-end; background: var(--bg-primary); border-radius: var(--radius-lg); padding: 4px 4px 4px 16px; border: 1px solid var(--border-light); transition: all 0.15s; }
.qa-input-wrapper:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(91,95,227,0.1); background: var(--bg-card); }
.qa-input { flex: 1; border: none; outline: none; background: transparent; font-family: var(--font-sans); font-size: 14px; color: var(--text-primary); padding: 8px 0; resize: none; max-height: 120px; line-height: 1.5; }
.qa-input::placeholder { color: var(--text-tertiary); }
.qa-send-btn { width: 36px; height: 36px; border-radius: 50%; border: none; background: var(--accent); color: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.15s; flex-shrink: 0; }
.qa-send-btn:hover:not(:disabled) { background: var(--accent-hover); transform: scale(1.05); }
.qa-send-btn:disabled { background: var(--border-light); color: var(--text-tertiary); cursor: not-allowed; }
</style>

