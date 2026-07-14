import { defineStore } from "pinia";
import { getKnowledgeBases, createKnowledgeBase, updateKnowledgeBase, deleteKnowledgeBase } from "../api/knowledgeBases";

export const useKnowledgeBaseStore = defineStore("knowledgeBase", {
  state: () => ({
    list: [],
    currentId: null,
    loading: false,
  }),

  getters: {
    current(state) {
      return state.list.find((kb) => kb.id === state.currentId) || null;
    },
    isShared(state) {
      const kb = state.list.find((kb) => kb.id === state.currentId);
      return kb ? kb.is_shared : false;
    },
    isAdmin() {
      return true;
    },
  },

  actions: {
    async fetchList() {
      this.loading = true;
      try {
        const res = await getKnowledgeBases();
        this.list = res.data;
        if (!this.currentId && this.list.length > 0) {
          this.currentId = this.list[0].id;
        }
      } finally {
        this.loading = false;
      }
    },

    select(kbId) {
      this.currentId = kbId;
      localStorage.setItem("selectedKbId", kbId);
    },

    restoreSelection() {
      const saved = localStorage.getItem("selectedKbId");
      if (saved && this.list.some((kb) => kb.id === saved)) {
        this.currentId = saved;
      } else if (this.list.length > 0) {
        this.currentId = this.list[0].id;
      }
    },

    async create(name, description) {
      const res = await createKnowledgeBase(name, description);
      this.list.push(res.data);
      if (!this.currentId) this.select(res.data.id);
      return res.data;
    },

    async update(id, data) {
      await updateKnowledgeBase(id, data);
      const kb = this.list.find((k) => k.id === id);
      if (kb) {
        if (data.name !== undefined) kb.name = data.name;
        if (data.description !== undefined) kb.description = data.description;
      }
    },

    async remove(id) {
      await deleteKnowledgeBase(id);
      this.list = this.list.filter((k) => k.id !== id);
      if (this.currentId === id) {
        this.currentId = this.list.length > 0 ? this.list[0].id : null;
        localStorage.removeItem("selectedKbId");
      }
    },
  },
});
