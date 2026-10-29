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


# Compatibility aliases
UNIDADES_PADRAO = STANDARD_UNITS
unidades_compativeis = compatible_units
converter_quantidade = convert_quantity
habilitar_ordenacao_treeview = enable_treeview_sorting
