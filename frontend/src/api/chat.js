import http from "./index.js";

export function getChatSessions(paperId, kbId) {
  const params = {};
  if (paperId != null) params.paper_id = paperId;
  if (kbId != null) params.kb_id = kbId;
  return http.get("/chat/sessions", { params });
}

export function createChatSession(title, paperId, kbId) {
  return http.post("/chat/sessions", { title: title || "", paper_id: paperId || null, kb_id: kbId || null });
}

export function renameChatSession(sessionId, title) {
  return http.put("/chat/sessions/" + sessionId, { title });
}

export function deleteChatSession(sessionId) {
  return http.delete("/chat/sessions/" + sessionId);
}

export function getChatMessages(sessionId) {
  return http.get("/chat/sessions/" + sessionId + "/messages");
}

export function sendChatMessage(sessionId, message, onToken, onDone, onError) {
  return fetch("/api/chat/sessions/" + sessionId + "/send", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  }).then(async (response) => {
    if (!response.ok) { const err = await response.text(); throw new Error(err); }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") { onDone(); return; }
          if (data.startsWith("__ERROR__")) { onError(data.slice(9)); return; }
          onToken(data);
        }
      }
    }
  });
}
