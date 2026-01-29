"""
Accounting Service Layer
Handles all accounting business logic and journal entry creation
"""

from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_, func
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from ..models.accounting_models import (
    Account, JournalEntry, JournalEntryLine, SupplierLedger,
    CustomerLedger, PaymentVoucher, ReceiptVoucher,
    TransactionType, ReferenceType, AccountType,
    PaymentMethod, PayeeType
)
from ..models import Invoice, GRN, Supplier, Patient
from ..schemas.accounting_schemas import (
    JournalEntryCreate, JournalEntryLineCreate
)

class AccountingService:
    """Service class for accounting operations"""
    
    @staticmethod
    def generate_entry_number(db: Session, transaction_type: TransactionType) -> str:
        """Generate unique journal entry number"""
        prefix_map = {
            TransactionType.SALE: "JE-SALE",
            TransactionType.PURCHASE: "JE-PUR",
            TransactionType.PAYMENT: "JE-PAY",
            TransactionType.RECEIPT: "JE-REC",
            TransactionType.ADJUSTMENT: "JE-ADJ",
            TransactionType.OPENING: "JE-OPEN",
        }
        
        prefix = prefix_map.get(transaction_type, "JE")
        year = datetime.now().year
        
        # Get last entry number for this type and year
        last_entry = db.query(JournalEntry).filter(
            JournalEntry.entry_number.like(f"{prefix}-{year}-%")
        ).order_by(JournalEntry.id.desc()).first()
        
        if last_entry:
            last_num = int(last_entry.entry_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"{prefix}-{year}-{new_num:05d}"
    
    @staticmethod
    def create_journal_entry(
        db: Session,
        entry_data: JournalEntryCreate,
        user_id: Optional[int] = None
    ) -> JournalEntry:
        """Create a journal entry with lines"""
        
        # Generate entry number
        entry_number = AccountingService.generate_entry_number(db, entry_data.transaction_type)
        
        # Calculate totals
        total_debit = sum(line.debit_amount for line in entry_data.lines)
        total_credit = sum(line.credit_amount for line in entry_data.lines)
        
        # Create journal entry
        journal_entry = JournalEntry(
            entry_number=entry_number,
            entry_date=entry_data.entry_date,
            transaction_type=entry_data.transaction_type,
            reference_type=entry_data.reference_type,
            reference_id=entry_data.reference_id,
            description=entry_data.description,
            total_debit=total_debit,
            total_credit=total_credit,
            is_posted=entry_data.is_posted,
            created_by=user_id
        )
        
        db.add(journal_entry)
        db.flush()
        
        # Create journal entry lines
        for line_data in entry_data.lines:
            line = JournalEntryLine(
                journal_entry_id=journal_entry.id,
                account_id=line_data.account_id,
                debit_amount=line_data.debit_amount,
                credit_amount=line_data.credit_amount,
                description=line_data.description,
                line_number=line_data.line_number
            )
            db.add(line)
            
            # Update account balance
            account = db.query(Account).get(line_data.account_id)
            if account:
                if account.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
                    # Debit increases, Credit decreases
                    account.current_balance += (line_data.debit_amount - line_data.credit_amount)
                else:
                    # Credit increases, Debit decreases
                    account.current_balance += (line_data.credit_amount - line_data.debit_amount)
        
        db.commit()
        db.refresh(journal_entry)
        return journal_entry
    
    @staticmethod
    def get_account_by_code(db: Session, account_code: str) -> Optional[Account]:
        """Get account by code"""
        return db.query(Account).filter(Account.account_code == account_code).first()
    
    @staticmethod
    def record_sale_transaction(
        db: Session,
        invoice: Invoice,
        user_id: Optional[int] = None
    ) -> JournalEntry:
        """
        Record journal entry for a sale transaction
        
        Cash Sale:
        Dr. Cash (1000)
        Dr. Discount Given (5400) - if discount
            Cr. Sales Revenue (4000)
        
        Dr. COGS (5000)
            Cr. Inventory (1300)
        """
        
        # Get accounts
        cash_account = AccountingService.get_account_by_code(db, "1000")
        ar_account = AccountingService.get_account_by_code(db, "1200")
        revenue_account = AccountingService.get_account_by_code(db, "4000")
        discount_account = AccountingService.get_account_by_code(db, "5400")
        cogs_account = AccountingService.get_account_by_code(db, "5000")
        inventory_account = AccountingService.get_account_by_code(db, "1300")
        
        if not all([cash_account, revenue_account, cogs_account, inventory_account]):
            raise ValueError("Required accounts not found in Chart of Accounts")
        
        # Determine if cash or credit sale
        is_cash_sale = invoice.payment_method in ["Cash", "Card", "Bank"]
        debit_account = cash_account if is_cash_sale else ar_account
        
        # Calculate amounts
        gross_amount = invoice.sub_total
        discount_amount = invoice.discount_amount or Decimal('0.00')
        net_amount = invoice.net_total
        
        # Create journal entry lines
        lines = []
        line_num = 1
        
        # Dr. Cash/AR
        lines.append(JournalEntryLineCreate(
            account_id=debit_account.id,
            debit_amount=net_amount,
            credit_amount=Decimal('0.00'),
            description=f"Sale - Invoice #{invoice.invoice_number}",
            line_number=line_num
        ))
        line_num += 1
        
        # Dr. Discount (if any)
        if discount_amount > 0:
            lines.append(JournalEntryLineCreate(
                account_id=discount_account.id,
                debit_amount=discount_amount,
                credit_amount=Decimal('0.00'),
                description=f"Discount on Invoice #{invoice.invoice_number}",
                line_number=line_num
            ))
            line_num += 1
        
        # Cr. Sales Revenue
        lines.append(JournalEntryLineCreate(
            account_id=revenue_account.id,
            debit_amount=Decimal('0.00'),
            credit_amount=gross_amount,
            description=f"Sale - Invoice #{invoice.invoice_number}",
            line_number=line_num
        ))
        
        # Create journal entry for sale
        sale_entry_data = JournalEntryCreate(
            entry_date=invoice.created_at.date() if invoice.created_at else date.today(),
            transaction_type=TransactionType.SALE,
            reference_type=ReferenceType.INVOICE,
            reference_id=invoice.id,
            description=f"Sale - Invoice #{invoice.invoice_number}",
            lines=lines
        )
        
        sale_entry = AccountingService.create_journal_entry(db, sale_entry_data, user_id)
        
        # Calculate COGS
        cogs_amount = Decimal('0.00')
        for item in invoice.items:
            # Get cost from inventory
            from ..models import StockInventory
            stock = db.query(StockInventory).filter(
                and_(
                    StockInventory.inventory_id == item.batch_id,
                    StockInventory.product_id == item.medicine_id
                )
            ).first()
            
            if stock:
                cost_per_unit = stock.unit_cost or Decimal('0.00')
                cogs_amount += cost_per_unit * Decimal(str(item.quantity))
        
        # Create COGS entry
        if cogs_amount > 0:
            cogs_lines = [
                JournalEntryLineCreate(
                    account_id=cogs_account.id,
                    debit_amount=cogs_amount,
                    credit_amount=Decimal('0.00'),
                    description=f"COGS - Invoice #{invoice.invoice_number}",
                    line_number=1
                ),
                JournalEntryLineCreate(
                    account_id=inventory_account.id,
                    debit_amount=Decimal('0.00'),
                    credit_amount=cogs_amount,
                    description=f"COGS - Invoice #{invoice.invoice_number}",
                    line_number=2
                )
            ]
            
            cogs_entry_data = JournalEntryCreate(
                entry_date=invoice.created_at.date() if invoice.created_at else date.today(),
                transaction_type=TransactionType.SALE,
                reference_type=ReferenceType.INVOICE,
                reference_id=invoice.id,
                description=f"COGS - Invoice #{invoice.invoice_number}",
                lines=cogs_lines
            )
            
            AccountingService.create_journal_entry(db, cogs_entry_data, user_id)
        
        # Update customer ledger if credit sale
        if not is_cash_sale and invoice.patient_id:
            customer_ledger = CustomerLedger(
                patient_id=invoice.patient_id,
                journal_entry_id=sale_entry.id,
                transaction_date=sale_entry.entry_date,
                transaction_type=TransactionType.SALE,
                reference_number=invoice.invoice_number,
                debit_amount=net_amount,
                credit_amount=Decimal('0.00'),
                balance=net_amount,  # Will be calculated properly in production
                description=f"Sale - Invoice #{invoice.invoice_number}"
            )
            db.add(customer_ledger)
            db.commit()
        
        db.commit() # Final safety commit
        return sale_entry
    
    @staticmethod
    def record_purchase_transaction(
        db: Session,
        grn: GRN,
        user_id: Optional[int] = None
    ) -> JournalEntry:
        """
        Record journal entry for a purchase transaction
        
        Credit Purchase:
        Dr. Inventory (1300)
            Cr. Accounts Payable (2000)
            
        Cash Purchase (Auto-Payment):
        1. Record Purchase: Dr. Inventory (1300), Cr. AP (2000)
        2. Record Payment: Dr. AP (2000), Cr. Cash (1000)
        """
        
        # Get accounts
        inventory_account = AccountingService.get_account_by_code(db, "1300")
        ap_account = AccountingService.get_account_by_code(db, "2000")
        cash_account = AccountingService.get_account_by_code(db, "1000")
        tax_account = AccountingService.get_account_by_code(db, "1450") # Advance Tax Receivable
        
        if not all([inventory_account, ap_account, cash_account, tax_account]):
            raise ValueError("Required accounts not found in Chart of Accounts (Ensure 1450 exists)")
        
        # Calculate amounts
        # Inventory value = SubTotal + Loading + Freight + PurchaseTax (if non-adjustable) + Other - Discount
        # Note: advance_tax is kept separate as per user request
        
        # Helper to convert float to Decimal safely
        def to_dec(val):
            return Decimal(str(val or 0.0))
            
        inv_val = (to_dec(grn.sub_total) + to_dec(grn.loading_exp) + 
                  to_dec(grn.freight_exp) + to_dec(grn.other_exp) + 
                  to_dec(grn.purchase_tax) - to_dec(grn.discount))
                  
        tax_val = to_dec(grn.advance_tax)
        total_liability = to_dec(grn.net_total)
        
        # Determine if cash or credit purchase (mode from GRN)
        is_cash_purchase = grn.payment_mode.strip().lower() == "cash" if grn.payment_mode else False
        
        # 1. ALWAYS Record the Purchase against AP first to maintain Supplier Ledger history
        purchase_lines = []
        line_num = 1
        
        # Line 1: Inventory (Debit)
        purchase_lines.append(JournalEntryLineCreate(
            account_id=inventory_account.id,
            debit_amount=inv_val,
            credit_amount=Decimal('0.00'),
            description=f"Inventory - GRN #{grn.custom_grn_no} (Landed Cost exc. Advance Tax)",
            line_number=line_num
        ))
        line_num += 1
        
        # Line 2: Advance Tax (Debit) - Only if > 0
        if tax_val > 0:
            purchase_lines.append(JournalEntryLineCreate(
                account_id=tax_account.id,
                debit_amount=tax_val,
                credit_amount=Decimal('0.00'),
                description=f"Advance Tax - GRN #{grn.custom_grn_no}",
                line_number=line_num
            ))
            line_num += 1
            
        # Line 3: Accounts Payable (Credit)
        purchase_lines.append(JournalEntryLineCreate(
            account_id=ap_account.id,
            debit_amount=Decimal('0.00'),
            credit_amount=total_liability,
            description=f"Accounts Payable - GRN #{grn.custom_grn_no}",
            line_number=line_num
        ))
        
        purchase_entry_data = JournalEntryCreate(
            entry_date=grn.invoice_date.date() if grn.invoice_date else date.today(),
            transaction_type=TransactionType.PURCHASE,
            reference_type=ReferenceType.GRN,
            reference_id=grn.id,
            description=f"Purchase - GRN #{grn.custom_grn_no} ({grn.payment_mode})",
            lines=purchase_lines
        )
        
        purchase_entry = AccountingService.create_journal_entry(db, purchase_entry_data, user_id)
        
        # Update supplier ledger for the purchase
        supplier = None
        if grn.supplier_id:
            supplier = db.query(Supplier).get(grn.supplier_id)
            if supplier:
                # Update Supplier Master Balance
                current_bal = Decimal(str(supplier.ledger_balance or 0.0))
                supplier.ledger_balance = float(current_bal + total_liability)

            supplier_ledger_purchase = SupplierLedger(
                supplier_id=grn.supplier_id,
                journal_entry_id=purchase_entry.id,
                transaction_date=purchase_entry.entry_date,
                transaction_type=TransactionType.PURCHASE,
                reference_number=grn.custom_grn_no,
                debit_amount=Decimal('0.00'),
                credit_amount=total_liability,
                balance=Decimal(str(supplier.ledger_balance)),
                description=f"Purchase - GRN #{grn.custom_grn_no}"
            )
            db.add(supplier_ledger_purchase)
            db.flush()
        
        # 2. If it's a CASH purchase, record an immediate PAYMENT
        if is_cash_purchase:
            payment_lines = [
                JournalEntryLineCreate(
                    account_id=ap_account.id,
                    debit_amount=total_liability,
                    credit_amount=Decimal('0.00'),
                    description=f"Cash Payment for GRN #{grn.custom_grn_no}",
                    line_number=1
                ),
                JournalEntryLineCreate(
                    account_id=cash_account.id,
                    debit_amount=Decimal('0.00'),
                    credit_amount=total_liability,
                    description=f"Cash Payment for GRN #{grn.custom_grn_no}",
                    line_number=2
                )
            ]
            
            payment_entry_data = JournalEntryCreate(
                entry_date=grn.invoice_date.date() if grn.invoice_date else date.today(),
                transaction_type=TransactionType.PAYMENT,
                reference_type=ReferenceType.GRN,
                reference_id=grn.id,
                description=f"Immediate Cash Payment - GRN #{grn.custom_grn_no}",
                lines=payment_lines
            )
            
            payment_entry = AccountingService.create_journal_entry(db, payment_entry_data, user_id)
            
            # Record in Supplier Ledger for the payment
            if grn.supplier_id:
                if supplier:
                    # Deduct from Supplier Master Balance
                    current_bal = Decimal(str(supplier.ledger_balance or 0.0))
                    supplier.ledger_balance = float(current_bal - total_liability)

                supplier_ledger_payment = SupplierLedger(
                    supplier_id=grn.supplier_id,
                    journal_entry_id=payment_entry.id,
                    transaction_date=payment_entry.entry_date,
                    transaction_type=TransactionType.PAYMENT,
                    reference_number=grn.custom_grn_no,
                    debit_amount=total_liability,
                    credit_amount=Decimal('0.00'),
                    balance=Decimal(str(supplier.ledger_balance)),
                    description=f"Cash Payment - GRN #{grn.custom_grn_no}"
                )
                db.add(supplier_ledger_payment)
                
            # Create a PaymentVoucher record as well
            payment_voucher = PaymentVoucher(
                voucher_number=f"PV-GRN-{grn.custom_grn_no}",
                payment_date=payment_entry.entry_date,
                payment_method=PaymentMethod.CASH,
                payee_type=PayeeType.SUPPLIER,
                payee_id=grn.supplier_id,
                amount=total_liability,
                account_id=cash_account.id,
                journal_entry_id=payment_entry.id,
                description=f"Auto-generated payment for Cash GRN #{grn.custom_grn_no}",
                created_by=user_id
            )
            db.add(payment_voucher)
            db.commit()
            db.add(payment_voucher)
            db.commit()
            
        db.commit() # Final safety commit
        return purchase_entry

    
    @staticmethod
    def record_return_transaction(
        db: Session,
        invoice: Invoice,
        user_id: Optional[int] = None
    ) -> JournalEntry:
        """
        Record journal entry for a sales return
        
        Dr. Sales Revenue (4000)
            Cr. Cash/AR (1000/1200)
        
        Dr. Inventory (1300)
            Cr. COGS (5000)
        """
        
        # Get accounts
        revenue_account = AccountingService.get_account_by_code(db, "4000")
        cash_account = AccountingService.get_account_by_code(db, "1000")
        ar_account = AccountingService.get_account_by_code(db, "1200")
        inventory_account = AccountingService.get_account_by_code(db, "1300")
        cogs_account = AccountingService.get_account_by_code(db, "5000")
        
        if not all([revenue_account, cash_account, inventory_account, cogs_account]):
            raise ValueError("Required accounts not found")
        
        # Determine credit account based on original payment method
        is_cash = invoice.payment_method in ["Cash", "Card", "Bank"]
        credit_account = cash_account if is_cash else ar_account
        
        return_amount = abs(invoice.net_total)
        
        # Revenue reversal
        revenue_lines = [
            JournalEntryLineCreate(
                account_id=revenue_account.id,
                debit_amount=return_amount,
                credit_amount=Decimal('0.00'),
                description=f"Sales Return - Invoice #{invoice.invoice_number}",
                line_number=1
            ),
            JournalEntryLineCreate(
                account_id=credit_account.id,
                debit_amount=Decimal('0.00'),
                credit_amount=return_amount,
                description=f"Sales Return - Invoice #{invoice.invoice_number}",
                line_number=2
            )
        ]
        
        revenue_entry_data = JournalEntryCreate(
            entry_date=date.today(),
            transaction_type=TransactionType.SALE,
            reference_type=ReferenceType.INVOICE,
            reference_id=invoice.id,
            description=f"Sales Return - Invoice #{invoice.invoice_number}",
            lines=revenue_lines
        )
        
        return AccountingService.create_journal_entry(db, revenue_entry_data, user_id)

    @staticmethod
    def get_account_balance(db: Session, account_id: int, as_of_date: date) -> Decimal:
        """Calculate account balance as of a specific date"""
        account = db.query(Account).get(account_id)
        if not account:
            return Decimal('0.00')
        
        # Start with opening balance
        balance = account.opening_balance or Decimal('0.00')
        
        # Get total debits and credits up to as_of_date
        totals = db.query(
            func.sum(JournalEntryLine.debit_amount).label('total_debit'),
            func.sum(JournalEntryLine.credit_amount).label('total_credit')
        ).join(JournalEntry).filter(
            and_(
                JournalEntryLine.account_id == account_id,
                JournalEntry.entry_date <= as_of_date,
                JournalEntry.is_posted == True
            )
        ).first()
        
        total_debit = totals.total_debit or Decimal('0.00')
        total_credit = totals.total_credit or Decimal('0.00')
        
        if account.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
            # Normal debit balance: Opening + Debit - Credit
            balance += (total_debit - total_credit)
        else:
            # Normal credit balance: Opening + Credit - Debit
            balance += (total_credit - total_debit)
            
        return balance

    @staticmethod
    def record_inventory_adjustment_accounting(
        db: Session,
        adjustment: Any, # StockAdjustment model instance
        user_id: Optional[int] = None
    ) -> Optional[JournalEntry]:
        """
        Record accounting entries for specific inventory adjustment types.
        Currently handles: Return to Supplier
        
        Return to Supplier Logic:
        Dr. Accounts Payable (2000)
            Cr. Inventory (1300)
        """
        if adjustment.adjustment_type != "return_to_supplier":
            return None
            
        # Get accounts
        inventory_account = AccountingService.get_account_by_code(db, "1300")
        ap_account = AccountingService.get_account_by_code(db, "2000")
        
        if not all([inventory_account, ap_account]):
            # Log warning or handle as needed - strictly speaking we might want to fail 
            # but adjustments can be non-financial too. For Return to Supplier, it MUST have accounts.
            raise ValueError("Required accounts (Inventory 1300, AP 2000) not found in COA")

        # Get the associated inventory record to find supplier and unit cost
        # adjustment.inventory is available via relationship
        stock = adjustment.inventory
        if not stock:
            raise ValueError("Associated inventory record not found for adjustment")
            
        supplier_id = stock.supplier_id
        unit_cost = Decimal(str(stock.unit_cost or 0.0))
        qty = Decimal(str(abs(adjustment.quantity_adjusted)))
        total_value = unit_cost * qty
        
        if total_value <= 0:
            return None # No financial impact if cost is 0

        # 1. Create Journal Entry
        lines = [
            JournalEntryLineCreate(
                account_id=ap_account.id,
                debit_amount=total_value,
                credit_amount=Decimal('0.00'),
                description=f"Supplier Return - Adjustment #{adjustment.adjustment_id} (Batch: {adjustment.batch_number})",
                line_number=1
            ),
            JournalEntryLineCreate(
                account_id=inventory_account.id,
                debit_amount=Decimal('0.00'),
                credit_amount=total_value,
                description=f"Supplier Return - Adjustment #{adjustment.adjustment_id} (Batch: {adjustment.batch_number})",
                line_number=2
            )
        ]
        
        adj_entry_data = JournalEntryCreate(
            entry_date=adjustment.adjustment_date.date() if adjustment.adjustment_date else date.today(),
            transaction_type=TransactionType.ADJUSTMENT,
            reference_type=ReferenceType.MANUAL, # Could add RETURN to ReferenceType if needed
            reference_id=adjustment.adjustment_id,
            description=f"Stock Return to Supplier - Adj #{adjustment.adjustment_id} - Qty: {qty}",
            lines=lines
        )
        
        journal_entry = AccountingService.create_journal_entry(db, adj_entry_data, user_id)
        
        # 2. Update Supplier Ledger if we have a supplier
        if supplier_id:
            supplier = db.query(Supplier).get(supplier_id)
            if supplier:
                # Update Supplier Master Balance (Debit reduces liability)
                current_ledger_bal = Decimal(str(supplier.ledger_balance or 0.0))
                supplier.ledger_balance = float(current_ledger_bal - total_value)
                
                # Create Ledger Row
                supplier_ledger = SupplierLedger(
                    supplier_id=supplier_id,
                    journal_entry_id=journal_entry.id,
                    transaction_date=journal_entry.entry_date,
                    transaction_type=TransactionType.ADJUSTMENT,
                    reference_number=f"ADJ-{adjustment.adjustment_id}",
                    debit_amount=total_value,
                    credit_amount=Decimal('0.00'),
                    balance=Decimal(str(supplier.ledger_balance)),
                    description=f"Returns - Adj #{adjustment.adjustment_id}"
                )
                db.add(supplier_ledger)
                db.flush()
        
        # 3. Link Journal to Adjustment
        adjustment.journal_entry_id = journal_entry.id
        db.commit()
        
        return journal_entry
