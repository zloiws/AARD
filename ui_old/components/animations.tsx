'use client'

import { motion, HTMLMotionProps } from 'framer-motion'

// Fade in animation
export function FadeIn({
  children,
  delay = 0,
  duration = 0.5,
  ...props
}: HTMLMotionProps<'div'> & { delay?: number; duration?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration, delay }}
      {...props}
    >
      {children}
    </motion.div>
  )
}

// Slide up animation
export function SlideUp({
  children,
  delay = 0,
  duration = 0.5,
  ...props
}: HTMLMotionProps<'div'> & { delay?: number; duration?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ duration, delay }}
      {...props}
    >
      {children}
    </motion.div>
  )
}

// Scale animation
export function ScaleIn({
  children,
  delay = 0,
  duration = 0.3,
  ...props
}: HTMLMotionProps<'div'> & { delay?: number; duration?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration, delay }}
      {...props}
    >
      {children}
    </motion.div>
  )
}

// Stagger children animation
export function StaggerChildren({
  children,
  staggerDelay = 0.1,
  ...props
}: HTMLMotionProps<'div'> & { staggerDelay?: number }) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={{
        visible: {
          transition: {
            staggerChildren: staggerDelay,
          },
        },
      }}
      {...props}
    >
      {children}
    </motion.div>
  )
}

// Stagger child item
export function StaggerItem({
  children,
  ...props
}: HTMLMotionProps<'div'>) {
  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 10 },
        visible: { opacity: 1, y: 0 },
      }}
      {...props}
    >
      {children}
    </motion.div>
  )
}

// Loading spinner
export function Spinner({ size = 24 }: { size?: number }) {
  return (
    <motion.div
      style={{
        width: size,
        height: size,
        border: `2px solid currentColor`,
        borderTopColor: 'transparent',
        borderRadius: '50%',
      }}
      animate={{ rotate: 360 }}
      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
    />
  )
}

// Pulse animation
export function Pulse({
  children,
  ...props
}: HTMLMotionProps<'div'>) {
  return (
    <motion.div
      animate={{
        scale: [1, 1.05, 1],
        opacity: [1, 0.8, 1],
      }}
      transition={{
        duration: 2,
        repeat: Infinity,
        ease: 'easeInOut',
      }}
      {...props}
    >
      {children}
    </motion.div>
  )
}
