import { num } from "../data";
import { pp } from "../format";
import { preview } from "../ui";
import type { Page } from "./page";

// Numbers come from segments_facts (derived in scripts/build_dashboard_data.py).
export const segments: Page = {
  path: "/segments",
  nav: "Segments",
  title: "The cost depends more on what is shown than on who sees it",
  question: "Which content and which users absorb exploration best?",
  data: ["segments"],
  notes: [
    "Segments come from data before the test period only (Apr 8 to 21, 2022). Each segment is compared with the rest of its group, with a correction for testing many segments at once. Merged category groups are groupings made for sample size, with no topical meaning, and are not interpreted.",
  ],
  agreement(data) {
    return data.tables.segments_facts[0].effective_view_methods_agree_all === true
      ? "Bootstrap and regression agree on effective view in every segment"
      : null;
  },
  render(root, data) {
    const f = data.tables.segments_facts[0];
    const worst = String(f.worst_label).toLowerCase();
    const best = String(f.best_label).toLowerCase();
    root.append(
      preview(
        `Every segment pays a large cost, but the type of video matters most: random ${worst} videos cost the most and random ${best} videos the least. User groups differ by a few points.`,
        { value: `${pp(num(f, "worst_estimate"))} vs ${pp(num(f, "best_estimate"))}`, label: `Effective views, random ${worst} vs random ${best} videos` },
        "by Dec 2",
      ),
    );
  },
};
