"""
Budget tracking module for Nimeslug.
Stores transactions in SQLite, provides analytics, and supports natural-language input.
"""

from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import extract


# ─── Configuration ───────────────────────────────────────────
DB_PATH = Path("data") / "budget.db"
DB_PATH.parent.mkdir(exist_ok=True)

# Standard categories — both TR and EN aliases supported in code
CATEGORIES = [
    "Market",         # groceries
    "Yemek",          # food / restaurants
    "Ulaşım",         # transport
    "Eğlence",        # entertainment
    "Sağlık",         # health
    "Faturalar",      # bills
    "Kira",           # rent
    "Alışveriş",      # shopping
    "Eğitim",         # education
    "Maaş",           # salary (income)
    "Gelir",          # other income
    "Tasarruf",       # savings
    "Diğer",          # other
]


# ─── Database Setup ──────────────────────────────────────────
Base = declarative_base()


class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(String(200), default="")
    currency = Column(String(10), default="TRY")
    transaction_type = Column(String(10), default="expense")  # 'expense' or 'income'
    date = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)


class Goal(Base):
    __tablename__ = "goals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    currency = Column(String(10), default="TRY")
    deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


# Initialize engine
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)


# ─── Transaction Functions ───────────────────────────────────

def add_transaction(
    amount: float,
    category: str,
    description: str = "",
    currency: str = "TRY",
    transaction_type: str = "expense",
) -> dict:
    """
    Record a new transaction (expense or income).
    
    Args:
        amount: Amount (positive number)
        category: Category name (e.g., 'Market', 'Yemek')
        description: Optional details
        currency: Currency code
        transaction_type: 'expense' or 'income'
    
    Returns:
        dict with transaction info or error
    """
    try:
        if amount <= 0:
            return {"error": "Amount must be positive"}
        
        # Normalize category — use closest match from CATEGORIES if possible
        category_normalized = _normalize_category(category)
        
        with SessionLocal() as session:
            txn = Transaction(
                amount=float(amount),
                category=category_normalized,
                description=description.strip(),
                currency=currency.upper(),
                transaction_type=transaction_type.lower(),
            )
            session.add(txn)
            session.commit()
            
            return {
                "id": txn.id,
                "amount": txn.amount,
                "category": txn.category,
                "description": txn.description,
                "currency": txn.currency,
                "type": txn.transaction_type,
                "date": txn.date.strftime("%Y-%m-%d %H:%M"),
                "status": "Transaction recorded successfully",
            }
    except Exception as e:
        return {"error": f"Failed to add transaction: {str(e)}"}


def _normalize_category(category: str) -> str:
    """Match user-provided category to standard list (case-insensitive)."""
    category_lower = category.strip().lower()
    
    # Direct match
    for cat in CATEGORIES:
        if cat.lower() == category_lower:
            return cat
    
    # Common aliases (TR + EN)
    aliases = {
        "yiyecek": "Yemek", "food": "Yemek", "restaurant": "Yemek",
        "grocery": "Market", "groceries": "Market", "süpermarket": "Market",
        "transport": "Ulaşım", "taksi": "Ulaşım", "otobüs": "Ulaşım",
        "entertainment": "Eğlence", "sinema": "Eğlence", "konser": "Eğlence",
        "health": "Sağlık", "doktor": "Sağlık", "ilaç": "Sağlık",
        "bills": "Faturalar", "elektrik": "Faturalar", "su": "Faturalar",
        "rent": "Kira",
        "shopping": "Alışveriş", "giyim": "Alışveriş",
        "education": "Eğitim", "kitap": "Eğitim",
        "salary": "Maaş",
        "income": "Gelir",
        "savings": "Tasarruf", "birikim": "Tasarruf",
        "other": "Diğer",
    }
    
    if category_lower in aliases:
        return aliases[category_lower]
    
    return category.strip().title()  # Fall back to user input


# ─── Querying ────────────────────────────────────────────────

def get_summary(period: str = "month") -> dict:
    """
    Get a summary of transactions for a period.
    
    Args:
        period: 'today', 'week', 'month', 'year', 'all'
    
    Returns:
        dict with totals, category breakdown, and recent transactions
    """
    try:
        now = datetime.now()
        if period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start = now - timedelta(days=7)
        elif period == "month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "year":
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "all":
            start = datetime(1970, 1, 1)
        else:
            return {"error": f"Unknown period: {period}"}
        
        with SessionLocal() as session:
            transactions = (
                session.query(Transaction)
                .filter(Transaction.date >= start)
                .order_by(Transaction.date.desc())
                .all()
            )
            
            if not transactions:
                return {
                    "period": period,
                    "total_expense": 0,
                    "total_income": 0,
                    "net": 0,
                    "transaction_count": 0,
                    "by_category": {},
                    "recent": [],
                    "message": "No transactions found for this period.",
                }
            
            total_expense = sum(t.amount for t in transactions if t.transaction_type == "expense")
            total_income = sum(t.amount for t in transactions if t.transaction_type == "income")
            
            # Group expenses by category
            by_category = {}
            for t in transactions:
                if t.transaction_type == "expense":
                    by_category[t.category] = by_category.get(t.category, 0) + t.amount
            
            # Sort categories by amount (highest first)
            by_category = dict(sorted(by_category.items(), key=lambda x: -x[1]))
            
            recent = [
                {
                    "id": t.id,
                    "date": t.date.strftime("%Y-%m-%d"),
                    "amount": t.amount,
                    "category": t.category,
                    "type": t.transaction_type,
                    "description": t.description or "",
                    "currency": t.currency,
                }
                for t in transactions[:10]
            ]
            
            return {
                "period": period,
                "total_expense": round(total_expense, 2),
                "total_income": round(total_income, 2),
                "net": round(total_income - total_expense, 2),
                "transaction_count": len(transactions),
                "by_category": {k: round(v, 2) for k, v in by_category.items()},
                "recent": recent,
            }
    except Exception as e:
        return {"error": f"Failed to get summary: {str(e)}"}


def delete_transaction(transaction_id: int) -> dict:
    """Delete a transaction by ID."""
    try:
        with SessionLocal() as session:
            txn = session.query(Transaction).filter(Transaction.id == transaction_id).first()
            if not txn:
                return {"error": f"Transaction {transaction_id} not found"}
            session.delete(txn)
            session.commit()
            return {"status": f"Transaction {transaction_id} deleted"}
    except Exception as e:
        return {"error": str(e)}


def get_all_transactions(limit: int = 100) -> list:
    """Get all transactions (for table display)."""
    try:
        with SessionLocal() as session:
            transactions = (
                session.query(Transaction)
                .order_by(Transaction.date.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": t.id,
                    "date": t.date.strftime("%Y-%m-%d"),
                    "amount": t.amount,
                    "category": t.category,
                    "type": t.transaction_type,
                    "description": t.description or "",
                    "currency": t.currency,
                }
                for t in transactions
            ]
    except Exception:
        return []


def clear_all_transactions() -> dict:
    """Delete every transaction (full reset)."""
    try:
        with SessionLocal() as session:
            count = session.query(Transaction).delete()
            session.commit()
            return {"status": f"Deleted {count} transactions"}
    except Exception as e:
        return {"error": str(e)}


# ─── Quick Test ──────────────────────────────────────────────
if __name__ == "__main__":
    print("Budget module loaded.")
    print(f"DB path: {DB_PATH.absolute()}")
    print(f"Summary (month): {get_summary('month')}")