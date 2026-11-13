import { Button } from '@/components/base/buttons/button'
import { Chip } from '@/components/base/badges/chip'
import { type Booking, type Slot } from '@/api'

import { formatRange } from './format'

interface Props {
  booking: Booking
  slot: Slot
  onDone: () => void
}

export function Confirmation({ booking, slot, onDone }: Props) {
  const rows: [string, string][] = [
    ['Booking ID', booking.id],
    ['Provider', slot.provider],
    ['When', formatRange(slot.start, slot.end)],
    ['Name', booking.name],
    ['Email', booking.email],
  ]

  return (
    <section className="flex flex-col gap-4 rounded-3xl border border-border-button-default bg-background-primary-default p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-title-3-semibold text-text-primary">You are booked</h2>
        <Chip variant="subtle" color="lime">
          {booking.status}
        </Chip>
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-body-2-regular">
        {rows.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-text-secondary">{label}</dt>
            <dd className="break-all text-text-primary">{value}</dd>
          </div>
        ))}
      </dl>
      <div>
        <Button variant="secondary" onClick={onDone}>
          Book another
        </Button>
      </div>
    </section>
  )
}
