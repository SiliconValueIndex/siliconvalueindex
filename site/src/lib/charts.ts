// Chart.js helpers shared by the detail, compare and methodology pages.
import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale, ScatterController, Tooltip, Legend, Filler } from 'chart.js';

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, ScatterController, Tooltip, Legend, Filler);

const css = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const mono = () => css('--font-num') || 'monospace';

export function drawSparkline(canvas: HTMLCanvasElement, points: [string, number, string][]) {
  const great = css('--great');
  new Chart(canvas, {
    type: 'line',
    data: {
      labels: points.map((p) => p[0]),
      datasets: [
        {
          data: points.map((p) => p[1]),
          borderColor: great,
          backgroundColor: css('--great-soft'),
          fill: true,
          tension: 0.25,
          pointRadius: points.length > 40 ? 0 : 3,
          borderWidth: 2,
        },
      ],
    },
    options: {
      animation: false,
      aspectRatio: 3,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => items[0].label,
            label: (item) => ` $${(item.parsed.y as number).toFixed(2)} at ${points[item.dataIndex][2]}`,
          },
        },
      },
      scales: {
        x: { ticks: { color: css('--muted'), font: { family: mono(), size: 11 }, maxTicksLimit: 6 }, grid: { display: false } },
        y: { ticks: { color: css('--muted'), font: { family: mono(), size: 11 }, callback: (v) => `$${v}` }, grid: { color: css('--rule') } },
      },
    },
  });
}

export interface OverlapChartInput {
  points: [string, number, number][];
  names: Record<string, string>;
  method: string;
  params: Record<string, number | number[]>;
  dropped: string[];
  legacyRange: [number, number];
  constantRatio?: number;
}

export function drawOverlapChart(canvas: HTMLCanvasElement, input: OverlapChartInput) {
  const [lo, hi] = input.legacyRange;
  const x0 = Math.max(0, lo - 10);
  const x1 = hi + 10;
  const predict = (x: number) => {
    if (input.method === 'linear') return (input.params.a as number) * x + (input.params.b as number);
    if (input.method === 'ratio_trimmed') return (input.params.scale as number) * x;
    return NaN;
  };
  const used = input.points.filter((p) => !input.dropped.includes(p[0]));
  const dropped = input.points.filter((p) => input.dropped.includes(p[0]));
  const datasets: any[] = [
    {
      type: 'scatter',
      label: 'Used in fit',
      data: used.map((p) => ({ x: p[1], y: p[2], id: p[0] })),
      backgroundColor: css('--great'),
      pointRadius: 5,
    },
    {
      type: 'scatter',
      label: 'Excluded outlier',
      data: dropped.map((p) => ({ x: p[1], y: p[2], id: p[0] })),
      backgroundColor: css('--poor'),
      pointRadius: 5,
      pointStyle: 'crossRot',
      borderColor: css('--poor'),
      borderWidth: 2,
    },
    {
      type: 'line',
      label: 'Fitted transform',
      data: [
        { x: x0, y: predict(x0) },
        { x: x1, y: predict(x1) },
      ],
      borderColor: css('--text'),
      borderWidth: 2,
      pointRadius: 0,
    },
  ];
  if (input.constantRatio) {
    datasets.push({
      type: 'line',
      label: `Old constant ratio (${input.constantRatio.toFixed(3)})`,
      data: [
        { x: x0, y: x0 * input.constantRatio },
        { x: x1, y: x1 * input.constantRatio },
      ],
      borderColor: css('--muted'),
      borderDash: [6, 4],
      borderWidth: 1.5,
      pointRadius: 0,
    });
  }
  new Chart(canvas, {
    data: { datasets },
    options: {
      animation: false,
      aspectRatio: 1.7,
      plugins: {
        legend: { labels: { color: css('--muted'), font: { family: css('--font-ui') } } },
        tooltip: {
          callbacks: {
            label: (item) => {
              const raw = item.raw as { x: number; y: number; id?: string };
              return raw.id ? ` ${input.names[raw.id] ?? raw.id}: ${raw.x.toFixed(1)} → ${raw.y.toFixed(1)}` : ` ${raw.y.toFixed(1)}`;
            },
          },
        },
      },
      scales: {
        x: { type: 'linear', title: { display: true, text: 'FPS in the older suite', color: css('--muted') }, ticks: { color: css('--muted'), font: { family: mono() } }, grid: { color: css('--rule') }, min: x0, max: x1 },
        y: { type: 'linear', title: { display: true, text: 'FPS in the current suite', color: css('--muted') }, ticks: { color: css('--muted'), font: { family: mono() } }, grid: { color: css('--rule') } },
      },
    },
  });
}
