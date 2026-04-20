export function fmt(n: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n)
}

export function fmtFull(n: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
}

export function fmtPct(n: number | null): string {
  if (n === null) return '--'
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
}

export function fmtSign(n: number): string {
  const prefix = n >= 0 ? '+' : ''
  return prefix + fmt(n)
}
