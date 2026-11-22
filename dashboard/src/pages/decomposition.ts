import { num } from "../data";
import { pp } from "../format";
import { preview } from "../ui";
import type { Page } from "./page";

// Numbers come from decomposition_facts (derived in scripts/build_dashboard_data.py).
export const decomposition: Page = {
  path: "/content-vs-targeting",
  nav: "Content vs targeting",
  title: "The same videos do well when they reach the right people",
  question: "Is a random slot costly because the videos are worse, or because they reach the wrong person?",
  data: ["decomposition"],
  notes: [
    "The gap between a user's recommended videos and that user's random videos splits into two parts. Content: how good the random pool's videos are. Targeting: whether they reach people who want them.",
  ],
  agreement(data) {
    return data.tables.decomposition_facts[0].effective_view_methods_agree === true
      ? "Bootstrap and regression agree on the effective-view split"
      : null;
  },
  render(root, data) {
    const f = data.tables.decomposition_facts[0];
    const gap = (c: string) => pp(num(f, c)).replace("+", "");
    root.append(
      preview(
        `Of the ${gap("total_gap")} effective-view gap between a user's recommended and random videos, ${gap("targeting_gap")} comes from targeting and only ${gap("content_gap")} from the videos themselves.`,
        { value: `${Math.round(num(f, "targeting_share") * 100)}%`, label: "of the effective-view gap is targeting" },
        "by Dec 2",
      ),
    );
  },
};
