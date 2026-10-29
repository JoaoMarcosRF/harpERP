"""
ui/theme.py — Theme Engine (Dark Mode / Light Mode) and Modern ttk Styling
==========================================================================
Centralizes color palettes, typography, and component styles (Tkinter/ttk
and Matplotlib charts) with real-time theme toggling.
"""

from tkinter import ttk

FONT_FAMILY = "Segoe UI"

PALETTES = {
    "dark": {
        "name": "dark",
        "bg_principal": "#0f172a",      # Slate 900
        "bg_card": "#1e293b",           # Slate 800
        "bg_input": "#0f172a",          # Slate 900
        "bg_tabela": "#1e293b",         # Slate 800
        "bg_tabela_alt": "#243247",     # Slate 800/750
        "bg_cabecalho": "#0f172a",      # Header bar
        "borda": "#334155",             # Slate 700
        "texto": "#f1f5f9",             # Slate 100
        "texto_suave": "#94a3b8",       # Slate 400
        "primaria": "#3b82f6",          # Blue 500
        "primaria_hover": "#2563eb",    # Blue 600
        "secundaria": "#334155",        # Slate 700
        "secundaria_hover": "#475569",  # Slate 600
        "sucesso": "#10b981",           # Emerald 500
        "sucesso_hover": "#059669",     # Emerald 600
        "perigo": "#ef4444",            # Red 500
        "perigo_hover": "#dc2626",      # Red 600
        "aviso": "#f59e0b",             # Amber 500
        "roxo": "#a855f7",              # Purple 500
        "selecao_bg": "#2563eb",        # Blue 600
        "selecao_fg": "#ffffff",
        "tag_baixo_fg": "#fca5a5",
        "tag_baixo_bg": "#451a1a",
        "tag_vencido_fg": "#fca5a5",
        "tag_vencido_bg": "#451a1a",
        "tag_vencendo_fg": "#fcd34d",
        "tag_vencendo_bg": "#422c10",
        "tag_zerado_fg": "#64748b",
        "tag_receita_fg": "#34d399",
        "tag_despesa_fg": "#f87171",
    },
    "light": {
        "name": "light",
        "bg_principal": "#f1f5f9",      # Slate 100
        "bg_card": "#ffffff",           # White
        "bg_input": "#ffffff",          # White
        "bg_tabela": "#ffffff",         # White
        "bg_tabela_alt": "#f8fafc",     # Slate 50
        "bg_cabecalho": "#1e293b",      # Slate 800
        "borda": "#cbd5e1",             # Slate 300
        "texto": "#0f172a",             # Slate 900
        "texto_suave": "#475569",       # Slate 600
        "primaria": "#2563eb",          # Blue 600
        "primaria_hover": "#1d4ed8",    # Blue 700
        "secundaria": "#e2e8f0",        # Slate 200
        "secundaria_hover": "#cbd5e1",  # Slate 300
        "sucesso": "#059669",           # Emerald 600
        "sucesso_hover": "#047857",     # Emerald 700
        "perigo": "#dc2626",            # Red 600
        "perigo_hover": "#b91c1c",      # Red 700
        "aviso": "#d97706",             # Amber 600
        "roxo": "#7c3aed",              # Violet 600
        "selecao_bg": "#dbeafe",        # Blue 100
        "selecao_fg": "#1e3a8a",        # Blue 900
        "tag_baixo_fg": "#b91c1c",
        "tag_baixo_bg": "#fef2f2",
        "tag_vencido_fg": "#b91c1c",
        "tag_vencido_bg": "#fef2f2",
        "tag_vencendo_fg": "#b45309",
        "tag_vencendo_bg": "#fffbeb",
        "tag_zerado_fg": "#94a3b8",
        "tag_receita_fg": "#059669",
        "tag_despesa_fg": "#dc2626",
    },
}


