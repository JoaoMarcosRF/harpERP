"""
ui/operational_frame.py — Operational Products & Supplies Management Tab
========================================================================
Manages operational supplies, cleaning materials, disposables, packaging,
utensils, and maintenance items with category management, unit conversion,
weighted average cost, and automatic financial expense recording.
"""

import tkinter as tk
from tkinter import ttk, messagebox

import database
from ui.i18n import I18n, t
from ui.theme import ThemeManager, configure_treeview_tags
from ui.utils import (
    STANDARD_UNITS,
    compatible_units,
    convert_quantity,
    enable_treeview_sorting,
    open_category_manager,
)


class OperationalFrame(ttk.Frame):
    def __init__(self, parent, on_change=None):
        super().__init__(parent, padding=10)
        self.on_change = on_change or (lambda: None)
        self.selected_id = None
        self._mov_map = {}
        self._mov_base_unit = {}

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_table_panel()
        ThemeManager.register_listener(self._on_theme_change)
        I18n.register_listener(self._on_language_change)
        self.refresh_categories()
        self.refresh_list()

    def _build_left_panel(self):
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # ── Operational Product Registration Card
        self.card_reg = ttk.LabelFrame(left, text=t("op_form_title"), padding=10)
        self.card_reg.pack(fill="x")

        self.vars = {
            "nome": tk.StringVar(),
            "marca": tk.StringVar(),
            "categoria": tk.StringVar(),
            "unidade": tk.StringVar(value="un"),
            "quantidade": tk.StringVar(),
            "estoque_minimo": tk.StringVar(),
            "preco_custo": tk.StringVar(),
            "observacao": tk.StringVar(),
        }

        self.lbl_name = ttk.Label(self.card_reg, text=t("op_name"), style="Card.TLabel")
        self.lbl_name.grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(self.card_reg, textvariable=self.vars["nome"], width=28).grid(
            row=0, column=1, pady=2, padx=(8, 0), sticky="w"
        )

        self.lbl_brand = ttk.Label(self.card_reg, text=t("op_brand"), style="Card.TLabel")
        self.lbl_brand.grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(self.card_reg, textvariable=self.vars["marca"], width=28).grid(
            row=1, column=1, pady=2, padx=(8, 0), sticky="w"
        )

        self.lbl_cat = ttk.Label(self.card_reg, text=t("op_category"), style="Card.TLabel")
        self.lbl_cat.grid(row=2, column=0, sticky="w", pady=2)
        cat_frame = ttk.Frame(self.card_reg, style="Card.TFrame")
        cat_frame.grid(row=2, column=1, sticky="w", pady=2, padx=(8, 0))
        self.combo_cat = ttk.Combobox(
            cat_frame, textvariable=self.vars["categoria"], width=17
        )
        self.combo_cat.pack(side="left")
        self.btn_cat_mgr = ttk.Button(
            cat_frame,
            text=t("cat_btn_manage"),
            command=self._open_category_dialog,
        )
        self.btn_cat_mgr.pack(side="left", padx=(4, 0))

        self.lbl_unit = ttk.Label(self.card_reg, text=t("op_unit"), style="Card.TLabel")
        self.lbl_unit.grid(row=3, column=0, sticky="w", pady=2)
        self.combo_unit = ttk.Combobox(
            self.card_reg,
            textvariable=self.vars["unidade"],
            values=STANDARD_UNITS,
            width=10,
            state="readonly",
        )
        self.combo_unit.grid(row=3, column=1, sticky="w", pady=2, padx=(8, 0))

        self.lbl_qty = ttk.Label(self.card_reg, text=t("op_init_qty"), style="Card.TLabel")
        self.lbl_qty.grid(row=4, column=0, sticky="w", pady=2)
        ttk.Entry(self.card_reg, textvariable=self.vars["quantidade"], width=14).grid(
            row=4, column=1, sticky="w", pady=2, padx=(8, 0)
        )

        self.lbl_min = ttk.Label(self.card_reg, text=t("op_min_stock"), style="Card.TLabel")
        self.lbl_min.grid(row=5, column=0, sticky="w", pady=2)
        ttk.Entry(self.card_reg, textvariable=self.vars["estoque_minimo"], width=14).grid(
            row=5, column=1, sticky="w", pady=2, padx=(8, 0)
        )

        self.lbl_cost = ttk.Label(self.card_reg, text=t("op_cost"), style="Card.TLabel")
        self.lbl_cost.grid(row=6, column=0, sticky="w", pady=2)
        ttk.Entry(self.card_reg, textvariable=self.vars["preco_custo"], width=14).grid(
            row=6, column=1, sticky="w", pady=2, padx=(8, 0)
        )

        self.lbl_notes = ttk.Label(self.card_reg, text=t("op_notes"), style="Card.TLabel")
        self.lbl_notes.grid(row=7, column=0, sticky="w", pady=2)
        ttk.Entry(self.card_reg, textvariable=self.vars["observacao"], width=28).grid(
            row=7, column=1, sticky="w", pady=2, padx=(8, 0)
        )

        self.init_fin_var = tk.BooleanVar(value=False)
        self.chk_init_fin = ttk.Checkbutton(
            self.card_reg, text=t("op_init_fin"), variable=self.init_fin_var
        )
        self.chk_init_fin.grid(row=8, column=0, columnspan=2, sticky="w", pady=(4, 0))

        btn_frame = ttk.Frame(self.card_reg, style="Card.TFrame")
        btn_frame.grid(row=9, column=0, columnspan=2, pady=(8, 0))
        self.btn_save = ttk.Button(
            btn_frame, text=t("btn_save"), style="Primary.TButton", command=self.save
        )
        self.btn_save.pack(side="left", padx=3)
        self.btn_new = ttk.Button(btn_frame, text=t("btn_new"), command=self.clear)
        self.btn_new.pack(side="left", padx=3)
        self.btn_del = ttk.Button(
            btn_frame, text=t("btn_delete"), style="Danger.TButton", command=self.delete
        )
        self.btn_del.pack(side="left", padx=3)

        # ── Operational Stock Movement Card
        self.card_mov = ttk.LabelFrame(left, text=t("op_mov_title"), padding=10)
        self.card_mov.pack(fill="x", pady=(8, 0))

        self.lbl_mov_item = ttk.Label(self.card_mov, text=t("op_select"), style="Card.TLabel")
        self.lbl_mov_item.grid(row=0, column=0, sticky="w", pady=2)
        self.mov_item_var = tk.StringVar()
        self.combo_mov = ttk.Combobox(
            self.card_mov, textvariable=self.mov_item_var, width=26, state="readonly"
        )
        self.combo_mov.grid(row=0, column=1, pady=2, padx=(8, 0), sticky="w")
        self.combo_mov.bind("<<ComboboxSelected>>", self._on_select_mov_item)

        self.lbl_mov_type = ttk.Label(self.card_mov, text=t("op_type"), style="Card.TLabel")
        self.lbl_mov_type.grid(row=1, column=0, sticky="w", pady=2)
        self.tipo_var = tk.StringVar(value="entrada")
        tf = ttk.Frame(self.card_mov, style="Card.TFrame")
        tf.grid(row=1, column=1, sticky="w", padx=(8, 0))
        self.rb_in = ttk.Radiobutton(tf, text=t("op_in"), variable=self.tipo_var, value="entrada")
        self.rb_in.pack(side="left")
        self.rb_out = ttk.Radiobutton(tf, text=t("op_out"), variable=self.tipo_var, value="saida")
        self.rb_out.pack(side="left", padx=(8, 0))

        self.lbl_mov_qty = ttk.Label(self.card_mov, text=t("op_qty_unit"), style="Card.TLabel")
        self.lbl_mov_qty.grid(row=2, column=0, sticky="w", pady=2)
        qf = ttk.Frame(self.card_mov, style="Card.TFrame")
        qf.grid(row=2, column=1, sticky="w", pady=2, padx=(8, 0))
        self.mov_qtd_var = tk.StringVar()
        ttk.Entry(qf, textvariable=self.mov_qtd_var, width=10).pack(side="left")
        self.mov_unid_var = tk.StringVar(value="un")
        self.combo_mov_unid = ttk.Combobox(
            qf, textvariable=self.mov_unid_var, values=STANDARD_UNITS, width=6, state="readonly"
        )
        self.combo_mov_unid.pack(side="left", padx=(6, 0))

        self.lbl_mov_cost = ttk.Label(self.card_mov, text=t("op_unit_cost"), style="Card.TLabel")
        self.lbl_mov_cost.grid(row=3, column=0, sticky="w", pady=2)
        self.mov_custo_var = tk.StringVar()
        ttk.Entry(self.card_mov, textvariable=self.mov_custo_var, width=12).grid(
            row=3, column=1, sticky="w", pady=2, padx=(8, 0)
        )

        self.lbl_mov_notes = ttk.Label(self.card_mov, text=t("ing_notes"), style="Card.TLabel")
        self.lbl_mov_notes.grid(row=4, column=0, sticky="w", pady=2)
        self.mov_obs_var = tk.StringVar()
        ttk.Entry(self.card_mov, textvariable=self.mov_obs_var, width=26).grid(
            row=4, column=1, pady=2, padx=(8, 0), sticky="w"
        )

        self.mov_fin_var = tk.BooleanVar(value=True)
        self.chk_mov_fin = ttk.Checkbutton(
            self.card_mov, text=t("op_auto_fin"), variable=self.mov_fin_var
        )
        self.chk_mov_fin.grid(row=5, column=0, columnspan=2, sticky="w", pady=(3, 0))

        self.btn_mov = ttk.Button(
            self.card_mov, text=t("op_btn_mov"), style="Success.TButton", command=self.record_movement
        )
        self.btn_mov.grid(row=6, column=0, columnspan=2, pady=(8, 0))

        # ── Search & Category Filter Card
        self.card_search = ttk.LabelFrame(left, text=t("op_search_title"), padding=8)
        self.card_search.pack(fill="x", pady=(8, 0))

        row1 = ttk.Frame(self.card_search, style="Card.TFrame")
        row1.pack(fill="x", pady=(0, 4))
        self.busca_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.busca_var, width=18).pack(side="left")
        self.filtro_cat_var = tk.StringVar(value=t("all"))
        self.combo_filtro_cat = ttk.Combobox(
            row1, textvariable=self.filtro_cat_var, width=14, state="readonly"
        )
        self.combo_filtro_cat.pack(side="left", padx=(6, 0))
        self.combo_filtro_cat.bind("<<ComboboxSelected>>", lambda _: self.refresh_list())

        row2 = ttk.Frame(self.card_search, style="Card.TFrame")
        row2.pack(fill="x")
        self.btn_search = ttk.Button(
            row2,
            text=t("btn_search"),
            style="Primary.TButton",
            command=self.refresh_list,
        )
        self.btn_search.pack(side="left", padx=(0, 5))
        self.btn_clear_search = ttk.Button(
            row2,
            text=t("btn_clear"),
            command=self._clear_filters,
        )
        self.btn_clear_search.pack(side="left")

    def _build_table_panel(self):
        self.nb = ttk.Notebook(self)
        self.nb.grid(row=0, column=1, sticky="nsew")

        # Tab 1: Operational Inventory
        tab_est = ttk.Frame(self.nb, padding=6)
        self.nb.add(tab_est, text=t("op_subtab_stock"))
        tab_est.grid_columnconfigure(0, weight=1)
        tab_est.grid_rowconfigure(0, weight=1)

        cols = (
            "id", "nome", "marca", "categoria", "unidade",
            "quantidade", "estoque_minimo", "preco_custo", "valor_total", "observacao"
        )
        self.table = ttk.Treeview(tab_est, columns=cols, show="headings", height=16)
        widths = {
            "id": 42, "nome": 145, "marca": 95, "categoria": 115, "unidade": 48,
            "quantidade": 65, "estoque_minimo": 58, "preco_custo": 85,
            "valor_total": 100, "observacao": 130
        }
        for c in cols:
            self.table.column(c, width=widths.get(c, 95), anchor="center")
        self.table.grid(row=0, column=0, sticky="nsew")

        scroll_est = ttk.Scrollbar(tab_est, orient="vertical", command=self.table.yview)
        scroll_est.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scroll_est.set)
        self.table.bind("<<TreeviewSelect>>", self._on_select_row)
        enable_treeview_sorting(self.table)
        configure_treeview_tags(self.table)

        # Tab 2: Operational Movement History
        tab_mov = ttk.Frame(self.nb, padding=6)
        self.nb.add(tab_mov, text=t("op_subtab_history"))
        tab_mov.grid_columnconfigure(0, weight=1)
        tab_mov.grid_rowconfigure(0, weight=1)

        cols_m = ("id", "data", "produto_nome", "tipo", "quantidade", "custo_unitario", "observacao")
        self.table_mov = ttk.Treeview(tab_mov, columns=cols_m, show="headings", height=16)
        for c in cols_m:
            self.table_mov.column(c, width=70 if c in ("id", "quantidade") else 120, anchor="center")
        self.table_mov.grid(row=0, column=0, sticky="nsew")
        scroll_mov = ttk.Scrollbar(tab_mov, orient="vertical", command=self.table_mov.yview)
        scroll_mov.grid(row=0, column=1, sticky="ns")
        self.table_mov.configure(yscrollcommand=scroll_mov.set)
        enable_treeview_sorting(self.table_mov)
        configure_treeview_tags(self.table_mov)

        self.btn_refresh_mov = ttk.Button(tab_mov, text=t("btn_refresh"), command=self.refresh_movements)
        self.btn_refresh_mov.grid(row=1, column=0, sticky="e", pady=(6, 0))
        self._update_table_headings()

    def _update_table_headings(self):
        headings_stock = {
            "id": t("op_col_id"),
            "nome": t("op_col_name"),
            "marca": t("op_col_brand"),
            "categoria": t("op_col_cat"),
            "unidade": t("op_col_unit"),
            "quantidade": t("op_col_qty"),
            "estoque_minimo": t("op_col_min"),
            "preco_custo": t("op_col_cost"),
            "valor_total": t("op_col_total"),
            "observacao": t("op_col_notes"),
        }
        for col, text in headings_stock.items():
            self.table.heading(col, text=text)

        headings_mov = {
            "id": t("op_col_id"),
            "data": t("op_col_date"),
            "produto_nome": t("op_col_name"),
            "tipo": t("op_col_type"),
            "quantidade": t("op_col_qty"),
            "custo_unitario": t("op_col_cost"),
            "observacao": t("op_col_notes"),
        }
        for col, text in headings_mov.items():
            self.table_mov.heading(col, text=text)

    def _open_category_dialog(self):
        open_category_manager(
            self,
            default_scope="operacional",
            on_select=lambda nome: self.vars["categoria"].set(nome),
            on_updated=self._on_categories_changed,
        )

    def _on_categories_changed(self):
        self.refresh_categories()
        self.refresh_list()
        self.on_change()

    def refresh_categories(self):
        cats = database.listar_nomes_categorias("operacional")
        self.combo_cat["values"] = cats
        all_lbl = t("all")
        self.combo_filtro_cat["values"] = [all_lbl] + cats
        if self.filtro_cat_var.get() not in self.combo_filtro_cat["values"]:
            self.filtro_cat_var.set(all_lbl)

    def _clear_filters(self):
        self.busca_var.set("")
        self.filtro_cat_var.set(t("all"))
        self.refresh_list()

    def _on_theme_change(self):
        configure_treeview_tags(self.table)
        configure_treeview_tags(self.table_mov)

    def _on_language_change(self):
        self.card_reg.config(text=t("op_form_title"))
        self.lbl_name.config(text=t("op_name"))
        self.lbl_brand.config(text=t("op_brand"))
        self.lbl_cat.config(text=t("op_category"))
        self.btn_cat_mgr.config(text=t("cat_btn_manage"))
        self.lbl_unit.config(text=t("op_unit"))
        self.lbl_qty.config(text=t("op_init_qty"))
        self.lbl_min.config(text=t("op_min_stock"))
        self.lbl_cost.config(text=t("op_cost"))
        self.lbl_notes.config(text=t("op_notes"))
        self.chk_init_fin.config(text=t("op_init_fin"))
        self.btn_save.config(text=t("btn_save"))
        self.btn_new.config(text=t("btn_new"))
        self.btn_del.config(text=t("btn_delete"))

        self.card_mov.config(text=t("op_mov_title"))
        self.lbl_mov_item.config(text=t("op_select"))
        self.lbl_mov_type.config(text=t("op_type"))
        self.rb_in.config(text=t("op_in"))
        self.rb_out.config(text=t("op_out"))
        self.lbl_mov_qty.config(text=t("op_qty_unit"))
        self.lbl_mov_cost.config(text=t("op_unit_cost"))
        self.lbl_mov_notes.config(text=t("ing_notes"))
        self.chk_mov_fin.config(text=t("op_auto_fin"))
        self.btn_mov.config(text=t("op_btn_mov"))

        self.card_search.config(text=t("op_search_title"))
        self.btn_search.config(text=t("btn_search"))
        self.btn_clear_search.config(text=t("btn_clear"))
        self.btn_refresh_mov.config(text=t("btn_refresh"))

        self.nb.tab(0, text=t("op_subtab_stock"))
        self.nb.tab(1, text=t("op_subtab_history"))
        self._update_table_headings()
        self.refresh_categories()
        self.refresh_list()

    # ══════════════════════════════════════════ DATA
    def refresh_list(self, search_term=None):
        self.refresh_categories()
        for i in self.table.get_children():
            self.table.delete(i)

        termo = search_term if search_term is not None else self.busca_var.get().strip()
        cat_sel = self.filtro_cat_var.get().strip()
        cat_filter = None if cat_sel in ("", t("all"), "All", "Todos") else cat_sel

        for idx, p in enumerate(database.listar_produtos_operacionais(termo or None, categoria=cat_filter)):
            valor_total = round(p["preco_custo"] * p["quantidade"], 2)
            zebra = "par" if idx % 2 == 0 else "impar"
            tag = ("baixo",) if p["quantidade"] <= p["estoque_minimo"] else (zebra,)
            self.table.insert("", "end", iid=p["id"], tags=tag, values=(
                p["id"], p["nome"], p["marca"], p["categoria"], p["unidade"],
                round(p["quantidade"], 4), p["estoque_minimo"],
                f'{p["preco_custo"]:.2f}', f'{valor_total:.2f}', p["observacao"] or ""
            ))
        self._refresh_mov_combo()
        self.refresh_movements()

    def refresh_movements(self):
        for i in self.table_mov.get_children():
            self.table_mov.delete(i)
        for idx, m in enumerate(database.listar_mov_operacionais()):
            zebra = "par" if idx % 2 == 0 else "impar"
            tag_tipo = "receita" if m["tipo"] == "entrada" else "despesa"
            tipo_label = t("op_in") if m["tipo"] == "entrada" else t("op_out")
            self.table_mov.insert("", "end", tags=(zebra, tag_tipo), values=(
                m["id"], m["data"], m["produto_nome"],
                tipo_label,
                f'{round(m["quantidade"], 4)} {m["unidade"]}',
                f'{m["custo_unitario"]:.2f}',
                m["observacao"]
            ))

    def _refresh_mov_combo(self):
        items = database.listar_produtos_operacionais()
        self._mov_map = {}
        self._mov_base_unit = {}
        for i in items:
            label = f'{i["nome"]} ({round(i["quantidade"], 4)} {i["unidade"]})'
            self._mov_map[label] = i["id"]
            self._mov_base_unit[i["id"]] = i["unidade"] or "un"
        self.combo_mov["values"] = list(self._mov_map.keys())

    def _on_select_mov_item(self, _=None):
        pid = self._mov_map.get(self.mov_item_var.get())
        if pid is not None:
            ubase = self._mov_base_unit.get(pid, "un")
            options = compatible_units(ubase)
            self.combo_mov_unid["values"] = options
            self.mov_unid_var.set(ubase)

    def _on_select_row(self, _):
        sel = self.table.selection()
        if not sel:
            return
        p = database.obter_produto_operacional(int(sel[0]))
        if not p:
            return
        self.selected_id = p["id"]
        self.vars["nome"].set(p["nome"])
        self.vars["marca"].set(p["marca"] or "")
        self.vars["categoria"].set(p["categoria"] or "")
        self.vars["unidade"].set(p["unidade"] or "un")
        self.vars["quantidade"].set(p["quantidade"])
        self.vars["estoque_minimo"].set(p["estoque_minimo"])
        self.vars["preco_custo"].set(p["preco_custo"])
        self.vars["observacao"].set(p["observacao"] or "")

    # ══════════════════════════════════════════ ACTIONS
    def save(self):
        nome = self.vars["nome"].get().strip()
        if not nome:
            messagebox.showerror(t("err_title"), t("op_err_name"))
            return
        try:
            qtd = float(self.vars["quantidade"].get().replace(",", ".") or 0)
            est_min = float(self.vars["estoque_minimo"].get().replace(",", ".") or 0)
            preco_custo = float(self.vars["preco_custo"].get().replace(",", ".") or 0)
            if qtd < 0 or est_min < 0 or preco_custo < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(t("err_title"), t("op_err_num"))
            return

        marca = self.vars["marca"].get().strip()
        categoria = self.vars["categoria"].get().strip()
        unidade = self.vars["unidade"].get().strip() or "un"
        obs = self.vars["observacao"].get().strip()

        if self.selected_id is None:
            database.adicionar_produto_operacional(
                nome,
                marca,
                categoria,
                qtd,
                est_min,
                unidade,
                preco_custo,
                observacao=obs,
                lancar_financeiro=self.init_fin_var.get(),
            )
            messagebox.showinfo(t("info_title"), t("op_msg_saved"))
        else:
            database.atualizar_produto_operacional(
                self.selected_id,
                nome,
                marca,
                categoria,
                est_min,
                unidade,
                preco_custo,
                quantidade=qtd,
                observacao=obs,
            )
            messagebox.showinfo(t("info_title"), t("op_msg_updated"))

        self.clear()
        self.refresh_list()
        self.on_change()

    def delete(self):
        if self.selected_id is None:
            messagebox.showwarning(t("warn_title"), t("op_err_select"))
            return
        if messagebox.askyesno(t("confirm_title"), t("op_confirm_del")):
            database.excluir_produto_operacional(self.selected_id)
            self.clear()
            self.refresh_list()
            self.on_change()

    def clear(self):
        self.selected_id = None
        for v in self.vars.values():
            v.set("")
        self.vars["unidade"].set("un")
        self.init_fin_var.set(False)
        self.table.selection_remove(self.table.selection())

    def record_movement(self):
        key = self.mov_item_var.get()
        pid = self._mov_map.get(key)
        if pid is None:
            messagebox.showerror(t("err_title"), t("op_err_select"))
            return
        try:
            input_qty = float(self.mov_qtd_var.get().replace(",", "."))
            if input_qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(t("err_title"), t("op_err_qty"))
            return

        base_unit = self._mov_base_unit.get(pid, "un")
        sel_unit = self.mov_unid_var.get() or base_unit
        converted_qty = convert_quantity(input_qty, sel_unit, base_unit)

        new_cost = None
        cost_txt = self.mov_custo_var.get().strip().replace(",", ".")
        if cost_txt:
            try:
                input_cost = float(cost_txt)
                if input_cost <= 0:
                    raise ValueError
                factor = converted_qty / input_qty if input_qty > 0 else 1.0
                new_cost = round(input_cost / factor, 4) if factor > 0 else input_cost
            except ValueError:
                messagebox.showerror(t("err_title"), t("op_err_cost"))
                return

        notes = self.mov_obs_var.get().strip()
        if sel_unit != base_unit:
            conv_note = f"[{input_qty:g} {sel_unit} = {converted_qty:g} {base_unit}]"
            notes = f"{notes} {conv_note}".strip()

        try:
            database.registrar_mov_operacional(
                pid,
                self.tipo_var.get(),
                converted_qty,
                notes,
                novo_custo=new_cost,
                lancar_financeiro=self.mov_fin_var.get(),
            )
        except ValueError as err:
            messagebox.showerror(t("err_title"), str(err))
            return

        self.mov_qtd_var.set("")
        self.mov_custo_var.set("")
        self.mov_obs_var.set("")
        self.refresh_list()
        self.on_change()
        messagebox.showinfo(t("info_title"), t("op_msg_mov"))

    atualizar_lista = refresh_list


# Backward-compatible alias
ProdutosOperacionaisFrame = OperationalFrame

