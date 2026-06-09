import { defineStore } from "pinia";
import { getSettings, updateSettings } from "../api/settings";

export const useSettingsStore = defineStore("settings", {
  state: () => ({
    items: {},
    loaded: false,
  }),

  actions: {
    async fetch() {
      try {
        const res = await getSettings();
        this.items = {};
        for (const s of res.data) {
          this.items[s.key] = s.value;
        }
        this.loaded = true;
      } catch {
        this.loaded = true;
      }
    },

    async save(changes) {
      const settings = Object.entries(changes).map(([key, value]) => ({
        key,
        value: String(value),
      }));
      const res = await updateSettings(settings);
      for (const s of res.data) {
        this.items[s.key] = s.value;
      }
    },
  },
});
