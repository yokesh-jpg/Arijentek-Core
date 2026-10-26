/* ===================================================================
 * Gemora 360 — Staff Hub
 *
 * The portal shipped with its own design system (emerald #064E3B, Plus
 * Jakarta Sans / Cinzel headings). Rather than rewrite ~14,600 colour
 * classes across 148 files, the PALETTES THEMSELVES are remapped here:
 * `emerald-600` still exists, it just resolves to the Gemora accent.
 * That keeps the diff reviewable and reversible — revert this file and
 * the old look comes back.
 *
 * Which is which:
 *   emerald / primary / blue / indigo / violet / purple / sky / cyan
 *        → the accent ramp. Emerald was the portal's BRAND colour, and
 *          this system has no informational blue, so all of them land on
 *          one hue instead of five competing ones.
 *   gray / slate / zinc / neutral / stone → the Gemora neutral ladder.
 *   green / teal   → semantic success (kept green ON PURPOSE — see below)
 *   red / rose     → semantic danger
 *   amber / yellow / orange → semantic warning
 *
 * Note on emerald: the portal used it for the brand AND, via `tag-emerald`,
 * for success. Brand won, because it is 1,867 uses against a handful. Any
 * badge that genuinely means "success" should use `green-*`, which stays
 * green. `tag-emerald` in index.css was repointed accordingly.
 * =================================================================== */

// The Gemora accent ramp, expressed as a Tailwind scale so existing
// `-50 … -950` classes keep working. Values mirror styles/tokens.css.
const ACCENT = {
	50: '#F4F2FD',
	100: '#EAE8F7',
	200: '#D1CBF8',
	300: '#C4BBF6',
	400: '#A192F2',
	500: '#8E7EEC',
	600: '#5B4BC4',
	700: '#4738AA',
	800: '#3B2F8F',
	900: '#33287B',
	950: '#241C56',
}

// Gemora neutral ladder. 700–950 are the dark-mode graphite surfaces, so a
// `bg-gray-900` panel lands on the same colour the POS uses.
const NEUTRAL = {
	50: '#F8F8FA',
	100: '#F5F5F8',
	200: '#ECECF1',
	300: '#DCDCE3',
	400: '#9AA0A8',
	500: '#7B7F88',
	600: '#5C6169',
	700: '#2D3138',
	800: '#212126',
	900: '#17181B',
	950: '#0F0F11',
}

const GREEN = {
	50: '#ECFDF5', 100: '#D1FAE5', 200: '#A7F3D0', 300: '#6EE7B7', 400: '#34D399',
	500: '#059669', 600: '#059669', 700: '#047857', 800: '#065F46', 900: '#064E3B', 950: '#022C22',
}
const AMBER = {
	50: '#FFFBEB', 100: '#FEF3C7', 200: '#FDE68A', 300: '#FCD34D', 400: '#FBBF24',
	500: '#D97706', 600: '#D97706', 700: '#B45309', 800: '#92400E', 900: '#78350F', 950: '#451A03',
}
const RED = {
	50: '#FEF2F2', 100: '#FEE2E2', 200: '#FECACA', 300: '#FCA5A5', 400: '#F87171',
	500: '#DC2626', 600: '#DC2626', 700: '#B91C1C', 800: '#991B1B', 900: '#7F1D1D', 950: '#450A0A',
}

module.exports = {
	darkMode: 'class',
	presets: [require('frappe-ui/tailwind')],
	content: [
		'./index.html',
		'./src/**/*.{vue,js,ts,jsx,tsx}',
		'./node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}',
	],
	theme: {
		// Defined HERE, not in extend, so it overrides rather than merges.
		// Inter only; JetBrains Mono for codes and IDs. Cinzel and Plus Jakarta
		// Sans are gone — the shell loads neither now.
		fontFamily: {
			sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
			serif: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
			display: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
			mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
		},
		extend: {
			colors: {
				white: '#FFFFFF',

				// --- remapped palettes -----------------------------------
				gray: NEUTRAL,
				slate: NEUTRAL,
				zinc: NEUTRAL,
				neutral: NEUTRAL,
				stone: NEUTRAL,

				emerald: ACCENT,
				blue: ACCENT,
				indigo: ACCENT,
				violet: ACCENT,
				purple: ACCENT,
				fuchsia: ACCENT,
				sky: ACCENT,
				cyan: ACCENT,

				green: GREEN,
				teal: GREEN,
				lime: GREEN,

				red: RED,
				rose: RED,
				pink: RED,

				amber: AMBER,
				yellow: AMBER,
				orange: AMBER,

				// --- design-system tokens --------------------------------
				// Dark-mode graphite ladder, same steps as the POS.
				surface: {
					0: '#0F0F11',
					1: '#18181B',
					2: '#212126',
					3: '#2A2A30',
				},

				// Accent ramp. Values live in styles/tokens.css — change the
				// brand colour there, not here. Channels plus <alpha-value> is
				// what makes bg-accent/10 work; a finished colour cannot take
				// an injected alpha.
				accent: {
					DEFAULT: 'rgb(var(--accent-rgb) / <alpha-value>)',
					hover: 'rgb(var(--accent-hover-rgb) / <alpha-value>)',
					deep: 'rgb(var(--accent-deep-rgb) / <alpha-value>)',
					chart: 'rgb(var(--accent-chart-rgb) / <alpha-value>)',
					soft: 'rgb(var(--accent-soft-rgb) / <alpha-value>)',
					light: 'rgb(var(--accent-light-rgb) / <alpha-value>)',
					pale: 'rgb(var(--accent-pale-rgb) / <alpha-value>)',
					palest: 'rgb(var(--accent-palest-rgb) / <alpha-value>)',
					wash: 'rgb(var(--accent-wash-rgb) / <alpha-value>)',
					'wash-mid': 'rgb(var(--accent-wash-mid-rgb) / <alpha-value>)',
				},

				// `primary` was the portal's own brand token. It now points at
				// the accent so bg-primary / text-primary-600 keep working.
				primary: { ...ACCENT, DEFAULT: '#5B4BC4' },
			},
			backgroundImage: {
				// Was a hard emerald radial; now a soft accent field.
				'emerald-glow':
					'radial-gradient(circle at 50% 0%, rgb(var(--accent-rgb) / 0.14), transparent 70%)',
			},
			boxShadow: {
				// Coloured lift under active/selected items, on the accent.
				'glow-emerald': '0 8px 24px -6px rgb(var(--accent-rgb) / 0.42)',
				'glow-red': '0 8px 24px -6px rgba(220, 38, 38, 0.42)',
				'glow-amber': '0 8px 24px -6px rgba(217, 119, 6, 0.42)',
			},
			borderRadius: {
				// The 8/12/18 three-step scale the POS uses.
				sm: '8px',
				DEFAULT: '10px',
				md: '12px',
				lg: '18px',
				xl: '18px',
				'2xl': '20px',
			},
		},
	},
	plugins: [],
}
