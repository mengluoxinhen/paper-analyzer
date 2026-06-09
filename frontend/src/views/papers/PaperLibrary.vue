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
      <div v-if="addingTag" class="tag-input-row">
        <el-input v-model="newTagName" placeholder="标签名称" size="small" @keydown.enter="confirmAddTag" @keydown.escape="cancelAddTag" ref="tagInputRef" />
        <el-button size="small" text @click="confirmAddTag"><el-icon :size="14"><Check /></el-icon></el-button>
        <el-button size="small" text @click="cancelAddTag"><el-icon :size="14"><Close /></el-icon></el-button>
      </div>
      <div class="tag-list">
        <span v-for="tag in tags" :key="tag.id" class="tag-pill" :class="{ active: activeTag === tag.name }" @click="selectTag(tag.name)">
          #{{ tag.name }}
          <el-icon class="tag-close" :size="10" @click.stop="handleDeleteTag(tag.id)"><Close /></el-icon>
        </span>
      </div>
    </div>

    <!-- 论文列表 -->
    <div class="library-list" v-loading="loading">
      <div v-if="papers.length === 0 && !loading" class="list-empty">
        <div class="empty-icon">📚</div>
        <div class="empty-text">暂无匹配论文</div>
      </div>
      <div
        v-for="paper in papers"
        :key="paper.id"
        class="paper-item"
        :class="{ active: paper.id === currentId, dragging: dragPaperId === paper.id }"
        draggable="true"
        @click="$emit('select', paper)"
        @dragstart="onDragStart(paper)"
        @dragend="onDragEnd"
      >
        <div class="paper-icon"><span>{{ (paper.title || paper.filename).charAt(0).toUpperCase() }}</span></div>
        <div class="paper-info">
          <div class="paper-title">{{ paper.title || paper.filename }}</div>
          <div class="paper-meta">{{ formatTime(paper.created_at) }}</div>
        </div>
        <el-popconfirm title="确定删除这篇论文？" confirm-button-text="删除" cancel-button-text="取消" @confirm="$emit('delete', paper)" @click.stop>
          <template #reference>
            <el-button class="delete-btn" size="small" text @click.stop><el-icon :size="14"><Delete /></el-icon></el-button>
          </template>
        </el-popconfirm>
    </div>

    <el-dialog v-model="uploadVisible" title="上传论文" width="480px" destroy-on-close :close-on-click-modal="false">
    
      <el-form label-width="80px">
        <el-form-item label="目标文件夹">
          <el-tree-select v-model="uploadFolderId" :data="folderTreeData" :props="{ label: 'name', value: 'id', children: 'children' }" placeholder="未分类" clearable check-strictly style="width:100%" />
        </el-form-item>
        <el-form-item label="论文标题">
          <el-input v-model="uploadTitle" placeholder="可选，留空使用文件名" />
        </el-form-item>
        <el-form-item label="PDF 文件">
          <el-upload :auto-upload="false" :limit="1" :on-change="(f) => pdfFile = f.raw" accept=".pdf" drag>
            <div class="upload-placeholder">
              <el-icon class="upload-icon"><UploadFilled /></el-icon>
              <div class="upload-text">拖拽或点击上传 PDF</div>
              <div class="upload-hint">用于原文预览</div>
            </div>
          </el-upload>
        </el-form-item>
        <el-form-item label="MD 文件">
          <el-upload :auto-upload="false" :limit="1" :on-change="(f) => mdFile = f.raw" accept=".md" drag>
            <div class="upload-placeholder">
              <el-icon class="upload-icon"><UploadFilled /></el-icon>
              <div class="upload-text">拖拽或点击上传 MD</div>
              <div class="upload-hint">MinerU 解析后的 Markdown 文件</div>
            </div>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirm" :disabled="!pdfFile">确认上传</el-button>
      </template>
    </el-dialog>
  </div></div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from "vue";
