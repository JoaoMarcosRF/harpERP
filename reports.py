"""
reports.py — Excel (.xlsx) & PDF (.pdf) Management Reports for harErp
=====================================================================
Generates multi-sheet Excel workbooks and executive PDF reports covering
Ingredient Inventory, Recipes & Profit Margins, Product Batches, Stock Movements,
and Financial Cash Flow, respecting the active UI language (EN or PT-BR).
"""

from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import database
from ui.i18n import I18n

TITLE_FONT = Font(bold=True, size=13, name="Arial")
HEADER_FONT = Font(bold=True, color="FFFFFF", name="Arial")
HEADER_FILL = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")


def _format_header(ws, row_idx, columns):
    for i, title in enumerate(columns, start=1):
        cell = ws.cell(row=row_idx, column=i, value=title)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")


def _autofit_columns(ws, max_width=42):
    for col in ws.columns:
        length = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        letter = get_column_letter(col[0].column)
        ws.column_dimensions[letter].width = min(length + 4, max_width)


def export_excel(file_path):
    """Generates a 5-sheet .xlsx management report in the active UI language (EN / PT-BR)."""
    en = I18n.is_en()
    wb = Workbook()

    # --- 1. Ingredients ------------------------------------------------------
    ws_ing = wb.active
    ws_ing.title = "Ingredients" if en else "Ingredientes"
    ws_ing["A1"] = (
        "harErp — Ingredient Inventory Report"
        if en
        else "harErp — Relatório de Estoque de Ingredientes (Insumos)"
    )
    ws_ing["A1"].font = TITLE_FONT
    cols_ing = (
        [
            "ID", "Name", "Brand", "Category", "Unit",
            "Quantity", "Min. Stock", "Unit Cost ($)",
            "Stock Value ($)", "Status", "Created Date",
        ]
        if en
        else [
            "ID", "Nome", "Marca", "Categoria", "Unidade",
            "Quantidade", "Estoque Mínimo", "Custo Unit. (R$)",
            "Valor em Estoque (R$)", "Status", "Data Cadastro",
        ]
    )
    _format_header(ws_ing, 3, cols_ing)
    for i, p in enumerate(database.listar_ingredientes(), start=4):
        total_val = round(p["preco_custo"] * p["quantidade"], 2)
        status = (
            ("LOW STOCK" if en else "ABAIXO DO MÍNIMO")
            if p["quantidade"] <= p["estoque_minimo"]
            else "OK"
        )
        ws_ing.cell(row=i, column=1, value=p["id"])
        ws_ing.cell(row=i, column=2, value=p["nome"])
        ws_ing.cell(row=i, column=3, value=p["marca"])
        ws_ing.cell(row=i, column=4, value=p["categoria"])
        ws_ing.cell(row=i, column=5, value=p["unidade"])
        ws_ing.cell(row=i, column=6, value=p["quantidade"])
        ws_ing.cell(row=i, column=7, value=p["estoque_minimo"])
        ws_ing.cell(row=i, column=8, value=round(p["preco_custo"], 4))
        ws_ing.cell(row=i, column=9, value=total_val)
        ws_ing.cell(row=i, column=10, value=status)
        ws_ing.cell(row=i, column=11, value=p["data_cadastro"])
    _autofit_columns(ws_ing)

    # --- 2. Recipes & Profitability ------------------------------------------
    ws_rec = wb.create_sheet("Recipes & Costs" if en else "Receitas e Custos")
    ws_rec["A1"] = (
        "harErp — Recipes (BOM) & Profitability Analysis"
        if en
        else "harErp — Fichas Técnicas (Receitas) e Análise de Rentabilidade"
    )
    ws_rec["A1"].font = TITLE_FONT
    cols_rec = (
        [
            "ID", "Recipe", "Yield (un/batch)", "Shelf Life (days)",
            "# Inputs", "Batch Cost ($)", "Unit Cost ($)",
            "Selling Price ($)", "Unit Profit ($)", "Margin (%)",
        ]
        if en
        else [
            "ID", "Receita", "Rendimento (un/lote)", "Validade (dias)",
            "Nº Insumos", "Custo Lote (R$)", "Custo Unit. (R$)",
            "Preço Venda (R$)", "Lucro Unit. (R$)", "Margem (%)",
        ]
    )
    _format_header(ws_rec, 3, cols_rec)
    for i, r in enumerate(database.analise_rentabilidade_receitas(), start=4):
        ws_rec.cell(row=i, column=1, value=r["id"])
        ws_rec.cell(row=i, column=2, value=r["nome"])
        ws_rec.cell(row=i, column=3, value=r["rendimento"])
        ws_rec.cell(row=i, column=4, value=r["validade_dias"] or "—")
        ws_rec.cell(row=i, column=5, value=r["n_ingredientes"])
        ws_rec.cell(row=i, column=6, value=round(r["custo_lote"], 4))
        ws_rec.cell(row=i, column=7, value=round(r["custo_unitario"], 4))
        ws_rec.cell(row=i, column=8, value=round(r["preco_venda"], 2))
        ws_rec.cell(row=i, column=9, value=round(r["lucro_unitario"], 2))
        ws_rec.cell(row=i, column=10, value=round(r["margem_percentual"], 2))
    _autofit_columns(ws_rec)

    # --- 3. Product Batches --------------------------------------------------
    ws_batches = wb.create_sheet("Product Batches" if en else "Lotes de Produtos")
    ws_batches["A1"] = (
        "harErp — Manufactured Batches & Finished Goods Inventory"
        if en
        else "harErp — Lotes Fabricados e Estoque de Produtos Acabados"
    )
    ws_batches["A1"].font = TITLE_FONT
    cols_batches = (
        [
            "Batch ID", "Recipe", "Produced Date", "Expiration Date",
            "Total Produced", "Available Qty", "Total Cost ($)",
            "Unit Cost ($)", "Notes",
        ]
        if en
        else [
            "Lote ID", "Receita", "Data Fabricação", "Data Vencimento",
            "Qtd. Fabricada", "Qtd. Disponível", "Custo Total (R$)",
            "Custo Unit. (R$)", "Observação",
        ]
    )
    _format_header(ws_batches, 3, cols_batches)
    for i, l in enumerate(database.listar_lotes(), start=4):
        ws_batches.cell(row=i, column=1, value=l["id"])
        ws_batches.cell(row=i, column=2, value=l["receita_nome"])
        ws_batches.cell(row=i, column=3, value=l["data_fabricacao"])
        ws_batches.cell(row=i, column=4, value=l["data_vencimento"] or "—")
        ws_batches.cell(row=i, column=5, value=l["quantidade_total"])
        ws_batches.cell(row=i, column=6, value=l["quantidade_disponivel"])
        ws_batches.cell(row=i, column=7, value=round(l["custo_total"], 2))
        ws_batches.cell(row=i, column=8, value=round(l["custo_unitario"], 4))
        ws_batches.cell(row=i, column=9, value=l["observacao"])
    _autofit_columns(ws_batches)

    # --- 4. Stock Movements --------------------------------------------------
    ws_mov = wb.create_sheet("Stock Movements" if en else "Movimentacoes Estoque")
    ws_mov["A1"] = (
        "harErp — Ingredient Stock Movement History"
        if en
        else "harErp — Histórico de Movimentações de Insumos"
    )
    ws_mov["A1"].font = TITLE_FONT
    cols_mov = (
        ["ID", "Date", "Ingredient", "Type", "Quantity", "Notes"]
        if en
        else ["ID", "Data", "Ingrediente", "Tipo", "Quantidade", "Observação"]
    )
    _format_header(ws_mov, 3, cols_mov)
    row_idx = 4
    for m in database.listar_mov_ingredientes():
        ws_mov.cell(row=row_idx, column=1, value=m["id"])
        ws_mov.cell(row=row_idx, column=2, value=m["data"])
        ws_mov.cell(row=row_idx, column=3, value=m["ingrediente_nome"])
        ws_mov.cell(
            row=row_idx,
            column=4,
            value=("Inflow" if m["tipo"] == "entrada" else "Outflow")
            if en
            else ("Entrada" if m["tipo"] == "entrada" else "Saída"),
        )
        ws_mov.cell(row=row_idx, column=5, value=m["quantidade"])
        ws_mov.cell(row=row_idx, column=6, value=m["observacao"])
        row_idx += 1

    row_idx += 2
    ws_mov.cell(
        row=row_idx,
        column=1,
        value="Batch Outflows / Sales History" if en else "Histórico de Saídas / Vendas de Lotes",
    ).font = TITLE_FONT
    row_idx += 2
    cols_sales = (
        ["ID", "Date", "Batch ID", "Product / Recipe", "Quantity", "Unit Price ($)", "Total ($)", "Notes"]
        if en
        else ["ID", "Data", "Lote ID", "Produto / Receita", "Quantidade", "Preço Unit. (R$)", "Valor Total (R$)", "Observação"]
    )
    _format_header(ws_mov, row_idx, cols_sales)
    row_idx += 1
    for s in database.listar_saidas_lote():
        ws_mov.cell(row=row_idx, column=1, value=s["id"])
        ws_mov.cell(row=row_idx, column=2, value=s["data"])
        ws_mov.cell(row=row_idx, column=3, value=s["lote_id"])
        ws_mov.cell(row=row_idx, column=4, value=s["receita_nome"])
        ws_mov.cell(row=row_idx, column=5, value=s["quantidade"])
        ws_mov.cell(row=row_idx, column=6, value=round(s["preco_unitario"], 2))
        ws_mov.cell(row=row_idx, column=7, value=round(s["valor_total"], 2))
        ws_mov.cell(row=row_idx, column=8, value=s["observacao"])
        row_idx += 1
    _autofit_columns(ws_mov)

    # --- 5. Finance ----------------------------------------------------------
    ws_fin = wb.create_sheet("Finance" if en else "Financeiro")
    ws_fin["A1"] = (
        "harErp — Financial Transactions"
        if en
        else "harErp — Movimentações Financeiras"
    )
    ws_fin["A1"].font = TITLE_FONT
    cols_fin = (
        ["ID", "Date", "Type", "Category", "Description", "Amount ($)"]
        if en
        else ["ID", "Data", "Tipo", "Categoria", "Descrição", "Valor (R$)"]
    )
    _format_header(ws_fin, 3, cols_fin)
    row_idx = 4
    for m in database.listar_movimentacoes_financeiras():
        ws_fin.cell(row=row_idx, column=1, value=m["id"])
        ws_fin.cell(row=row_idx, column=2, value=m["data"])
        ws_fin.cell(
            row=row_idx,
            column=3,
            value=("Revenue" if m["tipo"] == "receita" else "Expense")
            if en
            else ("Receita" if m["tipo"] == "receita" else "Despesa"),
        )
        ws_fin.cell(row=row_idx, column=4, value=m["categoria"])
        ws_fin.cell(row=row_idx, column=5, value=m["descricao"])
        ws_fin.cell(row=row_idx, column=6, value=round(m["valor"], 2))
        row_idx += 1
    revenues, expenses, balance = database.saldo_atual()
    row_idx += 1
    ws_fin.cell(row=row_idx, column=5, value="Total Revenues:" if en else "Total Receitas:").font = Font(bold=True)
    ws_fin.cell(row=row_idx, column=6, value=round(revenues, 2))
    row_idx += 1
    ws_fin.cell(row=row_idx, column=5, value="Total Expenses:" if en else "Total Despesas:").font = Font(bold=True)
    ws_fin.cell(row=row_idx, column=6, value=round(expenses, 2))
    row_idx += 1
    ws_fin.cell(row=row_idx, column=5, value="Current Balance:" if en else "Saldo Atual:").font = Font(bold=True)
    ws_fin.cell(row=row_idx, column=6, value=round(balance, 2))
    _autofit_columns(ws_fin)

    wb.save(file_path)
    return file_path


