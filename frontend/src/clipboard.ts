// ── Copy store ────────────────────────────────────────────────────────────────
// Clipboard text is keyed by int so copy-btns only need a small data attribute.

const _store = new Map<number, string>();
let _seq = 0;

export function reg(text: string): number {
  const k = ++_seq;
  _store.set(k, text);
  return k;
}

document
  .getElementById("panel-body")!
  .addEventListener("click", (e: MouseEvent) => {
    const btn = (e.target as Element).closest<HTMLElement>(".copy-btn");
    if (btn) {
      const ckStr = btn.dataset["ck"];
      const text = _store.get(+(ckStr ?? "0")) ?? "";
      void navigator.clipboard.writeText(text).then(() => {
        btn.classList.add("ok");
        const orig = btn.innerHTML;
        btn.innerHTML = "✓ Copiado";
        setTimeout(() => {
          btn.classList.remove("ok");
          btn.innerHTML = orig;
        }, 1500);
      });
    }
  });
