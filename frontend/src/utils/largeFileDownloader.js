/**
 * 大文件分片下载工具
 *
 * 核心思路：
 * 1. 使用 HTTP Range 请求每次拉取一个切片（默认 100MB）
 * 2. 通过 File System Access API 将每个切片直接写入磁盘的指定偏移位置
 * 3. 任意时刻内存中只保留当前正在下载的那一个切片，下载完毕立即释放
 * 4. 最终得到一个完整的单文件，而不是多个分散的文件
 *
 * 前置条件：后端必须支持 Range 请求（返回 206 + Content-Range）
 */

const DEFAULT_CHUNK_SIZE = 100 * 1024 * 1024; // 100MB

/**
 * @typedef {Object} DownloadOptions
 * @property {string} url               - 下载地址
 * @property {number} [totalSize]       - 文件总大小（字节），不传则先发 HEAD 请求获取
 * @property {number} [chunkSize]       - 每个切片大小，默认 100MB
 * @property {string} [suggestedName]   - 保存对话框的建议文件名
 * @property {number} [maxRetries]      - 单个切片失败时的最大重试次数，默认 2
 * @property {number} [retryDelay]      - 重试间隔（ms），默认 1000
 * @property {AbortSignal} [signal]     - 外部取消信号
 * @property {function} [onProgress]    - 进度回调 ({ downloaded, total, percent })
 * @property {function} [onChunk]       - 每个切片完成回调 ({ index, totalChunks, size })
 * @property {function} [onStart]       - 开始回调 ({ totalSize, totalChunks })
 */

/**
 * 从 Content-Range 响应头解析文件总大小
 * 格式: "bytes 0-104857599/10737418240"
 */
function parseTotalSize(contentRange) {
  if (!contentRange) return null;
  const match = contentRange.match(/bytes \d+-\d+\/(\d+)/);
  return match ? parseInt(match[1], 10) : null;
}

/**
 * 通过 HEAD 请求获取文件元信息
 */
async function fetchFileInfo(url, signal) {
  const resp = await fetch(url, { method: "HEAD", signal });
  if (!resp.ok) throw new Error(`HEAD request failed: ${resp.status}`);

  const contentLength = resp.headers.get("content-length");
  const acceptRanges = resp.headers.get("accept-ranges");

  if (!acceptRanges || acceptRanges.toLowerCase() !== "bytes") {
    throw new Error("Server does not support Range requests (Accept-Ranges: bytes)");
  }

  return {
    totalSize: contentLength ? parseInt(contentLength, 10) : null,
  };
}

/**
 * 下载单个切片，支持重试
 */
async function fetchChunk(url, start, end, signal, maxRetries = 2, retryDelay = 1000) {
  let lastError = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const resp = await fetch(url, {
        headers: { Range: `bytes=${start}-${end}` },
        signal,
      });

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status} for range ${start}-${end}`);
      }

      const arrayBuffer = await resp.arrayBuffer();
      return arrayBuffer;
    } catch (err) {
      lastError = err;
      if (attempt < maxRetries && !signal?.aborted) {
        console.warn(
          `Chunk ${start}-${end} failed (attempt ${attempt + 1}), retrying in ${retryDelay}ms...`
        );
        await new Promise((resolve) => setTimeout(resolve, retryDelay));
      }
    }
  }

  throw lastError || new Error(`Failed to download chunk ${start}-${end}`);
}

/**
 * 发起大文件下载。会弹出系统保存对话框，用户选择保存路径后开始分片下载。
 *
 * @param {DownloadOptions} options
 * @returns {Promise<{success: boolean, filePath?: string, totalSize: number, reason?: string}>}
 *
 * 使用示例：
 *   import { downloadLargeFile } from "@/utils/largeFileDownloader.js";
 *
 *   const controller = new AbortController();
 *
 *   downloadLargeFile({
 *     url: "/api/files/big-model.bin",
 *     chunkSize: 100 * 1024 * 1024,   // 100MB
 *     suggestedName: "model.bin",
 *     signal: controller.signal,
 *     onProgress: ({ percent, downloaded, total }) => {
 *       console.log(`${percent}% (${downloaded}/${total})`);
 *     },
 *   }).then((result) => {
 *     if (result.success) {
 *       console.log("下载完成:", result.filePath);
 *     }
 *   });
 *
 *   // 取消下载
 *   // controller.abort();
 */
export async function downloadLargeFile(options) {
  const {
    url,
    totalSize: _totalSize,
    chunkSize = DEFAULT_CHUNK_SIZE,
    suggestedName = "download.bin",
    maxRetries = 2,
    retryDelay = 1000,
    signal,
    onProgress,
    onChunk,
    onStart,
  } = options;

  // ---------- Step 1: 获取文件信息 ----------
  let totalSize = _totalSize;

  if (!totalSize) {
    const info = await fetchFileInfo(url, signal);
    totalSize = info.totalSize;
    if (!totalSize) {
      throw new Error("Unable to determine file size. Please pass totalSize explicitly.");
    }
  }

  const totalChunks = Math.ceil(totalSize / chunkSize);

  if (onStart) {
    onStart({ totalSize, totalChunks, chunkSize });
  }

  // ---------- Step 2: 打开保存对话框 ----------
  if (!window.showSaveFilePicker) {
    throw new Error(
      "Your browser does not support the File System Access API. " +
        "Please use Chrome 86+, Edge 86+, or Opera 72+."
    );
  }

  /** @type {FileSystemFileHandle} */
  let fileHandle;
  try {
    fileHandle = await window.showSaveFilePicker({
      suggestedName,
      types: [
        {
          description: "All Files",
          accept: { "application/octet-stream": ["*"] },
        },
      ],
    });
  } catch (err) {
    // 用户取消了保存对话框
    if (err.name === "AbortError" || err.name === "DOMException") {
      return { success: false, reason: "user-cancelled", totalSize };
    }
    throw err;
  }

  /** @type {FileSystemWritableFileStream} */
  let writable;
  try {
    writable = await fileHandle.createWritable({ keepExistingData: false });
  } catch (err) {
    throw new Error(`Failed to create writable file: ${err.message}`);
  }

  // ---------- Step 3: 逐片下载并写入 ----------
  let downloaded = 0;

  try {
    for (let i = 0; i < totalChunks; i++) {
      if (signal?.aborted) {
        throw new DOMException("Download aborted by user", "AbortError");
      }

      const start = i * chunkSize;
      // 最后一片可能不足 chunkSize
      const end = Math.min(start + chunkSize, totalSize) - 1;

      // 下载当前切片（内存中只有这一片）
      const arrayBuffer = await fetchChunk(url, start, end, signal, maxRetries, retryDelay);

      // 写入磁盘指定位置
      await writable.write({ type: "write", position: start, data: arrayBuffer });

      downloaded += arrayBuffer.byteLength;

      if (onChunk) {
        onChunk({ index: i, totalChunks, size: arrayBuffer.byteLength });
      }

      if (onProgress) {
        onProgress({
          downloaded,
          total: totalSize,
          percent: Math.round((downloaded / totalSize) * 10000) / 100,
        });
      }
    }

    // 关闭写入流
    await writable.close();

    return {
      success: true,
      filePath: fileHandle.name,
      totalSize,
    };
  } catch (err) {
    // 确保关闭流（丢弃未完成的文件）
    try {
      await writable.abort();
    } catch (_) {
      // ignore
    }

    if (err.name === "AbortError") {
      return { success: false, reason: "aborted", totalSize };
    }

    throw err;
  }
}

export default downloadLargeFile;
