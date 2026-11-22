import { num } from "../data";
import { preview } from "../ui";
import type { Page } from "./page";

// Numbers come from budget_facts (derived in scripts/build_dashboard_data.py).
export const budget: Page = {
  path: "/budget",
  nav: "Budget simulator",
  title: "Most segments can take the full 1.388%; dance videos cannot",
  question: "How much exploration can a segment take before a guardrail breaks?",
  data: ["budget"],
  notes: [
    "The simulator assumes a linear effect within the observed range of exploration shares (0.658% to 1.388% of feed impressions). Shares above 1.388% were never observed and need a new test.",
  ],
  render(root, data) {
    const f = data.tables.budget_facts[0];
    const clear = `${num(f, "n_no_guardrail_crossed")} of ${num(f, "n_segments")}`;
    root.append(
      preview(
        `${clear} segments cross no guardrail up to 1.388%. Dance videos cross the hate limit even at the lowest share in the data, 0.658%. Six more segments may cross it, but their intervals are too wide to say.`,
        { value: clear, label: "segments cross no guardrail up to 1.388%" },
        "by Nov 28",
      ),
    );
  },
};
