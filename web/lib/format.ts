export function formatCurrency(cents: number | null | undefined, currency = "USD") {
  const amount = (cents ?? 0) / 100;
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(amount);
}

export function formatDate(value: string | null | undefined) {
  if (!value) {
    return "Not set";
  }
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

export function centsToInput(cents: number | null | undefined) {
  if (cents === null || cents === undefined) {
    return "";
  }
  return (cents / 100).toFixed(2);
}

export function inputToCents(value: string) {
  const parsed = Number.parseFloat(value);
  if (Number.isNaN(parsed) || parsed < 0) {
    return null;
  }
  return Math.round(parsed * 100);
}
