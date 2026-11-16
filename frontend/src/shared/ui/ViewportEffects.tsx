import { useEffect } from "react";
export function ViewportEffects() {
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const reduce = matchMedia("(prefers-reduced-motion: reduce)");
    const seen = new WeakSet<Element>();
    const running = new Set<Animation>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries)
          if (entry.isIntersecting) {
            observer.unobserve(entry.target);
            if (reduce.matches || !(entry.target instanceof HTMLElement))
              continue;
            // Content remains visible before intersection and without JavaScript.
            const animation = entry.target.animate(
              [
                { opacity: 0.65, transform: "translateY(12px)" },
                { opacity: 1, transform: "translateY(0)" },
              ],
              { duration: 420, easing: "ease-out" },
            );
            running.add(animation);
            void animation.finished
              .catch(() => undefined)
              .finally(() => running.delete(animation));
          }
      },
      { threshold: 0.08 },
    );
    const scan = () => {
      document
        .querySelectorAll(".section-heading, .ritual, .profile-section")
        .forEach((element) => {
          if (!seen.has(element)) {
            seen.add(element);
            observer.observe(element);
          }
        });
    };
    const stopMotion = () => {
      if (reduce.matches) running.forEach((animation) => animation.cancel());
    };
    scan();
    const changes = new MutationObserver(scan);
    changes.observe(document.getElementById("root") ?? document.body, {
      childList: true,
      subtree: true,
    });
    reduce.addEventListener("change", stopMotion);
    return () => {
      observer.disconnect();
      changes.disconnect();
      reduce.removeEventListener("change", stopMotion);
      running.forEach((animation) => animation.cancel());
    };
  }, []);
  return null;
}
