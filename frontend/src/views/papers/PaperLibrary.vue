<template>
  <div class="library">
    <div class="library-header">
      <h3>论文库</h3>
      <div class="header-actions">
        <el-button size="small" text circle @click="$emit('open-settings')">
          <el-icon :size="16"><Setting /></el-icon>
        </el-button>
        <el-button type="primary" size="small" @click="uploadVisible = true">
          <el-icon :size="14"><Upload /></el-icon>
          <span>上传</span>
        </el-button>
      </div>
    </div>

    <div class="qa-nav">
      <button class="qa-nav-btn" @click="router_qa.push('/qa')">
        <span class="qa-nav-icon">💬</span>
        <span class="qa-nav-label">全局问答</span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
    </div>

    <div class="library-search">
      <el-input v-model="keyword" placeholder="搜索论文…" size="small" clearable :prefix-icon="Search" @input="debouncedSearch" class="search-input" />
    </div>

    <!-- 文件夹 -->
    <div class="section">
      <div class="section-header">
        <span class="section-title">文件夹</span>
        <el-button size="small" text @click="startAddFolder(null)">
          <el-icon :size="14"><Plus /></el-icon>
        </el-button>
      </div>

      <div v-if="showAddInput" class="folder-input-row">
        <el-input v-model="addingName" placeholder="文件夹名称" size="small" @keydown.enter="confirmAddFolder" @keydown.escape="cancelAddFolder" />
        <el-button size="small" text @click="confirmAddFolder"><el-icon :size="14"><Check /></el-icon></el-button>
        <el-button size="small" text @click="cancelAddFolder"><el-icon :size="14"><Close /></el-icon></el-button>
      </div>

      <div class="folder-tree">
        <div
          class="folder-row"
          :class="{ active: activeFolderId === '__uncat__', 'drop-target': dropTargetId === '__uncat__' }"
          @click="selectFolder('__uncat__')"
          @dragover.prevent="onDragOver('__uncat__')"
          @dragleave="onDragLeave"
          @drop="onDrop('__uncat__')"
        >
          <span class="folder-arrow" style="visibility:hidden">▶</span>
          <el-icon class="folder-icon" :size="14"><Folder /></el-icon>
          <span class="folder-name">未分类</span>
          <span class="folder-count">{{ uncatCount }}</span>
        </div>

        <FolderTreeItem
          v-for="f in folders"
          :key="f.id"
          :folder="f"
          :depth="0"
          :activeId="activeFolderId"
          :dropTargetId="dropTargetId"
          :editingId="editingFolderId"
          :editingName="editingName"
          @select="selectFolder"
          @dragOver="onDragOver"
          @dragLeave="onDragLeave"
          @drop="onDrop"
          @startAdd="startAddFolder"
          @startEdit="startEditFolder"
          @updateEditingName="(v) => editingName = v"
          @confirmEdit="confirmEditFolder"
          @cancelEdit="cancelEditFolder"
          @delete="handleDeleteFolder"
        />
      </div>
    </div>

    <!-- 标签 -->
    <div class="section">
      <div class="section-header">
        <span class="section-title">标签</span>
        <el-button size="small" text @click="startAddTag"><el-icon :size="14"><Plus /></el-icon></el-button>
      </div>

      <div v-if="showTagInput" class="tag-input-row">
        <el-input v-model="tagInputName" placeholder="标签名称" size="small" @keydown.enter="confirmAddTag" @keydown.escape="cancelAddTag" />
        <el-button size="small" text @click="confirmAddTag"><el-icon :size="14"><Check /></el-icon></el-button>
        <el-button size="small" text @click="cancelAddTag"><el-icon :size="14"><Close /></el-icon></el-button>
      </div>

      <div class="tag-list">
        <span
          v-for="tag in tags"
          :key="tag.id"
          class="tag-pill"
          :class="{ active: activeTag === tag.name }"
          @click="selectTag(tag.name)"
        >
          {{ tag.name }}
          <el-icon class="tag-close" :size="10" @click.stop="handleDeleteTag(tag.id)"><Close /></el-icon>
        </span>
      </div>
    </div>

    <!-- 论文列表 -->
    <div class="library-list">
      <div v-if="loading" style="text-align:center; padding: 20px; color: var(--text-tertiary); font-size: var(--font-size-sm);">
        加载中...
      </div>
      <div v-else-if="!papers.length" class="list-empty">
        <div class="empty-icon">📚</div>
        <div class="empty-text">暂无论文</div>
      </div>
      <div
        v-for="paper in papers"
        :key="paper.id"
        class="paper-item"
        :class="{ active: paper.id === currentId, dragging: dragPaperId === paper.id }"
        draggable="true"
        @click="$emit('select', paper)"
        @dragstart="onDragStart(paper)"
      >
        <div class="paper-icon"><span>{{ (paper.title || paper.filename).charAt(0).toUpperCase() }}</span></div>
        <div class="paper-info">
          <div class="paper-title">{{ paper.title || paper.filename }}</div>
          <div class="paper-meta">
            <span class="paper-status" :class="'status-' + paper.status">{{ statusText(paper.status) }}</span>
            <span>{{ formatTime(paper.created_at) }}</span>
          </div>
          <!-- 解析进度条 -->
          <div v-if="parseProgressMap && parseProgressMap[paper.id]" class="paper-parse-progress">
            <div class="paper-parse-track">
              <div class="paper-parse-fill" :style="{ width: parseProgressMap[paper.id].progress + '%' }"></div>
            </div>
            <span class="paper-parse-msg">{{ parseProgressMap[paper.id].message }}</span>
          </div>
        </div>
        <el-popconfirm title="确定删除这篇论文？" confirm-button-text="删除" cancel-button-text="取消" @confirm="$emit('delete', paper)" @click.stop>
          <template #reference>
            <el-button size="small" text class="delete-btn"><el-icon :size="14"><Delete /></el-icon></el-button>
          </template>
        </el-popconfirm>
      </div>
    </div>

    <el-dialog v-model="uploadVisible" title="上传论文" width="640px" destroy-on-close :close-on-click-modal="false">
      <div class="upload-dialog">
        <el-form label-width="80px">
          <el-form-item label="目标文件夹" class="folder-select-item">
            <el-tree-select v-model="uploadFolderId" :data="folderTreeData" :props="{ label: 'name', value: 'id', children: 'children' }" placeholder="未分类" clearable check-strictly style="width:100%" />
          </el-form-item>
          <el-form-item label="论文标题">
            <el-input v-model="uploadTitle" placeholder="可选，留空使用文件名" />
          </el-form-item>
          <el-form-item label="PDF 文件">
            <el-upload :auto-upload="false" :limit="1" :show-file-list="false" :on-change="onFileChange" accept=".pdf" drag>
              <div class="upload-placeholder">
                <el-icon class="upload-icon"><UploadFilled /></el-icon>
                <div class="upload-text">点击或拖拽 PDF 文件</div>
                <div class="upload-hint">支持 PDF 格式，MinerU 将自动解析</div>
              </div>
            </el-upload>
            <div v-if="selectedFileName" class="upload-filename" :title="selectedFileName">{{ selectedFileName }}</div>
          </el-form-item>

        </el-form>
      </div>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirm" :disabled="!pdfFile">确认上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router';
