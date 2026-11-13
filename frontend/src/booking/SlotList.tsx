import { Button } from '@/components/base/buttons/button'
import { Chip } from '@/components/base/badges/chip'
import { type Slot } from '@/api'

import { formatRange } from './format'

interface Props {
  slots: Slot[]
  onSelect: (slot: Slot) => void
}

export function SlotList({ slots, onSelect }: Props) {
  if (slots.length === 0) {
    return <p className="text-text-secondary">No appointment slots yet.</p>
  }

  return (
    <ul className="flex flex-col gap-3">
      {slots.map((slot) => (
        <li
          key={slot.id}
          className="flex items-center justify-between gap-4 rounded-3xl border border-border-button-default bg-background-primary-default p-4"
        >
          <div className="flex flex-col gap-1">
            <span className="text-body-medium text-text-primary">{slot.provider}</span>
            <span className="text-body-2-regular text-text-secondary">{formatRange(slot.start, slot.end)}</span>
          </div>
          <div className="flex items-center gap-3">
            <Chip variant="subtle" color={slot.available ? 'lime' : 'gray'}>
              {slot.available ? 'Available' : 'Booked'}
            </Chip>
            <Button size="small" disabled={!slot.available} onClick={() => onSelect(slot)}>
              Book
            </Button>
          </div>
        </li>
      ))}
    </ul>
  )
}
