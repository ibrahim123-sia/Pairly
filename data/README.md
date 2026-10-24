# Data

Pairly's demo and tests use the **Online Retail II** dataset.

| Folder | In git? | What it holds |
|---|---|---|
| `sample/` | yes | `online_retail_ii_sample.csv`: about 57,000 rows (2,668 whole invoices, under 5 MB) |
| `raw/` | no (ignored) | The full dataset, if you download it |

## Source and licence

- **Dataset:** Online Retail II
- **Creator:** Daqing Chen
- **Publisher:** UCI Machine Learning Repository, <https://archive.ics.uci.edu/dataset/502/online+retail+ii>
- **DOI:** <https://doi.org/10.24432/C5CG6D>
- **Licence:** [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)

Citation:

> Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D

The data covers real transactions from a UK online gift shop, December 2009 to December 2011.

**Changes we made.** The sample was cleaned first. Cancelled invoices and rows with no price, quantity or customer ID were removed, and the two yearly sheets were joined. Then 8% of invoices were picked at random (seed 42), keeping every line of each chosen invoice, and columns the app computes itself were dropped. `backend/scripts/make_sample.py` rebuilds it.

## The sample

Columns: `Invoice, StockCode, Description, Quantity, InvoiceDate, Price, CustomerID, Country`.
Pairly maps these to its own names when it loads the file (for example `Price` becomes `UnitPrice`).

Because whole invoices are sampled across the full two years, the basket patterns, seasonality and customer segments still look like the full data. The counts are about 8% of the full totals.

## Using the full dataset

1. Download `online_retail_II.xlsx` from the UCI page above.
2. Convert both sheets into one CSV in `data/raw/`:

   ```bash
   python -c "import pandas as pd; pd.concat(pd.read_excel('online_retail_II.xlsx', sheet_name=None).values()).to_csv('data/raw/online_retail_II.csv', index=False)"
   ```

3. Run `notebooks/Phase-1.ipynb` to write the cleaned file, `data/raw/Online_Retail_II_Cleaned.csv`.
4. Use it:
   - Demo seed: `python scripts/seed_demo.py --file ../data/raw/Online_Retail_II_Cleaned.csv`
   - Rebuild the sample: `python scripts/make_sample.py`
   - Or upload the CSV on the **My Datasets** page.

The full file has about 1 million rows. Analytics need more memory (plan on 2 GB or more) and the first load of each page is slower.
