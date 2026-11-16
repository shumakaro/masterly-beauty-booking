// Runs before styles/React to avoid a light flash for a saved dark preference.
(() => {
  let preference = "system";
  try {
    const stored = localStorage.getItem("masterly:theme");
    if (stored === "light" || stored === "dark") preference = stored;
  } catch {
    /* Theme still follows the device when storage is unavailable. */
  }
  const dark =
    preference === "dark" ||
    (preference === "system" &&
      matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
})();
