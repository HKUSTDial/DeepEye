interface PlaceholderProps {
  name: string
}

export default function Placeholder({ name }: PlaceholderProps) {
  return (
    <div className="flex items-center justify-center h-full text-[var(--main-text-muted)]">
      {name} (Coming soon...)
    </div>
  )
}

