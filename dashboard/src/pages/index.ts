import { num } from "../data";
import { pp } from "../format";
import { preview } from "../ui";
import { headline } from "./headline";
import type { Page } from "./page";

export const PAGES: Page[] = [
  headline,
  {
    path: "/content-vs-targeting",
    nav: "Content vs targeting",
    title: "Most of the cost of a random slot is targeting, not content",
    question: "Is a random slot costly because the videos are worse, or because they reach the wrong person?",
    data: ["decomposition"],
    notes: [
      "The gap between a user's recommended videos and that user's random videos splits into two parts. Content: how good the random pool's videos are. Targeting: whether they reach people who want them.",
    ],
    render(root, data) {
      const c = data.tables.comparison_c.filter((r) => r.variant === "main" && r.metric === "effective_view");
      const term = (t: string) => num(c.find((r) => r.term === t)!, "estimate");
      const share = Math.round((term("targeting") / term("total")) * 100);
      root.append(
        preview(
          `When the random pool's videos are recommended, they do almost as well as other recommended videos. Of the ${pp(term("total")).replace("+", "")} effective-view gap, ${pp(term("targeting")).replace("+", "")} comes from targeting and only ${pp(term("content")).replace("+", "")} from the videos themselves.`,
          { value: `${share}%`, label: "of the effective-view gap is targeting" },
          "by Dec 2",
        ),
      );
    },
  },
  {
    path: "/segments",
    nav: "Segments",
    title: "The cost depends more on what is shown than on who sees it",
    question: "Which content and which users absorb exploration best?",
    data: ["segments"],
    notes: [
      "Segments come from data before the test period only (Apr 8 to 21, 2022). Each segment is compared with the rest of its group, with a correction for testing many segments at once.",
    ],
    render(root, data) {
      const labels = new Map(data.tables.category_labels.map((r) => [String(r.category_segment), String(r.label_en)]));
      const cats = data.tables.segments.filter(
        (r) => r.dimension === "category_segment" && r.metric === "effective_view" && r.interpretable === true,
      );
      const worst = cats.reduce((a, b) => (num(b, "estimate") < num(a, "estimate") ? b : a));
      const best = cats.reduce((a, b) => (num(b, "estimate") > num(a, "estimate") ? b : a));
      const name = (r: (typeof cats)[number]) => labels.get(String(r.segment))!.toLowerCase();
      root.append(
        preview(
          `Every segment pays a large cost, but the type of video matters most: random ${name(worst)} videos cost the most and random ${name(best)} videos the least. User groups differ by a few points.`,
          { value: `${pp(num(worst, "estimate"))} vs ${pp(num(best, "estimate"))}`, label: `Effective views, random ${name(worst)} vs random ${name(best)} videos` },
          "by Dec 2",
        ),
      );
    },
  },
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
