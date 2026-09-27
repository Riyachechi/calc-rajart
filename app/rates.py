"""
Rate lookup logic - ported directly from the original Streamlit
calculator.py so pricing behaviour stays identical.
"""

from pathlib import Path
import pandas as pd

DATA_FILE = Path(__file__).parent / "data" / "Sorted_Sheet_Rates_For_Dashboard.xlsx"

LAMINATION_OPTIONS = ["None", "Gloss", "Matte", "Velvet"]

# All rates in the sheet are for a full A3 sheet (12x18"). A4 is exactly
# half of an A3 sheet, and A5 is exactly a quarter of an A3 sheet (four
# A5 pieces come out of one A3), so their per-piece printing price is the
# A3 rate scaled down by that fraction.
SHEET_SIZE_OPTIONS = ["A3", "A4", "A5"]
SHEET_SIZE_MULTIPLIERS = {
    "A3": 1.0,
    "A4": 0.5,
    "A5": 0.25,
}


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
            "sheet_size_options": SHEET_SIZE_OPTIONS,
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
    # Printing rate lookup (quantity-bracket fallback)
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

            # The rows in the sheet are quantity brackets (100 / 500 / 1000
            # / 5000 pieces), each with its own per-piece rate that gets
            # cheaper as the bracket goes up. You only unlock a bracket's
            # rate once you actually reach that many pieces, so an order
            # that doesn't match a bracket exactly (e.g. 105, 250, 499
            # pieces) is priced at the highest bracket it has REACHED, not
            # the next one up.
            # e.g. 105 pieces -> still priced at the 100-piece bracket's
            # rate (hasn't reached 500 yet). 750 pieces -> priced at the
            # 500-piece bracket's rate (hasn't reached 1000 yet).
            reached_brackets = [q for q in available if q <= quantity]
            bracket = max(reached_brackets) if reached_brackets else min(available)

            selected = gsm_rates[
                (gsm_rates["Quantity"] == bracket)
                & (gsm_rates["Printing Side"] == printing_side)
            ]
            return selected, bracket, True

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
        sheet_size: str = "A3",
        use_nearest_quantity: bool = True,
    ) -> dict:
        if sheet_size not in SHEET_SIZE_MULTIPLIERS:
            raise ValueError(
                f"Unknown sheet size '{sheet_size}'. Choose one of "
                f"{', '.join(SHEET_SIZE_OPTIONS)}."
            )

        selected_rate, rate_quantity_used, used_nearest = self.find_printing_rate(
            gsm, quantity, printing_side, use_nearest_quantity
        )

        if selected_rate.empty:
            raise ValueError(
                "No matching rate found for the given GSM, quantity and "
                "printing type."
            )

        # Base rates in the sheet are always for a full A3 sheet — printing
        # AND lamination both scale down with a smaller sheet, since a
        # smaller piece needs proportionally less ink/laminate film.
        size_multiplier = SHEET_SIZE_MULTIPLIERS[sheet_size]
        printing_min = float(selected_rate.iloc[0]["Min Selling Price (₹)"]) * size_multiplier
        printing_max = float(selected_rate.iloc[0]["Max Selling Price (₹)"]) * size_multiplier

        lamination_price = self.get_lamination_price(lamination, printing_side) * size_multiplier

        final_min_per_piece = printing_min + lamination_price
        final_max_per_piece = printing_max + lamination_price

        total_min = final_min_per_piece * quantity
        total_max = final_max_per_piece * quantity

        return {
            "gsm": gsm,
            "quantity": quantity,
            "printing_side": printing_side,
            "lamination": lamination,
            "sheet_size": sheet_size,
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
