var A = (k, x, d) =>
	new Promise((n, i) => {
		var b = (c) => {
				try {
					p(d.next(c));
				} catch (v) {
					i(v);
				}
			},
			y = (c) => {
				try {
					p(d.throw(c));
				} catch (v) {
					i(v);
				}
			},
			p = (c) => (c.done ? n(c.value) : Promise.resolve(c.value).then(b, y));
		p((d = d.apply(k, x)).next());
	});
import {
	c as W,
	d as $,
	r as f,
	x as B,
	m as F,
	a as l,
	b as t,
	g,
	h as w,
	f as S,
	y as V,
	F as m,
	n as h,
	M as j,
	U,
	p as z,
	o,
	t as u,
	B as _,
	k as Y,
} from "./main.js";
import { a as E } from "./api.js";
import { C as T } from "./chevron-down.js";
/**
 * @license lucide-vue-next v0.563.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */ const I = W("chevron-left", [["path", { d: "m15 18-6-6 6-6", key: "1wnfg3" }]]),
	K = {
		class: "flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8 animate-fade-in",
	},
	q = { class: "flex items-center gap-2" },
	G = { class: "relative" },
	J = ["value"],
	Q = { class: "flex flex-wrap gap-3 mb-6" },
	X = { key: 0, class: "flex items-center justify-center py-20" },
	Z = { key: 1, class: "glass-card overflow-hidden animate-slide-up" },
	ee = { class: "overflow-x-auto" },
	te = { class: "w-full border-collapse", style: { "min-width": "800px" } },
	se = { class: "border-b border-white/[0.06]" },
	ae = {
		class: "sticky left-0 z-10 px-4 py-3",
		style: { backgroundColor: "var(--surface)", borderRight: "1px solid var(--border-color)" },
	},
	le = { class: "text-sm font-medium text-white truncate max-w-[160px]" },
	oe = { class: "text-[10px] text-slate-500 truncate" },
	ne = ["title"],
	re = { key: 2, class: "glass-card p-12 text-center" },
	pe = $({
		__name: "RosterView",
		setup(k) {
			const x = f(!0),
				d = new Date(),
				n = f(d.getMonth() + 1),
				i = f(d.getFullYear()),
				b = f([]),
				y = f([]),
				p = f({}),
				c = z(() => {
					const s = [],
						a = new Date();
					for (let e = -6; e <= 2; e++) {
						const r = new Date(a.getFullYear(), a.getMonth() + e, 1),
							L = r.getMonth() + 1,
							M = r.getFullYear();
						s.push({
							value: `${M}-${L}`,
							label: r.toLocaleDateString("en-US", {
								month: "long",
								year: "numeric",
							}),
							month: L,
							year: M,
						});
					}
					return s;
				}),
				v = z({
					get: () => `${i.value}-${n.value}`,
					set: (s) => {
						const [a, e] = s.split("-").map(Number);
						(i.value = a), (n.value = e);
					},
				});
			function D(s) {
				return (
					{
						Present: "#22c55e",
						Absent: "#ef4444",
						"Half Day": "#f59e0b",
						"On Leave": "#3b82f6",
						WO: "#6b7280",
						H: "#a855f7",
						"-": "transparent",
					}[s] || "#374151"
				);
			}
			function C(s) {
				return (
					{
						Present: "rgba(34,197,94,0.15)",
						Absent: "rgba(239,68,68,0.15)",
						"Half Day": "rgba(245,158,11,0.15)",
						"On Leave": "rgba(59,130,246,0.15)",
						WO: "rgba(107,114,128,0.1)",
						H: "rgba(168,85,247,0.15)",
						"-": "rgba(255,255,255,0.02)",
					}[s] || "rgba(255,255,255,0.03)"
				);
			}
			function H(s) {
				return (
					{
						Present: "P",
						Absent: "A",
						"Half Day": "HD",
						"On Leave": "L",
						WO: "WO",
						H: "H",
						"-": "—",
					}[s] || s.charAt(0)
				);
			}
			function R(s, a) {
				const e = p.value[a];
				return e ? `${s} — ${e.description}` : s;
			}
			function O() {
				return A(this, null, function* () {
					x.value = !0;
					try {
						const s = yield E.getRoster(n.value, i.value);
						s &&
							((b.value = s.employees || []),
							(y.value = s.dates || []),
							(p.value = s.holidays || {}));
					} catch (s) {
						console.error("Roster load error", s);
					} finally {
						x.value = !1;
					}
				});
			}
			function N() {
				n.value === 1 ? ((n.value = 12), (i.value -= 1)) : (n.value -= 1);
			}
			function P() {
				n.value === 12 ? ((n.value = 1), (i.value += 1)) : (n.value += 1);
			}
			return (
				B([n, i], O),
				F(O),
				(s, a) => (
					o(),
					l("div", null, [
						t("div", K, [
							a[1] ||
								(a[1] = t(
									"div",
									null,
									[
										t(
											"h1",
											{ class: "text-2xl sm:text-3xl font-bold text-white" },
											"Roster"
										),
										t(
											"p",
											{ class: "text-sm text-slate-500 mt-1" },
											"Department attendance overview"
										),
									],
									-1
								)),
							t("div", q, [
								t(
									"button",
									{
										onClick: N,
										class: "p-2 rounded-lg bg-white/[0.04] text-slate-400 hover:bg-white/[0.08] hover:text-white transition-all",
									},
									[g(w(I), { size: 18 })]
								),
								t("div", G, [
									S(
										t(
											"select",
											{
												"onUpdate:modelValue":
													a[0] || (a[0] = (e) => (v.value = e)),
												class: "input-dark appearance-none pr-8 pl-3 py-2 text-sm cursor-pointer min-w-[180px] border border-white/10 rounded-lg",
											},
											[
												(o(!0),
												l(
													m,
													null,
													h(
														c.value,
														(e) => (
															o(),
															l(
																"option",
																{ key: e.value, value: e.value },
																u(e.label),
																9,
																J
															)
														)
													),
													128
												)),
											],
											512
										),
										[[V, v.value]]
									),
									g(w(T), {
										size: 14,
										class: "absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none",
									}),
								]),
								t(
									"button",
									{
										onClick: P,
										class: "p-2 rounded-lg bg-white/[0.04] text-slate-400 hover:bg-white/[0.08] hover:text-white transition-all",
									},
									[g(w(j), { size: 18 })]
								),
							]),
						]),
						t("div", Q, [
							(o(),
							l(
								m,
								null,
								h(
									[
										{ label: "Present", status: "Present" },
										{ label: "Absent", status: "Absent" },
										{ label: "Half Day", status: "Half Day" },
										{ label: "On Leave", status: "On Leave" },
										{ label: "Weekly Off", status: "WO" },
										{ label: "Holiday", status: "H" },
									],
									(e) =>
										t(
											"div",
											{
												key: e.status,
												class: "flex items-center gap-2 text-xs text-slate-400",
											},
											[
												t(
													"div",
													{
														class: "w-5 h-5 rounded-md flex items-center justify-center text-[9px] font-bold",
														style: _({
															backgroundColor: C(e.status),
															color: D(e.status),
														}),
													},
													u(H(e.status)),
													5
												),
												Y(" " + u(e.label), 1),
											]
										)
								),
								64
							)),
						]),
						x.value
							? (o(),
							  l("div", X, [
									...(a[2] ||
										(a[2] = [
											t(
												"div",
												{
													class: "w-10 h-10 border-2 border-accent/30 border-t-accent rounded-full animate-spin",
												},
												null,
												-1
											),
										])),
							  ]))
							: b.value.length
							? (o(),
							  l("div", Z, [
									t("div", ee, [
										t("table", te, [
											t("thead", null, [
												t("tr", se, [
													a[3] ||
														(a[3] = t(
															"th",
															{
																class: "sticky left-0 z-10 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3 min-w-[180px]",
																style: {
																	backgroundColor:
																		"var(--surface)",
																	borderRight:
																		"1px solid var(--border-color)",
																},
															},
															" Employee ",
															-1
														)),
													(o(!0),
													l(
														m,
														null,
														h(
															y.value,
															(e) => (
																o(),
																l(
																	"th",
																	{
																		key: e.date,
																		class: "text-center text-[10px] font-semibold uppercase tracking-wider px-1 py-3 min-w-[32px]",
																		style: _({
																			color: e.is_weekend
																				? "var(--accent)"
																				: "var(--text-tertiary)",
																		}),
																	},
																	[
																		t(
																			"div",
																			null,
																			u(e.weekday.charAt(0)),
																			1
																		),
																		t(
																			"div",
																			{
																				class: "text-[11px] font-bold",
																				style: _({
																					color: e.is_weekend
																						? "var(--accent)"
																						: "var(--text-secondary)",
																				}),
																			},
																			u(e.day),
																			5
																		),
																	],
																	4
																)
															)
														),
														128
													)),
												]),
											]),
											t("tbody", null, [
												(o(!0),
												l(
													m,
													null,
													h(
														b.value,
														(e) => (
															o(),
															l(
																"tr",
																{
																	key: e.employee,
																	class: "border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors",
																},
																[
																	t("td", ae, [
																		t(
																			"p",
																			le,
																			u(e.employee_name),
																			1
																		),
																		t("p", oe, u(e.shift), 1),
																	]),
																	(o(!0),
																	l(
																		m,
																		null,
																		h(
																			e.dates,
																			(r) => (
																				o(),
																				l(
																					"td",
																					{
																						key: r.date,
																						class: "text-center px-0.5 py-2",
																						title: R(
																							r.status,
																							r.date
																						),
																					},
																					[
																						t(
																							"div",
																							{
																								class: "w-7 h-7 mx-auto rounded-md flex items-center justify-center text-[10px] font-bold cursor-default transition-all hover:scale-110",
																								style: _(
																									{
																										backgroundColor:
																											C(
																												r.status
																											),
																										color: D(
																											r.status
																										),
																									}
																								),
																							},
																							u(
																								H(
																									r.status
																								)
																							),
																							5
																						),
																					],
																					8,
																					ne
																				)
																			)
																		),
																		128
																	)),
																]
															)
														)
													),
													128
												)),
											]),
										]),
									]),
							  ]))
							: (o(),
							  l("div", re, [
									g(w(U), {
										size: 40,
										class: "mx-auto text-slate-600 mb-3",
									}),
									a[4] ||
										(a[4] = t(
											"h3",
											{ class: "text-lg font-medium text-white mb-1" },
											"No roster data",
											-1
										)),
									a[5] ||
										(a[5] = t(
											"p",
											{ class: "text-slate-500 text-sm" },
											"No employees found in your department",
											-1
										)),
							  ])),
					])
				)
			);
		},
	});
export { pe as default };
