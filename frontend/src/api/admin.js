import http from "./index.js";

export function getPendingPapers(kbId) {
  return http.get("/admin/review", { params: { kb_id: kbId } });
}

export function approvePaper(paperId) {
  return http.post("/admin/review/" + paperId + "/approve");
}

export function rejectPaper(paperId, comment) {
  return http.post("/admin/review/" + paperId + "/reject", { comment });
}
