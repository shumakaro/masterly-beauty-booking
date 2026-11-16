import type { KeyboardEvent } from "react";
export function containDialogFocus(event: KeyboardEvent<HTMLDialogElement>) {
  if (event.key !== "Tab" || event.ctrlKey || event.altKey || event.metaKey)
    return;
  const dialog = event.currentTarget;
  const controls = Array.from(
    dialog.querySelectorAll<HTMLElement>(
      "button, a[href], input, select, textarea, [tabindex]",
    ),
  ).filter(
    (element) =>
      element.tabIndex >= 0 &&
      !element.matches(":disabled") &&
      element.getClientRects().length > 0,
  );
  const first = controls[0];
  const last = controls.at(-1);
  if (!first || !last) {
    event.preventDefault();
    dialog.focus();
    return;
  }
  if (
    (event.shiftKey && document.activeElement === first) ||
    (!event.shiftKey && document.activeElement === last) ||
    !dialog.contains(document.activeElement)
  ) {
    event.preventDefault();
    (event.shiftKey ? last : first).focus();
  }
}
