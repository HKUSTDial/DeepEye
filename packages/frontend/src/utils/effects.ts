export function deferEffectWork(work: () => void) {
  const timeoutId: ReturnType<typeof globalThis.setTimeout> = globalThis.setTimeout(work, 0)
  return () => globalThis.clearTimeout(timeoutId)
}
