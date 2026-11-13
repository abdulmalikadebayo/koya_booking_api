import { useRef, useState, type FormEvent } from 'react'

import { Button } from '@/components/base/buttons/button'
import { Input } from '@/components/base/input/input'
import { Spinner } from '@/components/base/spinner/spinner'
import { toast } from '@/components/base/toast/toast'
import { ApiError, createBooking, type Booking, type Slot } from '@/api'

import { formatRange } from './format'

interface Props {
  slot: Slot
  onBooked: (booking: Booking) => void
  onCancel: () => void
}

export function BookingForm({ slot, onBooked, onCancel }: Props) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  // One key per distinct submission: a double click or retry books only once,
  // but editing the form starts a new attempt.
  const keyRef = useRef(crypto.randomUUID())

  function edit(setter: (value: string) => void) {
    return (value: string) => {
      keyRef.current = crypto.randomUUID()
      setter(value)
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (submitting) return
    setSubmitting(true)
    try {
      const booking = await createBooking({ slot_id: slot.id, name, email }, keyRef.current)
      onBooked(booking)
    } catch (error) {
      if (error instanceof ApiError && error.status === 429) {
        const wait = error.retryAfter ? ` Try again in ${error.retryAfter}s.` : ''
        toast('Too many attempts', { status: 'information', description: `Please slow down.${wait}` })
      } else {
        toast(error instanceof Error ? error.message : 'Something went wrong.', {
          status: 'error',
        })
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form
      onSubmit={submit}
      className="flex flex-col gap-4 rounded-3xl border border-border-button-default bg-background-primary-default p-5"
    >
      <div>
        <h2 className="text-title-3-semibold text-text-primary">Confirm your booking</h2>
        <p className="text-body-2-regular text-text-secondary">
          {slot.provider} - {formatRange(slot.start, slot.end)}
        </p>
      </div>
      <Input
        label="Full name"
        value={name}
        onChange={edit(setName)}
        isRequired
        autoComplete="name"
      />
      <Input
        label="Email"
        type="email"
        value={email}
        onChange={edit(setEmail)}
        isRequired
        autoComplete="email"
      />
      <div className="flex gap-3">
        <Button type="submit" disabled={submitting}>
          {submitting ? <Spinner size="xs" /> : null}
          Book appointment
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel} disabled={submitting}>
          Back
        </Button>
      </div>
    </form>
  )
}
