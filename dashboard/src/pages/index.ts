import { headline } from "./headline";
import type { Page } from "./page";

export const PAGES: Page[] = [
  headline,
  {
    path: "/content-vs-targeting",
    nav: "Content vs targeting",
    title: "Most of the cost of a random slot is targeting, not content",
    question: "Is a random slot costly because the videos are worse, or because they reach the wrong person?",
    data: "decomposition",
    due: "by Dec 2",
    notes: [
      "Comparison C splits the gap between a user's recommended items and that user's random items into a content part (the random pool's videos) and a targeting part (who sees them). Comparison B compares the same pool video when recommended and when random.",
    ],
  },
  {
    path: "/segments",
    nav: "Segments",
    title: "The cost varies most with the content, less with the user",
    question: "Which content and which users absorb exploration best?",
    data: "segments",
    due: "by Dec 2",
    notes: [
      "Segments come from pre-period data only (Apr 8 to 21, 2022). Each segment's effect is compared with the rest of its dimension; Benjamini-Hochberg and Benjamini-Yekutieli corrections are applied per metric. Merged category groups are power-based groupings with no topical meaning.",
    ],
  },
  {
    path: "/budget",
    nav: "Budget simulator",
    title: "How much exploration each segment can take",
    question: "How much exploration can a segment take before a guardrail breaks?",
    data: "budget",
    due: "by Nov 28",
    notes: [
      "The simulator assumes a linear effect within the observed range of exploration shares (0.658% to 1.388% of tab-1 exposures). Shares above 1.388% were never observed and need a new test.",
    ],
  },
];
