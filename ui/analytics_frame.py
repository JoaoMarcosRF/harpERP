"""
ui/analytics_frame.py — Executive BI Analytics Dashboard for harErp
===================================================================
Displays:
  - Period quick-filter bar (All Time, Current Month, Last 30 Days, Last 90 Days, Current Year)
  - 2x4 grid of 8 KPI Cards (Finance, Raw Material Capital, Finished Goods, Sales/COGS & Turnover)
  - Intelligent operational alert banner (Low Stock + Batch Expiration financial risk)
  - 2 Interactive Chart Sub-tabs with data labels and full live EN / PT-BR internationalization.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import database
from ui.theme import ThemeManager
from ui.i18n import I18n, t


class AnalyticsFrame(ttk.Frame):
    PERIOD_KEYS = ("bi_p_all", "bi_p_month", "bi_p_30d", "bi_p_90d", "bi_p_year")

    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._selected_period_idx = 0

        self._build_top_bar()
        self._build_kpi_cards()
        self._build_alerts_banner()
        self._build_chart_tabs()

        ThemeManager.register_listener(self.refresh)
        I18n.register_listener(self._on_language_change)
        self.refresh()

    # ══════════════════════════════════════════ 1. PERIOD FILTER BAR
    def _build_top_bar(self):
        bar = ttk.Frame(self)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.lbl_title = ttk.Label(bar, text=t("bi_title"), style="SectionTitle.TLabel")
        self.lbl_title.pack(side="left")

        right = ttk.Frame(bar)
        right.pack(side="right")

        self.lbl_period = ttk.Label(right, text=t("bi_period_lbl"))
        self.lbl_period.pack(side="left", padx=(0, 6))
        self.period_var = tk.StringVar(value=t("bi_p_all"))
        self.combo_period = ttk.Combobox(
            right,
            textvariable=self.period_var,
            values=[t(k) for k in self.PERIOD_KEYS],
            width=18,
            state="readonly",
        )
        self.combo_period.pack(side="left", padx=(0, 8))
        self.combo_period.bind("<<ComboboxSelected>>", self._on_period_selected)

        self.btn_refresh = ttk.Button(
            right, text=t("bi_btn_refresh"), style="Primary.TButton", command=self.refresh
        )
        self.btn_refresh.pack(side="left")

    def _on_period_selected(self, _=None):
        vals = list(self.combo_period["values"])
        cur = self.period_var.get()
        if cur in vals:
            self._selected_period_idx = vals.index(cur)
        self.refresh()

    def _get_date_range(self):
        today_dt = datetime.now().date()
        key = self.PERIOD_KEYS[self._selected_period_idx]
        if key == "bi_p_month":
            return today_dt.replace(day=1).strftime("%Y-%m-%d"), None
        if key == "bi_p_30d":
            return (today_dt - timedelta(days=30)).strftime("%Y-%m-%d"), None
        if key == "bi_p_90d":
            return (today_dt - timedelta(days=90)).strftime("%Y-%m-%d"), None
        if key == "bi_p_year":
            return today_dt.replace(month=1, day=1).strftime("%Y-%m-%d"), None
        return None, None

    # ══════════════════════════════════════════ 2. 2x4 KPI CARDS GRID
    def _build_kpi_cards(self):
        grid = ttk.Frame(self)
        grid.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        for c in range(4):
            grid.grid_columnconfigure(c, weight=1, uniform="kpi")

        defs = [
            ("saldo", "kpi_saldo"),
            ("receitas", "kpi_receitas"),
            ("despesas", "kpi_despesas"),
            ("resultado", "kpi_resultado"),
            ("insumos", "kpi_insumos"),
            ("lotes", "kpi_lotes"),
            ("vendas", "kpi_vendas"),
            ("giro", "kpi_giro"),
        ]

        self.kpi_cards = {}
        for idx, (key, t_key) in enumerate(defs):
            r, c = divmod(idx, 4)
            card = tk.Frame(grid, bd=1, relief="solid", padx=12, pady=8)
            card.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)

            lbl_tit = tk.Label(card, text=t(t_key), anchor="w", font=("Segoe UI", 8, "bold"))
            lbl_tit.pack(fill="x")

            lbl_val = tk.Label(card, text="$ 0.00", anchor="w", font=("Segoe UI", 14, "bold"))
            lbl_val.pack(fill="x", pady=(2, 2))

            lbl_sub = tk.Label(card, text="—", anchor="w", font=("Segoe UI", 8))
            lbl_sub.pack(fill="x")

            self.kpi_cards[key] = (card, lbl_tit, lbl_val, lbl_sub, t_key)

    # ══════════════════════════════════════════ 3. OPERATIONAL ALERTS BANNER
    def _build_alerts_banner(self):
        self.alerts_frame = tk.Frame(self, bd=1, relief="solid", padx=12, pady=6)
        self.alerts_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8), padx=4)
        self.alerts_frame.grid_columnconfigure(0, weight=1)
        self.alerts_frame.grid_columnconfigure(1, weight=1)

        self.lbl_alert_inputs = tk.Label(
            self.alerts_frame, text="", anchor="w", font=("Segoe UI", 9, "bold")
        )
        self.lbl_alert_inputs.grid(row=0, column=0, sticky="w")

        self.lbl_alert_batches = tk.Label(
            self.alerts_frame, text="", anchor="e", font=("Segoe UI", 9, "bold")
        )
        self.lbl_alert_batches.grid(row=0, column=1, sticky="e")

    # ══════════════════════════════════════════ 4. CHART SUB-TABS (2 VIEWS)
    def _build_chart_tabs(self):
        self.nb_charts = ttk.Notebook(self)
        self.nb_charts.grid(row=3, column=0, sticky="nsew")

        # Sub-tab 1: Financial & Profitability
        self.tab_fin = ttk.Frame(self.nb_charts, padding=4)
        self.nb_charts.add(self.tab_fin, text=t("bi_subtab_fin"))
        self.tab_fin.grid_rowconfigure(0, weight=1)
        self.tab_fin.grid_columnconfigure(0, weight=1)

        self.fig_fin = Figure(figsize=(9.5, 4.6), dpi=92)
        self.ax_cashflow = self.fig_fin.add_subplot(2, 2, 1)
        self.ax_exp_cat = self.fig_fin.add_subplot(2, 2, 2)
        self.ax_unit_margin = self.fig_fin.add_subplot(2, 2, 3)
        self.ax_sales_cmv = self.fig_fin.add_subplot(2, 2, 4)
        self.canvas_fin = FigureCanvasTkAgg(self.fig_fin, master=self.tab_fin)
        self.canvas_fin.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # Sub-tab 2: Inventory, Inputs & Production
        self.tab_est = ttk.Frame(self.nb_charts, padding=4)
        self.nb_charts.add(self.tab_est, text=t("bi_subtab_est"))
        self.tab_est.grid_rowconfigure(0, weight=1)
        self.tab_est.grid_columnconfigure(0, weight=1)

        self.fig_est = Figure(figsize=(9.5, 4.6), dpi=92)
        self.ax_batches = self.fig_est.add_subplot(2, 2, 1)
        self.ax_cost = self.fig_est.add_subplot(2, 2, 2)
        self.ax_stock = self.fig_est.add_subplot(2, 2, 3)
        self.ax_expiry = self.fig_est.add_subplot(2, 2, 4)
        self.canvas_est = FigureCanvasTkAgg(self.fig_est, master=self.tab_est)
        self.canvas_est.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    def _on_language_change(self):
        self.lbl_title.config(text=t("bi_title"))
        self.lbl_period.config(text=t("bi_period_lbl"))
        new_vals = [t(k) for k in self.PERIOD_KEYS]
        self.combo_period["values"] = new_vals
        self.period_var.set(new_vals[self._selected_period_idx])
        self.btn_refresh.config(text=t("bi_btn_refresh"))
        self.nb_charts.tab(self.tab_fin, text=t("bi_subtab_fin"))
        self.nb_charts.tab(self.tab_est, text=t("bi_subtab_est"))
        for _, (_, lbl_tit, _, _, t_key) in self.kpi_cards.items():
            lbl_tit.config(text=t(t_key))
        self.refresh()

    # ══════════════════════════════════════════ FULL REFRESH
    def _style_axis(self, ax, title):
        p = ThemeManager.palette()
        ax.set_facecolor(p["bg_card"])
        ax.set_title(title, color=p["texto"], fontsize=9.5, fontweight="bold", pad=8)
        ax.tick_params(colors=p["texto_suave"], labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(p["borda"])
        ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.35, color=p["borda"])
        ax.set_axisbelow(True)

    def _annotate_bars(self, ax, bars, prefix="", suffix="", decimals=0, color=None):
        p = ThemeManager.palette()
        txt_color = color or p["texto"]
        for b in bars:
            h = b.get_height()
            if h == 0:
                continue
            fmt = f"{prefix}{h:.{decimals}f}{suffix}"
            ax.annotate(
                fmt,
                xy=(b.get_x() + b.get_width() / 2, h),
                xytext=(0, 2),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7,
                color=txt_color,
                fontweight="bold",
            )

    def refresh(self):
        p = ThemeManager.palette()
        ini, fim = self._get_date_range()
        kpi = database.indicadores_dashboard(ini, fim)
        en = I18n.is_en()
        cur = "$" if en else "R$"

        if en:
            kpi_values = {
                "saldo": (
                    f"{cur} {kpi['saldo_global']:.2f}",
                    f"Cumulative: +{cur} {kpi['rec_global']:.0f} / -{cur} {kpi['desp_global']:.0f}",
                    p["sucesso"] if kpi["saldo_global"] >= 0 else p["perigo"],
                ),
                "receitas": (
                    f"{cur} {kpi['rec_periodo']:.2f}",
                    f"{kpi['n_rec']} inflow entry(ies) in period",
                    p["sucesso"],
                ),
                "despesas": (
                    f"{cur} {kpi['desp_periodo']:.2f}",
                    f"{kpi['n_desp']} outflow entry(ies) in period",
                    p["perigo"],
                ),
                "resultado": (
                    f"{cur} {kpi['resultado_periodo']:.2f}",
                    f"Net cash margin: {kpi['margem_caixa']:.1f}%",
                    p["sucesso"] if kpi["resultado_periodo"] >= 0 else p["perigo"],
                ),
                "insumos": (
                    f"{cur} {kpi['capital_insumos']:.2f}",
                    f"{kpi['total_insumos']} items ({kpi['insumos_alerta']} low stock)",
                    p["primaria"],
                ),
                "lotes": (
                    f"{cur} {kpi['custo_lotes_ativos']:.2f}",
                    f"Potential rev.: {cur} {kpi['venda_potencial_lotes']:.2f} ({kpi['lotes_ativos']} batches)",
                    p["roxo"],
                ),
                "vendas": (
                    f"{cur} {kpi['faturamento_lotes']:.2f}",
                    f"Gross Profit: {cur} {kpi['lucro_bruto_vendas']:.2f} (Margin: {kpi['margem_bruta_vendas']:.1f}%)",
                    p["sucesso"],
                ),
                "giro": (
                    f"{kpi['giro_producao']:.1f}% sold",
                    f"{kpi['total_escoado']} sold of {kpi['total_produzido']} produced ({kpi['total_disponivel']} avail.)",
                    p["aviso"],
                ),
            }
        else:
            kpi_values = {
                "saldo": (
                    f"{cur} {kpi['saldo_global']:.2f}",
                    f"Acumulado: +{cur} {kpi['rec_global']:.0f} / -{cur} {kpi['desp_global']:.0f}",
                    p["sucesso"] if kpi["saldo_global"] >= 0 else p["perigo"],
                ),
                "receitas": (
                    f"{cur} {kpi['rec_periodo']:.2f}",
                    f"{kpi['n_rec']} lançamento(s) de entrada no período",
                    p["sucesso"],
                ),
                "despesas": (
                    f"{cur} {kpi['desp_periodo']:.2f}",
                    f"{kpi['n_desp']} lançamento(s) de saída no período",
                    p["perigo"],
                ),
                "resultado": (
                    f"{cur} {kpi['resultado_periodo']:.2f}",
                    f"Margem líquida de caixa: {kpi['margem_caixa']:.1f}%",
                    p["sucesso"] if kpi["resultado_periodo"] >= 0 else p["perigo"],
                ),
                "insumos": (
                    f"{cur} {kpi['capital_insumos']:.2f}",
                    f"{kpi['total_insumos']} insumos ({kpi['insumos_alerta']} abaixo do mín.)",
                    p["primaria"],
                ),
                "lotes": (
                    f"{cur} {kpi['custo_lotes_ativos']:.2f}",
                    f"Venda potencial: {cur} {kpi['venda_potencial_lotes']:.2f} ({kpi['lotes_ativos']} lotes)",
                    p["roxo"],
                ),
                "vendas": (
                    f"{cur} {kpi['faturamento_lotes']:.2f}",
                    f"Lucro Bruto: {cur} {kpi['lucro_bruto_vendas']:.2f} (Margem: {kpi['margem_bruta_vendas']:.1f}%)",
                    p["sucesso"],
                ),
                "giro": (
                    f"{kpi['giro_producao']:.1f}% escoado",
                    f"{kpi['total_escoado']} vendidas de {kpi['total_produzido']} produzidas ({kpi['total_disponivel']} disp.)",
                    p["aviso"],
                ),
            }

        for key, (card, lbl_tit, lbl_val, lbl_sub, _) in self.kpi_cards.items():
            val_txt, sub_txt, col_val = kpi_values[key]
            card.configure(bg=p["bg_card"], highlightbackground=p["borda"], highlightcolor=p["borda"])
            lbl_tit.configure(bg=p["bg_card"], fg=p["texto_suave"])
            lbl_val.configure(bg=p["bg_card"], fg=col_val, text=val_txt)
            lbl_sub.configure(bg=p["bg_card"], fg=p["texto_suave"], text=sub_txt)

        # Alerts banner
        self.alerts_frame.configure(bg=p["bg_card"])
        alerts = database.ingredientes_abaixo_minimo()
        if alerts:
            names = ", ".join(a["nome"] for a in alerts[:4])
            extra = "..." if len(alerts) > 4 else ""
            msg = (
                f"⚠ Low stock ingredients ({len(alerts)}): {names}{extra}"
                if en
                else f"⚠ Insumos críticos ({len(alerts)}): {names}{extra}"
            )
            self.lbl_alert_inputs.configure(bg=p["bg_card"], fg=p["perigo"], text=msg)
        else:
            msg = (
                "✔ Ingredient inventory healthy (no items below minimum stock)."
                if en
                else "✔ Estoque de insumos saudável (nenhum item abaixo do mínimo)."
            )
            self.lbl_alert_inputs.configure(bg=p["bg_card"], fg=p["sucesso"], text=msg)

        expired, expiring = database.lotes_alertas_vencimento()
        if expired or expiring:
            risk_cost = sum(
                (l["custo_unitario"] * l["quantidade_disponivel"]) for l in (expired + expiring)
            )
            msg = (
                f"⚠ Shelf-life alert: {len(expired)} expired, {len(expiring)} expiring ({cur} {risk_cost:.2f} at risk)"
                if en
                else f"⚠ Perecibilidade: {len(expired)} vencido(s), {len(expiring)} vencendo ({cur} {risk_cost:.2f} em risco)"
            )
            self.lbl_alert_batches.configure(bg=p["bg_card"], fg=p["aviso"], text=msg)
        else:
            msg = (
                "✔ All active product batches are within safe shelf-life dates."
                if en
                else "✔ Todos os lotes ativos dentro do prazo seguro de validade."
            )
            self.lbl_alert_batches.configure(bg=p["bg_card"], fg=p["sucesso"], text=msg)

        # Render charts across both sub-tabs
        for fig, cv in ((self.fig_fin, self.canvas_fin), (self.fig_est, self.canvas_est)):
            fig.patch.set_facecolor(p["bg_principal"])
            cv.get_tk_widget().configure(bg=p["bg_principal"])

        self._chart_cashflow(p)
        self._chart_expenses_by_category(p, ini, fim)
        self._chart_recipe_profitability(p)
        self._chart_sales_vs_cogs(p, ini, fim)
        self.fig_fin.tight_layout(pad=2.4)
        self.canvas_fin.draw()

        self._chart_batches(p)
        self._chart_ingredient_capital(p)
        self._chart_ingredient_evolution(p)
        self._chart_expiry_health(p)
        self.fig_est.tight_layout(pad=2.4)
        self.canvas_est.draw()

    # Alias for legacy callers
    atualizar = refresh

    # ══════════════════════════════════════════ VIEW 1 CHARTS (FINANCE)
    def _chart_cashflow(self, p):
        self.ax_cashflow.clear()
        self._style_axis(self.ax_cashflow, t("chart_cashflow"))
        data = database.fluxo_caixa_mensal()
        if not data:
            self.ax_cashflow.text(0.5, 0.5, t("chart_no_data"), ha="center", va="center", color=p["texto_suave"])
            return
        months = [d[0] for d in data]
        revs = [d[1] for d in data]
        exps = [d[2] for d in data]
        nets = [r - d for r, d in zip(revs, exps)]
        pos = list(range(len(months)))
        w = 0.34
        en = I18n.is_en()
        b1 = self.ax_cashflow.bar([i - w / 2 for i in pos], revs, w, label=t("revenue"), color=p["sucesso"])
        b2 = self.ax_cashflow.bar([i + w / 2 for i in pos], exps, w, label=t("expense"), color=p["perigo"])
        self.ax_cashflow.plot(
            pos, nets, marker="o", linewidth=2, color=p["primaria"], label="Net Result" if en else "Resultado Líq."
        )
        self._annotate_bars(self.ax_cashflow, b1, decimals=0)
        self._annotate_bars(self.ax_cashflow, b2, decimals=0)
        self.ax_cashflow.set_xticks(pos)
        self.ax_cashflow.set_xticklabels(months, rotation=20, ha="right", fontsize=8)
        self.ax_cashflow.legend(fontsize=7.5, facecolor=p["bg_card"], edgecolor=p["borda"], labelcolor=p["texto"])

    def _chart_expenses_by_category(self, p, ini, fim):
        self.ax_exp_cat.clear()
        self.ax_exp_cat.set_facecolor(p["bg_card"])
        self.ax_exp_cat.set_title(
            t("chart_exp_cat"), color=p["texto"], fontsize=9.5, fontweight="bold", pad=8
        )
        data = database.despesas_por_categoria(ini, fim)
        if not data:
            self.ax_exp_cat.text(0.5, 0.5, t("chart_no_data"), ha="center", va="center", color=p["texto_suave"])
            self.ax_exp_cat.set_xticks([])
            self.ax_exp_cat.set_yticks([])
            for sp in self.ax_exp_cat.spines.values():
                sp.set_color(p["borda"])
            return
        cats = [d[0][:18] for d in data[:6]]
        vals = [d[1] for d in data[:6]]
        colors = [p["perigo"], p["aviso"], p["roxo"], p["primaria"], p["sucesso"], "#64748b"]
        _, _, autotexts = self.ax_exp_cat.pie(
            vals,
            labels=cats,
            autopct="%1.1f%%",
            startangle=140,
            colors=colors[: len(vals)],
            pctdistance=0.75,
            wedgeprops={"width": 0.45, "edgecolor": p["bg_card"]},
            textprops={"color": p["texto"], "fontsize": 8},
        )
        for at in autotexts:
            at.set_color("#ffffff")
            at.set_fontweight("bold")
            at.set_fontsize(7.5)

    def _chart_recipe_profitability(self, p):
        self.ax_unit_margin.clear()
        self._style_axis(self.ax_unit_margin, t("chart_unit_margin"))
        data = database.analise_rentabilidade_receitas()
        if not data:
            self.ax_unit_margin.text(0.5, 0.5, t("chart_no_data"), ha="center", va="center", color=p["texto_suave"])
            return
        names = [d["nome"][:16] for d in data]
        costs = [d["custo_unitario"] for d in data]
        profits = [max(0, d["lucro_unitario"]) for d in data]
        pos = list(range(len(names)))
        w = 0.45
        en = I18n.is_en()
        self.ax_unit_margin.bar(pos, costs, w, label="Unit Cost" if en else "Custo Unit.", color=p["aviso"])
        self.ax_unit_margin.bar(
            pos, profits, w, bottom=costs, label="Unit Profit" if en else "Lucro Unit.", color=p["sucesso"]
        )
        for idx, d in enumerate(data):
            if d["preco_venda"] > 0:
                self.ax_unit_margin.annotate(
                    f"{d['margem_percentual']:.0f}%",
                    xy=(idx, costs[idx] + profits[idx]),
                    xytext=(0, 2),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=7.5,
                    color=p["texto"],
                    fontweight="bold",
                )
        self.ax_unit_margin.set_xticks(pos)
        self.ax_unit_margin.set_xticklabels(names, rotation=20, ha="right", fontsize=8)
        self.ax_unit_margin.legend(fontsize=7.5, facecolor=p["bg_card"], edgecolor=p["borda"], labelcolor=p["texto"])

    def _chart_sales_vs_cogs(self, p, ini, fim):
        self.ax_sales_cmv.clear()
        self._style_axis(self.ax_sales_cmv, t("chart_sales_cmv"))
        data = database.desempenho_vendas_por_receita(ini, fim)
        if not data:
            self.ax_sales_cmv.text(0.5, 0.5, t("chart_no_data"), ha="center", va="center", color=p["texto_suave"])
            return
        names = [d["receita"][:16] for d in data]
        revs = [d["faturamento"] for d in data]
        cmvs = [d["cmv"] for d in data]
        pos = list(range(len(names)))
        w = 0.35
        en = I18n.is_en()
        b1 = self.ax_sales_cmv.bar(
            [i - w / 2 for i in pos], revs, w, label="Revenue" if en else "Faturamento", color=p["primaria"]
        )
        b2 = self.ax_sales_cmv.bar(
            [i + w / 2 for i in pos], cmvs, w, label="COGS" if en else "Custo (CMV)", color=p["aviso"]
        )
        self._annotate_bars(self.ax_sales_cmv, b1, decimals=0)
        self._annotate_bars(self.ax_sales_cmv, b2, decimals=0)
        self.ax_sales_cmv.set_xticks(pos)
        self.ax_sales_cmv.set_xticklabels(names, rotation=20, ha="right", fontsize=8)
        self.ax_sales_cmv.legend(fontsize=7.5, facecolor=p["bg_card"], edgecolor=p["borda"], labelcolor=p["texto"])

    # ══════════════════════════════════════════ VIEW 2 CHARTS (INVENTORY & PRODUCTION)
    def _chart_batches(self, p):
        self.ax_batches.clear()
        self._style_axis(self.ax_batches, t("chart_prod_vol"))
        data = database.resumo_lotes_produto()
        if not data:
            self.ax_batches.text(0.5, 0.5, t("chart_no_data"), ha="center", va="center", color=p["texto_suave"])
            return
        names = [d["receita"][:16] for d in data]
        fab = [d["fabricadas"] for d in data]
        sold = [d["saidas"] for d in data]
        avail = [d["disponivel"] for d in data]
        pos = list(range(len(names)))
        w = 0.26
        en = I18n.is_en()
        b1 = self.ax_batches.bar(
            [i - w for i in pos], fab, w, label="Produced" if en else "Fabricado", color=p["roxo"]
        )
        b2 = self.ax_batches.bar(pos, sold, w, label="Sold" if en else "Vendido", color=p["primaria"])
        b3 = self.ax_batches.bar(
            [i + w for i in pos], avail, w, label="Available" if en else "Disponível", color=p["sucesso"]
        )
        self._annotate_bars(self.ax_batches, b1, decimals=0)
        self._annotate_bars(self.ax_batches, b2, decimals=0)
        self._annotate_bars(self.ax_batches, b3, decimals=0)
        self.ax_batches.set_xticks(pos)
        self.ax_batches.set_xticklabels(names, rotation=20, ha="right", fontsize=8)
        self.ax_batches.legend(fontsize=7.5, facecolor=p["bg_card"], edgecolor=p["borda"], labelcolor=p["texto"])

    def _chart_ingredient_capital(self, p):
        self.ax_cost.clear()
        self._style_axis(self.ax_cost, t("chart_ing_cap"))
        data = sorted(database.estoque_ingredientes_resumo(), key=lambda r: r["valor_total"], reverse=True)
        if not data:
            self.ax_cost.text(0.5, 0.5, t("chart_no_data"), ha="center", va="center", color=p["texto_suave"])
            return
        names = [d["nome"][:15] for d in data[:8]]
        vals = [d["valor_total"] for d in data[:8]]
        colors = [
            p["perigo"] if d["quantidade"] <= d["estoque_minimo"] else p["primaria"]
            for d in data[:8]
        ]
        pos = list(range(len(names)))
        b = self.ax_cost.bar(pos, vals, color=colors, width=0.55)
        self._annotate_bars(self.ax_cost, b, decimals=0)
        self.ax_cost.set_xticks(pos)
        self.ax_cost.set_xticklabels(names, rotation=20, ha="right", fontsize=8)

    def _chart_ingredient_evolution(self, p):
        self.ax_stock.clear()
        self._style_axis(self.ax_stock, t("chart_ing_evol"))
        data = database.evolucao_mov_ingredientes()
        if not data:
            self.ax_stock.text(0.5, 0.5, t("chart_no_data"), ha="center", va="center", color=p["texto_suave"])
            return
        dates = [d[0] for d in data]
        vals = [d[1] for d in data]
        pos = list(range(len(dates)))
        self.ax_stock.plot(pos, vals, marker="o", linewidth=2, color=p["primaria"])
        self.ax_stock.fill_between(pos, vals, alpha=0.18, color=p["primaria"])
        self.ax_stock.set_xticks(pos)
        self.ax_stock.set_xticklabels(dates, rotation=20, ha="right", fontsize=8)

    def _chart_expiry_health(self, p):
        self.ax_expiry.clear()
        self._style_axis(self.ax_expiry, t("chart_exp_health"))
        batches = database.listar_lotes(apenas_ativos=True)
        if not batches:
            self.ax_expiry.text(0.5, 0.5, t("chart_no_data"), ha="center", va="center", color=p["texto_suave"])
            return
        today_dt = datetime.now().date()
        healthy, expiring, expired, no_exp = 0, 0, 0, 0
        for b in batches:
            qty = b["quantidade_disponivel"]
            exp = b["data_vencimento"]
            if not exp:
                no_exp += qty
                continue
            try:
                dv = datetime.strptime(exp, "%Y-%m-%d").date()
                delta = (dv - today_dt).days
                if delta < 0:
                    expired += qty
                elif delta <= 7:
                    expiring += qty
                else:
                    healthy += qty
            except ValueError:
                no_exp += qty

        en = I18n.is_en()
        cats = (
            ["Healthy (>7d)", "Expiring (≤7d)", "Expired", "No Expiry"]
            if en
            else ["Em dia (>7d)", "Vencendo (≤7d)", "Vencido", "Sem validade"]
        )
        vals = [healthy, expiring, expired, no_exp]
        colors = [p["sucesso"], p["aviso"], p["perigo"], p["secundaria_hover"]]
        b = self.ax_expiry.bar(range(len(cats)), vals, color=colors, width=0.5)
        self._annotate_bars(self.ax_expiry, b, suffix=" un", decimals=0)
        self.ax_expiry.set_xticks(range(len(cats)))
        self.ax_expiry.set_xticklabels(cats, fontsize=8)


# Backward-compatible alias
EstatisticasFrame = AnalyticsFrame

