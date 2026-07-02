import http from "./index";

export function uploadPaper(title, pdfFile, folderId) {
  const form = new FormData();
  if (pdfFile) form.append("pdf_file", pdfFile);
  
  let url = "/papers/upload?title=" + encodeURIComponent(title);
  if (folderId != null) url += "&folder_id=" + folderId;
  return http.post(url, form);
}


export function getPapers(params) {
  return http.get("/papers", { params });
}

export function getPaper(id) {
  return http.get("/papers/" + id);
}

export function updatePaper(id, data) {
  return http.put("/papers/" + id, data);
}

export function deletePaper(id) {
  return http.delete("/papers/" + id);
}

export function movePaper(id, folderId) {
  return http.put('/papers/' + id + '/move', { folder_id: folderId });
}

export function setPaperTags(id, tagIds) {
  return http.put("/papers/" + id + "/tags", { tag_ids: tagIds });
}

export function getSummary(paperId) {
  return http.get("/papers/" + paperId + "/summary");
}

export function getConversations(paperId, limit) {
  return http.get("/papers/" + paperId + "/conversations", { params: { limit: limit || 50 } });
}

export function getExtractions(paperId) {
  return http.get("/papers/" + paperId + "/extractions");
}

// Folders
export function getFolders() {
  return http.get("/folders");
}

export function createFolder(name, parentId) {
  return http.post("/folders", { name, parent_id: parentId || null });
}

export function renameFolder(id, name) {
  return http.put("/folders/" + id, { name });
}

export function deleteFolder(id) {
  return http.delete("/folders/" + id);
}

// Tags
export function getTags() {
  return http.get("/tags");
}

export function createTag(name) {
  return http.post("/tags", { name });
}

export function deleteTag(id) {
  return http.delete("/tags/" + id);
}


