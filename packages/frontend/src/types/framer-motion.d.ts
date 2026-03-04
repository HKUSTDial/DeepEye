import 'framer-motion'

declare module 'framer-motion' {
  interface MotionProps {
    initial?: unknown
    animate?: unknown
    exit?: unknown
    whileHover?: unknown
    whileTap?: unknown
    whileFocus?: unknown
    whileDrag?: unknown
    whileInView?: unknown
    transition?: unknown
    variants?: unknown
    layout?: unknown
    layoutId?: string
  }
}
