import { defineStore } from "pinia";
import { getPapers, getPaper, deletePaper, getSummary } from "../api/papers";

export const usePapersStore = defineStore("papers", {
  state: () => ({
    list: [],
    total: 0,
    currentPaper: null,
    currentSummary: null,
    loading: false,
    kbId: null,
  }),

  actions: {
    setKbId(kbId) {
      this.kbId = kbId;
    },

    async fetchList(params = {}) {
      this.loading = true;
      try {
        if (this.kbId) params.kb_id = this.kbId;
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
  },
});
