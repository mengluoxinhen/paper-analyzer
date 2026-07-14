import http from "./index.js";

export function uploadPaper(title, pdfFile, folderId, kbId) {
  const form = new FormData();
  if (pdfFile) form.append("pdf_file", pdfFile);
  let url = "/papers/upload?title=" + encodeURIComponent(title) + "&kb_id=" + encodeURIComponent(kbId);
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
  return http.put("/papers/" + id + "/move", { folder_id: folderId });
}

export function setPaperTags(id, tagIds) {
  return http.put("/papers/" + id + "/tags", { tag_ids: tagIds });
}

export function getSummary(paperId) {
  return http.get("/papers/" + paperId + "/summary");
}

export function getExtractions(paperId) {
  return http.get("/papers/" + paperId + "/extractions");
}

export function getFolders(kbId) {
  return http.get("/folders", { params: { kb_id: kbId } });
}

export function createFolder(name, parentId, kbId) {
  return http.post("/folders", { name, parent_id: parentId || null, knowledge_base_id: kbId });
}

export function renameFolder(id, name) {
  return http.put("/folders/" + id, { name });
}

export function deleteFolder(id) {
  return http.delete("/folders/" + id);
}

export function getTags(kbId) {
  return http.get("/tags", { params: { kb_id: kbId } });
}

export function createTag(name, kbId) {
  return http.post("/tags", { name, knowledge_base_id: kbId });
}

export function deleteTag(id) {
  return http.delete("/tags/" + id);
}
