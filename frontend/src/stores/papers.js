import { defineStore } from "pinia";
import { getPapers, getPaper, deletePaper, getSummary, getConversations } from "../api/papers";

export const usePapersStore = defineStore("papers", {
  state: () => ({
    list: [],
    total: 0,
    currentPaper: null,
    currentSummary: null,
    conversations: [],
    loading: false,
  }),

  actions: {
    async fetchList(params = {}) {
      this.loading = true;
      try {
        const res = await getPapers(params);
        this.list = res.data.papers;
        this.total = res.data.total;
      } finally {
        this.loading = false;
      }
    },

    async fetchPaper(id) {
      const res = await getPaper(id);
      this.currentPaper = res.data;
      return res.data;
    },

    async removePaper(id) {
      await deletePaper(id);
      this.list = this.list.filter((p) => p.id !== id);
      if (this.currentPaper && this.currentPaper.id === id) {
        this.currentPaper = null;
        this.currentSummary = null;
        this.conversations = [];
      }
    },

    async fetchSummary(paperId) {
      try {
        const res = await getSummary(paperId);
        this.currentSummary = res.data;
      } catch {
        this.currentSummary = null;
      }
    },

    async fetchConversations(paperId) {
      const res = await getConversations(paperId);
      this.conversations = res.data || [];
    },
  },
});
