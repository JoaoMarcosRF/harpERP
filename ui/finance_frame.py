"""
ui/finance_frame.py — Financial Management Tab for harErp
=========================================================
Manages revenues, expenses, cash flow summary, and date/type/search filters
with full live EN / PT-BR internationalization.
"""

import tkinter as tk
from tkinter import ttk, messagebox

import database
from ui.theme import ThemeManager, configure_treeview_tags
from ui.utils import enable_treeview_sorting, open_category_manager
from ui.i18n import I18n, t


class FinanceFrame(ttk.Frame):
    def __init__(self, parent, on_change=None):
        super().__init__(parent, padding=12)
        self.on_change = on_change or (lambda: None)
        self.selected_id = None

        self._build_form()
        self._build_summary()
        self._build_table()

        ThemeManager.register_listener(self._on_theme_change)
        I18n.register_listener(self._on_language_change)
        self.refresh_list()

    def _build_form(self):
        self.form_frame = ttk.LabelFrame(self, text=t("fin_form_title"), padding=12)
        self.form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.lbl_type = ttk.Label(self.form_frame, text=t("fin_type"), style="Card.TLabel")
        self.lbl_type.grid(row=0, column=0, sticky="w", pady=4)
        self.type_var = tk.StringVar(value="receita")
        type_box = ttk.Frame(self.form_frame, style="Card.TFrame")
        type_box.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.rb_rev = ttk.Radiobutton(type_box, text=t("revenue"), variable=self.type_var, value="receita")
        self.rb_rev.pack(side="left")
        self.rb_exp = ttk.Radiobutton(type_box, text=t("expense"), variable=self.type_var, value="despesa")
        self.rb_exp.pack(side="left", padx=(10, 0))

        field_defs = [
            ("fin_cat", "categoria"),
            ("fin_desc", "descricao"),
            ("fin_val", "valor"),
            ("fin_date", "data"),
        ]
        self.vars = {}
        self.form_labels = {}
        for i, (t_key, key) in enumerate(field_defs, start=1):
            lbl = ttk.Label(self.form_frame, text=t(t_key), style="Card.TLabel")
            lbl.grid(row=i, column=0, sticky="w", pady=4)
            self.form_labels[t_key] = lbl
            var = tk.StringVar()
            if key == "categoria":
                cat_box = ttk.Frame(self.form_frame, style="Card.TFrame")
                cat_box.grid(row=i, column=1, sticky="w", pady=4, padx=(8, 0))
                self.combo_cat = ttk.Combobox(cat_box, textvariable=var, width=16)
                self.combo_cat.pack(side="left")
                self.btn_cat_mgr = ttk.Button(
                    cat_box,
                    text=t("cat_btn_manage"),
                    command=self._open_category_dialog,
                )
                self.btn_cat_mgr.pack(side="left", padx=(4, 0))
            else:
                ttk.Entry(self.form_frame, textvariable=var, width=28).grid(row=i, column=1, pady=4, padx=(8, 0))
            self.vars[key] = var
        self.vars["data"].set(database.hoje())

        btns = ttk.Frame(self.form_frame, style="Card.TFrame")
        btns.grid(row=len(field_defs) + 1, column=0, columnspan=2, pady=(12, 0))
        self.btn_save = ttk.Button(btns, text=t("btn_save"), style="Primary.TButton", command=self.save_transaction)
        self.btn_save.pack(side="left", padx=3)
        self.btn_new = ttk.Button(btns, text=t("btn_new"), command=self.clear_form)
        self.btn_new.pack(side="left", padx=3)
        self.btn_del = ttk.Button(btns, text=t("btn_delete"), style="Danger.TButton", command=self.delete_transaction)
        self.btn_del.pack(side="left", padx=3)

    def _build_summary(self):
        self.summary_frame = ttk.LabelFrame(self, text=t("fin_summary_title"), padding=12)
        self.summary_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 12), pady=(12, 0))

        self.label_revenues = ttk.Label(self.summary_frame, text="", style="CardBold.TLabel")
        self.label_revenues.pack(anchor="w", pady=2)
        self.label_expenses = ttk.Label(self.summary_frame, text="", style="CardBold.TLabel")
        self.label_expenses.pack(anchor="w", pady=2)
        self.label_balance = ttk.Label(self.summary_frame, text="", style="KPIValor.TLabel")
        self.label_balance.pack(anchor="w", pady=(8, 0))

    def _build_table(self):
        right = ttk.Frame(self)
        right.grid(row=0, column=1, rowspan=2, sticky="nsew")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        # Filter bar
        self.filter_frame = ttk.LabelFrame(right, text=t("fin_filter_title"), padding=10)
        self.filter_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        self.lbl_from = ttk.Label(self.filter_frame, text=t("fin_from"), style="Card.TLabel")
        self.lbl_from.pack(side="left")
        self.filter_start_var = tk.StringVar()
        ttk.Entry(self.filter_frame, textvariable=self.filter_start_var, width=11).pack(side="left", padx=(4, 10))

        self.lbl_to = ttk.Label(self.filter_frame, text=t("fin_to"), style="Card.TLabel")
        self.lbl_to.pack(side="left")
        self.filter_end_var = tk.StringVar()
        ttk.Entry(self.filter_frame, textvariable=self.filter_end_var, width=11).pack(side="left", padx=(4, 10))

        self.lbl_ftype = ttk.Label(self.filter_frame, text=t("fin_type").replace("*", "") + ":", style="Card.TLabel")
        self.lbl_ftype.pack(side="left")
        self.filter_type_var = tk.StringVar(value=t("all"))
        self.combo_type = ttk.Combobox(
            self.filter_frame,
            textvariable=self.filter_type_var,
            values=(t("all"), t("revenue"), t("expense")),
            width=10,
            state="readonly",
        )
        self.combo_type.pack(side="left", padx=(4, 10))

        self.lbl_fsearch = ttk.Label(self.filter_frame, text=t("fin_search"), style="Card.TLabel")
        self.lbl_fsearch.pack(side="left")
        self.filter_term_var = tk.StringVar()
        ttk.Entry(self.filter_frame, textvariable=self.filter_term_var, width=16).pack(side="left", padx=(4, 10))

        self.btn_filter = ttk.Button(
            self.filter_frame, text=t("btn_filter"), style="Primary.TButton", command=self.refresh_list
        )
        self.btn_filter.pack(side="left", padx=3)
        self.btn_clear_filter = ttk.Button(self.filter_frame, text=t("btn_clear"), command=self.clear_filters)
        self.btn_clear_filter.pack(side="left", padx=3)

        cols = ("id", "data", "tipo", "categoria", "descricao", "valor")
        self.table = ttk.Treeview(right, columns=cols, show="headings", height=18)
        for c in cols:
            width = 55 if c == "id" else (190 if c == "descricao" else 110)
            self.table.column(c, width=width, anchor="center")
        self._update_table_headings()
        self.table.grid(row=1, column=0, sticky="nsew")
        self.table.bind("<<TreeviewSelect>>", self._on_select)
        enable_treeview_sorting(self.table)
        configure_treeview_tags(self.table)

        scroll = ttk.Scrollbar(right, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky="ns")

    def _update_table_headings(self):
        headings = {
            "id": t("fin_col_id"),
            "data": t("fin_col_date"),
            "tipo": t("fin_col_type"),
            "categoria": t("fin_col_cat"),
            "descricao": t("fin_col_desc"),
            "valor": t("fin_col_val"),
        }
        for col, text in headings.items():
            self.table.heading(col, text=text)

    def _open_category_dialog(self):
        open_category_manager(
            self,
            default_scope="financeiro",
            on_select=lambda nome: self.vars["categoria"].set(nome),
            on_updated=self._on_categories_changed,
        )

    def _on_categories_changed(self):
        self.refresh_categories()
        self.refresh_list()
        self.on_change()

    def refresh_categories(self):
        if hasattr(self, "combo_cat"):
            self.combo_cat["values"] = database.listar_nomes_categorias("financeiro")

    def _on_theme_change(self):
        configure_treeview_tags(self.table)
        self._update_summary_colors()

    def _on_language_change(self):
        self.form_frame.config(text=t("fin_form_title"))
        self.lbl_type.config(text=t("fin_type"))
        self.rb_rev.config(text=t("revenue"))
        self.rb_exp.config(text=t("expense"))
        for t_key, lbl in self.form_labels.items():
            lbl.config(text=t(t_key))
        if hasattr(self, "btn_cat_mgr"):
            self.btn_cat_mgr.config(text=t("cat_btn_manage"))
        self.btn_save.config(text=t("btn_save"))
        self.btn_new.config(text=t("btn_new"))
        self.btn_del.config(text=t("btn_delete"))

        self.summary_frame.config(text=t("fin_summary_title"))
        self.filter_frame.config(text=t("fin_filter_title"))
        self.lbl_from.config(text=t("fin_from"))
        self.lbl_to.config(text=t("fin_to"))
        self.lbl_ftype.config(text=t("fin_type").replace("*", "") + ":")
        self.lbl_fsearch.config(text=t("fin_search"))
        self.combo_type["values"] = (t("all"), t("revenue"), t("expense"))
        self.filter_type_var.set(t("all"))
        self.btn_filter.config(text=t("btn_filter"))
        self.btn_clear_filter.config(text=t("btn_clear"))

        self._update_table_headings()
        self.refresh_list()

    def _update_summary_colors(self):
        p = ThemeManager.palette()
        self.label_revenues.config(foreground=p["sucesso"])
        self.label_expenses.config(foreground=p["perigo"])

    def clear_filters(self):
        self.filter_start_var.set("")
        self.filter_end_var.set("")
        self.filter_type_var.set(t("all"))
        self.filter_term_var.set("")
        self.refresh_list()

    def refresh_list(self):
        self.refresh_categories()
        for item in self.table.get_children():
            self.table.delete(item)

        ini = self.filter_start_var.get().strip() or None
        fim = self.filter_end_var.get().strip() or None
        raw_type = self.filter_type_var.get().strip()
        if raw_type in (t("revenue"), "receita", "Revenue", "Receita"):
            db_type = "receita"
        elif raw_type in (t("expense"), "despesa", "Expense", "Despesa"):
            db_type = "despesa"
        else:
            db_type = None
        termo = self.filter_term_var.get().strip() or None

        for idx, m in enumerate(database.listar_movimentacoes_financeiras(ini, fim, tipo=db_type, termo=termo)):
            zebra = "par" if idx % 2 == 0 else "impar"
            tag_type = "receita" if m["tipo"] == "receita" else "despesa"
            type_label = t("revenue") if m["tipo"] == "receita" else t("expense")
            self.table.insert(
                "",
                "end",
                iid=m["id"],
                tags=(zebra, tag_type),
                values=(
                    m["id"],
                    m["data"],
                    type_label,
                    m["categoria"],
                    m["descricao"],
                    f'{m["valor"]:.2f}',
                ),
            )

        revenues, expenses, balance = database.saldo_atual()
        self.label_revenues.config(text=t("fin_lbl_rev", val=revenues))
        self.label_expenses.config(text=t("fin_lbl_exp", val=expenses))
        self.label_balance.config(text=t("fin_lbl_bal", val=balance))
        self._update_summary_colors()

    # Alias for legacy callers
    atualizar_lista = refresh_list

    def _on_select(self, _):
        sel = self.table.selection()
        if not sel:
            return
        m = database.obter_movimentacao_financeira(int(sel[0]))
        if not m:
            return
        self.selected_id = m["id"]
        self.type_var.set(m["tipo"])
        self.vars["categoria"].set(m["categoria"] or "")
        self.vars["descricao"].set(m["descricao"] or "")
        self.vars["valor"].set(f'{m["valor"]:.2f}')
        self.vars["data"].set(m["data"])

    def clear_form(self):
        self.selected_id = None
        self.type_var.set("receita")
        self.vars["categoria"].set("")
        self.vars["descricao"].set("")
        self.vars["valor"].set("")
        self.vars["data"].set(database.hoje())
        self.table.selection_remove(self.table.selection())

    limpar = clear_form

    def save_transaction(self):
        try:
            val = float(self.vars["valor"].get().replace(",", "."))
            if val <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(t("err_title"), t("fin_err_val"))
            return

        dt = self.vars["data"].get().strip() or database.hoje()
        cat = self.vars["categoria"].get().strip()
        desc = self.vars["descricao"].get().strip()

        try:
            if self.selected_id is None:
                database.adicionar_movimentacao_financeira(self.type_var.get(), cat, desc, val, dt)
            else:
                database.atualizar_movimentacao_financeira(self.selected_id, self.type_var.get(), cat, desc, val, dt)
        except ValueError as err:
            messagebox.showerror(t("err_title"), str(err))
            return

        self.clear_form()
        self.refresh_list()
        self.on_change()

    registrar = save_transaction

    def delete_transaction(self):
        sel = self.table.selection()
        if not sel:
            messagebox.showwarning(t("warn_title"), t("fin_err_sel"))
            return
        if messagebox.askyesno(t("confirm_title"), t("fin_confirm_del")):
            database.excluir_movimentacao_financeira(int(sel[0]))
            self.clear_form()
            self.refresh_list()
            self.on_change()

    excluir = delete_transaction


# Backward-compatible alias
FinanceiroFrame = FinanceFrame

