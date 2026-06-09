import { ref, readonly } from "vue";
import { downloadLargeFile } from "@/utils/largeFileDownloader.js";

/**
 * Vue 3 组合式函数 —— 将大文件下载封装为响应式状态
 *
 * 用法：
 *   const { downloading, progress, error, startDownload, cancel } = useLargeFileDownload();
 *   await startDownload({ url: "/api/download/bigfile.bin", suggestedName: "data.bin" });
 */
export function useLargeFileDownload() {
  const downloading = ref(false);
  const progress = ref(0);        // 0-100
  const downloaded = ref(0);      // bytes
  const totalSize = ref(0);
  const chunkIndex = ref(0);
  const totalChunks = ref(0);
  const error = ref(null);

  let controller = null;

  async function startDownload(options = {}) {
    if (downloading.value) return;

    downloading.value = true;
    error.value = null;
    progress.value = 0;
    downloaded.value = 0;
    chunkIndex.value = 0;

    controller = new AbortController();

    try {
      const result = await downloadLargeFile({
        ...options,
        signal: controller.signal,
        onStart: ({ totalSize: ts, totalChunks: tc }) => {
          totalSize.value = ts;
          totalChunks.value = tc;
        },
        onProgress: ({ downloaded: d, total: t, percent }) => {
          downloaded.value = d;
          totalSize.value = t;
          progress.value = percent;
        },
        onChunk: ({ index }) => {
          chunkIndex.value = index;
        },
      });

      if (!result.success) {
        error.value = result.reason || "Download failed";
      }

      return result;
    } catch (err) {
      if (err.name !== "AbortError") {
        error.value = err.message;
      }
      throw err;
    } finally {
      downloading.value = false;
      controller = null;
    }
  }

  function cancel() {
    if (controller) {
      controller.abort();
    }
  }

  return {
    downloading: readonly(downloading),
    progress: readonly(progress),
    downloaded: readonly(downloaded),
    totalSize: readonly(totalSize),
    chunkIndex: readonly(chunkIndex),
    totalChunks: readonly(totalChunks),
    error: readonly(error),
    startDownload,
    cancel,
  };
}

export default useLargeFileDownload;
