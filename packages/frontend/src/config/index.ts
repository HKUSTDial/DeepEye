/**
 * Application configuration
 * All environment variables and constants should be defined here
 */

// Environment detection
export const isDev = import.meta.env.DEV
export const isProd = import.meta.env.PROD
export const mode = import.meta.env.MODE

// API Configuration
export const config = {
  api: {
    baseUrl: import.meta.env.VITE_API_URL || 'http://localhost:8001/api',
    timeout: Number(import.meta.env.VITE_API_TIMEOUT) || 30000,
  },

  // App settings
  app: {
    name: import.meta.env.VITE_APP_NAME || 'DeepEye',
    version: import.meta.env.VITE_APP_VERSION || '0.1.0',
  },

  // Feature flags
  features: {
    enableDebugLogs: import.meta.env.VITE_ENABLE_DEBUG === 'true' || isDev,
  },
} as const

// Type export for type-safe access
export type AppConfig = typeof config

