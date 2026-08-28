/** Format a work duration for Cursor-style "Worked for …" summaries. */
export function formatWorkedDuration(ms: number): string {
  const totalSec = Math.max(0, Math.floor(ms / 1000));
  if (totalSec < 60) return `${totalSec}s`;
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  if (min < 60) {
    return sec > 0 ? `${min}m ${sec}s` : `${min}m`;
  }
  const hr = Math.floor(min / 60);
  const remMin = min % 60;
  if (remMin > 0) return `${hr}h ${remMin}m`;
  return `${hr}h`;
}
