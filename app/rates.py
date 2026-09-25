"""
Rate lookup logic - ported directly from the original Streamlit
calculator.py so pricing behaviour stays identical.
"""

from pathlib import Path
import pandas as pd

DATA_FILE = Path(__file__).parent / "data" / "Sorted_Sheet_Rates_For_Dashboard.xlsx"

LAMINATION_OPTIONS = ["None", "Gloss", "Matte", "Velvet"]


class RateBook:
    """Loads the rate workbook once and answers pricing questions."""

    def __init__(self, file_path: Path = DATA_FILE):
        self.rates_df = pd.read_excel(file_path, sheet_name="Sheet_Rates_Sorted")
        self.lamination_df = pd.read_excel(file_path, sheet_name="Lamination_Rates")
        self._normalize()

    def _normalize(self):
        self.rates_df["GSM"] = self.rates_df["GSM"].astype(int)
        self.rates_df["Quantity"] = self.rates_df["Quantity"].astype(int)
        self.rates_df["Printing Side"] = (
            self.rates_df["Printing Side"].astype(str).str.strip()
        )

        self.lamination_df["Lamination"] = (
            self.lamination_df["Lamination"].astype(str).str.strip()
        )
        self.lamination_df["Printing Side"] = (
            self.lamination_df["Printing Side"].astype(str).str.strip()
        )

    # ---------------------------------------------------------------
    # Metadata for building the frontend's dropdowns
    # ---------------------------------------------------------------
    def options(self):
        return {
            "gsm_options": sorted(self.rates_df["GSM"].unique().tolist()),
            "printing_sides": sorted(self.rates_df["Printing Side"].unique().tolist()),
            "lamination_options": LAMINATION_OPTIONS,
            "quantity_brackets": sorted(self.rates_df["Quantity"].unique().tolist()),
        }

    # ---------------------------------------------------------------
    # Lamination price lookup
    # ---------------------------------------------------------------
    def get_lamination_price(self, lamination: str, printing_side: str) -> float:
        df = self.lamination_df
        result = df[
            (df["Lamination"].str.lower() == lamination.lower())
            & (df["Printing Side"] == printing_side)
        ]
        if result.empty:
            return 0.0
        return float(result.iloc[0]["Lamination Price (₹)"])

    # ---------------------------------------------------------------
    # Printing rate lookup (with nearest-quantity fallback)
    # ---------------------------------------------------------------
    def find_printing_rate(
        self,
        gsm: int,
        quantity: int,
        printing_side: str,
        use_nearest_quantity: bool = True,
    ):
        gsm_rates = self.rates_df[self.rates_df["GSM"] == gsm].copy()

        exact = gsm_rates[
            (gsm_rates["Quantity"] == quantity)
            & (gsm_rates["Printing Side"] == printing_side)
        ]
        if not exact.empty:
            return exact, quantity, False

        if use_nearest_quantity:
            available = sorted(gsm_rates["Quantity"].unique().tolist())
            if not available:
                return pd.DataFrame(), quantity, False

            nearest = min(available, key=lambda q: abs(q - quantity))
            selected = gsm_rates[
                (gsm_rates["Quantity"] == nearest)
                & (gsm_rates["Printing Side"] == printing_side)
            ]
            return selected, nearest, True

        return pd.DataFrame(), quantity, False

    # ---------------------------------------------------------------
    # Full quotation calculation
    # ---------------------------------------------------------------
    def calculate(
        self,
        gsm: int,
        quantity: int,
        printing_side: str,
        lamination: str,
        use_nearest_quantity: bool = True,
    ) -> dict:
        selected_rate, rate_quantity_used, used_nearest = self.find_printing_rate(
            gsm, quantity, printing_side, use_nearest_quantity
        )

        if selected_rate.empty:
            raise ValueError(
                "No matching rate found for the given GSM, quantity and "
                "printing type."
            )

        printing_min = float(selected_rate.iloc[0]["Min Selling Price (₹)"])
        printing_max = float(selected_rate.iloc[0]["Max Selling Price (₹)"])

        lamination_price = self.get_lamination_price(lamination, printing_side)

        final_min_per_piece = printing_min + lamination_price
        final_max_per_piece = printing_max + lamination_price

        total_min = final_min_per_piece * quantity
        total_max = final_max_per_piece * quantity

        return {
            "gsm": gsm,
            "quantity": quantity,
            "printing_side": printing_side,
            "lamination": lamination,
            "rate_quantity_used": int(rate_quantity_used),
            "used_nearest_quantity": bool(used_nearest),
            "printing_min": printing_min,
            "printing_max": printing_max,
            "lamination_price": lamination_price,
            "final_min_per_piece": final_min_per_piece,
            "final_max_per_piece": final_max_per_piece,
            "total_min": total_min,
            "total_max": total_max,
        }


# Single shared instance, loaded once at process startup
rate_book = RateBook()
