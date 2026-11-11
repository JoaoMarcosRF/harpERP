"""
main.py — harErp Desktop Application Entry Point
================================================
Manufacturing, Batch Inventory & Financial Cash Flow ERP
Run with:  python main.py
"""

from datetime import datetime
import os
import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt

import database
from ui.theme import ThemeManager
from ui.i18n import I18n, t
from ui.ingredients_frame import IngredientsFrame
from ui.operational_frame import OperationalFrame
from ui.recipes_frame import RecipesFrame
from ui.products_frame import ProductsFrame
from ui.finance_frame import FinanceFrame
from ui.analytics_frame import AnalyticsFrame
from ui.reports_frame import ReportsFrame


class HarErpApp(tk.Tk):
    def __init__(self, lang=None, theme=None):
        super().__init__()

        database.load_env()
        database.criar_tabelas()

        resolved_lang = lang or os.environ.get("HARERP_DEFAULT_LANG", "en")
        resolved_theme = theme or os.environ.get("HARERP_DEFAULT_THEME", "dark")
        geometry = os.environ.get("HARERP_WINDOW_GEOMETRY", "1280x800")

        # Reset listeners when re-instantiating in tests and apply initial language & theme
        ThemeManager._listeners.clear()
        I18n._listeners.clear()
        I18n.set_lang(resolved_lang)
        ThemeManager.apply(self, resolved_theme)

        self.title(t("app_title"))
        self.geometry(geometry)
        self.minsize(1060, 680)

        self._build_header()

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=(8, 4))

        self.ingredients_frame = IngredientsFrame(nb, on_change=self._on_change)
        self.operational_frame = OperationalFrame(nb, on_change=self._on_change)
        self.recipes_frame = RecipesFrame(nb, on_change=self._on_change)
        self.products_frame = ProductsFrame(nb, on_change=self._on_change)
        self.finance_frame = FinanceFrame(nb, on_change=self._on_change)
        self.analytics_frame = AnalyticsFrame(nb)
        self.reports_frame = ReportsFrame(nb, on_change=self._on_change)

        # Keep Portuguese attribute aliases for backward compatibility
        self.ingredientes_frame = self.ingredients_frame
        self.operacionais_frame = self.operational_frame
        self.receitas_frame = self.recipes_frame
        self.produtos_frame = self.products_frame
        self.financeiro_frame = self.finance_frame
        self.estatisticas_frame = self.analytics_frame
        self.relatorios_frame = self.reports_frame

        nb.add(self.ingredients_frame, text=t("tab_ingredients"))
        nb.add(self.operational_frame, text=t("tab_operational"))
        nb.add(self.recipes_frame, text=t("tab_recipes"))
        nb.add(self.products_frame, text=t("tab_products"))
        nb.add(self.finance_frame, text=t("tab_finance"))
        nb.add(self.analytics_frame, text=t("tab_analytics"))
        nb.add(self.reports_frame, text=t("tab_reports"))

        nb.bind("<<NotebookTabChanged>>", self._on_tab_change)
        self.notebook = nb

        self._build_footer()
        self._bind_shortcuts()
        I18n.register_listener(self._on_language_change)
        self._refresh_top_summary()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_header(self):
        self.header = ttk.Frame(self, style="Header.TFrame", padding=(16, 10))
        self.header.pack(fill="x")

        left = ttk.Frame(self.header, style="Header.TFrame")
        left.pack(side="left")
        ttk.Label(left, text="harErp", style="HeaderTitle.TLabel").pack(side="left")
        self.lbl_subtitle = ttk.Label(
            left, text=t("header_subtitle"), style="HeaderSub.TLabel"
        )
        self.lbl_subtitle.pack(side="left", pady=(3, 0))

        right = ttk.Frame(self.header, style="Header.TFrame")
        right.pack(side="right")

        self.lbl_top_status = ttk.Label(right, text="", style="HeaderSub.TLabel")
        self.lbl_top_status.pack(side="left", padx=(0, 14))

        self.btn_lang = ttk.Button(
            right,
            text=t("btn_lang"),
            style="ThemeToggle.TButton",
            command=self._toggle_language,
        )
        self.btn_lang.pack(side="right", padx=(8, 0))

        self.btn_theme = ttk.Button(
            right,
            text=t("btn_theme_light") if ThemeManager._current_mode == "dark" else t("btn_theme_dark"),
            style="ThemeToggle.TButton",
            command=self._toggle_theme,
        )
        self.btn_theme.pack(side="right")

    def _build_footer(self):
        footer = ttk.Frame(self, padding=(14, 4))
        footer.pack(fill="x", side="bottom")

        self.lbl_footer_left = ttk.Label(footer, text="", font=("Segoe UI", 8))
        self.lbl_footer_left.pack(side="left")

        self.lbl_footer_right = ttk.Label(
            footer, text=t("footer_shortcuts"), font=("Segoe UI", 8)
        )
        self.lbl_footer_right.pack(side="right")

    def _bind_shortcuts(self):
        self.bind("<F5>", lambda _: self._on_change())
        self.bind("<Control-d>", lambda _: self._toggle_theme())
        self.bind("<Control-D>", lambda _: self._toggle_theme())
        self.bind("<Control-l>", lambda _: self._toggle_language())
        self.bind("<Control-L>", lambda _: self._toggle_language())
        self.bind("<Control-b>", lambda _: self.reports_frame.backup_database())
        self.bind("<Control-B>", lambda _: self.reports_frame.backup_database())
        for i in range(7):
            self.bind(f"<Control-Key-{i + 1}>", lambda _, idx=i: self.notebook.select(idx))

    def _toggle_theme(self):
        new_theme = ThemeManager.toggle(self)
        self.btn_theme.config(
            text=t("btn_theme_light") if new_theme == "dark" else t("btn_theme_dark")
        )

    _alternar_tema = _toggle_theme

    def _toggle_language(self):
        I18n.toggle()

    def _on_language_change(self):
        self.title(t("app_title"))
        self.lbl_subtitle.config(text=t("header_subtitle"))
        self.btn_lang.config(text=t("btn_lang"))
        self.btn_theme.config(
            text=t("btn_theme_light") if ThemeManager._current_mode == "dark" else t("btn_theme_dark")
        )
        self.notebook.tab(self.ingredients_frame, text=t("tab_ingredients"))
        self.notebook.tab(self.operational_frame, text=t("tab_operational"))
        self.notebook.tab(self.recipes_frame, text=t("tab_recipes"))
        self.notebook.tab(self.products_frame, text=t("tab_products"))
        self.notebook.tab(self.finance_frame, text=t("tab_finance"))
        self.notebook.tab(self.analytics_frame, text=t("tab_analytics"))
        self.notebook.tab(self.reports_frame, text=t("tab_reports"))
        self.lbl_footer_right.config(text=t("footer_shortcuts"))
        self._refresh_top_summary()

    def _refresh_top_summary(self):
        _, _, balance = database.saldo_atual()
        alerts = len(database.ingredientes_abaixo_minimo()) + len(database.operacionais_abaixo_minimo())
        alert_txt = t("header_alert_warn", count=alerts) if alerts else t("header_alert_ok")
        self.lbl_top_status.config(text=f"{t('header_cash', saldo=balance)}{alert_txt}")
        if hasattr(self, "lbl_footer_left"):
            now_str = datetime.now().strftime("%H:%M:%S")
            self.lbl_footer_left.config(
                text=t("footer_db", path=database.DB_PATH, time=now_str)
            )

    def _on_change(self):
        """Propagates cross-tab updates after any data modification."""
        self.ingredients_frame.refresh_list()
        self.operational_frame.refresh_list()
        self.recipes_frame.refresh_ingredients_map()
        self.products_frame.refresh_recipes()
        self.products_frame.refresh_batches()
        self.finance_frame.refresh_list()
        self.analytics_frame.refresh()
        self._refresh_top_summary()

    def _on_tab_change(self, _):
        widget = self.nametowidget(self.notebook.select())
        if widget is self.analytics_frame:
            self.analytics_frame.refresh()

    def _on_close(self):
        try:
            if hasattr(self, "recipes_frame"):
                self.recipes_frame._auto_persist_if_editing()
            database.sincronizar_banco()
            plt.close("all")
            self.quit()
        finally:
            self.destroy()

    _ao_fechar = _on_close


# Backward-compatible alias
Aplicacao = HarErpApp


if __name__ == "__main__":
    app = HarErpApp()
    app.mainloop()
