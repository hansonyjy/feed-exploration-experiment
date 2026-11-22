import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./style.css";
import { PAGES } from "./pages";
import { renderPage } from "./pages/page";
import { el } from "./ui";

const nav = document.getElementById("nav")!;
const main = document.getElementById("main")!;

nav.append(el("ul", {}, ...PAGES.map((p) => el("li", {}, el("a", { href: `#${p.path}`, "data-path": p.path }, p.nav)))));

function route(): void {
  const path = location.hash.replace(/^#/, "") || "/";
  const page = PAGES.find((p) => p.path === path) ?? PAGES[0];
  for (const a of nav.querySelectorAll<HTMLAnchorElement>("a")) {
    if (a.dataset.path === page.path) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
  document.title = page.path === "/" ? "Feed Exploration Budget" : `${page.nav} · Feed Exploration Budget`;
  void renderPage(page, main);
  main.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}

window.addEventListener("hashchange", route);
route();
