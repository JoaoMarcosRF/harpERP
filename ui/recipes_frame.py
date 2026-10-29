"""
ui/recipes_frame.py — Recipes / Bill of Materials (BOM) Management Tab
======================================================================
Defines recipe ingredients with unit conversion dropdown, batch yield,
default shelf life, selling price, and live profitability analysis.
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
)


class RecipesFrame(ttk.Frame):
    def __init__(self, parent, on_change=None):
        super().__init__(parent, padding=10)
        self.on_change = on_change or (lambda: None)
        self.recipe_id = None
        self.components = []
        self._ing_map = {}
        self._ing_unit = {}

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()
        ThemeManager.register_listener(self._on_theme_change)
        I18n.register_listener(self._on_language_change)
        self.refresh_ingredients_map()
        self.refresh_recipes_list()

    def _build_left_panel(self):
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # ── Recipe Header Details
        self.card_rec = ttk.LabelFrame(left, text=t("rec_form_title"), padding=10)
        self.card_rec.pack(fill="x")

        self.lbl_name = ttk.Label(self.card_rec, text=t("rec_name"), style="Card.TLabel")
        self.lbl_name.grid(row=0, column=0, sticky="w", pady=3)
        self.nome_var = tk.StringVar()
        ttk.Entry(self.card_rec, textvariable=self.nome_var, width=30).grid(
            row=0, column=1, pady=3, padx=(8, 0), sticky="w"
        )

        self.lbl_yield = ttk.Label(self.card_rec, text=t("rec_yield"), style="Card.TLabel")
        self.lbl_yield.grid(row=1, column=0, sticky="w", pady=3)
        self.rend_var = tk.StringVar(value="1")
        self.rend_var.trace_add("write", lambda *_: self._update_cost_labels())
        ttk.Entry(self.card_rec, textvariable=self.rend_var, width=10).grid(
            row=1, column=1, sticky="w", pady=3, padx=(8, 0)
        )

        self.lbl_shelf = ttk.Label(self.card_rec, text=t("rec_shelf_life"), style="Card.TLabel")
        self.lbl_shelf.grid(row=2, column=0, sticky="w", pady=3)
        self.validade_var = tk.StringVar()
        ttk.Entry(self.card_rec, textvariable=self.validade_var, width=10).grid(
            row=2, column=1, sticky="w", pady=3, padx=(8, 0)
        )

        self.lbl_sell = ttk.Label(self.card_rec, text=t("rec_sell_price"), style="Card.TLabel")
        self.lbl_sell.grid(row=3, column=0, sticky="w", pady=3)
        self.preco_venda_var = tk.StringVar()
        self.preco_venda_var.trace_add("write", lambda *_: self._update_cost_labels())
        ttk.Entry(self.card_rec, textvariable=self.preco_venda_var, width=12).grid(
            row=3, column=1, sticky="w", pady=3, padx=(8, 0)
        )

        self.lbl_notes = ttk.Label(self.card_rec, text=t("rec_notes"), style="Card.TLabel")
        self.lbl_notes.grid(row=4, column=0, sticky="w", pady=3)
        self.obs_var = tk.StringVar()
        ttk.Entry(self.card_rec, textvariable=self.obs_var, width=30).grid(
            row=4, column=1, pady=3, padx=(8, 0), sticky="w"
        )

        # ── Batch Composition
        self.card_comp = ttk.LabelFrame(left, text=t("rec_comp_title"), padding=10)
        self.card_comp.pack(fill="x", pady=(10, 0))

        self.lbl_comp_ing = ttk.Label(self.card_comp, text=t("rec_comp_ing"), style="Card.TLabel")
        self.lbl_comp_ing.grid(row=0, column=0, sticky="w")
        self.comp_ing_var = tk.StringVar()
        self.combo_ing = ttk.Combobox(
            self.card_comp, textvariable=self.comp_ing_var, width=26, state="readonly"
        )
        self.combo_ing.grid(row=0, column=1, padx=(8, 0), sticky="w")
        self.combo_ing.bind("<<ComboboxSelected>>", self._on_select_ingredient)

        self.lbl_comp_qty = ttk.Label(self.card_comp, text=t("rec_comp_qty"), style="Card.TLabel")
        self.lbl_comp_qty.grid(row=1, column=0, sticky="w", pady=4)
        qf = ttk.Frame(self.card_comp, style="Card.TFrame")
        qf.grid(row=1, column=1, sticky="w", pady=4, padx=(8, 0))
        self.comp_qtd_var = tk.StringVar()
        ttk.Entry(qf, textvariable=self.comp_qtd_var, width=10).pack(side="left")

        self.comp_unid_var = tk.StringVar(value="un")
        self.combo_comp_unid = ttk.Combobox(
            qf, textvariable=self.comp_unid_var, values=STANDARD_UNITS, width=6, state="readonly"
        )
        self.combo_comp_unid.pack(side="left", padx=(6, 0))

        btn_comp = ttk.Frame(self.card_comp, style="Card.TFrame")
        btn_comp.grid(row=2, column=0, columnspan=2, pady=(6, 0))
        self.btn_add_comp = ttk.Button(
            btn_comp, text=t("rec_btn_add"), style="Primary.TButton", command=self._add_component
        )
        self.btn_add_comp.pack(side="left", padx=3)
        self.btn_rem_comp = ttk.Button(
            btn_comp, text=t("rec_btn_rem"), command=self._remove_component
        )
        self.btn_rem_comp.pack(side="left", padx=3)

        cols_c = ("ingrediente", "quantidade", "unidade", "custo_unit", "subtotal")
        self.tab_comp = ttk.Treeview(self.card_comp, columns=cols_c, show="headings", height=5)
        widths_c = {"ingrediente": 140, "quantidade": 65, "unidade": 45, "custo_unit": 100, "subtotal": 90}
        for c in cols_c:
            self.tab_comp.column(c, width=widths_c.get(c, 80), anchor="center")
        self.tab_comp.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        configure_treeview_tags(self.tab_comp)

        self.lbl_custo_lote = ttk.Label(self.card_comp, text="", style="CardBold.TLabel")
        self.lbl_custo_lote.grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.lbl_custo_unit = ttk.Label(self.card_comp, text="", style="CardBold.TLabel")
        self.lbl_custo_unit.grid(row=4, column=1, sticky="w", pady=(6, 0))

        self.lbl_margem = ttk.Label(self.card_comp, text="", style="CardBold.TLabel")
        self.lbl_margem.grid(row=5, column=0, columnspan=2, sticky="w", pady=(3, 0))

        btn_r = ttk.Frame(left)
        btn_r.pack(fill="x", pady=(10, 0))
        self.btn_save = ttk.Button(btn_r, text=t("rec_btn_save"), style="Success.TButton", command=self.save)
        self.btn_save.pack(side="left", padx=3)
        self.btn_new = ttk.Button(btn_r, text=t("rec_btn_new"), command=self.clear)
        self.btn_new.pack(side="left", padx=3)
        self.btn_del = ttk.Button(btn_r, text=t("rec_btn_del"), style="Danger.TButton", command=self.delete)
        self.btn_del.pack(side="left", padx=3)

    def _build_right_panel(self):
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self.lbl_list_title = ttk.Label(right, text=t("rec_list_title"), style="SectionTitle.TLabel")
        self.lbl_list_title.grid(row=0, column=0, sticky="w", pady=(0, 6))

        cols = ("id", "nome", "rendimento", "validade_dias", "custo_unitario", "preco_venda", "margem")
        self.tab_rec = ttk.Treeview(right, columns=cols, show="headings", height=22)
        widths = {
            "id": 45, "nome": 175, "rendimento": 80, "validade_dias": 85,
            "custo_unitario": 100, "preco_venda": 100, "margem": 90
        }
        for c in cols:
            self.tab_rec.column(c, width=widths.get(c, 100), anchor="center")
        self.tab_rec.grid(row=1, column=0, sticky="nsew")
        self.tab_rec.bind("<<TreeviewSelect>>", self._on_select_recipe)

        scroll_rec = ttk.Scrollbar(right, orient="vertical", command=self.tab_rec.yview)
        scroll_rec.grid(row=1, column=1, sticky="ns")
        self.tab_rec.configure(yscrollcommand=scroll_rec.set)
        enable_treeview_sorting(self.tab_rec)
        configure_treeview_tags(self.tab_rec)
        self._update_table_headings()
        self._update_cost_labels()

    def _update_table_headings(self):
        comp_heads = {
            "ingrediente": t("rec_col_ing"),
            "quantidade": t("rec_col_qty"),
            "unidade": t("rec_col_unit"),
            "custo_unit": t("rec_col_ucost"),
            "subtotal": t("rec_col_sub"),
        }
        for c, txt in comp_heads.items():
            self.tab_comp.heading(c, text=txt)

        rec_heads = {
            "id": t("rec_col_id"),
            "nome": t("rec_col_rname"),
            "rendimento": t("rec_col_yield"),
            "validade_dias": t("rec_col_val"),
            "custo_unitario": t("rec_col_ucost"),
            "preco_venda": t("rec_col_sell"),
            "margem": t("rec_col_margin"),
        }
        for c, txt in rec_heads.items():
            self.tab_rec.heading(c, text=txt)

    def _on_theme_change(self):
        configure_treeview_tags(self.tab_comp)
        configure_treeview_tags(self.tab_rec)
        self._update_cost_labels()

    def _on_language_change(self):
        self.card_rec.config(text=t("rec_form_title"))
        self.lbl_name.config(text=t("rec_name"))
        self.lbl_yield.config(text=t("rec_yield"))
        self.lbl_shelf.config(text=t("rec_shelf_life"))
        self.lbl_sell.config(text=t("rec_sell_price"))
        self.lbl_notes.config(text=t("rec_notes"))
        self.card_comp.config(text=t("rec_comp_title"))
        self.lbl_comp_ing.config(text=t("rec_comp_ing"))
        self.lbl_comp_qty.config(text=t("rec_comp_qty"))
        self.btn_add_comp.config(text=t("rec_btn_add"))
        self.btn_rem_comp.config(text=t("rec_btn_rem"))
        self.btn_save.config(text=t("rec_btn_save"))
        self.btn_new.config(text=t("rec_btn_new"))
        self.btn_del.config(text=t("rec_btn_del"))
        self.lbl_list_title.config(text=t("rec_list_title"))
        self._update_table_headings()
        self._update_cost_labels()

    # ══════════════════════════════════════════ DATA
    def refresh_ingredients_map(self):
        ings = database.listar_ingredientes()
        self._ing_map = {}
        self._ing_unit = {}
        for i in ings:
            label = f'{i["nome"]} ({i["unidade"]})'
            self._ing_map[label] = i["id"]
            self._ing_unit[i["id"]] = i["unidade"] or "un"
        self.combo_ing["values"] = list(self._ing_map.keys())
        self.refresh_recipes_list()

    def _on_select_ingredient(self, _=None):
        iid = self._ing_map.get(self.comp_ing_var.get())
        if iid is not None:
            ubase = self._ing_unit.get(iid, "un")
            self.combo_comp_unid["values"] = compatible_units(ubase)
            self.comp_unid_var.set(ubase)

    def refresh_recipes_list(self):
        for i in self.tab_rec.get_children():
            self.tab_rec.delete(i)
        for idx, r in enumerate(database.analise_rentabilidade_receitas()):
            val_str = str(r["validade_dias"]) if r["validade_dias"] else "—"
            venda_str = f'{r["preco_venda"]:.2f}' if r["preco_venda"] > 0 else "—"
            margem_str = f'{r["margem_percentual"]:.1f}%' if r["preco_venda"] > 0 else "—"
            zebra = "par" if idx % 2 == 0 else "impar"
            self.tab_rec.insert("", "end", iid=r["id"], tags=(zebra,), values=(
                r["id"], r["nome"], r["rendimento"], val_str,
                f'{r["custo_unitario"]:.4f}', venda_str, margem_str
            ))

    def _populate_comp_table(self):
        for i in self.tab_comp.get_children():
            self.tab_comp.delete(i)
        for idx, c in enumerate(self.components):
            zebra = "par" if idx % 2 == 0 else "impar"
            self.tab_comp.insert("", "end", tags=(zebra,), values=(
                c["ingrediente_nome"], round(c["quantidade"], 6), c.get("unidade", "un"),
                f'{c["preco_custo"]:.4f}', f'{c["subtotal"]:.4f}'
            ))
        self._update_cost_labels()

    def _update_cost_labels(self):
        p = ThemeManager.palette()
        try:
            rend = max(1, int(self.rend_var.get()))
        except ValueError:
            rend = 1
        batch_cost = sum(c["subtotal"] for c in self.components)
        unit_cost = batch_cost / rend
        self.lbl_custo_lote.config(text=t("rec_lbl_batch_cost", val=batch_cost))
        self.lbl_custo_unit.config(text=t("rec_lbl_unit_cost", val=unit_cost))

        try:
            pv = float(self.preco_venda_var.get().replace(",", ".") or 0)
        except ValueError:
            pv = 0.0
        if pv > 0:
            profit = pv - unit_cost
            margin = (profit / pv) * 100.0
            color = p["sucesso"] if profit > 0 else p["perigo"]
            self.lbl_margem.config(
                text=t("rec_lbl_margin", profit=profit, margin=margin),
                foreground=color,
            )
        else:
            self.lbl_margem.config(text=t("rec_lbl_margin_empty"), foreground=p["texto_suave"])

    def _on_select_recipe(self, _):
        sel = self.tab_rec.selection()
        if not sel:
            return
        rid = int(sel[0])
        self.recipe_id = rid
        rec, comps = database.obter_receita(rid)
        if not rec:
            return
        self.nome_var.set(rec["nome"])
        self.rend_var.set(rec["rendimento"])
        self.validade_var.set(str(rec["validade_dias"]) if rec["validade_dias"] else "")
        self.preco_venda_var.set(f'{rec["preco_venda"]:.2f}' if rec["preco_venda"] else "")
        self.obs_var.set(rec["observacao"] or "")
        self.components = []
        for c in comps:
            self.components.append({
                "ingrediente_id":   c["ingrediente_id"],
                "ingrediente_nome": c["ingrediente_nome"],
                "quantidade":       c["quantidade"],
                "unidade":          c["unidade"] or "un",
                "preco_custo":      c["preco_custo"],
                "subtotal":         c["preco_custo"] * c["quantidade"],
            })
        self._populate_comp_table()

    # ══════════════════════════════════════════ COMPONENT ACTIONS
    def _add_component(self):
        key = self.comp_ing_var.get()
        iid = self._ing_map.get(key)
        if iid is None:
            messagebox.showerror(t("err_title"), t("ing_err_select"))
            return
        try:
            input_qty = float(self.comp_qtd_var.get().replace(",", "."))
            if input_qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(t("err_title"), t("ing_err_qty"))
            return

        ing = database.obter_ingrediente(iid)
        real_name = ing["nome"] if ing else key
        cost = ing["preco_custo"] if ing else 0.0
        base_unit = (ing["unidade"] if ing else "un") or "un"
        sel_unit = self.comp_unid_var.get() or base_unit
        qty = convert_quantity(input_qty, sel_unit, base_unit)

        for c in self.components:
            if c["ingrediente_id"] == iid:
                c["quantidade"] = round(c["quantidade"] + qty, 6)
                c["subtotal"] = c["preco_custo"] * c["quantidade"]
                self.comp_qtd_var.set("")
                self._populate_comp_table()
                return

        self.components.append({
            "ingrediente_id":   iid,
            "ingrediente_nome": real_name,
            "quantidade":       qty,
            "unidade":          base_unit,
            "preco_custo":      cost,
            "subtotal":         cost * qty,
        })
        self.comp_qtd_var.set("")
        self._populate_comp_table()

    def _remove_component(self):
        sel = self.tab_comp.selection()
        if not sel:
            messagebox.showwarning(t("warn_title"), t("ing_err_select"))
            return
        idx = self.tab_comp.index(sel[0])
        del self.components[idx]
        self._populate_comp_table()

    # ══════════════════════════════════════════ RECIPE ACTIONS
    def save(self):
        nome = self.nome_var.get().strip()
        if not nome:
            messagebox.showerror(t("err_title"), t("rec_err_name"))
            return
        if not self.components:
            messagebox.showerror(t("err_title"), t("rec_err_comp"))
            return
        try:
            rend = int(self.rend_var.get())
            if rend <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(t("err_title"), t("rec_err_yield"))
            return

        validade_dias = None
        val_txt = self.validade_var.get().strip()
        if val_txt:
            try:
                validade_dias = int(val_txt)
                if validade_dias <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(t("err_title"), t("rec_err_val"))
                return

        preco_venda = 0.0
        pv_txt = self.preco_venda_var.get().strip().replace(",", ".")
        if pv_txt:
            try:
                preco_venda = float(pv_txt)
                if preco_venda < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(t("err_title"), t("rec_err_price"))
                return

        comps = [
            {"ingrediente_id": c["ingrediente_id"], "quantidade": c["quantidade"]}
            for c in self.components
        ]
        database.salvar_receita(
            nome, rend, self.obs_var.get().strip(),
            comps, receita_id=self.recipe_id,
            validade_dias=validade_dias, preco_venda=preco_venda
        )
        messagebox.showinfo(t("info_title"), t("rec_msg_saved"))
        self.clear()
        self.refresh_recipes_list()
        self.on_change()

    def delete(self):
        if self.recipe_id is None:
            messagebox.showwarning(t("warn_title"), t("rec_err_name"))
            return
        if messagebox.askyesno(t("confirm_title"), t("rec_confirm_del")):
            database.excluir_receita(self.recipe_id)
            self.clear()
            self.refresh_recipes_list()
            self.on_change()

    def clear(self):
        self.recipe_id = None
        self.nome_var.set("")
        self.rend_var.set("1")
        self.validade_var.set("")
        self.preco_venda_var.set("")
        self.obs_var.set("")
        self.components = []
        self._populate_comp_table()
        self.tab_rec.selection_remove(self.tab_rec.selection())

    # Compatibility alias
    _refresh_mapa = refresh_ingredients_map

