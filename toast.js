const listeners = new Set();

export function toast(message, type = "info") {
  listeners.forEach(l => l({ id: Date.now() + Math.random(), message, type }));
}
export function onToast(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}