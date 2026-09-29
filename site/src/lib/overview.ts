import type { Gpu, RankingRow } from './data';

/** Preserve the pipeline's rank ordering while applying the buyer's budget. */
export function topList<T extends RankingRow>(rows: readonly T[], budget: number | null, n = 5): T[] {
  return rows.filter((r) => r.playable && (budget === null || r.price <= budget))
    .sort((a, b) => a.rank - b.rank).slice(0, Math.max(0, n));
}

export function pickVerdict<T extends RankingRow>(rows: readonly T[], budget: number | null) {
  const [best, runnerUp] = topList(rows, budget, 2);
  return best ? { best, runnerUp: runnerUp ?? null } : null;
}

export function findMaxBudget(gpus: readonly Pick<Gpu, 'current_price'>[]): number {
  return Math.ceil(Math.max(0, ...gpus.map((g) => g.current_price?.price ?? 0)) / 100) * 100;
}

export function picksHref(view: string, budget: number | null, gpus: readonly Pick<Gpu, 'current_price'>[]): string {
  const i = view.lastIndexOf('_');
  const params = new URLSearchParams({ budget: String(budget ?? findMaxBudget(gpus)), res: view.slice(0, i), mode: view.slice(i + 1) });
  return `/find/?${params}`;
}
