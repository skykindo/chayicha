export function startOfDay(date = new Date()) {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
}

export function isToday(date: Date) {
  const today = startOfDay();
  const target = startOfDay(date);
  return today.getTime() === target.getTime();
}
