import http from "./index.js";

export function getKnowledgeBases(userId) {
  return http.get("/knowledge-bases", { params: { user_id: userId || "default_user" } });
}

export function createKnowledgeBase(name, description, userId) {
  return http.post("/knowledge-bases", { name, description: description || "" }, { params: { user_id: userId || "default_user" } });
}

export function updateKnowledgeBase(id, data) {
  return http.put("/knowledge-bases/" + id, data);
}

export function deleteKnowledgeBase(id) {
  return http.delete("/knowledge-bases/" + id);
}
