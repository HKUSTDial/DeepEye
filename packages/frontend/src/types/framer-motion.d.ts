import 'framer-motion'

declare module 'framer-motion' {
  interface MotionProps {
    initial?: any
    animate?: any
    exit?: any
    whileHover?: any
    whileTap?: any
    whileFocus?: any
    whileDrag?: any
    whileInView?: any
    transition?: any
    variants?: any
    layout?: any
    layoutId?: string
  }
}
