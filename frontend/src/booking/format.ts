const dateTime = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  hour: 'numeric',
  minute: '2-digit',
})

const time = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' })

/** "Thu, 10 Dec, 9:00 AM - 9:30 AM" */
export function formatRange(start: string, end: string): string {
  return `${dateTime.format(new Date(start))} - ${time.format(new Date(end))}`
}
