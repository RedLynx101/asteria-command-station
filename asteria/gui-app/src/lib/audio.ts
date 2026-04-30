import { AUDIO_MANIFEST } from "./constants";

const cache: Record<string, HTMLAudioElement> = {};
let initialized = false;

export function initAudio() {
  if (initialized) return;
  initialized = true;
  for (const [name, path] of Object.entries(AUDIO_MANIFEST)) {
    const el = new Audio(path);
    el.preload = "auto";
    cache[name] = el;
  }
}

export function playCue(name: string) {
  const el = cache[name];
  if (!el) return;
  el.currentTime = 0;
  el.play().catch(() => {});
}
