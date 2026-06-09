import http from "./index";

export function getSettings() {
  return http.get("/settings");
}

export function updateSettings(settings) {
  return http.put("/settings", { settings });
}
