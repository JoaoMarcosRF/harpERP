"""
ui/products_frame.py — Manufacturing Batches, Simulator & FEFO Sales Tab
========================================================================
Handles batch manufacturing orders, Production Simulator & Shopping List,
and batch depletion via automatic FEFO (First-Expired, First-Out) or specific batch.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

import database
from ui.i18n import I18n, t
from ui.theme import ThemeManager, configure_treeview_tags
from ui.utils import enable_treeview_sorting


class ProductsFrame(ttk.Frame):
    def __init__(self, parent, on_change=None):
        super().__init__(parent, padding=10)
        self.on_change = on_change or (lambda: None)
        self._recipes_map = {}
        self._recipes_price = {}
        self._batches_map = {}
        self._batch_price = {}
        self._fefo_map = {}

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()
        ThemeManager.register_listener(self._on_theme_change)
        I18n.register_listener(self._on_language_change)
        self.refresh_recipes()
        self.refresh_batches()

    def _build_left_panel(self):
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # ── Manufacturing Card
        self.card_fab = ttk.LabelFrame(left, text=t("prod_fab_title"), padding=10)
        self.card_fab.pack(fill="x")

        self.lbl_rec = ttk.Label(self.card_fab, text=t("prod_recipe"), style="Card.TLabel")
        self.lbl_rec.grid(row=0, column=0, sticky="w", pady=3)
        self.receita_var = tk.StringVar()
        self.combo_receita = ttk.Combobox(
            self.card_fab, textvariable=self.receita_var, width=28, state="readonly"
        )
        self.combo_receita.grid(row=0, column=1, pady=3, padx=(8, 0))
        self.combo_receita.bind("<<ComboboxSelected>>", self._on_select_recipe)

        self.lbl_info_receita = ttk.Label(
            self.card_fab, text="", style="CardMuted.TLabel", wraplength=295
        )
        self.lbl_info_receita.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 4))

        self.lbl_num_batches = ttk.Label(self.card_fab, text=t("prod_num_batches"), style="Card.TLabel")
        self.lbl_num_batches.grid(row=2, column=0, sticky="w", pady=3)
        self.lotes_var = tk.StringVar(value="1")
        self.lotes_var.trace_add("write", self._update_preview)
        ttk.Entry(self.card_fab, textvariable=self.lotes_var, width=8).grid(
            row=2, column=1, sticky="w", pady=3, padx=(8, 0)
        )

        self.lbl_preview = ttk.Label(
            self.card_fab, text="", style="CardBold.TLabel", wraplength=295
        )
        self.lbl_preview.grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 4))

        self.card_val = ttk.LabelFrame(self.card_fab, text=t("prod_val_title"), padding=6)
        self.card_val.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        self.lbl_exp_date = ttk.Label(self.card_val, text=t("prod_exp_date"), style="Card.TLabel")
        self.lbl_exp_date.grid(row=0, column=0, sticky="w")
        self.venc_var = tk.StringVar()
        ttk.Entry(self.card_val, textvariable=self.venc_var, width=14).grid(
            row=0, column=1, padx=6, sticky="w"
        )

        self.lbl_exp_days = ttk.Label(self.card_val, text=t("prod_exp_days"), style="Card.TLabel")
        self.lbl_exp_days.grid(row=1, column=0, sticky="w", pady=(3, 0))
        self.prazo_var = tk.StringVar()
        self.prazo_var.trace_add("write", self._calculate_expiration)
        ttk.Entry(self.card_val, textvariable=self.prazo_var, width=6).grid(
            row=1, column=1, sticky="w", padx=6, pady=(3, 0)
        )
        self.lbl_exp_suffix = ttk.Label(self.card_val, text=t("prod_exp_suffix"), style="CardMuted.TLabel")
        self.lbl_exp_suffix.grid(row=1, column=2, sticky="w")

        self.lbl_fab_notes = ttk.Label(self.card_fab, text=t("prod_notes"), style="Card.TLabel")
        self.lbl_fab_notes.grid(row=5, column=0, sticky="w", pady=(6, 3))
        self.obs_fab_var = tk.StringVar()
        ttk.Entry(self.card_fab, textvariable=self.obs_fab_var, width=30).grid(
            row=5, column=1, pady=(6, 3), padx=(8, 0)
        )

        btns_fab = ttk.Frame(self.card_fab, style="Card.TFrame")
        btns_fab.grid(row=6, column=0, columnspan=2, pady=(8, 0))
        self.btn_fab = ttk.Button(
            btns_fab, text=t("prod_btn_fab"), style="Primary.TButton", command=self.produce_batch
        )
        self.btn_fab.pack(side="left", padx=3)
        self.btn_sim = ttk.Button(
            btns_fab, text=t("prod_btn_sim"), command=self.open_simulator
        )
        self.btn_sim.pack(side="left", padx=3)

        # ── Outflow / Sale Card (FEFO or Specific Batch)
        self.card_sale = ttk.LabelFrame(left, text=t("prod_sale_title"), padding=10)
        self.card_sale.pack(fill="x", pady=(10, 0))

        self.lbl_sale_mode = ttk.Label(self.card_sale, text=t("prod_sale_mode"), style="Card.TLabel")
        self.lbl_sale_mode.grid(row=0, column=0, sticky="w", pady=3)
        self.modo_saida_var = tk.StringVar(value="fefo")
        mf = ttk.Frame(self.card_sale, style="Card.TFrame")
        mf.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.rb_fefo = ttk.Radiobutton(
            mf, text=t("prod_mode_fefo"), variable=self.modo_saida_var,
            value="fefo", command=self._switch_depletion_mode
        )
        self.rb_fefo.pack(side="left")
        self.rb_batch = ttk.Radiobutton(
            mf, text=t("prod_mode_batch"), variable=self.modo_saida_var,
            value="lote", command=self._switch_depletion_mode
        )
        self.rb_batch.pack(side="left", padx=(8, 0))

        self.lbl_alvo_saida = ttk.Label(self.card_sale, text=t("prod_target_recipe"), style="Card.TLabel")
        self.lbl_alvo_saida.grid(row=1, column=0, sticky="w", pady=3)
        self.lote_saida_var = tk.StringVar()
        self.combo_lote = ttk.Combobox(
            self.card_sale, textvariable=self.lote_saida_var, width=28, state="readonly"
        )
        self.combo_lote.grid(row=1, column=1, pady=3, padx=(8, 0))
        self.combo_lote.bind("<<ComboboxSelected>>", self._on_select_sale_target)

        self.lbl_sale_qty = ttk.Label(self.card_sale, text=t("prod_sale_qty"), style="Card.TLabel")
        self.lbl_sale_qty.grid(row=2, column=0, sticky="w", pady=3)
        self.saida_qtd_var = tk.StringVar()
        ttk.Entry(self.card_sale, textvariable=self.saida_qtd_var, width=10).grid(
            row=2, column=1, sticky="w", pady=3, padx=(8, 0)
        )

        self.lbl_sale_price = ttk.Label(self.card_sale, text=t("prod_sale_price"), style="Card.TLabel")
        self.lbl_sale_price.grid(row=3, column=0, sticky="w", pady=3)
        self.saida_preco_var = tk.StringVar()
        ttk.Entry(self.card_sale, textvariable=self.saida_preco_var, width=10).grid(
            row=3, column=1, sticky="w", pady=3, padx=(8, 0)
        )

        self.lbl_sale_notes = ttk.Label(self.card_sale, text=t("prod_notes"), style="Card.TLabel")
        self.lbl_sale_notes.grid(row=4, column=0, sticky="w", pady=3)
        self.saida_obs_var = tk.StringVar()
        ttk.Entry(self.card_sale, textvariable=self.saida_obs_var, width=30).grid(
            row=4, column=1, pady=3, padx=(8, 0)
        )

        self.saida_fin_var = tk.BooleanVar(value=True)
        self.chk_sale_fin = ttk.Checkbutton(
            self.card_sale, text=t("prod_auto_fin"), variable=self.saida_fin_var
        )
        self.chk_sale_fin.grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self.btn_sale = ttk.Button(
            self.card_sale, text=t("prod_btn_sale"), style="Success.TButton", command=self.record_sale
        )
        self.btn_sale.grid(row=6, column=0, columnspan=2, pady=(10, 0))

    def _build_right_panel(self):
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_rowconfigure(3, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self.lbl_list_title = ttk.Label(right, text=t("prod_list_title"), style="SectionTitle.TLabel")
        self.lbl_list_title.grid(row=0, column=0, sticky="w", pady=(0, 6))

        cols_l = (
            "id", "receita_nome", "data_fabricacao", "data_vencimento",
            "quantidade_total", "quantidade_disponivel", "custo_unitario", "preco_venda"
        )
        self.tab_lotes = ttk.Treeview(right, columns=cols_l, show="headings", height=10)
        widths_l = {
            "id": 45, "quantidade_total": 60, "quantidade_disponivel": 70,
            "custo_unitario": 90, "preco_venda": 90, "data_fabricacao": 90, "data_vencimento": 90
        }
        for c in cols_l:
            self.tab_lotes.column(c, width=widths_l.get(c, 130), anchor="center")
        self.tab_lotes.grid(row=1, column=0, sticky="nsew")

        scroll_lotes = ttk.Scrollbar(right, orient="vertical", command=self.tab_lotes.yview)
        scroll_lotes.grid(row=1, column=1, sticky="ns")
        self.tab_lotes.configure(yscrollcommand=scroll_lotes.set)
        enable_treeview_sorting(self.tab_lotes)
        configure_treeview_tags(self.tab_lotes)

        filtro = ttk.Frame(right)
        filtro.grid(row=2, column=0, sticky="ew", pady=(8, 8))
        self.apenas_ativos_var = tk.BooleanVar(value=False)
        self.chk_active = ttk.Checkbutton(
            filtro, text=t("prod_chk_active"), style="Surface.TCheckbutton",
            variable=self.apenas_ativos_var, command=self.refresh_batches
        )
        self.chk_active.pack(side="left")
        self.btn_refresh = ttk.Button(filtro, text=t("btn_refresh"), command=self.refresh_batches)
        self.btn_refresh.pack(side="right")

        cols_s = ("id", "data", "receita_nome", "quantidade", "preco_unitario", "valor_total", "observacao")
        self.tab_saidas = ttk.Treeview(right, columns=cols_s, show="headings", height=7)
        for c in cols_s:
            self.tab_saidas.column(c, width=55 if c in ("id", "quantidade") else 105, anchor="center")
        self.tab_saidas.grid(row=3, column=0, sticky="nsew", pady=(5, 0))
        scroll_saidas = ttk.Scrollbar(right, orient="vertical", command=self.tab_saidas.yview)
        scroll_saidas.grid(row=3, column=1, sticky="ns", pady=(5, 0))
        self.tab_saidas.configure(yscrollcommand=scroll_saidas.set)
        enable_treeview_sorting(self.tab_saidas)
        configure_treeview_tags(self.tab_saidas)

        self.tab_saidas.grid_remove()
        self.scroll_saidas = scroll_saidas
        self.scroll_saidas.grid_remove()

        self.btn_toggle_sales = ttk.Button(
            right, text=t("prod_btn_toggle_sales"), command=self._toggle_sales_history
        )
        self.btn_toggle_sales.grid(row=4, column=0, sticky="e", pady=(6, 0))
        self._update_table_headings()

    def _update_table_headings(self):
        lotes_heads = {
            "id": t("prod_col_id"),
            "receita_nome": t("prod_col_rec"),
            "data_fabricacao": t("prod_col_fab"),
            "data_vencimento": t("prod_col_exp"),
            "quantidade_total": t("prod_col_tot"),
            "quantidade_disponivel": t("prod_col_avail"),
            "custo_unitario": t("prod_col_ucost"),
            "preco_venda": t("prod_col_usell"),
        }
        for c, txt in lotes_heads.items():
            self.tab_lotes.heading(c, text=txt)

        saidas_heads = {
            "id": t("prod_scol_id"),
            "data": t("prod_scol_date"),
            "receita_nome": t("prod_scol_rec"),
            "quantidade": t("prod_scol_qty"),
            "preco_unitario": t("prod_scol_price"),
            "valor_total": t("prod_scol_total"),
            "observacao": t("prod_scol_notes"),
        }
        for c, txt in saidas_heads.items():
            self.tab_saidas.heading(c, text=txt)

    def _on_theme_change(self):
        configure_treeview_tags(self.tab_lotes)
        configure_treeview_tags(self.tab_saidas)
        self._update_preview()

    def _on_language_change(self):
        self.card_fab.config(text=t("prod_fab_title"))
        self.lbl_rec.config(text=t("prod_recipe"))
        self.lbl_num_batches.config(text=t("prod_num_batches"))
        self.card_val.config(text=t("prod_val_title"))
        self.lbl_exp_date.config(text=t("prod_exp_date"))
        self.lbl_exp_days.config(text=t("prod_exp_days"))
        self.lbl_exp_suffix.config(text=t("prod_exp_suffix"))
        self.lbl_fab_notes.config(text=t("prod_notes"))
        self.btn_fab.config(text=t("prod_btn_fab"))
        self.btn_sim.config(text=t("prod_btn_sim"))

        self.card_sale.config(text=t("prod_sale_title"))
        self.lbl_sale_mode.config(text=t("prod_sale_mode"))
        self.rb_fefo.config(text=t("prod_mode_fefo"))
        self.rb_batch.config(text=t("prod_mode_batch"))
        self.lbl_sale_qty.config(text=t("prod_sale_qty"))
        self.lbl_sale_price.config(text=t("prod_sale_price"))
        self.lbl_sale_notes.config(text=t("prod_notes"))
        self.chk_sale_fin.config(text=t("prod_auto_fin"))
        self.btn_sale.config(text=t("prod_btn_sale"))

        self.lbl_list_title.config(text=t("prod_list_title"))
        self.chk_active.config(text=t("prod_chk_active"))
        self.btn_refresh.config(text=t("btn_refresh"))
        self.btn_toggle_sales.config(text=t("prod_btn_toggle_sales"))
        self._update_table_headings()
        self._switch_depletion_mode()
        self._update_preview()

    # ══════════════════════════════════════════ DATA
    def refresh_recipes(self):
        recs = database.listar_receitas()
        self._recipes_map = {}
        self._recipes_price = {}
        for r in recs:
            key = f'{r["nome"]}  ({r["rendimento"]} un/batch)'
            self._recipes_map[key] = r["id"]
            self._recipes_price[r["id"]] = r["preco_venda"] or 0.0
        self.combo_receita["values"] = list(self._recipes_map.keys())

    def refresh_batches(self):
        for i in self.tab_lotes.get_children():
            self.tab_lotes.delete(i)

        only_active = self.apenas_ativos_var.get()
        batches = database.listar_lotes(apenas_ativos=only_active)
        today = datetime.now().date()

        batches_combo = []
        self._batch_price = {}
        for idx, l in enumerate(batches):
            zebra = "par" if idx % 2 == 0 else "impar"
            tag = zebra
            venc = l["data_vencimento"] or "—"
            if l["quantidade_disponivel"] == 0:
                tag = "zerado"
            elif venc != "—":
                try:
                    dv = datetime.strptime(venc, "%Y-%m-%d").date()
                    delta = (dv - today).days
                    if delta < 0:
                        tag = "vencido"
                    elif delta <= 7:
                        tag = "vencendo"
                except ValueError:
                    pass

            pv = l["preco_venda_sugerido"] or 0.0
            pv_str = f"{pv:.2f}" if pv > 0 else "—"
            self._batch_price[l["id"]] = pv
            self.tab_lotes.insert("", "end", iid=l["id"], tags=(tag,), values=(
                l["id"], l["receita_nome"],
                l["data_fabricacao"], venc,
                l["quantidade_total"], l["quantidade_disponivel"],
                f'{l["custo_unitario"]:.4f}', pv_str
            ))
            if l["quantidade_disponivel"] > 0:
                batches_combo.append(
                    f'Batch #{l["id"]} — {l["receita_nome"]} '
                    f'(avail: {l["quantidade_disponivel"]}, exp: {venc})'
                )

        self._batches_map = {}
        for txt in batches_combo:
            lid = int(txt.split("#")[1].split(" ")[0])
            self._batches_map[txt] = lid

        self._switch_depletion_mode()

    def _switch_depletion_mode(self):
        self.lote_saida_var.set("")
        if self.modo_saida_var.get() == "fefo":
            self.lbl_alvo_saida.config(text=t("prod_target_recipe"))
            summary = database.resumo_lotes_produto()
            self._fefo_map = {}
            recs = {r["nome"]: r["id"] for r in database.listar_receitas()}
            for d in summary:
                if d["disponivel"] > 0 and d["receita"] in recs:
                    key = f'{d["receita"]} (avail: {d["disponivel"]} un.)'
                    self._fefo_map[key] = recs[d["receita"]]
            self.combo_lote["values"] = list(self._fefo_map.keys())
        else:
            self.lbl_alvo_saida.config(text=t("prod_target_batch"))
            self.combo_lote["values"] = list(self._batches_map.keys())

    def _refresh_sales_history(self):
        for i in self.tab_saidas.get_children():
            self.tab_saidas.delete(i)
        for idx, s in enumerate(database.listar_saidas_lote()):
            zebra = "par" if idx % 2 == 0 else "impar"
            self.tab_saidas.insert("", "end", tags=(zebra,), values=(
                s["id"], s["data"], s["receita_nome"],
                s["quantidade"],
                f'{s["preco_unitario"]:.2f}',
                f'{s["valor_total"]:.2f}',
                s["observacao"]
            ))

    def _toggle_sales_history(self):
        if self.tab_saidas.winfo_ismapped():
            self.tab_saidas.grid_remove()
            self.scroll_saidas.grid_remove()
        else:
            self._refresh_sales_history()
            self.tab_saidas.grid()
            self.scroll_saidas.grid()

    # ══════════════════════════════════════════ PREVIEW & SIMULATOR
    def _on_select_recipe(self, _=None):
        rid = self._recipes_map.get(self.receita_var.get())
        if rid is None:
            return
        rec, comps = database.obter_receita(rid)
        batch_cost, unit_cost = database.calcular_custo_receita(rid)
        info_ings = ", ".join(
            f'{c["ingrediente_nome"]} ({round(c["quantidade"], 4)} {c["unidade"]})'
            for c in comps
        )
        self.lbl_info_receita.config(
            text=f'{info_ings}  |  Cost/batch: $ {batch_cost:.2f}  |  Unit: $ {unit_cost:.2f}'
        )
        if rec and rec["validade_dias"]:
            self.prazo_var.set(str(rec["validade_dias"]))
        else:
            self.prazo_var.set("")
            self.venc_var.set("")
        self._update_preview()

    def _on_select_sale_target(self, _=None):
        key = self.lote_saida_var.get()
        if self.modo_saida_var.get() == "fefo":
            rid = self._fefo_map.get(key)
            if rid is not None:
                pv = self._recipes_price.get(rid, 0.0)
                if pv > 0:
                    self.saida_preco_var.set(f"{pv:.2f}")
        else:
            lid = self._batches_map.get(key)
            if lid is not None:
                pv = self._batch_price.get(lid, 0.0)
                if pv and pv > 0:
                    self.saida_preco_var.set(f"{pv:.2f}")

    def _update_preview(self, *_):
        p = ThemeManager.palette()
        rid = self._recipes_map.get(self.receita_var.get())
        if rid is None:
            return
        try:
            batches = int(self.lotes_var.get())
            if batches <= 0:
                raise ValueError
        except ValueError:
            self.lbl_preview.config(text="")
            return
        sim = database.simular_producao_e_compras(rid, batches)
        batch_cost, _ = database.calcular_custo_receita(rid)
        total_cost = batch_cost * batches
        if I18n.is_en():
            cap_txt = (
                f"✔ Current stock supports up to {sim['max_lotes_possiveis']} batch(es)"
                if sim["viavel"]
                else f"⚠ Missing inputs (max now: {sim['max_lotes_possiveis']} | restock: $ {sim['custo_reposicao_total']:.2f})"
            )
            line1 = f"→ {batches} batch(es) = {sim['unidades_desejadas']} un. | Cost: $ {total_cost:.2f}"
        else:
            cap_txt = (
                f"✔ Estoque comporta até {sim['max_lotes_possiveis']} lote(s)"
                if sim["viavel"]
                else f"⚠ Faltam insumos (máx. atual: {sim['max_lotes_possiveis']} | reposição: R$ {sim['custo_reposicao_total']:.2f})"
            )
            line1 = f"→ {batches} lote(s) = {sim['unidades_desejadas']} un. | Custo: R$ {total_cost:.2f}"

        color = p["sucesso"] if sim["viavel"] else p["aviso"]
        self.lbl_preview.config(text=f"{line1}\n{cap_txt}", foreground=color)

    def open_simulator(self):
        rid = self._recipes_map.get(self.receita_var.get())
        if rid is None:
            messagebox.showinfo(t("prod_sim_title"), t("ing_err_select"))
            return
        try:
            batches = max(1, int(self.lotes_var.get()))
        except ValueError:
            batches = 1

        sim = database.simular_producao_e_compras(rid, batches)
        p = ThemeManager.palette()

        win = tk.Toplevel(self)
        win.title(f"{t('prod_sim_title')} — {sim['receita_nome']}")
        win.geometry("760x440")
        win.configure(bg=p["bg_principal"])

        top = ttk.Frame(win, padding=12)
        top.pack(fill="x")
        ttk.Label(
            top,
            text=f"{sim['receita_nome']} — {batches} batch(es) ({sim['unidades_desejadas']} units)",
            style="SectionTitle.TLabel",
        ).pack(anchor="w")

        summary_txt = (
            f"Max Immediate Capacity: {sim['max_lotes_possiveis']} batch(es) ({sim['max_unidades_possiveis']} un.)  |  "
            f"Bottleneck: {sim['gargalo'] or '—'}  |  "
            f"Estimated Restock Cost: $ {sim['custo_reposicao_total']:.2f}"
        )
        ttk.Label(top, text=summary_txt).pack(anchor="w", pady=(4, 0))

        body = ttk.Frame(win, padding=(12, 4))
        body.pack(fill="both", expand=True)

        cols = ("ingrediente", "necessario", "disponivel", "falta", "custo_rep", "status")
        rots = ("Ingredient", "Required", "In Stock", "To Buy", "Restock Cost ($)", "Status")
        tree = ttk.Treeview(body, columns=cols, show="headings", height=11)
        for c, r in zip(cols, rots):
            tree.heading(c, text=r)
            tree.column(c, width=150 if c == "ingrediente" else 110, anchor="center")
        tree.pack(side="left", fill="both", expand=True)
        configure_treeview_tags(tree)

        for idx, it in enumerate(sim["itens"]):
            falta = it["falta_comprar"]
            tag = "baixo" if falta > 0 else ("par" if idx % 2 == 0 else "impar")
            status = "BUY / COMPRAR" if falta > 0 else "OK"
            tree.insert("", "end", tags=(tag,), values=(
                it["ingrediente_nome"],
                f'{it["necessario"]} {it["unidade"]}',
                f'{it["disponivel"]} {it["unidade"]}',
                f'{falta} {it["unidade"]}' if falta > 0 else "—",
                f'$ {it["custo_reposicao"]:.2f}' if falta > 0 else "$ 0.00",
                status,
            ))

    def _calculate_expiration(self, *_):
        try:
            days = int(self.prazo_var.get())
            if days > 0:
                exp_date = (datetime.now().date() + timedelta(days=days)).strftime("%Y-%m-%d")
                self.venc_var.set(exp_date)
        except ValueError:
            pass

    # ══════════════════════════════════════════ ACTIONS
    def produce_batch(self):
        rid = self._recipes_map.get(self.receita_var.get())
        if rid is None:
            messagebox.showerror(t("err_title"), t("ing_err_select"))
            return
        try:
            batches = int(self.lotes_var.get())
            if batches <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(t("err_title"), t("ing_err_qty"))
            return

        venc = self.venc_var.get().strip() or None
        if venc:
            try:
                datetime.strptime(venc, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror(t("err_title"), "Invalid expiration date (YYYY-MM-DD).")
                return

        rec, _ = database.obter_receita(rid)
        batch_cost, _ = database.calcular_custo_receita(rid)
        units = rec["rendimento"] * batches
        total_cost = batch_cost * batches

        msg = t("prod_confirm_fab", lotes=batches, nome=rec["nome"], unidades=units, custo=total_cost)
        if not messagebox.askyesno(t("confirm_title"), msg):
            return

        try:
            lote_id, produced_units, cost = database.fabricar_lote(
                rid, batches, data_vencimento=venc, observacao=self.obs_fab_var.get().strip()
            )
        except ValueError as err:
            messagebox.showerror(t("err_title"), str(err))
            return

        messagebox.showinfo(
            t("info_title"),
            t("prod_msg_fab", id=lote_id, units=produced_units, cost=cost),
        )
        self.lotes_var.set("1")
        self.venc_var.set("")
        self.prazo_var.set("")
        self.obs_fab_var.set("")
        self.refresh_batches()
        self.on_change()

    def record_sale(self):
        key = self.lote_saida_var.get()
        try:
            qty = int(self.saida_qtd_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(t("err_title"), t("ing_err_qty"))
            return

        unit_price = None
        pv_txt = self.saida_preco_var.get().strip().replace(",", ".")
        if pv_txt:
            try:
                unit_price = float(pv_txt)
                if unit_price < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(t("err_title"), t("rec_err_price"))
                return

        notes = self.saida_obs_var.get().strip()
        auto_fin = self.saida_fin_var.get()

        try:
            if self.modo_saida_var.get() == "fefo":
                rid = self._fefo_map.get(key)
                if rid is None:
                    messagebox.showerror(t("err_title"), t("ing_err_select"))
                    return
                depletions = database.registrar_saida_fefo(
                    rid, qty, notes, preco_unitario=unit_price, lancar_financeiro=auto_fin
                )
                summary = ", ".join(f"#{lid} ({q} un.)" for lid, q in depletions)
                messagebox.showinfo(t("info_title"), f"FEFO Outflow recorded:\n{summary}")
            else:
                lid = self._batches_map.get(key)
                if lid is None:
                    messagebox.showerror(t("err_title"), t("ing_err_select"))
                    return
                database.registrar_saida_lote(
                    lid, qty, notes, preco_unitario=unit_price, lancar_financeiro=auto_fin
                )
                messagebox.showinfo(t("info_title"), f"{qty} unit(s) deducted from Batch #{lid}.")
        except ValueError as err:
            messagebox.showerror(t("err_title"), str(err))
            return

        self.saida_qtd_var.set("")
        self.saida_obs_var.set("")
        self.refresh_batches()
        self._refresh_sales_history()
        self.on_change()

    # Compatibility aliases
    atualizar_receitas = refresh_recipes
    atualizar_lotes = refresh_batches

