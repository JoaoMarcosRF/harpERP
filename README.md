# harErp — Open-Source Manufacturing, Batch Inventory & Financial ERP

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Local_Persistence-003B57?logo=sqlite&logoColor=white)
![Tkinter](https://img.shields.io/badge/UI-Tkinter_%7C_Dark_%26_Light_Mode-38bdf8)
![i18n](https://img.shields.io/badge/Language-EN_%7C_PT--BR-10b981)
![License](https://img.shields.io/badge/License-MIT-22c55e)

**harErp** is a lightweight, zero-server open-source desktop ERP built in Python for small and medium manufacturers, artisanal bakeries, food producers, kitchens, and workshops. It connects **Raw Materials (Ingredients)**, **Recipes / Bill of Materials (BOM)**, **Finished Product Batches (with Shelf-Life & FEFO)**, **Financial Cash Flow**, and an **Executive BI Analytics Dashboard** in a fast local SQLite database.

---

## ✨ Key Features

- 🌐 **Bilingual Interface (`EN` / `PT-BR`)**: Instant one-click live language switching between **English (`EN`)** and **Brazilian Portuguese (`PT-BR`)** in the top header (`🌐 PT-BR` / `🌐 EN`) or via `Ctrl+L` — no restart required.
- 🌙 **Dark Mode & Light Mode**: Modern, high-contrast theme engine (`Ctrl+D`) that updates all forms, tables, KPI cards, and Matplotlib charts in real time.
- ⚖ **Smart Unit Selector & Automatic Unit Conversion**:
  - Dropdown combobox (`un`, `kg`, `g`, `mg`, `L`, `ml`, `cx`, `pct`, `fd`, `dz`, `m`, `cm`) when registering ingredients, recording stock movements, and building recipes.
  - Automatic proportional conversion between compatible units (`kg` ↔ `g` ↔ `mg`, `L` ↔ `ml`, `m` ↔ `cm`, `dz` ↔ `un`) — e.g., buy flour in `kg` and add `250 g` to a recipe seamlessly.
- 📦 **Raw Material Inventory & Weighted Average Cost**:
  - Tracks current stock, minimum stock alerts, purchase cost, and total tied-up capital.
  - Automatically recalculates **Weighted Average Cost** on stock inflows and optionally records a **Financial Expense**.
- 📋 **Recipes (BOM) & Profit Margin Engineering**:
  - Define batch yield, default shelf life (in days), unit selling price, and ingredient composition.
  - Real-time calculation of **Batch Cost**, **Unit Cost**, **Unit Profit**, and **Gross Margin (%)**.
- 🏭 **Batch Manufacturing, Simulator & FEFO Depletion**:
  - **Production Simulator & Automatic Shopping List**: Check how many batches can be produced with current stock, identify bottlenecks, and generate a shopping list with estimated replenishment cost.
  - **FEFO (*First-Expired, First-Out*) Outflow Mode**: Automatically depletes non-expired batches closest to their expiration date first, or select a specific batch manually.
  - Optional automatic recording of batch sales as **Financial Revenue**.
- 📊 **Executive BI Analytics Dashboard**:
  - Period filter (*All Time, Current Month, Last 30 Days, Last 90 Days, Current Year*).
  - **8 KPI Cards** + operational alert banners + **8 Interactive Matplotlib Charts** across Financial & Inventory/Production views.
- 📄 **Reports, CSV Export & Safe SQLite Backup/Restore**:
  - Export multi-sheet **Excel (`.xlsx`)**, executive **PDF (`.pdf`)**, and **CSV (`.csv`)** tables (adapting automatically to `EN` or `PT-BR`).
  - One-click **SQLite `.db` Backup**, **Integrity-Checked Restore**, and **Demo Data Seeder**.

---

## 🗂 Project Structure

```text
harErp/
├── main.py                  # Application entry point, header, shortcuts & tab orchestration
├── database.py              # SQLite persistence layer, migrations, FEFO, simulator & BI queries
├── reports.py               # Bilingual Excel (.xlsx) and PDF (.pdf) report generators
├── build_exe.py             # PyInstaller standalone executable builder (harErp.exe)
├── requirements.txt         # Python dependencies (matplotlib, openpyxl, reportlab)
├── ui/
│   ├── i18n.py              # Live bilingual translation engine (EN / PT-BR)
│   ├── theme.py             # Dark / Light mode palettes and TTK styling engine
│   ├── utils.py             # Standard units, automatic unit converter & Treeview sorting
│   ├── ingredients_frame.py # Ingredients registration, stock movements & history tab
│   ├── recipes_frame.py     # Recipes (BOM) & profit margin calculator tab
│   ├── products_frame.py    # Batch manufacturing, simulator/shopping list & FEFO sales tab
│   ├── finance_frame.py     # Cash flow transactions & multi-filter tab
│   ├── analytics_frame.py   # Executive BI Dashboard (8 KPIs + 8 Matplotlib charts)
│   └── reports_frame.py     # Excel/PDF/CSV exports, DB backup/restore & demo data tab
└── tests/
    └── test_erp.py          # Automated unit & integration test suite
```

---

## 🚀 Quick Start

### 1. Clone & Create a Virtual Environment

```bash
git clone <repository-url>
cd palhermaErp
python -m venv .venv
```

Activate the virtual environment:

- **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- **Linux / macOS:**
  ```bash
  source .venv/bin/activate
  ```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run harErp

```bash
python main.py
```

---

## ⌨ Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `F5` | Refresh all tables, KPIs, and charts |
| `Ctrl + D` | Toggle between **Dark Mode** and **Light Mode** |
| `Ctrl + L` | Toggle UI language between **English (`EN`)** and **Portuguese (`PT-BR`)** |
| `Ctrl + B` | Open quick SQLite database backup dialog |
| `Ctrl + 1..6` | Switch directly between tabs 1 to 6 |

---

## 🧪 Running Automated Tests

```bash
python -m unittest discover -s tests -v
```

---

## 📦 Building a Standalone Executable (`.exe`)

To package **harErp** into a single standalone executable using PyInstaller:

```bash
pip install pyinstaller
python build_exe.py
```

The resulting executable will be generated in `dist/harErp`.