class ThemeManager:
    """Manages the active theme (dark/light) and applies styles across the entire UI."""

    _current_mode = "dark"
    _listeners = []

    @classmethod
    def palette(cls):
        return PALETTES[cls._current_mode]

    @classmethod
    def is_dark(cls):
        return cls._current_mode == "dark"

    @classmethod
    def register_listener(cls, callback):
        if callback not in cls._listeners:
            cls._listeners.append(callback)

    @classmethod
    def toggle(cls, root):
        new_mode = "light" if cls._current_mode == "dark" else "dark"
        cls.apply(root, new_mode)
        return new_mode

    @classmethod
    def apply(cls, root, mode="dark"):
        cls._current_mode = mode if mode in PALETTES else "dark"
        p = cls.palette()

        root.configure(bg=p["bg_principal"])

        root.option_add("*TCombobox*Listbox.background", p["bg_card"])
        root.option_add("*TCombobox*Listbox.foreground", p["texto"])
        root.option_add("*TCombobox*Listbox.selectBackground", p["primaria"])
        root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        root.option_add("*TCombobox*Listbox.font", (FONT_FAMILY, 10))

        style = ttk.Style(root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure(
            ".",
            background=p["bg_principal"],
            foreground=p["texto"],
            fieldbackground=p["bg_input"],
            bordercolor=p["borda"],
            darkcolor=p["bg_card"],
            lightcolor=p["bg_card"],
            troughcolor=p["bg_principal"],
            focuscolor=p["primaria"],
            font=(FONT_FAMILY, 10),
        )

        style.configure("TFrame", background=p["bg_principal"])
        style.configure("Card.TFrame", background=p["bg_card"], relief="flat")
        style.configure("Header.TFrame", background=p["bg_cabecalho"])

        style.configure(
            "TLabelframe",
            background=p["bg_card"],
            bordercolor=p["borda"],
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "TLabelframe.Label",
            background=p["bg_card"],
            foreground=p["primaria"],
            font=(FONT_FAMILY, 10, "bold"),
            padding=(4, 0),
        )

        style.configure("TLabel", background=p["bg_principal"], foreground=p["texto"], font=(FONT_FAMILY, 10))
        style.configure("Card.TLabel", background=p["bg_card"], foreground=p["texto"], font=(FONT_FAMILY, 10))
        style.configure("CardMuted.TLabel", background=p["bg_card"], foreground=p["texto_suave"], font=(FONT_FAMILY, 9))
        style.configure("CardBold.TLabel", background=p["bg_card"], foreground=p["texto"], font=(FONT_FAMILY, 10, "bold"))
        style.configure("SectionTitle.TLabel", background=p["bg_principal"], foreground=p["texto"], font=(FONT_FAMILY, 11, "bold"))
        style.configure("KPIValor.TLabel", background=p["bg_card"], foreground=p["texto"], font=(FONT_FAMILY, 13, "bold"))
        style.configure("KPITitulo.TLabel", background=p["bg_card"], foreground=p["texto_suave"], font=(FONT_FAMILY, 9))

        style.configure("HeaderTitle.TLabel", background=p["bg_cabecalho"], foreground="#f8fafc", font=(FONT_FAMILY, 14, "bold"))
        style.configure("HeaderSub.TLabel", background=p["bg_cabecalho"], foreground="#94a3b8", font=(FONT_FAMILY, 9))

        style.configure(
            "TNotebook",
            background=p["bg_principal"],
            borderwidth=0,
            tabmargins=(2, 4, 2, 0),
        )
        style.configure(
            "TNotebook.Tab",
            background=p["bg_card"],
            foreground=p["texto_suave"],
            padding=(16, 8),
            borderwidth=1,
            bordercolor=p["borda"],
            font=(FONT_FAMILY, 10, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", p["primaria"]), ("active", p["secundaria_hover"])],
            foreground=[("selected", "#ffffff"), ("active", p["texto"])],
            expand=[("selected", (1, 1, 1, 0))],
        )

        style.configure(
            "TEntry",
            fieldbackground=p["bg_input"],
            foreground=p["texto"],
            insertcolor=p["texto"],
            bordercolor=p["borda"],
            lightcolor=p["borda"],
            darkcolor=p["borda"],
            padding=(6, 4),
        )
        style.map(
            "TEntry",
            bordercolor=[("focus", p["primaria"])],
            lightcolor=[("focus", p["primaria"])],
        )

        style.configure(
            "TCombobox",
            fieldbackground=p["bg_input"],
            background=p["secundaria"],
            foreground=p["texto"],
            arrowcolor=p["texto"],
            bordercolor=p["borda"],
            padding=(6, 4),
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", p["bg_input"])],
            foreground=[("readonly", p["texto"])],
            selectbackground=[("readonly", p["bg_input"])],
            selectforeground=[("readonly", p["texto"])],
            bordercolor=[("focus", p["primaria"])],
        )

        for w_style in ("TCheckbutton", "TRadiobutton"):
            style.configure(
                w_style,
                background=p["bg_card"],
                foreground=p["texto"],
                indicatorbackground=p["bg_input"],
                indicatorforeground=p["primaria"],
                font=(FONT_FAMILY, 9),
            )
            style.map(
                w_style,
                background=[("active", p["bg_card"])],
                foreground=[("active", p["primaria"])],
            )

        style.configure(
            "Surface.TCheckbutton",
            background=p["bg_principal"],
            foreground=p["texto"],
        )
        style.map("Surface.TCheckbutton", background=[("active", p["bg_principal"])])

        fg_sec = "#f8fafc" if cls.is_dark() else "#0f172a"
        style.configure(
            "TButton",
            background=p["secundaria"],
            foreground=fg_sec,
            bordercolor=p["borda"],
            padding=(12, 6),
            font=(FONT_FAMILY, 9, "bold"),
            relief="flat",
        )
        style.map(
            "TButton",
            background=[("active", p["secundaria_hover"]), ("pressed", p["primaria"])],
            foreground=[("pressed", "#ffffff")],
        )

        style.configure(
            "Primary.TButton",
            background=p["primaria"],
            foreground="#ffffff",
            bordercolor=p["primaria"],
            padding=(14, 6),
            font=(FONT_FAMILY, 9, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[("active", p["primaria_hover"]), ("pressed", p["primaria_hover"])],
            foreground=[("active", "#ffffff")],
        )

        style.configure(
            "Success.TButton",
            background=p["sucesso"],
            foreground="#ffffff",
            bordercolor=p["sucesso"],
            padding=(14, 6),
            font=(FONT_FAMILY, 9, "bold"),
        )
        style.map(
            "Success.TButton",
            background=[("active", p["sucesso_hover"]), ("pressed", p["sucesso_hover"])],
            foreground=[("active", "#ffffff")],
        )

        style.configure(
            "Danger.TButton",
            background=p["perigo"],
            foreground="#ffffff",
            bordercolor=p["perigo"],
            padding=(12, 6),
            font=(FONT_FAMILY, 9, "bold"),
        )
        style.map(
            "Danger.TButton",
            background=[("active", p["perigo_hover"]), ("pressed", p["perigo_hover"])],
            foreground=[("active", "#ffffff")],
        )

        style.configure(
            "ThemeToggle.TButton",
            background="#334155",
            foreground="#f8fafc",
            bordercolor="#475569",
            padding=(12, 5),
            font=(FONT_FAMILY, 9, "bold"),
        )
        style.map(
            "ThemeToggle.TButton",
            background=[("active", p["primaria"])],
            foreground=[("active", "#ffffff")],
        )

        style.configure(
            "Treeview",
            background=p["bg_tabela"],
            foreground=p["texto"],
            fieldbackground=p["bg_tabela"],
            bordercolor=p["borda"],
            rowheight=28,
            font=(FONT_FAMILY, 9),
        )
        style.map(
            "Treeview",
            background=[("selected", p["selecao_bg"])],
            foreground=[("selected", p["selecao_fg"])],
        )
        style.configure(
            "Treeview.Heading",
            background=p["secundaria"],
            foreground=fg_sec,
            bordercolor=p["borda"],
            relief="flat",
            padding=(6, 6),
            font=(FONT_FAMILY, 9, "bold"),
        )
        style.map(
            "Treeview.Heading",
            background=[("active", p["primaria"])],
            foreground=[("active", "#ffffff")],
        )

        style.configure(
            "Vertical.TScrollbar",
            background=p["secundaria"],
            troughcolor=p["bg_principal"],
            bordercolor=p["bg_principal"],
            arrowcolor=p["texto_suave"],
        )

        for cb in list(cls._listeners):
            try:
                cb()
            except Exception:
                pass

    # Aliases for compatibility
    paleta = palette
    registrar_ouvinte = register_listener
    alternar = toggle
    aplicar = apply
    _ouvintes = _listeners


GerenciadorTema = ThemeManager


def configure_treeview_tags(tree):
    """Configures semantic row colors on a Treeview according to the active theme."""
    p = ThemeManager.palette()
    tree.tag_configure("par", background=p["bg_tabela"])
    tree.tag_configure("impar", background=p["bg_tabela_alt"])
    tree.tag_configure("baixo", foreground=p["tag_baixo_fg"], background=p["tag_baixo_bg"])
    tree.tag_configure("vencido", foreground=p["tag_vencido_fg"], background=p["tag_vencido_bg"])
    tree.tag_configure("vencendo", foreground=p["tag_vencendo_fg"], background=p["tag_vencendo_bg"])
    tree.tag_configure("zerado", foreground=p["tag_zerado_fg"])
    tree.tag_configure("receita", foreground=p["tag_receita_fg"])
    tree.tag_configure("despesa", foreground=p["tag_despesa_fg"])


configurar_tags_treeview = configure_treeview_tags
