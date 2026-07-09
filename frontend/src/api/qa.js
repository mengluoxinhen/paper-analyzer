import http from "./index.js";

export function rebuildIndex() {
  return http.post("/qa/rebuild");
}
