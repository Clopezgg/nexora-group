export const motion = {
  fast: '0.12s ease',
  base: '0.18s ease',
  slow: '0.28s ease',
} as const

export const zIndex = {
  dropdown: 30,
  sticky: 40,
  overlay: 50,
  modal: 60,
  toast: 70,
  commandPalette: 80,
} as const

export const breakpoints = {
  mobileSm: 360,
  mobile: 430,
  tablet: 768,
  laptop: 1024,
  desktop: 1280,
  desktopLg: 1440,
} as const

export const touchTarget = '44px'
