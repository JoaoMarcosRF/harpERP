"""Shared UI utilities (Tkinter / ttk column sorting and unit of measure conversions)."""

STANDARD_UNITS = (
    "un",   # Unit
    "kg",   # Kilogram
    "g",    # Gram
    "mg",   # Milligram
    "L",    # Liter
    "ml",   # Milliliter
    "cx",   # Box
    "pct",  # Pack
    "fd",   # Bale/Bundle
    "dz",   # Dozen
    "m",    # Meter
    "cm",   # Centimeter
)

_UNIT_FAMILIES = {
    "kg": ("mass", 1000.0),
    "g":  ("mass", 1.0),
    "mg": ("mass", 0.001),
    "L":  ("volume", 1000.0),
    "ml": ("volume", 1.0),
    "m":  ("length", 100.0),
    "cm": ("length", 1.0),
    "dz": ("count", 12.0),
    "un": ("count", 1.0),
}


def compatible_units(base_unit):
    """Returns a tuple of compatible units for quick selection in stock movements and recipes."""
    u = (base_unit or "un").strip()
    if u in ("kg", "g", "mg"):
        options = ["kg", "g", "mg"]
    elif u in ("L", "ml"):
        options = ["L", "ml"]
    elif u in ("m", "cm"):
        options = ["m", "cm"]
    elif u in ("un", "dz"):
        options = ["un", "dz"]
    else:
        options = [u]
    if u in options:
        options.remove(u)
    return tuple([u] + options)


def convert_quantity(value, from_unit, to_unit):
    """
    Converts `value` from `from_unit` to `to_unit`.
    If both belong to the same measurement family (e.g., 250 g -> 0.25 kg),
    returns the converted float. Otherwise returns `value` unchanged.
    """
    u_orig = (from_unit or "un").strip()
    u_dest = (to_unit or "un").strip()
    if u_orig == u_dest:
        return float(value)
    info_o = _UNIT_FAMILIES.get(u_orig)
    info_d = _UNIT_FAMILIES.get(u_dest)
    if info_o and info_d and info_o[0] == info_d[0]:
        factor = info_o[1] / info_d[1]
        return round(float(value) * factor, 6)
    return float(value)


def _sort_key(value):
    """Converts a Treeview cell string into a comparable tuple (numeric or text)."""
    if value is None:
        return (1, "")
    text = str(value).strip()
    if not text or text == "—":
        return (1, "")
    cleaned = (
        text.replace("R$", "")
        .replace("$", "")
        .replace("%", "")
        .replace(" ", "")
        .replace(",", ".")
    )
    try:
        return (0, float(cleaned))
    except ValueError:
        return (1, text.lower())


def enable_treeview_sorting(tree):
    """Enables sorting on any column of a ttk.Treeview when clicking its header."""
    sort_state = {}

    def sort_by(col):
        reverse = sort_state.get(col, False)
        items = [(tree.set(iid, col), iid) for iid in tree.get_children("")]
        items.sort(key=lambda pair: _sort_key(pair[0]), reverse=reverse)

        for idx, (_, iid) in enumerate(items):
            tree.move(iid, "", idx)

        sort_state[col] = not reverse
        arrow = " ▼" if reverse else " ▲"
        for c in tree["columns"]:
            current_txt = tree.heading(c, "text").replace(" ▲", "").replace(" ▼", "")
            tree.heading(c, text=(current_txt + arrow) if c == col else current_txt)

    for col in tree["columns"]:
        tree.heading(col, command=lambda c=col: sort_by(c))


