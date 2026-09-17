// Per-browser convenience only. An explicit Compare URL always takes precedence.
const KEY = 'svi.compareSelection';
const LIMIT = 4;

export function get(): string[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(KEY) ?? '[]');
    if (!Array.isArray(value)) return [];
    return [...new Set(value.filter((id): id is string => typeof id === 'string' && /^[a-z0-9-]+$/.test(id)))].slice(-LIMIT);
  } catch {
    return [];
  }
}

function save(ids: string[]): string[] {
  try {
    localStorage.setItem(KEY, JSON.stringify(ids));
    return ids;
  } catch {
    return [];
  }
}

export function add(id: string): string[] {
  const ids = get();
  if (!/^[a-z0-9-]+$/.test(id) || ids.includes(id)) return ids;
  return save([...ids, id].slice(-LIMIT));
}

export function toggle(id: string): string[] {
  const ids = get();
  return ids.includes(id) ? save(ids.filter((item) => item !== id)) : add(id);
}

export function clear(): string[] {
  return save([]);
}
