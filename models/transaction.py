from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class Transaction:
    date: str
    amount: float
    reimbursed_amount: float
    description: Optional[str]
    category: Optional[str]
    payment_method: Optional[str]
    row_index: Optional[int] = None # To track where it is in the sheet

    @classmethod
    def from_row(cls, row: List[str], row_index: int = None) -> 'Transaction':
        """Creates a Transaction object from a spreadsheet row."""
        # Ensure row has enough columns, pad with empty strings if not
        if len(row) < 6:
            row = row + [""] * (6 - len(row))

        try:
            amount = float(str(row[1]).replace(',', '.')) if row[1] else 0.0
        except ValueError:
            amount = 0.0

        try:
            # Reimbursed amount can be empty or '0.00' or similar
            reimbursed_amount = float(str(row[2]).replace(',', '.')) if row[2] else 0.0
        except ValueError:
            reimbursed_amount = 0.0

        return cls(
            date=row[0],
            amount=amount,
            reimbursed_amount=reimbursed_amount,
            description=row[3] if row[3] else None,
            category=row[4] if row[4] else None,
            payment_method=row[5] if row[5] else None,
            row_index=row_index
        )

    def to_row(self) -> List[str]:
        """Converts the Transaction object back to a list for the spreadsheet."""
        return [
            self.date,
            str(self.amount).replace('.', ','),
            str(self.reimbursed_amount).replace('.', ','),
            self.description or "",
            self.category or "",
            self.payment_method or ""
        ]
    
    @property
    def is_expense(self) -> bool:
        """Returns True if it's an expense (amount is negative), False otherwise."""
        return self.amount < 0
    
    @property
    def is_income(self) -> bool:
        """Returns True if it's an income (amount is positive), False otherwise."""
        return self.amount > 0

    @property
    def net_value(self) -> float:
        """Returns the net value (amount + reimbursed). For expenses, this reduces the cost."""
        # If expense: -100 + 50 (reimbursed) = -50 (net cost)
        # If income: 100 + 0 = 100
        # Reimbursements are always positive values in this logic?
        # In the sheet, reimbursed column is positive.
        
        # Let's verify logic in code:
        # In GoogleSheetsService.add_expense: `reembolsado` is written as is.
        # Logic says: "valor_compra = self.get_expense_value(row)"
        # "if valor_reembolsado_atual >= abs(valor_compra):"
        
        return self.amount + self.reimbursed_amount
