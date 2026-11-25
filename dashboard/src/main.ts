import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource/fraunces/600.css";
import "./palettes.css";
import "./style.css";
import "./redesign.css";
import { renderStory, scrollToHash } from "./redesign";

// Prototype only: ?palette=harbor|graphite|sand previews a palette direction (removed after the pick).
const palette = new URLSearchParams(location.search).get("palette");
if (palette) document.documentElement.dataset.palette = palette;

const main = document.getElementById("main")!;
const navHost = document.getElementById("nav-host")!;
void renderStory(main, navHost);
window.addEventListener("hashchange", scrollToHash);
