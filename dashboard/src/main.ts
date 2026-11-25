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

const main = document.getElementById("main")!;
const navHost = document.getElementById("nav-host")!;
void renderStory(main, navHost);
window.addEventListener("hashchange", scrollToHash);
