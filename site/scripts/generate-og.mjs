// Static share previews. Use the same repository snapshot as src/lib/data.ts,
// never the public/data download copy. Restart dev after refreshing the snapshot.
import { mkdir, readFile, readdir, unlink, writeFile } from 'node:fs/promises';
import satori from 'satori';
import { Resvg } from '@resvg/resvg-js';

const json = async (name) => JSON.parse(await readFile(new URL(`../../data/site/${name}.json`, import.meta.url), 'utf8'));
const [manifest, gpus, medium, semibold] = await Promise.all([
  json('manifest'),
  json('gpus'),
  readFile(new URL('../assets/fonts/IBMPlexSans-Medium.ttf', import.meta.url)),
  readFile(new URL('../assets/fonts/IBMPlexSans-SemiBold.ttf', import.meta.url)),
]);
const fonts = [
  { name: 'IBM Plex Sans', data: medium, weight: 500, style: 'normal' },
  { name: 'IBM Plex Sans', data: semibold, weight: 600, style: 'normal' },
];

// Match styles/global.css: color identifies a vendor or a value zone.
const colors = {
  ink: '#f3f5f2', text: '#172026', muted: '#5b6770', rule: '#d4dad4',
  great: '#1f8a5b', fair: '#b07a12', poor: '#b9402b', unplayable: '#8a949b',
};
const vendors = { NVIDIA: '#76b900', AMD: '#ed1c24', Intel: '#0071c5' };
const zoneWords = { great: 'Great value', fair: 'Fair value', poor: 'Poor value', unplayable: 'Below the playable floor' };
const split = manifest.primary_view.lastIndexOf('_');
const resolution = manifest.primary_view.slice(0, split);
const mode = manifest.primary_view.slice(split + 1);
const view = `${resolution === '4k' ? '4K' : resolution}, ${mode === 'rt' ? 'ray tracing' : 'rasterization'}`;
const money = (value) => value.toLocaleString('en-US', {
  style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2,
});
const box = (children, style = {}) => ({ type: 'div', props: { style: { display: 'flex', ...style }, children } });
const text = (children, style = {}) => box(children, style);

function card(gpu) {
  const primary = gpu?.rankings[manifest.primary_view];
  if (primary && (!Number.isFinite(primary.cost_per_fps) || primary.cost_per_fps <= 0 || !Number.isInteger(primary.rank) || primary.rank < 1 || !zoneWords[primary.zone])) {
    throw new Error(`Invalid primary ranking for ${gpu.gpu_id}`);
  }
  const valueColor = primary ? colors[primary.zone] : colors.muted;
  const body = !gpu
    ? [
        text('What does a frame cost?', { fontSize: 72, fontWeight: 600, letterSpacing: -2 }),
        text('Graphics cards ranked by price ÷ performance.', { fontSize: 32, color: colors.muted, marginTop: 24 }),
        box([
          text('Compare value.', { color: colors.great }),
          text('Find your next card.', { marginLeft: 28 }),
        ], { fontSize: 32, marginTop: 48 }),
      ]
    : [
        box([
          box([], { width: 8, alignSelf: 'stretch', backgroundColor: vendors[gpu.vendor], borderRadius: 2, marginRight: 22 }),
          text(gpu.display_name, { fontSize: gpu.display_name.length > 30 ? 52 : 64, fontWeight: 600, letterSpacing: -1, flexShrink: 1 }),
        ], { alignItems: 'center', marginBottom: 24 }),
        text(view, { fontSize: 26, color: colors.muted }),
        ...(primary ? [
          box([
            text(money(primary.cost_per_fps), { fontSize: 100, fontWeight: 600, letterSpacing: -3, color: valueColor }),
            text('per frame', { fontSize: 28, marginLeft: 20, marginBottom: 18, color: colors.muted }),
          ], { alignItems: 'flex-end', marginTop: 12 }),
          box([
            text(`Rank #${primary.rank} of ${manifest.ranked_counts[manifest.primary_view]}`, { fontWeight: 600 }),
            text(zoneWords[primary.zone], { color: valueColor, marginLeft: 32 }),
          ], { fontSize: 28, marginTop: 8 }),
        ] : [
          text('Price unavailable', { fontSize: 64, fontWeight: 600, color: colors.muted, marginTop: 32 }),
          text('No current value ranking', { fontSize: 28, color: colors.muted, marginTop: 12 }),
        ]),
      ];
  return box([
    box([
      box([], { width: 16, height: 16, backgroundColor: colors.great, borderRadius: 3, marginRight: 12 }),
      text('SiliconValueIndex', { fontSize: 30, fontWeight: 600 }),
    ], { alignItems: 'center', paddingBottom: 22, borderBottom: `2px solid ${colors.rule}` }),
    box(body, { flexDirection: 'column', justifyContent: 'center', flexGrow: 1 }),
    box([
      text('Benchmarks. Prices. Perspective.'),
      text(`Data: ${manifest.generated_at.slice(0, 10)}`),
    ], { justifyContent: 'space-between', fontSize: 22, color: colors.muted, paddingTop: 18, borderTop: `2px solid ${colors.rule}` }),
  ], {
    width: 1200, height: 630, padding: '36px 56px', flexDirection: 'column',
    backgroundColor: colors.ink, color: colors.text, fontFamily: 'IBM Plex Sans', fontWeight: 500,
  });
}

const output = new URL('../public/og/', import.meta.url);
const gpuOutput = new URL('gpu/', output);
await mkdir(gpuOutput, { recursive: true });
const expected = new Set(gpus.map((gpu) => {
  if (!/^[a-z0-9-]+$/.test(gpu.gpu_id)) throw new Error(`Invalid GPU id: ${gpu.gpu_id}`);
  return `${gpu.gpu_id}.png`;
}));
if (expected.size !== gpus.length) throw new Error('Duplicate GPU ids in gpus.json');

async function render(gpu, destination) {
  const svg = await satori(card(gpu), { width: 1200, height: 630, fonts });
  const png = new Resvg(svg, { font: { loadSystemFonts: false } }).render().asPng();
  await writeFile(destination, png);
}
await render(null, new URL('default.png', output));
for (const gpu of gpus) await render(gpu, new URL(`${gpu.gpu_id}.png`, gpuOutput));
// A removed GPU must not leave an old share image in the next deployment.
for (const file of await readdir(gpuOutput)) {
  if (file.endsWith('.png') && !expected.has(file)) await unlink(new URL(file, gpuOutput));
}
console.log(`Generated ${gpus.length + 1} OG images (1200 × 630) from data/site.`);
