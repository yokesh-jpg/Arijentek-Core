/* Where a teleported, position:fixed menu should sit relative to its trigger.
 *
 * Menus inside filter cards and dialogs used to be position:absolute, so the
 * table card below them - with its sticky header - painted over the top of
 * the open list, and any card with overflow clipped it. Teleported to the body
 * they escape both; this works out where to put them.
 *
 * - Opens below the trigger, or above when there is not room below.
 * - `align: 'end'` lines its right edge up with the trigger's (for controls
 *   at the right of a row); otherwise the left edges line up.
 * - Large-text mode sets `zoom` on .filter-menu, and Chromium multiplies a
 *   fixed element's top/left by its own zoom, so every offset is divided by
 *   it - without that a menu drew ~12% further right and down than its button.
 */
export function placePopover(trigger, pop, { align = 'start', gap = 6, edge = 8, matchWidth = true } = {}) {
	if (!trigger) return {}
	const r = trigger.getBoundingClientRect()
	const z = pop ? parseFloat(getComputedStyle(pop).zoom) || 1 : 1
	const p = pop ? pop.getBoundingClientRect() : null
	const W = p?.width || r.width
	const H = p?.height || 240

	const below = window.innerHeight - r.bottom - gap - edge
	const above = r.top - gap - edge
	const flip = H > below && above > below

	let left = align === 'end' ? r.right - W : r.left
	left = Math.max(edge, Math.min(left, window.innerWidth - W - edge))

	const px = (v) => `${v / z}px`
	const style = {
		left: px(left),
		// Capped at 300px (~8 options), so a long list scrolls inside a
		// compact menu instead of running to the bottom of the window.
		maxHeight: px(Math.min(300, Math.max(160, flip ? above : below))),
	}
	if (matchWidth) style.minWidth = px(r.width)
	if (flip) style.bottom = px(window.innerHeight - r.top + gap)
	else style.top = px(r.bottom + gap)
	return style
}
