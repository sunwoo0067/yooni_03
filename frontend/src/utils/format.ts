/**
 * 숫자를 한국 원화 형식으로 포맷
 */
export const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'KRW',
  }).format(value)
}

/**
 * 날짜를 한국 형식으로 포맷
 */
export const formatDate = (date: Date | string): string => {
  const d = typeof date === 'string' ? new Date(date) : date
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(d)
}

/**
 * 백분율 포맷
 */
export const formatPercentage = (value: number): string => {
  return `${(value * 100).toFixed(1)}%`
}

/**
 * 숫자를 천 단위 구분자로 포맷
 */
export const formatNumber = (value: number): string => {
  return new Intl.NumberFormat('ko-KR').format(value)
}