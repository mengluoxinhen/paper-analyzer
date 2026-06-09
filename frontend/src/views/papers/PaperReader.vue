<template>
  <div class="reader-pane">
    <div class="pane-toolbar">
      <h3 class="pane-title">📄 原文</h3>
    </div>
    <div class="tag-bar" v-if="paper">
      <span v-for="t in paperTags" :key="t.id" class="tag-chip">
        #{{ t.name }}
        <el-icon class="tag-chip-close" :size="10" @click.stop="removeTag(t.id)"><Close /></el-icon>
      </span>
      <el-popover placement="bottom-start" :width="200" trigger="click">
        <template #reference>
          <el-button size="small" text circle class="tag-add-btn">
            <el-icon :size="12"><Plus /></el-icon>
          </el-button>
        </template>
        <div class="tag-popover">
          <div class="tag-popover-search">
            <el-input v-model="tagSearch" placeholder="搜索或创建标签" size="small" @keydown.enter="addTag" />
          </div>
          <div class="tag-popover-list">
            <div v-for="tag in availableTags" :key="tag.id" class="tag-option" :class="{ selected: paperTags.some(pt => pt.id === tag.id) }" @click="toggleTag(tag)">
              #{{ tag.name }}
              <el-icon v-if="paperTags.some(pt => pt.id === tag.id)" :size="12"><Check /></el-icon>
            </div>
            <div v-if="tagSearch && !availableTags.some(t => t.name === tagSearch)" class="tag-option new" @click="createAndAdd(tagSearch)">
              + 创建 "#{{ tagSearch }}"
            </div>
          </div>
        </div>
      </el-popover>
    </div>
        <div class="pane-body">
      <div v-if="paper.pdf_path" class="pdf-container">
        <iframe :src="'/api/papers/' + paper.id + '/pdf'" class="pdf-iframe" frameborder="0"></iframe>
      </div>
      <div v-else class="no-pdf">
        <div class="no-pdf-icon">📄</div>
        <p>无法显示原文预览</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { Plus, Close, Check, Folder, FolderOpened } from "@element-plus/icons-vue";

import { getTags, createTag, setPaperTags } from "../../api/papers";



const props = defineProps({ paper: Object });
const emit = defineEmits(["tagCreated"]);



// tags
const paperTags = ref([]);
const allTags = ref([]);
const tagSearch = ref("");
const availableTags = computed(() => {
  if (!tagSearch.value) return allTags.value;
  return allTags.value.filter(t => t.name.includes(tagSearch.value));
});

watch(() => props.paper, (p) => { paperTags.value = p ? (p.tags || []) : []; }, { immediate: true });

async function loadAllTags() { try { const r = await getTags(); allTags.value = r.data || []; } catch {} }
async function toggleTag(tag) {
  const has = paperTags.value.some(t => t.id === tag.id);
  const ids = has ? paperTags.value.filter(t => t.id !== tag.id).map(t => t.id) : [...paperTags.value.map(t => t.id), tag.id];
  await setPaperTags(props.paper.id, ids);
  paperTags.value = has ? paperTags.value.filter(t => t.id !== tag.id) : [...paperTags.value, tag];
}
async function removeTag(tagId) {
  const ids = paperTags.value.filter(t => t.id !== tagId).map(t => t.id);
  await setPaperTags(props.paper.id, ids);
  paperTags.value = paperTags.value.filter(t => t.id !== tagId);
}
async function addTag() {
  const name = tagSearch.value.trim(); if (!name) return;
  let tag = allTags.value.find(t => t.name === name);
  if (!tag) { try { const r = await createTag(name); tag = r.data; allTags.value.push(tag); emit('tagCreated'); } catch { return; } }
  await toggleTag(tag); tagSearch.value = "";
}
function createAndAdd(name) { tagSearch.value = name; addTag(); }

loadAllTags();
</script>

<style scoped>
.reader-pane { display: flex; flex-direction: column; height: 100%; width: 100%; align-self: stretch; overflow: hidden; }
.pane-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: var(--space-lg) var(--space-xl); flex-shrink: 0;
  border-bottom: 1px solid var(--border-light);
}
.pane-title { font-size: var(--font-size-md); font-weight: 600; color: var(--text-primary); }
.pane-body { flex: 1; overflow: hidden; padding: 0; position: relative; }

.tag-bar { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; padding: 6px var(--space-xl); border-bottom: 1px solid var(--border-light); flex-shrink: 0; }
.tag-chip { display: inline-flex; align-items: center; gap: 2px; font-size: 11px; color: var(--accent); background: var(--accent-light); padding: 1px 8px; border-radius: var(--radius-full); }
.tag-chip-close { cursor: pointer; opacity: 0.5; }
.tag-chip-close:hover { opacity: 1; }
.tag-add-btn { color: var(--text-tertiary) !important; }
.tag-popover-search { margin-bottom: 8px; }
.tag-popover-list { max-height: 160px; overflow-y: auto; }
.tag-option { display: flex; align-items: center; justify-content: space-between; padding: 4px 8px; font-size: 12px; cursor: pointer; border-radius: var(--radius-sm); }
.tag-option:hover { background: var(--bg-hover); }
.tag-option.selected { color: var(--accent); }
.tag-option.new { color: var(--accent); font-weight: 500; }

:deep(.markdown-body) { font-size: var(--font-size-md); line-height: 1.85; color: var(--text-primary); max-width: 100%; }
:deep(.markdown-body h1) { font-size: 1.6em; font-weight: 700; margin: 1.5em 0 0.6em; padding-bottom: 0.3em; border-bottom: 1px solid var(--border-light); }
:deep(.markdown-body h2) { font-size: 1.35em; font-weight: 600; margin: 1.3em 0 0.5em; }
:deep(.markdown-body h3) { font-size: 1.15em; font-weight: 600; margin: 1.1em 0 0.4em; }
:deep(.markdown-body p) { margin: 0.8em 0; }
:deep(.markdown-body pre) { background: #f6f8fa; padding: var(--space-lg); border-radius: var(--radius-md); overflow-x: auto; font-size: 13px; line-height: 1.6; border: 1px solid var(--border-light); }
:deep(.markdown-body code) { font-family: var(--font-mono); background: #f0f0f3; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
:deep(.markdown-body pre code) { background: none; padding: 0; }
:deep(.markdown-body table) { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: var(--font-size-sm); }
:deep(.markdown-body th), :deep(.markdown-body td) { border: 1px solid var(--border-light); padding: 8px 12px; text-align: left; }
:deep(.markdown-body th) { background: var(--bg-hover); font-weight: 600; }
:deep(.markdown-body img) { max-width: 100%; border-radius: var(--radius-md); }
:deep(.markdown-body blockquote) { border-left: 3px solid var(--accent); padding: var(--space-sm) var(--space-md); margin: 1em 0; color: var(--text-secondary); background: var(--bg-hover); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; }
:deep(.markdown-body a) { color: var(--text-link); text-decoration: none; }
:deep(.markdown-body a:hover) { text-decoration: underline; }
:deep(.markdown-body ul), :deep(.markdown-body ol) { padding-left: 1.5em; }
:deep(.markdown-body li) { margin: 0.3em 0; }
.pdf-container { position: absolute; top: 0; left: 0; right: 0; bottom: 0; }
.pdf-iframe { width: 100%; height: 100%; border: none; display: block; }
.no-pdf { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-tertiary); padding: var(--space-xl); }
.no-pdf-icon { font-size: 64px; margin-bottom: var(--space-lg); opacity: 0.5; }
</style>
