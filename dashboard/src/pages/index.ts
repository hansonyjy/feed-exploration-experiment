import { budget } from "./budget";
import { decomposition } from "./decomposition";
import { headline } from "./headline";
import type { Page } from "./page";
import { segments } from "./segments";

export const PAGES: Page[] = [headline, decomposition, segments, budget];
