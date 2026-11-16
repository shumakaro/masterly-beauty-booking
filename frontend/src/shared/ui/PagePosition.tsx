import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

export function PagePosition() {
  const { pathname, search, hash } = useLocation();
  const params = new URLSearchParams(search);
  const section = [
    "tab",
    "page",
    "offers_page",
    "portfolio_page",
    "reviews_page",
  ]
    .map((key) => params.get(key) ?? "")
    .join(":");
  const previous = useRef({ pathname, section });
  useEffect(() => {
    const pathChanged = previous.current.pathname !== pathname;
    const sectionChanged = previous.current.section !== section;
    let needsFocus = pathChanged || sectionChanged;
    previous.current = { pathname, section };
    const synchronize = () => {
      const main = document.getElementById("main");
      if (!main) return;
      main.tabIndex = -1;
      const heading = main.querySelector("h1");
      const title = heading?.textContent?.replace(/\s+/g, " ").trim();
      document.title = title
        ? `${title.slice(0, 100)} — MASTERLY`
        : "MASTERLY · Красота в вашем ритме";
      if (!needsFocus || hash) return;
      const target =
        (sectionChanged && !pathChanged
          ? main.querySelector(".workspace-section h2, .catalog-count, h1")
          : heading) ?? main.querySelector("[role=alert]");
      if (target instanceof HTMLElement) {
        target.tabIndex = -1;
        target.focus({ preventScroll: true });
        needsFocus = false;
        if (pathChanged) window.scrollTo({ top: 0, behavior: "instant" });
        else target.scrollIntoView({ block: "start", behavior: "instant" });
      }
    };
    synchronize();
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView();
    const observer = new MutationObserver(synchronize);
    observer.observe(document.getElementById("root") ?? document.body, {
      childList: true,
      subtree: true,
    });
    return () => observer.disconnect();
  }, [pathname, section, hash]);
  return null;
}
