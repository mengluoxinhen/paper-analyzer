<template>
  <div>
    <div
      class="folder-row"
      :class="{ active: activeId === folder.id, 'drop-target': dropTargetId === folder.id }"
      :style="{ paddingLeft: (8 + depth * 16) + 'px' }"
      @click="$emit('select', folder.id)"
      @dragover.prevent="$emit('dragOver', folder.id)"
      @dragleave="$emit('dragLeave')"
      @drop="$emit('drop', folder.id)"
    >
      <span
        class="folder-arrow"
        :style="{ visibility: folder.children && folder.children.length > 0 ? 'visible' : 'hidden' }"
        @click.stop="expanded = !expanded"
      >{{ expanded ? '\u25BC' : '\u25B6' }}</span>

      <el-icon class="folder-icon" :size="14">
        <FolderOpened v-if="activeId === folder.id" />
        <Folder v-else />
      </el-icon>

      <div v-if="editingId === folder.id" class="folder-edit-row" @click.stop>
        <input
          class="folder-edit-input"
          :value="editingName"
          @input="$emit('updateEditingName', $event.target.value)"
          @keydown.enter="$emit('confirmEdit')"
          @keydown.escape="$emit('cancelEdit')"
        />
      </div>
      <span v-else class="folder-name">{{ folder.name }}</span>

      <span class="folder-count">{{ folder.paper_count }}</span>

      <span class="folder-actions" @click.stop>
        <el-button v-if="depth < 2" size="small" text @click="$emit('startAdd', folder.id)">
          <el-icon :size="12"><Plus /></el-icon>
        </el-button>
        <el-button size="small" text @click="$emit('startEdit', folder)">
          <el-icon :size="12"><Edit /></el-icon>
        </el-button>
        <el-popconfirm title="删除此文件夹及其所有内容？" confirm-button-text="删除" cancel-button-text="取消" @confirm="$emit('delete', folder.id)">
          <template #reference>
            <el-button class="folder-del-btn" size="small" text>
              <el-icon :size="12"><Delete /></el-icon>
            </el-button>
          </template>
        </el-popconfirm>
      </span>
    </div>

    <FolderTreeItem
      v-if="expanded"
      v-for="child in folder.children"
      :key="child.id"
      :folder="child"
      :depth="depth + 1"
      :activeId="activeId"
      :dropTargetId="dropTargetId"
      :editingId="editingId"
      :editingName="editingName"
      @select="(id) => $emit('select', id)"
      @dragOver="(id) => $emit('dragOver', id)"
      @dragLeave="$emit('dragLeave')"
      @drop="(id) => $emit('drop', id)"
      @startAdd="(id) => $emit('startAdd', id)"
      @startEdit="(f) => $emit('startEdit', f)"
      @updateEditingName="(v) => $emit('updateEditingName', v)"
      @confirmEdit="$emit('confirmEdit')"
      @cancelEdit="$emit('cancelEdit')"
      @delete="(id) => $emit('delete', id)"
    />
  </div>
</template>

<script setup>
import { ref } from "vue";
import { Folder, FolderOpened, Plus, Edit, Delete } from "@element-plus/icons-vue";

defineProps({
  folder: Object, depth: Number, activeId: [Number, String],
  dropTargetId: [Number, String], editingId: [Number, String], editingName: String,
});
defineEmits([
  "select", "dragOver", "dragLeave", "drop",
  "startAdd", "startEdit", "updateEditingName", "confirmEdit", "cancelEdit", "delete",
]);
const expanded = ref(true);
</script>

<style scoped>
.folder-row {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 8px; border-radius: var(--radius-sm);
  cursor: pointer; transition: all var(--transition-fast);
}
.folder-row:hover { background: var(--bg-hover); }
.folder-row.active { background: var(--accent-light); }
.folder-row.active .folder-icon { color: var(--accent); }
.folder-row.drop-target { outline: 2px solid var(--accent); outline-offset: -2px; background: var(--accent-light); }

.folder-arrow { width: 14px; font-size: 8px; color: var(--text-tertiary); flex-shrink: 0; text-align: center; cursor: pointer; }
.folder-arrow:hover { color: var(--text-primary); }
.folder-icon { font-size: 14px; color: var(--text-tertiary); flex-shrink: 0; }
.folder-name { font-size: var(--font-size-sm); color: var(--text-primary); flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.folder-count { font-size: 10px; color: var(--text-tertiary); background: var(--bg-hover); padding: 0 5px; border-radius: var(--radius-full); flex-shrink: 0; }

.folder-actions { display: none; align-items: center; gap: 0; }
.folder-row:hover .folder-actions { display: flex; }
.folder-actions :deep(.el-button) { padding: 2px !important; }
.folder-del-btn :deep(.el-icon):hover { color: #ef4444; }

.folder-edit-row { flex: 1; min-width: 0; }
.folder-edit-input {
  width: 100%; border: 1px solid var(--accent); outline: none;
  border-radius: var(--radius-sm); padding: 1px 6px;
  font-size: var(--font-size-sm); font-family: var(--font-sans); background: var(--bg-card);
}
</style>
