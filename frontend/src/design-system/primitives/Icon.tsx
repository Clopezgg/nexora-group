import type { SVGAttributes } from 'react'

export type IconName =
  | 'home'
  | 'check'
  | 'inbox'
  | 'book'
  | 'bank'
  | 'card'
  | 'receipt'
  | 'refresh'
  | 'tag'
  | 'project'
  | 'grid'
  | 'ruler'
  | 'calendar'
  | 'chart'
  | 'shuffle'
  | 'notebook'
  | 'shield'
  | 'file'
  | 'send'
  | 'message'
  | 'scale'
  | 'package'
  | 'truck'
  | 'warehouse'
  | 'users'
  | 'target'
  | 'briefcase'
  | 'clock'
  | 'equipment'
  | 'fuel'
  | 'tool'
  | 'folder'
  | 'camera'
  | 'search'
  | 'settings'
  | 'menu'
  | 'bell'
  | 'warning'
  | 'clipboard'
  | 'plus'

const paths: Record<IconName, string> = {
  home: 'M3 11.5 12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
  check: 'M4 4h16v16H4z M8 12l2.5 2.5L16 9',
  inbox: 'M4 5h16l2 10v4H2v-4z M3 15h5l2 2h4l2-2h5',
  book: 'M4 5a2 2 0 0 1 2-2h14v16H6a2 2 0 0 0-2 2z M4 5v16 M8 7h8',
  bank: 'M3 10 12 4l9 6 M5 10v8m4-8v8m6-8v8m4-8v8M3 21h18',
  card: 'M3 6h18v12H3z M3 10h18 M7 15h4',
  receipt: 'M6 3h12v18l-3-2-3 2-3-2-3 2z M9 8h6m-6 4h6m-6 4h4',
  refresh: 'M20 7v5h-5 M4 17v-5h5 M6.1 8A7 7 0 0 1 18 6l2 1 M17.9 16A7 7 0 0 1 6 18l-2-1',
  tag: 'M3 12V4h8l10 10-7 7z M7.5 8h.01',
  project: 'M4 20V7h6V4h4v3h6v13z M8 11h2m4 0h2m-8 4h2m4 0h2',
  grid: 'M4 4h6v6H4zm10 0h6v6h-6zM4 14h6v6H4zm10 0h6v6h-6z',
  ruler: 'M5 19 19 5l3 3L8 22z M14 8l2 2m-5 1 2 2m-5 1 2 2',
  calendar: 'M4 6h16v15H4z M8 3v6m8-6v6M4 11h16',
  chart: 'M4 20V10m5 10V4m6 16v-7m5 7H2',
  shuffle: 'M4 7h3l10 10h3 M17 14l3 3-3 3 M4 17h3l3-3m4-4 3-3h3 M17 4l3 3-3 3',
  notebook: 'M6 3h14v18H6z M3 7h6m-6 5h6m-6 5h6 M11 8h5m-5 4h5',
  shield: 'M12 3 20 6v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6z M9 12l2 2 4-5',
  file: 'M6 3h8l4 4v14H6z M14 3v5h5 M9 13h6m-6 4h6',
  send: 'M3 11.5 21 3l-7 18-3-7z M11 14 21 3',
  message: 'M4 5h16v12H8l-4 4z M8 9h8m-8 4h5',
  scale: 'M12 4v17M7 7h10M5 7l-3 6h6zm14 0-3 6h6zM8 21h8',
  package: 'M4 7 12 3l8 4v10l-8 4-8-4z M4 7l8 4 8-4M12 11v10',
  truck: 'M3 6h11v11H3z M14 10h4l3 3v4h-7z M7 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm10 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
  warehouse: 'M3 10 12 4l9 6v11H3z M8 21v-7h8v7 M6 11h12',
  users: 'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-7 10c0-4 3-7 7-7s7 3 7 7 M17 4a3 3 0 0 1 0 6m1 4c3 .5 5 3 5 6',
  target: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zm0-5a5 5 0 1 0 0-10 5 5 0 0 0 0 10zm0-3a2 2 0 1 0 0-4 2 2 0 0 0 0 4',
  briefcase: 'M3 7h18v13H3z M8 7V4h8v3 M3 12h18 M10 12v2h4v-2',
  clock: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zm0-15v6l4 2',
  equipment: 'M4 16h12l3-5h2v5 M7 16l2-7h6l1 7 M4 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm14 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
  fuel: 'M6 3h9v18H6z M8 7h5v5H8z M15 8h3l2 3v7a2 2 0 0 1-4 0v-3',
  tool: 'M14 6a4 4 0 0 0-5-4l2 3-3 3-3-2a4 4 0 0 0 5 5l8 8 3-3-8-8z',
  folder: 'M3 6h7l2 2h9v12H3z',
  camera: 'M4 7h4l2-3h4l2 3h4v13H4z M12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
  search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zm6-2 5 5',
  settings: 'M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z M19 13.5l2 1-2 3-2-1.2a8 8 0 0 1-2 1.2V21h-4v-3.5a8 8 0 0 1-2-1.2L7 17.5l-2-3 2-1a8 8 0 0 1 0-3L5 9.5l2-3 2 1.2a8 8 0 0 1 2-1.2V3h4v3.5a8 8 0 0 1 2 1.2l2-1.2 2 3-2 1a8 8 0 0 1 0 3z',
  menu: 'M4 7h16M4 12h16M4 17h16',
  bell: 'M5 17h14l-2-3V9a5 5 0 0 0-10 0v5z M10 20h4',
  warning: 'M12 3 22 21H2z M12 9v5m0 3h.01',
  clipboard: 'M7 5h10v16H5V5h2 M9 3h6v4H9z M9 12h6m-6 4h6',
  plus: 'M12 5v14 M5 12h14',
}

interface IconProps extends Omit<SVGAttributes<SVGSVGElement>, 'name'> {
  name: IconName
  size?: number | string
  title?: string
}

export function Icon({ name, size = 20, title, className, ...props }: IconProps) {
  return (
    <svg
      className={['nx-icon', className].filter(Boolean).join(' ')}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={title ? undefined : true}
      role={title ? 'img' : undefined}
      {...props}
    >
      {title ? <title>{title}</title> : null}
      <path d={paths[name]} />
    </svg>
  )
}
