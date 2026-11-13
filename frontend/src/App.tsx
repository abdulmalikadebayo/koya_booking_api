import { useCallback, useEffect, useState } from 'react'

import { Button } from '@/components/base/buttons/button'
import { Spinner } from '@/components/base/spinner/spinner'
import { Toaster } from '@/components/base/toast/toast'
import { listSlots, type Booking, type Slot } from '@/api'

import { BookingForm } from './booking/BookingForm'
import { Confirmation } from './booking/Confirmation'
import { SlotList } from './booking/SlotList'

export default function App() {
  const [slots, setSlots] = useState<Slot[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Slot | null>(null)
  const [booking, setBooking] = useState<Booking | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      setSlots(await listSlots())
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Could not load slots.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  function finish() {
    setBooking(null)
    setSelected(null)
    void load()
  }

  function booked(result: Booking) {
    setBooking(result)
    void load()
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-4 py-10">
      <header>
        <h1 className="text-title-2-medium text-text-primary">Book an appointment</h1>
        <p className="text-body-regular text-text-secondary">
          Pick an available slot and confirm your details.
        </p>
      </header>

      {booking && selected ? (
        <Confirmation booking={booking} slot={selected} onDone={finish} />
      ) : selected ? (
        <BookingForm slot={selected} onBooked={booked} onCancel={() => setSelected(null)} />
      ) : loading ? (
        <div className="flex items-center gap-3 text-text-secondary">
          <Spinner size="sm" /> Loading slots...
        </div>
      ) : loadError ? (
        <div className="flex flex-col items-start gap-3">
          <p className="text-text-primary">{loadError}</p>
          <Button variant="secondary" onClick={() => void load()}>
            Try again
          </Button>
        </div>
      ) : (
        <SlotList slots={slots} onSelect={setSelected} />
      )}

      <Toaster />
    </main>
  )
}