const router_qa = useRouter();
import { ref, onMounted, watch } from "vue";
import {
  Plus, Check, Close, Folder, Upload, UploadFilled,
  Setting, Search, Delete,
} from "@element-plus/icons-vue";
import FolderTreeItem from "./FolderTreeItem.vue";
import {
  getFolders, createFolder, renameFolder, deleteFolder,
  getTags, createTag, deleteTag,
} from "../../api/papers";

const props = defineProps({
  papers: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  currentId: { type: [Number, String], default: null },
  parseProgressMap: { type: Object, default: () => ({}) },
});
const emit = defineEmits(["select", "delete", "upload", "search", "open-settings"]);

const folders = ref([]);
const uncatCount = ref(0);
const tags = ref([]);
const activeFolderId = ref(null);
const activeTag = ref("");
const keyword = ref("");
let searchTimer = null;

const showAddInput = ref(false);
const addingName = ref("");
const addingParentId = ref(null);
const editingFolderId = ref(null);
const editingName = ref("");
const dropTargetId = ref(null);
const dragPaperId = ref(null);

const showTagInput = ref(false);
const tagInputName = ref("");

const folderTreeData = ref([]);

function statusText(status) {
  const map = { uploaded: '待解析', parsing: '解析中…', parsed: '已解析', parse_failed: '解析失败' };
  return map[status] || status;
}

function debouncedSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(emitSearch, 300);
}

function emitSearch() { emit("search", { keyword: keyword.value, folder_id: activeFolderId.value === "__uncat__" ? -1 : activeFolderId.value, tag: activeTag.value }); }

async function loadFolders() {
  try {
    const res = await getFolders();
    folders.value = res.data.folders || [];
    uncatCount.value = res.data.uncategorized_count || 0;
    buildFolderTree();
  } catch {}
}

async function loadTags() {
  try {
    const res = await getTags();
    tags.value = Array.isArray(res.data) ? res.data : (res.data.tags || []);
  } catch {}
}

function buildFolderTree() {
  const map = new Map();
  const roots = [];
  for (const f of folders.value) {
    map.set(f.id, { ...f, children: [] });
  }
  for (const f of folders.value) {
    const node = map.get(f.id);
    if (f.parent_id && map.has(f.parent_id)) {
      map.get(f.parent_id).children.push(node);
    } else {
      roots.push(node);
    }
  }
  folderTreeData.value = roots;
}

function selectFolder(id) {
  activeFolderId.value = id;
  activeTag.value = "";
  emitSearch();
}

function selectTag(tag) {
  activeTag.value = activeTag.value === tag ? "" : tag;
  activeFolderId.value = null;
  emitSearch();
}

function startAddFolder(parentId) { showAddInput.value = true; addingName.value = ""; addingParentId.value = parentId || null; }
function cancelAddFolder() { showAddInput.value = false; addingName.value = ""; }

async function confirmAddFolder() {
  if (!addingName.value.trim()) return;
  try {
    await createFolder(addingName.value.trim(), addingParentId.value);
    showAddInput.value = false;
    addingName.value = "";
    await loadFolders();
  } catch {}
}

function startEditFolder(id, name) { editingFolderId.value = id; editingName.value = name; }
function cancelEditFolder() { editingFolderId.value = null; editingName.value = ""; }

async function confirmEditFolder() {
  if (!editingName.value.trim() || !editingFolderId.value) return;
  try {
    await renameFolder(editingFolderId.value, editingName.value.trim());
    editingFolderId.value = null;
    editingName.value = "";
    await loadFolders();
  } catch {}
}

async function handleDeleteFolder(id) {
  try {
    await deleteFolder(id);
    await loadFolders();
    if (activeFolderId.value === id) { activeFolderId.value = null; emitSearch(); }
  } catch {}
}

function onDragStart(paper) { dragPaperId.value = paper.id; }
function onDragOver(id) { dropTargetId.value = id; }
function onDragLeave() { dropTargetId.value = null; }
async function onDrop(folderId) {
  dropTargetId.value = null;
  const paperId = dragPaperId.value;
  dragPaperId.value = null;
  if (!paperId) return;
  try {
    const { movePaper } = await import("../../api/papers");
    await movePaper(paperId, folderId === "__uncat__" ? null : folderId);
    emitSearch();
  } catch {}
}

function startAddTag() { showTagInput.value = true; tagInputName.value = ""; }
function cancelAddTag() { showTagInput.value = false; tagInputName.value = ""; }
async function confirmAddTag() {
  if (!tagInputName.value.trim()) return;
  try {
    await createTag(tagInputName.value.trim());
    showTagInput.value = false;
    tagInputName.value = "";
    await loadTags();
  } catch {}
}
async function handleDeleteTag(id) {
  try {
    await deleteTag(id);
    await loadTags();
    if (activeTag.value) {
      const still = tags.value.find(t => t.name === activeTag.value);
      if (!still) { activeTag.value = ""; emitSearch(); }
    }
  } catch {}
}

const uploadVisible = ref(false);
const uploadTitle = ref("");
const uploadFolderId = ref(null);
const pdfFile = ref(null);
const selectedFileName = ref('');

function onFileChange(f) {
  pdfFile.value = f.raw;
  selectedFileName.value = f.name;
}