import { ElMessage } from "element-plus";
import { Upload, UploadFilled, Setting, Delete, Search, Plus, Check, Close, Folder } from "@element-plus/icons-vue";
import FolderTreeItem from "./FolderTreeItem.vue";
import { getFolders, createFolder, renameFolder, deleteFolder, getTags, createTag, deleteTag, movePaper } from "../../api/papers";

const props = defineProps({ papers: Array, loading: Boolean, currentId: Number });
const emit = defineEmits(["select", "delete", "upload", "search", "open-settings"]);

// folders
const folders = ref([]);
const activeFolderId = ref('__uncat__');
const showAddInput = ref(false);
const editingFolderId = ref(null);
const editingName = ref('');
const addParentId = ref(null);
const addingName = ref("");
const uncatCount = ref(0);
const folderTreeData = computed(() => [{ id: null, name: "未分类", children: [] }, ...folders.value]);
async function loadFolders() { try { const r = await getFolders(); folders.value = r.data.folders || []; uncatCount.value = r.data.uncategorized_count || 0; } catch {} }
function selectFolder(id) { const next = activeFolderId.value === id ? null : id; activeFolderId.value = next; localStorage.setItem("lastFolderId", next || "__uncat__"); activeTag.value = ""; emitSearch(); }
function startAddFolder(pid) { addParentId.value = pid; addingName.value = ""; showAddInput.value = true; nextTick(() => { const el = document.querySelector(".folder-input-row input"); if (el) el.focus(); }); }
async function confirmAddFolder() {
  const n = addingName.value.trim(); if (!n) { cancelAddFolder(); return; }
  try { await createFolder(n, addParentId.value); showAddInput.value = false; addParentId.value = null; await loadFolders(); ElMessage.success("文件夹已创建"); } catch (e) { ElMessage.error("创建失败"); }
}
function cancelAddFolder() { showAddInput.value = false; addParentId.value = null; addingName.value = ''; }
function startEditFolder(f) { editingFolderId.value = f.id; editingName.value = f.name; }
async function confirmEditFolder() { const n = editingName.value.trim(); if (!n) { cancelEditFolder(); return; } try { await renameFolder(editingFolderId.value, n); editingFolderId.value = null; await loadFolders(); } catch {} }
function cancelEditFolder() { editingFolderId.value = null; editingName.value = ''; }
async function handleDeleteFolder(id) { try { await deleteFolder(id); if (activeFolderId.value === id) activeFolderId.value = null; await loadFolders(); emitSearch(); ElMessage.success('文件夹已删除'); } catch {} }

// drag-drop
const dragPaperId = ref(null);
const dropTargetId = ref(null);
function onDragStart(paper) { dragPaperId.value = paper.id; }
function onDragEnd() { dragPaperId.value = null; dropTargetId.value = null; }
function onDragOver(id) { dropTargetId.value = id; }
function onDragLeave() { dropTargetId.value = null; }
async function onDrop(folderId) {
  dropTargetId.value = null;
  if (!dragPaperId.value) return;
  const pid = dragPaperId.value;
  const target = folderId === "__uncat__" ? null : folderId;
  try { await movePaper(pid, target); dragPaperId.value = null; emitSearch(); await loadFolders(); ElMessage.success("已移动"); } catch { ElMessage.error("移动失败"); }
}

// tags
const tags = ref([]);
const activeTag = ref("");
const addingTag = ref(false);
const newTagName = ref("");
const tagInputRef = ref(null);
async function loadTags() { try { const r = await getTags(); tags.value = r.data || []; } catch {} }
function selectTag(name) { activeTag.value = activeTag.value === name ? "" : name; activeFolderId.value = null; emitSearch(); }
function startAddTag() { addingTag.value = true; newTagName.value = ""; nextTick(() => tagInputRef.value?.focus()); }
async function confirmAddTag() { const n = newTagName.value.trim(); if (!n) { cancelAddTag(); return; } try { await createTag(n); addingTag.value = false; await loadTags(); } catch {} }
function cancelAddTag() { addingTag.value = false; newTagName.value = ""; }
async function handleDeleteTag(id) { try { await deleteTag(id); if (activeTag.value) { const d = tags.value.find(t => t.id === id); if (d && d.name === activeTag.value) activeTag.value = ""; emitSearch(); } await loadTags(); } catch {} }

