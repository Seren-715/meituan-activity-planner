// ===== 元信息卡片 =====

export function MetaBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="meta-block">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
