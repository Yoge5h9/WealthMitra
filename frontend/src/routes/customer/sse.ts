/**
 * Minimal SSE-over-fetch reader for `POST /api/chat`. TanStack
 * Query has no story for a streaming body (see queries.ts's
 * `sendChatMessage` docstring), so this reads the `ReadableStream` directly:
 * buffer bytes, split on blank-line-delimited `data: {...}` events, decode
 * each as one `ChatSseFrame`. Malformed frames are dropped, never thrown —
 * one bad chunk must not kill an otherwise-good stream.
 */
import type { ChatSseFrame } from "./types";

export async function readSseFrames(
  response: Response,
  onFrame: (frame: ChatSseFrame) => void
): Promise<void> {
  if (!response.body) return;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let separatorIndex: number;
    // eslint-disable-next-line no-cond-assign
    while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);
      const dataLine = rawEvent
        .split("\n")
        .find((line) => line.startsWith("data:"));
      if (!dataLine) continue;
      const payload = dataLine.slice(5).trim();
      if (!payload) continue;
      try {
        onFrame(JSON.parse(payload) as ChatSseFrame);
      } catch {
        // Malformed frame — skip it, the stream continues.
      }
    }
  }
}
