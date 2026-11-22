import { preview } from "../ui";
import { decomposition } from "./decomposition";
import { headline } from "./headline";
import { segments } from "./segments";
import type { Page } from "./page";

export const PAGES: Page[] = [
  headline,
  decomposition,
  segments,
  {
    path: "/budget",
    nav: "Budget simulator",
    title: "Most segments can take the full 1.388%; dance videos cannot",
    question: "How much exploration can a segment take before a guardrail breaks?",
    data: ["budget"],
    notes: [
      "The simulator assumes a linear effect within the observed range of exploration shares (0.658% to 1.388% of feed impressions). Shares above 1.388% were never observed and need a new test.",
    ],
    render(root, data) {
      const segs = data.tables.budget.filter((r) => r.dimension !== "overall");
      const clear = segs.filter((r) => r.binding_guardrail === "none in range").length;
      root.append(
        preview(
          `${clear} of ${segs.length} segments cross no guardrail up to 1.388%. Dance videos cross the hate limit even at the lowest share in the data, 0.658%. Six more segments may cross it, but their intervals are too wide to say.`,
          { value: `${clear} of ${segs.length}`, label: "segments cross no guardrail up to 1.388%" },
          "by Nov 28",
        ),
      );
    },
  },
];
