import http from "./index.js";

export function rebuildIndex(kbId) {
  return http.post("/qa/rebuild", null, { params: { kb_id: kbId } });
}
