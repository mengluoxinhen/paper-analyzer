<template>
  <el-dialog v-model="visible" title="LLM 设置" width="500px" destroy-on-close>
    <el-form label-width="120px">
      <el-form-item label="API Base URL">
        <el-input v-model="form.api_base" placeholder="https://api.deepseek.com" />
      </el-form-item>
      <el-form-item label="API Key">
        <el-input v-model="form.api_key" type="password" show-password placeholder="sk-..." />
      </el-form-item>
      <el-form-item label="模型名称">
        <el-input v-model="form.model" placeholder="deepseek-chat" />
      </el-form-item>
      <el-form-item label="Max Tokens">
        <el-input-number v-model="form.max_tokens" :min="256" :max="32768" :step="256" />
      </el-form-item>
      <el-form-item label="Temperature">
        <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" show-input />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch } from "vue";
import { ElMessage } from "element-plus";
import { useSettingsStore } from "../../stores/settings";

const store = useSettingsStore();
const visible = defineModel("visible", { default: false });
const saving = ref(false);

const form = reactive({
  api_base: "",
  api_key: "",
  model: "",
  max_tokens: 4096,
  temperature: 0.7,
});

watch(visible, async (val) => {
  if (val) {
    await store.fetch();
    form.api_base = store.items.llm_api_base || "";
    form.api_key = store.items.llm_api_key || "";
    form.model = store.items.llm_model || "";
    form.max_tokens = Number(store.items.llm_max_tokens) || 4096;
    form.temperature = Number(store.items.llm_temperature) || 0.7;
  }
});

async function handleSave() {
  saving.value = true;
  try {
    await store.save({
      llm_api_base: form.api_base,
      llm_api_key: form.api_key,
      llm_model: form.model,
      llm_max_tokens: String(form.max_tokens),
      llm_temperature: String(form.temperature),
    });
    ElMessage.success("设置已保存");
    visible.value = false;
  } catch {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
}
</script>
