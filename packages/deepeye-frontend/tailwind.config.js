/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // iOS specific colors (完整的 iOS 色彩系统)
        ios: {
          blue: {
            DEFAULT: '#007AFF',
            dark: '#0A84FF',
          },
          red: {
            DEFAULT: '#FF3B30',
            dark: '#FF453A',
          },
          green: {
            DEFAULT: '#34C759',
            dark: '#32D74B',
          },
          orange: {
            DEFAULT: '#FF9500',
            dark: '#FF9F0A',
          },
          yellow: {
            DEFAULT: '#FFCC00',
            dark: '#FFD60A',
          },
          pink: {
            DEFAULT: '#FF2D55',
            dark: '#FF375F',
          },
          purple: {
            DEFAULT: '#AF52DE',
            dark: '#BF5AF2',
          },
          teal: {
            DEFAULT: '#5AC8FA',
            dark: '#64D2FF',
          },
          indigo: {
            DEFAULT: '#5856D6',
            dark: '#5E5CE6',
          },
          gray: {
            DEFAULT: '#8E8E93',
            dark: '#98989D',
          }
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      fontFamily: {
        sans: ["SF Pro Display", "system-ui", "sans-serif"],
        mono: ["SF Mono", "Monaco", "monospace"],
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
      animationDelay: {
        '75': '75ms',
        '150': '150ms',
      },
      backdropBlur: {
        xs: "2px",
        '2xl': '40px',
        '3xl': '64px',
      },
      backdropSaturate: {
        150: '1.5',
        180: '1.8',
      },
      boxShadow: {
        'ios-sm': '0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.08)',
        'ios-md': '0 4px 12px rgba(0, 0, 0, 0.15), 0 2px 4px rgba(0, 0, 0, 0.1)',
        'ios-lg': '0 10px 40px rgba(0, 0, 0, 0.2), 0 4px 12px rgba(0, 0, 0, 0.15)',
        'ios-xl': '0 20px 60px rgba(0, 0, 0, 0.3), 0 8px 24px rgba(0, 0, 0, 0.2)',
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}