// search
const keyword = ref("");
let timer = null;
function debouncedSearch() { clearTimeout(timer); timer = setTimeout(emitSearch, 300); }
function emitSearch() { emit("search", { keyword: keyword.value, folder_id: activeFolderId.value === "__uncat__" ? -1 : activeFolderId.value, tag: activeTag.value }); }

// upload
const uploadVisible = ref(false);
const uploadTitle = ref("");
const uploadFolderId = ref(null);
const pdfFile = ref(null);
const mdFile = ref(null);
function handleConfirm() { emit("upload", { title: uploadTitle.value, pdfFile: pdfFile.value, mdFile: mdFile.value, folderId: uploadFolderId.value }); uploadVisible.value = false; uploadTitle.value = ""; uploadFolderId.value = null; pdfFile.value = null; mdFile.value = null; }
function formatTime(t) { if (!t) return ""; return new Date(t).toLocaleDateString("zh-CN"); }

defineExpose({ loadTags });
onMounted(async () => { await loadFolders(); await loadTags(); const saved = localStorage.getItem('lastFolderId'); if (saved) { activeFolderId.value = saved; } else { activeFolderId.value = '__uncat__'; } emitSearch(); });
</script>

<style scoped>
.library { display: flex; flex-direction: column; height: 100%; }
.library-header { display: flex; justify-content: space-between; align-items: center; padding: var(--space-lg) var(--space-lg) var(--space-md); }
.library-header h3 { font-size: var(--font-size-md); font-weight: 600; color: var(--text-primary); }
.header-actions { display: flex; align-items: center; gap: var(--space-xs); }
.library-search { padding: 0 var(--space-lg) var(--space-md); }
.search-input :deep(.el-input__wrapper) { border-radius: var(--radius-full) !important; background: var(--bg-primary); border: none; padding: 1px 12px; }
.search-input :deep(.el-input__inner) { font-size: var(--font-size-sm); }
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
.paper-item { display: flex; align-items: center; gap: var(--space-md); padding: var(--space-md) var(--space-md); margin: 2px 0; border-radius: var(--radius-md); cursor: pointer; transition: all var(--transition-fast); user-select: none; }
.paper-item:hover { background: var(--bg-hover); transform: translateX(2px); }
.paper-item.active { background: var(--accent-light); }
.paper-item.active .paper-icon { background: var(--accent); color: #fff; }
.paper-item.dragging { opacity: 0.4; }
.paper-icon { width: 36px; height: 36px; border-radius: var(--radius-sm); background: linear-gradient(135deg, #eef0ff, #e8eaff); color: var(--accent); display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 600; flex-shrink: 0; transition: all var(--transition-fast); }
.paper-item:hover .paper-icon { transform: scale(1.05); }
.paper-info { flex: 1; min-width: 0; }
.paper-title { font-size: var(--font-size-sm); font-weight: 500; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.4; }
.paper-meta { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; }
.delete-btn { opacity: 0; transition: all var(--transition-fast); color: var(--text-tertiary) !important; }
.paper-item:hover .delete-btn { opacity: 1; }
.delete-btn:hover { color: #ef4444 !important; background: rgba(239,68,68,0.06) !important; }

.list-empty { display: flex; flex-direction: column; align-items: center; padding: 40px 20px; text-align: center; }
.list-empty .empty-icon { font-size: 32px; margin-bottom: var(--space-md); opacity: 0.6; }
.list-empty .empty-text { font-size: var(--font-size-sm); color: var(--text-secondary); }

.upload-placeholder { padding: var(--space-lg) 0; text-align: center; }
.upload-icon { font-size: 28px; color: var(--text-tertiary); margin-bottom: var(--space-sm); }
.upload-text { font-size: var(--font-size-sm); color: var(--text-secondary); margin-bottom: var(--space-xs); }
.upload-hint { font-size: 11px; color: var(--text-tertiary); }
</style>