exportar_excel = export_excel


def _default_table_style():
    return TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2F5496")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
    ])


def export_pdf(file_path):
    """Generates an executive .pdf report in the active UI language (EN / PT-BR)."""
    en = I18n.is_en()
    cur = "$" if en else "R$"
    doc = SimpleDocTemplate(
        file_path, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], fontSize=17)
    sec_style = ParagraphStyle("Section", parent=styles["Heading2"], spaceBefore=14)

    elements = []
    elements.append(
        Paragraph(
            "harErp Executive Report — Manufacturing, Inventory & Finance"
            if en
            else "Relatório Executivo harErp — Gestão de Produção, Estoque e Financeiro",
            title_style,
        )
    )
    elements.append(
        Paragraph(
            f"{'Generated on' if en else 'Gerado em'} {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.4 * cm))

    # --- 1. General Indicators -----------------------------------------------
    revenues, expenses, balance = database.saldo_atual()
    inputs_val = database.custo_total_ingredientes_estoque()
    batches_val = database.custo_total_lotes_estoque()
    elements.append(Paragraph("Executive KPIs" if en else "Indicadores Gerais", sec_style))
    kpi_rows = (
        [
            ["Cumulative Revenues", f"{cur} {revenues:.2f}"],
            ["Cumulative Expenses", f"{cur} {expenses:.2f}"],
            ["Cash Balance", f"{cur} {balance:.2f}"],
            ["Capital in Raw Materials", f"{cur} {inputs_val:.2f}"],
            ["Active Finished Goods Cost", f"{cur} {batches_val:.2f}"],
        ]
        if en
        else [
            ["Receitas Acumuladas", f"{cur} {revenues:.2f}"],
            ["Despesas Acumuladas", f"{cur} {expenses:.2f}"],
            ["Saldo em Caixa", f"{cur} {balance:.2f}"],
            ["Valor Investido em Ingredientes", f"{cur} {inputs_val:.2f}"],
            ["Custo em Lotes de Produtos Acabados", f"{cur} {batches_val:.2f}"],
        ]
    )
    kpi_table = Table(kpi_rows, colWidths=[8.5 * cm, 6 * cm])
    kpi_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
    ]))
    elements.append(kpi_table)

    # --- 2. Ingredients ------------------------------------------------------
    elements.append(Paragraph("Ingredient Inventory" if en else "Estoque de Ingredientes (Insumos)", sec_style))
    ing_rows = [
        ["Name", "Category", "Qty", "Min.", f"Cost ({cur})", f"Total ({cur})"]
        if en
        else ["Nome", "Categoria", "Qtd.", "Mín.", f"Custo ({cur})", f"Total ({cur})"]
    ]
    for p in database.listar_ingredientes():
        total = p["preco_custo"] * p["quantidade"]
        ing_rows.append([
            p["nome"], p["categoria"], f'{p["quantidade"]} {p["unidade"]}',
            str(p["estoque_minimo"]), f'{p["preco_custo"]:.2f}', f'{total:.2f}'
        ])
    if len(ing_rows) == 1:
        ing_rows.append(["No ingredients registered." if en else "Nenhum ingrediente cadastrado.", "", "", "", "", ""])
    tab_ing = Table(ing_rows, colWidths=[5 * cm, 3 * cm, 2.2 * cm, 1.8 * cm, 2.2 * cm, 2.5 * cm])
    tab_ing.setStyle(_default_table_style())
    elements.append(tab_ing)

    # --- 3. Recipes & Profitability ------------------------------------------
    elements.append(Paragraph("Recipes & Profitability" if en else "Fichas Técnicas e Rentabilidade", sec_style))
    rec_rows = [
        ["Recipe", "Yield", "Batch Cost", "Unit Cost", "Sell Price", "Margin"]
        if en
        else ["Receita", "Rend.", "Custo Lote", "Custo Un.", "Venda Un.", "Margem"]
    ]
    for r in database.analise_rentabilidade_receitas():
        rec_rows.append([
            r["nome"], f'{r["rendimento"]} un',
            f'{cur} {r["custo_lote"]:.2f}', f'{cur} {r["custo_unitario"]:.2f}',
            f'{cur} {r["preco_venda"]:.2f}', f'{r["margem_percentual"]:.1f}%'
        ])
    if len(rec_rows) == 1:
        rec_rows.append(["No recipes registered." if en else "Nenhuma receita cadastrada.", "", "", "", "", ""])
    tab_rec = Table(rec_rows, colWidths=[5.2 * cm, 2 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm, 2.3 * cm])
    tab_rec.setStyle(_default_table_style())
    elements.append(tab_rec)

    # --- 4. Active Batches ---------------------------------------------------
    elements.append(Paragraph("Active Product Batches" if en else "Lotes de Produtos Disponíveis", sec_style))
    batch_rows = [
        ["Batch", "Recipe", "Produced", "Expiration", "Available", "Unit Cost"]
        if en
        else ["Lote", "Receita", "Fabricação", "Vencimento", "Disponível", "Custo Un."]
    ]
    for l in database.listar_lotes(apenas_ativos=True):
        batch_rows.append([
            f'#{l["id"]}', l["receita_nome"], l["data_fabricacao"],
            l["data_vencimento"] or "—", f'{l["quantidade_disponivel"]}/{l["quantidade_total"]}',
            f'{cur} {l["custo_unitario"]:.2f}'
        ])
    if len(batch_rows) == 1:
        batch_rows.append(["No active batches in stock." if en else "Nenhum lote ativo em estoque.", "", "", "", "", ""])
    tab_batches = Table(batch_rows, colWidths=[1.6 * cm, 5.4 * cm, 2.5 * cm, 2.5 * cm, 2.3 * cm, 2.4 * cm])
    tab_batches.setStyle(_default_table_style())
    elements.append(tab_batches)

    # --- 5. Recent Financial Transactions ------------------------------------
    elements.append(
        Paragraph(
            "Recent Financial Transactions (Last 20)"
            if en
            else "Movimentações Financeiras Recentes (Últimas 20)",
            sec_style,
        )
    )
    fin_rows = [
        ["Date", "Type", "Category", "Description", f"Amount ({cur})"]
        if en
        else ["Data", "Tipo", "Categoria", "Descrição", f"Valor ({cur})"]
    ]
    for m in database.listar_movimentacoes_financeiras()[:20]:
        fin_rows.append([
            m["data"],
            ("Revenue" if m["tipo"] == "receita" else "Expense")
            if en
            else ("Receita" if m["tipo"] == "receita" else "Despesa"),
            m["categoria"], m["descricao"], f'{m["valor"]:.2f}'
        ])
    if len(fin_rows) == 1:
        fin_rows.append(["No transactions recorded." if en else "Nenhuma movimentação registrada.", "", "", "", ""])
    tab_fin = Table(fin_rows, colWidths=[2.5 * cm, 2.2 * cm, 3.2 * cm, 6.3 * cm, 2.5 * cm])
    tab_fin.setStyle(_default_table_style())
    elements.append(tab_fin)

    doc.build(elements)
    return file_path


exportar_pdf = export_pdf
