"""
tests/test_erp.py — Automated Unit & Integration Test Suite for harErp
======================================================================
Run with:
    python -m unittest discover -s tests -v
"""

import os
import tempfile
import unittest

import database
import reports
from ui.i18n import I18n, t
from ui.utils import convert_quantity, compatible_units


class TestHarErp(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_original = database.DB_PATH
        database.DB_PATH = os.path.join(self.temp_dir.name, "test_estoque.db")
        database.criar_tabelas()
        I18n.set_lang("en")

    def tearDown(self):
        database.DB_PATH = self.db_original
        self.temp_dir.cleanup()

    def test_unit_conversion(self):
        self.assertAlmostEqual(convert_quantity(250, "g", "kg"), 0.25)
        self.assertAlmostEqual(convert_quantity(1.5, "kg", "g"), 1500.0)
        self.assertAlmostEqual(convert_quantity(500, "ml", "L"), 0.5)
        self.assertAlmostEqual(convert_quantity(2, "dz", "un"), 24.0)
        self.assertEqual(compatible_units("kg")[0], "kg")
        self.assertIn("g", compatible_units("kg"))

    def test_i18n_language_toggle(self):
        I18n.set_lang("en")
        self.assertTrue(I18n.is_en())
        self.assertIn("harErp", t("app_title"))
        self.assertIn("Ingredients", t("tab_ingredients"))

        I18n.toggle()
        self.assertEqual(I18n.get_lang(), "pt-br")
        self.assertFalse(I18n.is_en())
        self.assertIn("Ingredientes", t("tab_ingredients"))

        I18n.toggle()
        self.assertEqual(I18n.get_lang(), "en")

    def test_weighted_average_cost_and_finance(self):
        iid = database.adicionar_ingrediente("Flour", "Brand A", "Dry", 10.0, 2.0, "kg", 5.00)
        # Inflow of 10 kg at $7.00 -> weighted average cost must become $6.00 and record $70.00 expense
        database.registrar_mov_ingrediente(
            iid, "entrada", 10.0, "Restock", novo_custo=7.00, lancar_financeiro=True
        )
        ing = database.obter_ingrediente(iid)
        self.assertAlmostEqual(ing["quantidade"], 20.0)
        self.assertAlmostEqual(ing["preco_custo"], 6.00)

        _, desp, _ = database.saldo_atual()
        self.assertAlmostEqual(desp, 70.00)

    def test_production_simulator_and_shopping_list(self):
        i1 = database.adicionar_ingrediente("Chocolate", "Callebaut", "Sweets", 1.0, 0.5, "kg", 50.0)
        i2 = database.adicionar_ingrediente("Sugar", "Uniao", "Dry", 5.0, 1.0, "kg", 4.0)
        rid = database.salvar_receita(
            "Truffle", 20, "Notes", [{"ingrediente_id": i1, "quantidade": 0.4}, {"ingrediente_id": i2, "quantidade": 0.2}],
            validade_dias=5, preco_venda=5.0
        )

        sim_ok = database.simular_producao_e_compras(rid, 2)
        self.assertTrue(sim_ok["viavel"])
        self.assertEqual(sim_ok["max_lotes_possiveis"], 2)
        self.assertAlmostEqual(sim_ok["custo_reposicao_total"], 0.0)

        sim_shortage = database.simular_producao_e_compras(rid, 4)
        self.assertFalse(sim_shortage["viavel"])
        self.assertAlmostEqual(sim_shortage["custo_reposicao_total"], 30.00)

    def test_batch_manufacturing_and_fefo_sale(self):
        iid = database.adicionar_ingrediente("Milk", "Farm", "Dairy", 20.0, 2.0, "L", 4.00)
        rid = database.salvar_receita(
            "Dulce de Leche", 10, "", [{"ingrediente_id": iid, "quantidade": 2.0}],
            validade_dias=10, preco_venda=15.00
        )

        # Produce 2 batches with different expiration dates
        l1, _, _ = database.fabricar_lote(rid, 1, data_vencimento="2099-05-10")
        l2, _, _ = database.fabricar_lote(rid, 1, data_vencimento="2099-05-01")  # expires earlier!

        # FEFO sale of 14 units: must deplete all 10 from l2 first, then 4 from l1
        depletions = database.registrar_saida_fefo(rid, 14, "FEFO Order", lancar_financeiro=True)
        self.assertEqual(depletions, [(l2, 10), (l1, 4)])

        batches = {l["id"]: l["quantidade_disponivel"] for l in database.listar_lotes()}
        self.assertEqual(batches[l2], 0)
        self.assertEqual(batches[l1], 6)

        rec, _, _ = database.saldo_atual()
        self.assertAlmostEqual(rec, 14 * 15.00)

    def test_reports_csv_and_backup_restore(self):
        database.popular_dados_exemplo()
        xlsx = os.path.join(self.temp_dir.name, "harerp_report.xlsx")
        pdf = os.path.join(self.temp_dir.name, "harerp_report.pdf")
        bkp = os.path.join(self.temp_dir.name, "harerp_backup.db")
        csv_dir = os.path.join(self.temp_dir.name, "csvs")

        reports.export_excel(xlsx)
        reports.export_pdf(pdf)
        database.fazer_backup(bkp)
        csv_files = database.exportar_csv_tabelas(csv_dir)

        self.assertTrue(os.path.exists(xlsx))
        self.assertTrue(os.path.exists(pdf))
        self.assertTrue(os.path.exists(bkp))
        self.assertEqual(len(csv_files), 4)

        database.restaurar_backup(bkp)
        self.assertGreater(len(database.listar_ingredientes()), 0)

    def test_category_creation_and_renaming(self):
        cid = database.adicionar_categoria("Gourmet Line", "produto", "Premium recipes")
        self.assertIsNotNone(cid)
        self.assertIn("Gourmet Line", database.listar_nomes_categorias("produto"))

        iid = database.adicionar_ingrediente("Cocoa", "Brand", "Chocolates", 5.0, 1.0, "kg", 20.0)
        rid = database.salvar_receita(
            "Gourmet Cake", 8, "", [{"ingrediente_id": iid, "quantidade": 0.5}],
            categoria="Gourmet Line", preco_venda=25.0
        )

        # Rename category and verify product/recipe is updated automatically
        database.renomear_categoria(cid, "Signature Line")
        self.assertIn("Signature Line", database.listar_nomes_categorias("produto"))
        rec, _ = database.obter_receita(rid)
        self.assertEqual(rec["categoria"], "Signature Line")

    def test_operational_products_and_movements(self):
        pid = database.adicionar_produto_operacional(
            "Sanitizer 5L", "CleanCo", "Limpeza e Higiene", 2.0, 1.0, "un", 20.00,
            observacao="Kitchen cleaning", lancar_financeiro=True
        )
        # Inflow of 2 units at $30.00 -> weighted average cost becomes $25.00
        database.registrar_mov_operacional(
            pid, "entrada", 2.0, "Monthly restock", novo_custo=30.00, lancar_financeiro=True
        )
        # Outflow (consumption) of 3 units -> remaining 1 unit (<= min stock 1.0 -> alert)
        database.registrar_mov_operacional(pid, "saida", 3.0, "Weekly use")

        op = database.obter_produto_operacional(pid)
        self.assertAlmostEqual(op["quantidade"], 1.0)
        self.assertAlmostEqual(op["preco_custo"], 25.00)
        self.assertEqual(len(database.operacionais_abaixo_minimo()), 1)

        _, desp, _ = database.saldo_atual()
        # 2 * $20 (initial) + 2 * $30 (restock) = $100
        self.assertAlmostEqual(desp, 100.00)

    def test_persistence_across_close_and_reopen(self):
        iid = database.adicionar_ingrediente("Butter", "Farm", "Dairy", 4.0, 1.0, "kg", 30.0)
        database.atualizar_ingrediente(iid, "Butter", "Farm", "Dairy", 1.0, "kg", 30.0, quantidade=6.5)
        pid = database.adicionar_produto_operacional("Gloves Box", "Safe", "EPI", 5.0, 2.0, "cx", 18.0)
        database.sincronizar_banco()

        # Re-query from disk as a fresh session would after closing and reopening
        database.criar_tabelas()
        ing = database.obter_ingrediente(iid)
        op = database.obter_produto_operacional(pid)
        self.assertIsNotNone(ing)
        self.assertAlmostEqual(ing["quantidade"], 6.5)
        self.assertIsNotNone(op)
        self.assertAlmostEqual(op["quantidade"], 5.0)


if __name__ == "__main__":
    unittest.main()