def open_category_manager(parent, default_scope="geral", on_select=None, on_updated=None):
    """
    Opens a modal dialog to create, rename, delete, and select product/item categories.
    """
    import tkinter as tk
    from tkinter import ttk, messagebox
    import database
    from ui.i18n import t
    from ui.theme import ThemeManager, configure_treeview_tags

    p = ThemeManager.palette()
    win = tk.Toplevel(parent)
    win.title(t("cat_dlg_title"))
    win.geometry("680x460")
    win.configure(bg=p["bg_principal"])
    win.transient(parent.winfo_toplevel())
    win.grab_set()

    scope_options = [
        ("produto", t("cat_scope_prod")),
        ("ingrediente", t("cat_scope_ing")),
        ("operacional", t("cat_scope_op")),
        ("financeiro", t("cat_scope_fin")),
        ("geral", t("cat_scope_gen")),
    ]
    label_to_scope = {lbl: code for code, lbl in scope_options}
    scope_to_label = {code: lbl for code, lbl in scope_options}

    top_card = ttk.LabelFrame(win, text=t("cat_form_title"), padding=10)
    top_card.pack(fill="x", padx=12, pady=(12, 8))

    name_var = tk.StringVar()
    scope_var = tk.StringVar(value=scope_to_label.get(default_scope, t("cat_scope_gen")))
    desc_var = tk.StringVar()
    selected_cat_id = {"id": None, "name": ""}

    ttk.Label(top_card, text=t("cat_lbl_name"), style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=3)
    ent_name = ttk.Entry(top_card, textvariable=name_var, width=26)
    ent_name.grid(row=0, column=1, sticky="w", padx=(8, 16), pady=3)

    ttk.Label(top_card, text=t("cat_lbl_scope"), style="Card.TLabel").grid(row=0, column=2, sticky="w", pady=3)
    combo_scope = ttk.Combobox(
        top_card,
        textvariable=scope_var,
        values=[lbl for _, lbl in scope_options],
        width=22,
        state="readonly",
    )
    combo_scope.grid(row=0, column=3, sticky="w", padx=(8, 0), pady=3)

    ttk.Label(top_card, text=t("cat_lbl_desc"), style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=3)
    ttk.Entry(top_card, textvariable=desc_var, width=58).grid(
        row=1, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=3
    )

    btn_row = ttk.Frame(top_card, style="Card.TFrame")
    btn_row.grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 0))

    body = ttk.Frame(win, padding=(12, 0, 12, 12))
    body.pack(fill="both", expand=True)
    body.grid_rowconfigure(0, weight=1)
    body.grid_columnconfigure(0, weight=1)

    cols = ("id", "nome", "escopo", "descricao")
    tree = ttk.Treeview(body, columns=cols, show="headings", height=10)
    tree.heading("id", text=t("cat_col_id"))
    tree.heading("nome", text=t("cat_col_name"))
    tree.heading("escopo", text=t("cat_col_scope"))
    tree.heading("descricao", text=t("cat_col_desc"))
    tree.column("id", width=45, anchor="center")
    tree.column("nome", width=180, anchor="w")
    tree.column("escopo", width=150, anchor="center")
    tree.column("descricao", width=240, anchor="w")
    tree.grid(row=0, column=0, sticky="nsew")

    scroll = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
    scroll.grid(row=0, column=1, sticky="ns")
    tree.configure(yscrollcommand=scroll.set)
    enable_treeview_sorting(tree)
    configure_treeview_tags(tree)

    def refresh_table():
        for i in tree.get_children():
            tree.delete(i)
        cats = database.listar_categorias()
        for idx, c in enumerate(cats):
            zebra = "par" if idx % 2 == 0 else "impar"
            cid = c["id"] or f"tmp_{idx}"
            tree.insert(
                "",
                "end",
                iid=str(cid),
                tags=(zebra,),
                values=(
                    c["id"] or "—",
                    c["nome"],
                    scope_to_label.get(c["escopo"], c["escopo"]),
                    c["descricao"] or "",
                ),
            )

    def on_row_select(_=None):
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        try:
            selected_cat_id["id"] = int(vals[0])
        except ValueError:
            selected_cat_id["id"] = None
        selected_cat_id["name"] = vals[1]
        name_var.set(vals[1])
        scope_var.set(vals[2])
        desc_var.set(vals[3])

    def create_cat():
        nome = name_var.get().strip()
        if not nome:
            messagebox.showerror(t("err_title"), t("cat_err_name"), parent=win)
            return
        esc = label_to_scope.get(scope_var.get(), default_scope)
        database.adicionar_categoria(nome, esc, desc_var.get().strip())
        refresh_table()
        if on_updated:
            on_updated()
        if on_select:
            on_select(nome)
        messagebox.showinfo(t("info_title"), t("cat_msg_saved", nome=nome), parent=win)

    def rename_cat():
        if not selected_cat_id["id"]:
            messagebox.showwarning(t("warn_title"), t("cat_err_sel"), parent=win)
            return
        novo = name_var.get().strip()
        if not novo:
            messagebox.showerror(t("err_title"), t("cat_err_name"), parent=win)
            return
        database.renomear_categoria(selected_cat_id["id"], novo)
        refresh_table()
        if on_updated:
            on_updated()
        if on_select:
            on_select(novo)
        messagebox.showinfo(t("info_title"), t("cat_msg_renamed", nome=novo), parent=win)

    def delete_cat():
        if not selected_cat_id["id"]:
            messagebox.showwarning(t("warn_title"), t("cat_err_sel"), parent=win)
            return
        if messagebox.askyesno(
            t("confirm_title"),
            t("cat_confirm_del", nome=selected_cat_id["name"]),
            parent=win,
        ):
            database.excluir_categoria(selected_cat_id["id"])
            selected_cat_id["id"] = None
            selected_cat_id["name"] = ""
            name_var.set("")
            desc_var.set("")
            refresh_table()
            if on_updated:
                on_updated()

    def use_selected(_=None):
        chosen = name_var.get().strip() or selected_cat_id["name"]
        if not chosen:
            messagebox.showwarning(t("warn_title"), t("cat_err_sel"), parent=win)
            return
        esc = label_to_scope.get(scope_var.get(), default_scope)
        database.adicionar_categoria(chosen, esc, desc_var.get().strip())
        if on_updated:
            on_updated()
        if on_select:
            on_select(chosen)
        win.destroy()

    ttk.Button(btn_row, text=t("cat_btn_add"), style="Primary.TButton", command=create_cat).pack(side="left", padx=(0, 6))
    ttk.Button(btn_row, text=t("cat_btn_rename"), command=rename_cat).pack(side="left", padx=6)
    ttk.Button(btn_row, text=t("cat_btn_del"), style="Danger.TButton", command=delete_cat).pack(side="left", padx=6)
    ttk.Button(btn_row, text=t("cat_btn_select"), style="Success.TButton", command=use_selected).pack(side="left", padx=(14, 0))

    tree.bind("<<TreeviewSelect>>", on_row_select)
    tree.bind("<Double-1>", use_selected)
    refresh_table()
    ent_name.focus_set()
    return win


# Compatibility aliases
UNIDADES_PADRAO = STANDARD_UNITS
unidades_compativeis = compatible_units
converter_quantidade = convert_quantity
habilitar_ordenacao_treeview = enable_treeview_sorting
abrir_gerenciador_categorias = open_category_manager
