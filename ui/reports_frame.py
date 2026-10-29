"""
ui/reports_frame.py — Reports Export, Backup/Restore & Demo Data Tab for harErp
===============================================================================
Supports exporting management reports to Excel (.xlsx), PDF (.pdf), and CSV (.csv),
plus SQLite database backup, integrity-validated restore, and demo data seeding
with live EN / PT-BR internationalization.
"""

from tkinter import ttk, messagebox, filedialog

import database
import reports
from ui.i18n import I18n, t


class ReportsFrame(ttk.Frame):
    def __init__(self, parent, on_change=None):
        super().__init__(parent, padding=20)
        self.on_change = on_change or (lambda: None)

        # ── Management Reports Export
        self.sec_rel = ttk.LabelFrame(self, text=t("rep_sec_export"), padding=16)
        self.sec_rel.pack(fill="x", pady=(0, 16))

        self.lbl_desc_export = ttk.Label(self.sec_rel, style="Card.TLabel", text=t("rep_desc_export"))
        self.lbl_desc_export.pack(anchor="w", pady=(0, 14))

        btns_rel = ttk.Frame(self.sec_rel, style="Card.TFrame")
        btns_rel.pack(anchor="w")
        self.btn_xlsx = ttk.Button(
            btns_rel, text=t("rep_btn_xlsx"), style="Primary.TButton", command=self.export_excel
        )
        self.btn_xlsx.pack(side="left", padx=(0, 10))
        self.btn_pdf = ttk.Button(
            btns_rel, text=t("rep_btn_pdf"), style="Primary.TButton", command=self.export_pdf
        )
        self.btn_pdf.pack(side="left", padx=(0, 10))
        self.btn_csv = ttk.Button(btns_rel, text=t("rep_btn_csv"), command=self.export_csv)
        self.btn_csv.pack(side="left")

        # ── Data Safety (Backup / Restore) & Demo Data
        self.sec_bkp = ttk.LabelFrame(self, text=t("rep_sec_bkp"), padding=16)
        self.sec_bkp.pack(fill="x")

        self.lbl_desc_bkp = ttk.Label(self.sec_bkp, style="Card.TLabel", text=t("rep_desc_bkp"))
        self.lbl_desc_bkp.pack(anchor="w", pady=(0, 14))

        btns_bkp = ttk.Frame(self.sec_bkp, style="Card.TFrame")
        btns_bkp.pack(anchor="w")
        self.btn_bkp = ttk.Button(
            btns_bkp, text=t("rep_btn_bkp"), style="Success.TButton", command=self.backup_database
        )
        self.btn_bkp.pack(side="left", padx=(0, 10))
        self.btn_rest = ttk.Button(btns_bkp, text=t("rep_btn_rest"), command=self.restore_backup)
        self.btn_rest.pack(side="left", padx=(0, 10))
        self.btn_demo = ttk.Button(btns_bkp, text=t("rep_btn_demo"), command=self.load_demo_data)
        self.btn_demo.pack(side="left")

        self.status_label = ttk.Label(self, text="", style="SectionTitle.TLabel")
        self.status_label.pack(anchor="w", pady=(16, 0))

        I18n.register_listener(self._on_language_change)

    def _on_language_change(self):
        self.sec_rel.config(text=t("rep_sec_export"))
        self.lbl_desc_export.config(text=t("rep_desc_export"))
        self.btn_xlsx.config(text=t("rep_btn_xlsx"))
        self.btn_pdf.config(text=t("rep_btn_pdf"))
        self.btn_csv.config(text=t("rep_btn_csv"))
        self.sec_bkp.config(text=t("rep_sec_bkp"))
        self.lbl_desc_bkp.config(text=t("rep_desc_bkp"))
        self.btn_bkp.config(text=t("rep_btn_bkp"))
        self.btn_rest.config(text=t("rep_btn_rest"))
        self.btn_demo.config(text=t("rep_btn_demo"))

    def export_excel(self):
        en = I18n.is_en()
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook" if en else "Planilha Excel", "*.xlsx")],
            initialfile="harerp_report.xlsx" if en else "relatorio_harerp.xlsx",
        )
        if not path:
            return
        try:
            reports.exportar_excel(path)
            msg = f"✔ Excel report saved to: {path}" if en else f"✔ Relatório Excel salvo em: {path}"
            self.status_label.config(text=msg)
            messagebox.showinfo(t("info_title"), msg)
        except Exception as err:
            messagebox.showerror(t("err_title"), str(err))

    exportar_excel = export_excel

    def export_pdf(self):
        en = I18n.is_en()
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Document" if en else "Documento PDF", "*.pdf")],
            initialfile="harerp_report.pdf" if en else "relatorio_harerp.pdf",
        )
        if not path:
            return
        try:
            reports.exportar_pdf(path)
            msg = f"✔ PDF report saved to: {path}" if en else f"✔ Relatório PDF salvo em: {path}"
            self.status_label.config(text=msg)
            messagebox.showinfo(t("info_title"), msg)
        except Exception as err:
            messagebox.showerror(t("err_title"), str(err))

    exportar_pdf = export_pdf

    def export_csv(self):
        en = I18n.is_en()
        folder = filedialog.askdirectory(
            title="Select folder to save CSV files" if en else "Selecione a pasta para salvar os arquivos CSV"
        )
        if not folder:
            return
        try:
            files = database.exportar_csv_tabelas(folder)
            msg = (
                f"✔ {len(files)} CSV files exported to: {folder}"
                if en
                else f"✔ {len(files)} arquivos CSV exportados em: {folder}"
            )
            self.status_label.config(text=msg)
            messagebox.showinfo(t("info_title"), msg)
        except Exception as err:
            messagebox.showerror(t("err_title"), str(err))

    exportar_csv = export_csv

    def backup_database(self):
        en = I18n.is_en()
        path = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Database" if en else "Banco de Dados SQLite", "*.db")],
            initialfile=f"harerp_backup_{database.hoje()}.db",
        )
        if not path:
            return
        try:
            database.fazer_backup(path)
            msg = f"✔ Backup saved to: {path}" if en else f"✔ Backup realizado com sucesso em: {path}"
            self.status_label.config(text=msg)
            messagebox.showinfo(t("info_title"), msg)
        except Exception as err:
            messagebox.showerror(t("err_title"), str(err))

    fazer_backup = backup_database

    def restore_backup(self):
        en = I18n.is_en()
        path = filedialog.askopenfilename(
            title="Select backup file (.db)" if en else "Selecione o arquivo de backup (.db)",
            filetypes=[
                ("SQLite Database" if en else "Banco de Dados SQLite", "*.db"),
                ("All files" if en else "Todos os arquivos", "*.*"),
            ],
        )
        if not path:
            return
        confirm_msg = (
            "Warning: current data will be replaced by the selected backup file.\n\nProceed?"
            if en
            else "Atenção: os dados atuais serão substituídos pelo conteúdo do arquivo de backup selecionado.\n\nDeseja prosseguir?"
        )
        if not messagebox.askyesno(t("confirm_title"), confirm_msg):
            return
        try:
            database.restaurar_backup(path)
            self.on_change()
            msg = f"✔ Backup restored from: {path}" if en else f"✔ Backup restaurado a partir de: {path}"
            self.status_label.config(text=msg)
            messagebox.showinfo(t("info_title"), msg)
        except Exception as err:
            messagebox.showerror(t("err_title"), str(err))

    restaurar_backup = restore_backup

    def load_demo_data(self):
        en = I18n.is_en()
        confirm_msg = (
            "Insert sample ingredients, recipes, production batches, and financial transactions?"
            if en
            else "Deseja inserir insumos, receitas, lotes e lançamentos financeiros de exemplo?"
        )
        if not messagebox.askyesno(t("confirm_title"), confirm_msg):
            return
        try:
            inserted = database.popular_dados_exemplo()
            self.on_change()
            if inserted:
                msg = (
                    "✔ Demo data loaded successfully."
                    if en
                    else "✔ Dados de demonstração carregados com sucesso."
                )
                self.status_label.config(text=msg)
                messagebox.showinfo(t("info_title"), msg)
            else:
                msg = (
                    "ℹ Demo data was already present in the database."
                    if en
                    else "ℹ Os dados de demonstração já estavam carregados."
                )
                self.status_label.config(text=msg)
                messagebox.showinfo(t("warn_title"), msg)
        except Exception as err:
            messagebox.showerror(t("err_title"), str(err))

    carregar_demo = load_demo_data


# Backward-compatible alias
RelatoriosFrame = ReportsFrame

