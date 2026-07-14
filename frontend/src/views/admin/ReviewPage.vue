<template>
  <div class="review-page">
    <div class="review-header">
      <button class="back-btn" @click="$router.push('/papers')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
      <h3>审核管理 - 共享知识库</h3>
      <span class="review-count">待审核：{{ papers.length }} 篇</span>
    </div>

    <div class="review-list" v-if="papers.length > 0">
      <div v-for="paper in papers" :key="paper.id" class="review-row">
        <div class="review-info">
          <div class="review-title">{{ paper.title || paper.filename }}</div>
          <div class="review-meta">
            <span>{{ formatDate(paper.created_at) }}</span>
            <span v-if="paper.is_duplicate" class="dup-warn">⚠️ 疑似重复：{{ paper.duplicate_title }}</span>
          </div>
        </div>
        <div class="review-actions">
          <button class="approve-btn" @click="approve(paper.id)">✓ 通过</button>
          <button class="reject-btn" @click="startReject(paper)">✗ 驳回</button>
        </div>
      </div>
    </div>

    <div v-else class="review-empty">
      <div class="empty-icon">✅</div>
      <div class="empty-text">暂无待审核论文</div>
    </div>

    <div class="review-dialog-overlay" v-if="rejectVisible" @click.self="rejectVisible = false">
      <div class="review-dialog">
        <h4>驳回原因</h4>
        <textarea v-model="rejectComment" placeholder="填写驳回原因..." class="review-textarea"></textarea>
        <div class="review-dialog-actions">
          <button class="cancel-btn" @click="rejectVisible = false">取消</button>
          <button class="confirm-reject-btn" @click="confirmReject">确认驳回</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useKnowledgeBaseStore } from "../../stores/knowledgeBase";
import { getPendingPapers, approvePaper, rejectPaper } from "../../api/admin";

const kbStore = useKnowledgeBaseStore();
const papers = ref([]);
const rejectVisible = ref(false);
const rejectPaperId = ref(null);
const rejectComment = ref("");

onMounted(async () => {
  await kbStore.fetchList();
  kbStore.restoreSelection();
  loadPapers();
});

async function loadPapers() {
  try {
    const res = await getPendingPapers(kbStore.currentId);
    papers.value = res.data.papers || [];
  } catch (e) {
    console.error(e);
  }
}

async function approve(id) {
  try {
    await approvePaper(id);
    papers.value = papers.value.filter(p => p.id !== id);
  } catch (e) {
    alert("审核失败");
  }
}

function startReject(paper) {
  rejectPaperId.value = paper.id;
  rejectComment.value = "";
  rejectVisible.value = true;
}

async function confirmReject() {
  try {
    await rejectPaper(rejectPaperId.value, rejectComment.value);
    papers.value = papers.value.filter(p => p.id !== rejectPaperId.value);
    rejectVisible.value = false;
  } catch (e) {
    alert("驳回失败");
  }
}

function formatDate(d) {
  if (!d) return "";
  return new Date(d).toLocaleString("zh-CN");
}
</script>

<style scoped>
.review-page { height: 100vh; display: flex; flex-direction: column; background: var(--bg-primary); }
.review-header { display: flex; align-items: center; gap: 16px; padding: 16px 24px; background: var(--bg-card); border-bottom: 1px solid var(--border-light); flex-shrink: 0; }
.review-header h3 { font-size: 16px; font-weight: 600; }
.review-count { font-size: 13px; color: var(--text-tertiary); }
.back-btn { width: 32px; height: 32px; border: 1px solid var(--border-light); border-radius: var(--radius-sm); background: var(--bg-hover); cursor: pointer; display: flex; align-items: center; justify-content: center; color: var(--text-secondary); }
.back-btn:hover { border-color: var(--accent); color: var(--accent); }
.review-list { flex: 1; overflow-y: auto; padding: 16px 24px; }
.review-row { display: flex; align-items: center; justify-content: space-between; padding: 16px; margin-bottom: 8px; background: var(--bg-card); border-radius: var(--radius-lg); border: 1px solid var(--border-light); }
.review-info { flex: 1; min-width: 0; }
.review-title { font-size: 14px; font-weight: 500; color: var(--text-primary); }
.review-meta { display: flex; gap: 12px; font-size: 12px; color: var(--text-tertiary); margin-top: 4px; }
.dup-warn { color: #d97706; }
.review-actions { display: flex; gap: 8px; flex-shrink: 0; }
.approve-btn { padding: 6px 16px; border: none; border-radius: var(--radius-md); background: #059669; color: #fff; font-size: 13px; cursor: pointer; font-family: var(--font-sans); }
.approve-btn:hover { background: #047857; }
.reject-btn { padding: 6px 16px; border: 1px solid #dc2626; border-radius: var(--radius-md); background: #fff; color: #dc2626; font-size: 13px; cursor: pointer; font-family: var(--font-sans); }
.reject-btn:hover { background: #fef2f2; }
.review-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.empty-icon { font-size: 48px; opacity: 0.5; margin-bottom: 16px; }
.empty-text { font-size: 14px; color: var(--text-tertiary); }

.review-dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); backdrop-filter: blur(4px); z-index: 2000; display: flex; align-items: center; justify-content: center; }
.review-dialog { background: var(--bg-card); border-radius: var(--radius-xl); padding: 24px; width: 400px; }
.review-dialog h4 { margin-bottom: 12px; font-size: 15px; }
.review-textarea { width: 100%; height: 80px; padding: 10px; border: 1px solid var(--border-light); border-radius: var(--radius-md); font-size: 13px; font-family: var(--font-sans); resize: none; outline: none; background: var(--bg-hover); }
.review-textarea:focus { border-color: var(--accent); }
.review-dialog-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
.cancel-btn { padding: 8px 16px; border: 1px solid var(--border-light); border-radius: var(--radius-md); background: var(--bg-card); cursor: pointer; font-size: 13px; }
.confirm-reject-btn { padding: 8px 16px; border: none; border-radius: var(--radius-md); background: #dc2626; color: #fff; cursor: pointer; font-size: 13px; }
</style>