function handleConfirm() { emit("upload", { title: uploadTitle.value, pdfFile: pdfFile.value, folderId: uploadFolderId.value }); uploadVisible.value = false; uploadTitle.value = ""; uploadFolderId.value = null; pdfFile.value = null; selectedFileName.value = ""; }
function formatTime(t) { if (!t) return ""; return new Date(t).toLocaleDateString("zh-CN"); }

onMounted(() => { loadFolders(); loadTags(); });
watch(() => props.papers, () => {}, { deep: true });

defineExpose({ loadTags });
</script>

<style scoped>
.library { display: flex; flex-direction: column; height: 100%; }
.library-header { display: flex; justify-content: space-between; align-items: center; padding: var(--space-lg) var(--space-lg) var(--space-md); }
.library-header h3 { font-size: var(--font-size-md); font-weight: 600; color: var(--text-primary); }
.header-actions { display: flex; align-items: center; gap: var(--space-xs); }
.qa-nav { padding: 0 var(--space-sm); margin-bottom: 8px; }
.qa-nav-btn { display: flex; align-items: center; gap: 8px; width: 100%; padding: 10px 12px; border: 1px solid var(--accent); border-radius: var(--radius-md); background: linear-gradient(135deg, var(--accent-light), rgba(129,140,248,0.08)); color: var(--accent); cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.15s; }
.qa-nav-btn:hover { background: var(--accent); color: #fff; }
.qa-nav-btn:hover .qa-nav-icon { transform: scale(1.1); }
.qa-nav-icon { font-size: 16px; transition: transform 0.15s; }
.qa-nav-label { flex: 1; text-align: left; }

.library-search { padding: 0 var(--space-lg) var(--space-md); }
.search-input :deep(.el-input__wrapper) { border-radius: var(--radius-full) !important; background: var(--bg-primary); border: none; padding: 1px 12px; }
.search-input :deep(.el-input__inner) { font-size: var(--font-size-sm); }
.section { padding: 0 var(--space-lg); margin-bottom: var(--space-sm); }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.section-title { font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; }
.folder-input-row { display: flex; align-items: center; gap: 4px; padding: 0 8px 6px; }
.folder-input-row :deep(.el-input__wrapper) { border-radius: var(--radius-sm) !important; }
.folder-tree { margin-bottom: var(--space-xs); }

.folder-row {
  display: flex; align-items: center; gap: 4px; padding: 4px 8px;
  border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition-fast);
}
.folder-row:hover { background: var(--bg-hover); }
.folder-row.active { background: var(--accent-light); }
.folder-row.active .folder-icon { color: var(--accent); }
.folder-row.drop-target { outline: 2px solid var(--accent); outline-offset: -2px; background: var(--accent-light); }
.folder-arrow { width: 14px; font-size: 8px; color: var(--text-tertiary); flex-shrink: 0; text-align: center; cursor: pointer; }
.folder-icon { font-size: 14px; color: var(--text-tertiary); flex-shrink: 0; }
.folder-name { font-size: var(--font-size-sm); color: var(--text-primary); flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.folder-count { font-size: 10px; color: var(--text-tertiary); background: var(--bg-hover); padding: 0 5px; border-radius: var(--radius-full); flex-shrink: 0; }

.tag-list { display: flex; flex-wrap: wrap; gap: 4px; padding-bottom: var(--space-sm); }
.tag-pill { display: inline-flex; align-items: center; gap: 2px; font-size: 11px; color: var(--text-secondary); background: var(--bg-hover); padding: 2px 8px; border-radius: var(--radius-full); cursor: pointer; transition: all var(--transition-fast); }
.tag-pill:hover { background: var(--accent-light); color: var(--accent); }
.tag-pill.active { background: var(--accent); color: #fff; }
.tag-pill .tag-close { opacity: 0; }
.tag-pill:hover .tag-close { opacity: 1; }
.tag-input-row { display: flex; align-items: center; gap: 4px; padding: 0 0 6px; }
.tag-input-row :deep(.el-input__wrapper) { border-radius: var(--radius-sm) !important; }

.library-list { flex: 1; overflow-y: auto; padding: 0 var(--space-sm); }
.paper-item { display: flex; align-items: flex-start; gap: var(--space-md); padding: var(--space-md) var(--space-md); margin: 2px 0; border-radius: var(--radius-md); cursor: pointer; transition: all var(--transition-fast); user-select: none; }
.paper-item:hover { background: var(--bg-hover); transform: translateX(2px); }
.paper-item.active { background: var(--accent-light); }
.paper-item.active .paper-icon { background: var(--accent); color: #fff; }
.paper-item.dragging { opacity: 0.4; }
.paper-icon { width: 36px; height: 36px; border-radius: var(--radius-sm); background: linear-gradient(135deg, #eef0ff, #e8eaff); color: var(--accent); display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 600; flex-shrink: 0; transition: all var(--transition-fast); margin-top: 1px; }
.paper-item:hover .paper-icon { transform: scale(1.05); }
.paper-info { flex: 1; min-width: 0; }
.paper-title { font-size: var(--font-size-sm); font-weight: 500; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.4; }
.paper-meta { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; display: flex; align-items: center; gap: 6px; }
.paper-status { font-size: 10px; padding: 0 5px; border-radius: var(--radius-full); font-weight: 500; flex-shrink: 0; }
.paper-status.status-uploaded { background: #fef3c7; color: #d97706; }
.paper-status.status-parsing { background: #dbeafe; color: #2563eb; animation: pulse 1.5s ease-in-out infinite; }
.paper-status.status-parsed { background: #d1fae5; color: #059669; }
.paper-status.status-parse_failed { background: #fee2e2; color: #dc2626; }

/* Inline parse progress bar */
.paper-parse-progress { margin-top: 4px; }
.paper-parse-track { width: 100%; height: 3px; background: #e5e7eb; border-radius: 2px; overflow: hidden; }
.paper-parse-fill { height: 100%; background: linear-gradient(90deg, #3b82f6, #6366f1); border-radius: 2px; transition: width 0.3s ease; }
.paper-parse-msg { display: block; font-size: 10px; color: #6b7280; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.delete-btn { opacity: 0; transition: all var(--transition-fast); color: var(--text-tertiary) !important; }
.paper-item:hover .delete-btn { opacity: 1; }
.delete-btn:hover { color: #ef4444 !important; background: rgba(239,68,68,0.06) !important; }

.list-empty { display: flex; flex-direction: column; align-items: center; padding: 40px 20px; text-align: center; }
.list-empty .empty-icon { font-size: 32px; margin-bottom: var(--space-md); opacity: 0.6; }
.list-empty .empty-text { font-size: var(--font-size-sm); color: var(--text-secondary); }

.upload-dialog { max-height: 60vh; overflow-y: auto; overflow-x: hidden; }
.upload-dialog :deep(.el-select-dropdown) { max-width: 100%; overflow-x: hidden; }
.upload-dialog :deep(.el-select-dropdown__item) { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.upload-placeholder { padding: var(--space-lg) 0; text-align: center; }
.upload-icon { font-size: 28px; color: var(--text-tertiary); margin-bottom: var(--space-sm); }
.upload-text { font-size: var(--font-size-sm); color: var(--text-secondary); margin-bottom: var(--space-xs); }
.upload-hint { font-size: 11px; color: var(--text-tertiary); }
.upload-filename { margin-top: 8px; font-size: var(--font-size-sm); color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; background: var(--bg-hover); padding: 6px 10px; border-radius: var(--radius-sm); }

.folder-select-item :deep(.el-select) { width: 100% !important; }
.folder-select-item :deep(.el-select .el-input__wrapper) { max-width: 100%; }
.folder-select-item :deep(.el-select .el-input__inner) { overflow: hidden !important; text-overflow: ellipsis !important; white-space: nowrap !important; }
.folder-select-item :deep(.el-tree-select__popper) { max-width: 100% !important; }
.folder-select-item :deep(.el-tree-node__label) { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; }
.upload-dialog .el-form-item__content { overflow: hidden; }
</style>

<style>
.upload-dialog .el-form-item__content { flex: 1; min-width: 0; }
.upload-dialog .el-upload { display: block !important; width: 100% !important; }
.upload-dialog .el-upload-dragger { width: 100% !important; }
</style>
