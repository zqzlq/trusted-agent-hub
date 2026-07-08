'use client';

const STATUS_LABELS: Record<string, string> = {
  published: '已发布',
  pending_review: '待审核',
  rejected: '已驳回',
  draft: '草稿',
  yanked: '已下架',
};

interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const label = STATUS_LABELS[status] ?? status;
  const className = `status-badge ${status}`;

  return <span className={className}>{label}</span>;
}
