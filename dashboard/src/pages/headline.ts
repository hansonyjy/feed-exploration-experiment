import * as Plot from "@observablehq/plot";
import { num } from "../data";
import { pct } from "../format";
import { el, placeholder } from "../ui";
import type { Page } from "./page";

const LABELS: Record<string, string> = {
  effective_view: "Effective view (primary)",
  naive_completion: "Naive completion",
  watch_time_ms: "Watch time",
  like_: "Like",
  comment_: "Comment",
  forward_: "Forward",
  profile_enter: "Profile enter",
  new_author_follow: "New-author follow",
  new_category_effective_view: "New-category effective view",
  hate: "Hate",
  fast_skip: "Fast skip",
};

export const headline: Page = {
  path: "/",
  nav: "Headline result",
  title: "At least 1.388% of the feed can go to exploration with no guardrail crossed",
  question: "What does a random slot cost compared with a recommended one, and what should the feed do about it?",
  data: "headline",
  due: "by Nov 28",
  notes: [
    "Comparison A: random vs recommended items in the same feed request, 2022-04-23 to 05-08, equal weight per user. Intervals: user-clustered bootstrap (2,000 resamples), cross-checked with a user fixed-effects regression.",
  ],
  render(root, data) {
    root.append(placeholder("The decision box and full comparison land by Nov 28. Draft chart below."));
    const rows = data.tables.comparison_a.filter(
      (r) => r.analysis === "A_request" && r.variant === "main" && r.weighting === "equal_user",
    );
    const points = rows.map((r) => {
      const base = num(r, "baseline_rec");
      return {
        metric: LABELS[String(r.metric)] ?? String(r.metric),
        relative: num(r, "relative"),
        low: num(r, "ci_low") / base,
        high: num(r, "ci_high") / base,
      };
    });
    const width = Math.min(root.clientWidth || 720, 760);
    const chart = Plot.plot({
      width,
      marginLeft: 190,
      x: { label: "Random minus recommended, relative to the recommended rate", tickFormat: (d: number) => pct(d) },
      y: { label: null, domain: points.map((p) => p.metric) },
      marks: [
        Plot.ruleX([0], { stroke: "currentColor", strokeOpacity: 0.4 }),
        Plot.ruleY(points, { y: "metric", x1: "low", x2: "high", stroke: "var(--accent)", strokeWidth: 2 }),
        Plot.dot(points, { y: "metric", x: "relative", fill: "var(--accent)", r: 4, tip: true }),
      ],
    });
    root.append(el("figure", { class: "chart" }, chart, el("figcaption", {}, "Draft: relative effect with 95% interval (relative interval = absolute interval ÷ recommended rate).")));
  },
};
