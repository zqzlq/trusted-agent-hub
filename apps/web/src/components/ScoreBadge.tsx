'use client';

interface ScoreBadgeProps {
  score: number | null;
  size?: 'sm' | 'lg';
}

function getScoreClass(score: number | null): string {
  if (score === null) return 'unknown';
  if (score >= 80) return 'trusted';
  if (score >= 50) return 'caution';
  return 'danger';
}

export default function ScoreBadge({ score, size = 'sm' }: ScoreBadgeProps) {
  const classNames = [
    'score-badge',
    getScoreClass(score),
    size === 'lg' ? 'size-lg' : '',
  ]
    .filter(Boolean)
    .join(' ');

  const display = score !== null ? score : '--';

  return <span className={classNames}>{display}</span>;
}
