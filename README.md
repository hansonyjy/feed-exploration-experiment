# Feed Exploration Experiment

**Status: in progress.** Results, dashboard and memo land here when the analysis is done.

How much of a short-video feed can go to exploration, and for which users? This project uses a
public dataset where a short-video app randomly replaced some recommended videos, and treats each
random slot as a measured exploration slot.

- Plan: [`docs/design.md`](docs/design.md)
- Pre-registered metrics and parameters: [`docs/analysis_plan.md`](docs/analysis_plan.md)
- Decisions and data-quality findings: [`docs/decisions.md`](docs/decisions.md), [`docs/data_quality.md`](docs/data_quality.md)

## Stack
BigQuery · dbt · Python · static web dashboard on GitHub Pages · Tableau Public

## Data
[KuaiRand](https://kuairand.com/) (Gao et al., CIKM 2022, [arXiv 2208.08696](https://arxiv.org/abs/2208.08696)),
licensed CC BY-SA 4.0. Video categories come from the KuaiRand supplementary files by Chongming Gao
([Zenodo 10.5281/zenodo.18159199](https://zenodo.org/records/18159199)), licensed CC BY 4.0.
Raw data is not stored in this repo. Derived data in `exports/` is shared
under CC BY-SA 4.0.
