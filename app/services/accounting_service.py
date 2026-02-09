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
        print(f"--- TRACE: create_journal_entry -> Generated {entry_number}")
        
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
        
        try:
            db.commit()
            print(f"--- TRACE: create_journal_entry -> DB COMMIT SUCCESS for {entry_number}")
        except Exception as e:
            print(f"--- ERROR: create_journal_entry -> DB COMMIT FAILED: {e}")
            db.rollback()
            raise e
            
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
        Record journal entry for a sale transaction (Handles integrated Sales, Returns, and Exchanges)
        """
        
        # Get accounts
        cash_account = AccountingService.get_account_by_code(db, "1000")
        bank_account = AccountingService.get_account_by_code(db, "1100")
        ar_account = AccountingService.get_account_by_code(db, "1200")
        revenue_account = AccountingService.get_account_by_code(db, "4000")
        discount_account = AccountingService.get_account_by_code(db, "5400")
        cogs_account = AccountingService.get_account_by_code(db, "5000")
        inventory_account = AccountingService.get_account_by_code(db, "1300")
        tax_account = AccountingService.get_account_by_code(db, "2200")
        
        if not all([cash_account, bank_account, revenue_account, cogs_account, inventory_account, tax_account]):
            raise ValueError("Required accounts (1000, 1100, 4000, 5000, 1300, 2200) not found in Chart of Accounts")
        
        # 1. Financial Impact (Cash/Bank/AR vs Revenue/Tax/Discount)
        payment_method = (invoice.payment_method or "Cash").strip()
        
        if payment_method == "Card":
            payment_account = bank_account
        elif payment_method == "Credit":
            payment_account = ar_account
        else: # Default and "Cash"
            payment_account = cash_account
        
        # Helper to convert float to rounded Decimal safely
        def to_dec(val):
            return Decimal(str(val or 0.0)).quantize(Decimal('0.01'))
            
        net_total = to_dec(invoice.net_total)
        tax_amount = to_dec(invoice.tax_amount)
        discount_amount = to_dec(invoice.discount_amount)
        
        # Enforce mathematical balance: Net = Sub + Tax - Discount  =>  Sub = Net + Discount - Tax
        # This prevents rounding mismatches (a few cents) from causing Pydantic validation errors.
        sub_total = (net_total + discount_amount - tax_amount).quantize(Decimal('0.01'))
        
        print(f"--- TRACE: record_sale_transaction for {invoice.invoice_number}")
        print(f"DEBUG Accounting: Net={net_total}, Tax={tax_amount}, Disc={discount_amount}, BAL={sub_total}")
        
        lines = []
        line_num = 1
        
        # Entry for Payment (Net change in Cash/AR)
        if net_total > 0:
            # Net Receipt
            lines.append(JournalEntryLineCreate(
                account_id=payment_account.id,
                debit_amount=net_total,
                credit_amount=Decimal('0.00'),
                description=f"Sale/Exchange - Inv #{invoice.invoice_number}",
                line_number=line_num
            ))
        elif net_total < 0:
            # Net Refund
            lines.append(JournalEntryLineCreate(
                account_id=payment_account.id,
                debit_amount=Decimal('0.00'),
                credit_amount=abs(net_total),
                description=f"Refund - Inv #{invoice.invoice_number}",
                line_number=line_num
            ))
        line_num += 1

        # Entry for Revenue (Net Revenue)
        # sub_total can be negative if it's a net refund
        if sub_total > 0:
            lines.append(JournalEntryLineCreate(
                account_id=revenue_account.id,
                debit_amount=Decimal('0.00'),
                credit_amount=sub_total,
                description=f"Revenue - Inv #{invoice.invoice_number}",
                line_number=line_num
            ))
        elif sub_total < 0:
            lines.append(JournalEntryLineCreate(
                account_id=revenue_account.id,
                debit_amount=abs(sub_total),
                credit_amount=Decimal('0.00'),
                description=f"Revenue Reversal - Inv #{invoice.invoice_number}",
                line_number=line_num
            ))
        line_num += 1

        # Tax
        if tax_amount > 0:
            lines.append(JournalEntryLineCreate(
                account_id=tax_account.id,
                debit_amount=Decimal('0.00'),
                credit_amount=tax_amount,
                description=f"GST Collected - Inv #{invoice.invoice_number}",
                line_number=line_num
            ))
        elif tax_amount < 0:
            lines.append(JournalEntryLineCreate(
                account_id=tax_account.id,
                debit_amount=abs(tax_amount),
                credit_amount=Decimal('0.00'),
                description=f"GST Reversal - Inv #{invoice.invoice_number}",
                line_number=line_num
            ))
        line_num += 1

        # Discount
        if discount_amount > 0:
            # Discount is an expense (Debit)
            lines.append(JournalEntryLineCreate(
                account_id=discount_account.id,
                debit_amount=discount_amount,
                credit_amount=Decimal('0.00'),
                description=f"Discount Given - Inv #{invoice.invoice_number}",
                line_number=line_num
            ))
        elif discount_amount < 0:
            # Unusual but handled: Discount reversal
            lines.append(JournalEntryLineCreate(
                account_id=discount_account.id,
                debit_amount=Decimal('0.00'),
                credit_amount=abs(discount_amount),
                description=f"Discount Reversal - Inv #{invoice.invoice_number}",
                line_number=line_num
            ))
        line_num += 1

        # 2. Inventory / COGS (Item by Item to handle cost reversals)
        total_cogs_impact = Decimal('0.00')
        for item in invoice.items:
            # We need the cost at the time of sale.
            from ..models import StockInventory
            stock = db.query(StockInventory).filter(
                StockInventory.inventory_id == item.batch_id,
                StockInventory.product_id == item.medicine_id
            ).first()
            
            if stock:
                unit_cost = to_dec(stock.unit_cost)
                total_cogs_impact += unit_cost * to_dec(item.quantity)
                
        total_cogs_impact = total_cogs_impact.quantize(Decimal('0.01'))
        
        total_cogs_impact = total_cogs_impact.quantize(Decimal('0.01'))

        if total_cogs_impact > 0:
            # Net Sale of items: Dr. COGS, Cr. Inventory
            lines.append(JournalEntryLineCreate(
                account_id=cogs_account.id,
                debit_amount=total_cogs_impact,
                credit_amount=to_dec(0),
                description=f"COGS - Inv #{invoice.invoice_number}",
                line_number=line_num
            ))
            line_num += 1
            lines.append(JournalEntryLineCreate(
                account_id=inventory_account.id,
                debit_amount=to_dec(0),
                credit_amount=total_cogs_impact,
                description=f"Inventory Reduction - Inv #{invoice.invoice_number}",
                line_number=line_num
            ))
        elif total_cogs_impact < 0:
            # Net Return of items: Dr. Inventory, Cr. COGS
            lines.append(JournalEntryLineCreate(
                account_id=inventory_account.id,
                debit_amount=abs(total_cogs_impact),
                credit_amount=Decimal('0.00'),
                description=f"Inventory Restock - Inv #{invoice.invoice_number}",
                line_number=line_num
            ))
            line_num += 1
            lines.append(JournalEntryLineCreate(
                account_id=cogs_account.id,
                debit_amount=Decimal('0.00'),
                credit_amount=abs(total_cogs_impact),
                description=f"COGS Reversal - Inv #{invoice.invoice_number}",
                line_number=line_num
            ))

        print(f"--- TRACE: Journal entry lines count: {len(lines)}")
        for i, l in enumerate(lines):
            print(f"  Line {i+1}: Acc={l.account_id}, Dr={l.debit_amount}, Cr={l.credit_amount}, Desc='{l.description}'")
            
        # Create the journal entry
        entry_data = JournalEntryCreate(
            entry_date=invoice.created_at.date() if invoice.created_at else date.today(),
            transaction_type=TransactionType.SALE,
            reference_type=ReferenceType.INVOICE,
            reference_id=invoice.id,
            description=f"POS Transaction - Inv #{invoice.invoice_number}",
            lines=lines
        )
        
        print(f"--- TRACE: Calling create_journal_entry for {invoice.invoice_number}")
        sale_entry = AccountingService.create_journal_entry(db, entry_data, user_id)
        print(f"--- TRACE: create_journal_entry SUCCESS for {invoice.invoice_number}")
        
        # Update customer ledger if credit
        if payment_method == "Credit" and (invoice.customer_id or invoice.patient_id):
            customer_ledger = CustomerLedger(
                customer_id=invoice.customer_id,
                patient_id=invoice.patient_id,
                journal_entry_id=sale_entry.id,
                transaction_date=sale_entry.entry_date,
                transaction_type=TransactionType.SALE if net_total >= 0 else TransactionType.ADJUSTMENT,
                reference_number=invoice.invoice_number,
                debit_amount=net_total if net_total > 0 else Decimal('0.00'),
                credit_amount=abs(net_total) if net_total < 0 else Decimal('0.00'),
                description=f"POS Trans - Inv #{invoice.invoice_number}"
            )
            db.add(customer_ledger)

        db.commit()
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
        
        # Helper to convert float to rounded Decimal safely
        def to_dec(val):
            return Decimal(str(val or 0.0)).quantize(Decimal('0.01'))
            
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
            
        return purchase_entry

    
    @staticmethod
    def record_sales_return_accounting(
        db: Session,
        sales_return: Any, # SalesReturn model instance
        user_id: Optional[int] = None
    ) -> JournalEntry:
        """
        Record journal entry for a sales return (Credit Note)
        
        Dr. Sales Revenue (4000)
        Dr. Sales Tax Payable (2200) - if applicable
            Cr. Cash/Bank (1000) or Accounts Receivable (1200)
            
        Dr. Inventory Asset (1300)
            Cr. Cost of Goods Sold (5000)
        """
        
        # 1. Get Accounts
        revenue_account = AccountingService.get_account_by_code(db, "4000")
        tax_account = AccountingService.get_account_by_code(db, "2200")
        cash_account = AccountingService.get_account_by_code(db, "1000")
        ar_account = AccountingService.get_account_by_code(db, "1200")
        inventory_account = AccountingService.get_account_by_code(db, "1300")
        cogs_account = AccountingService.get_account_by_code(db, "5000")
        
        if not all([revenue_account, cash_account, inventory_account, cogs_account]):
            raise ValueError("Required accounts (4000, 1000, 1300, 5000) not found in COA")

        # 2. Determine Credit Account (Cash or AR)
        # If invoice exists, use its payment method. If ad-hoc, assume Cash for now.
        payment_method = "Cash"
        if sales_return.invoice:
            payment_method = sales_return.invoice.payment_method
            
        is_cash = payment_method in ["Cash", "Card", "Bank"]
        credit_account = cash_account if is_cash else ar_account

        # Helper to convert float to rounded Decimal safely
        def to_dec(val):
            return Decimal(str(val or 0.0)).quantize(Decimal('0.01'))
            
        # 3. Calculate Totals
        total_refund = to_dec(sales_return.net_total)
        tax_refund = to_dec(sales_return.tax_amount)
        revenue_refund = (total_refund - tax_refund).quantize(Decimal('0.01'))
        
        # Calculate COGS Reversal (Total cost of items being returned)
        total_cost_reversal = Decimal('0.00')
        for item in sales_return.items:
            # We need to find the unit cost. Usually stored in StockInventory
            if item.inventory:
                unit_cost = to_dec(item.inventory.unit_cost)
                total_cost_reversal += unit_cost * to_dec(item.quantity)

        # 4. Create Journal Lines
        lines = []
        line_no = 1
        
        # Dr. Revenue
        lines.append(JournalEntryLineCreate(
            account_id=revenue_account.id,
            debit_amount=revenue_refund,
            credit_amount=Decimal('0.00'),
            description=f"Sales Return - {sales_return.id}",
            line_number=line_no
        ))
        line_no += 1
        
        # Dr. Tax (if any)
        if tax_refund > 0:
            if tax_account:
                lines.append(JournalEntryLineCreate(
                    account_id=tax_account.id,
                    debit_amount=tax_refund,
                    credit_amount=Decimal('0.00'),
                    description=f"GST Reversal on Return - {sales_return.id}",
                    line_number=line_no
                ))
                line_no += 1
        
        # Cr. Cash/AR
        lines.append(JournalEntryLineCreate(
            account_id=credit_account.id,
            debit_amount=Decimal('0.00'),
            credit_amount=total_refund,
            description=f"Refund Issued - {sales_return.id}",
            line_number=line_no
        ))
        line_no += 1
        
        # Dr. Inventory / Cr. COGS (Inventory Value Reversal)
        if total_cost_reversal > 0:
            lines.append(JournalEntryLineCreate(
                account_id=inventory_account.id,
                debit_amount=total_cost_reversal,
                credit_amount=Decimal('0.00'),
                description=f"Inventory Restock (Cost) - Return {sales_return.id}",
                line_number=line_no
            ))
            line_no += 1
            lines.append(JournalEntryLineCreate(
                account_id=cogs_account.id,
                debit_amount=Decimal('0.00'),
                credit_amount=total_cost_reversal,
                description=f"COGS Reversal - Return {sales_return.id}",
                line_number=line_no
            ))
            line_no += 1

        # 5. Save Journal Entry
        entry_data = JournalEntryCreate(
            entry_date=sales_return.return_date.date() if sales_return.return_date else date.today(),
            transaction_type=TransactionType.ADJUSTMENT,
            reference_type=ReferenceType.INVOICE if sales_return.invoice_id else ReferenceType.MANUAL,
            reference_id=sales_return.id,
            description=f"Sales Return (Credit Note) #{sales_return.id}. Reason: {sales_return.reason}",
            lines=lines
        )
        
        journal_entry = AccountingService.create_journal_entry(db, entry_data, user_id)
        
        # 6. Update Customer Ledger if not anonymous
        if not is_cash and sales_return.invoice and sales_return.invoice.patient_id:
            customer_ledger = CustomerLedger(
                patient_id=sales_return.invoice.patient_id,
                journal_entry_id=journal_entry.id,
                transaction_date=journal_entry.entry_date,
                transaction_type=TransactionType.ADJUSTMENT,
                reference_number=f"RET-{sales_return.id}",
                debit_amount=Decimal('0.00'),
                credit_amount=total_refund,
                # Balance update logic usually handled by a common service or trigger
                description=f"Return against Inv #{sales_return.invoice.invoice_number}"
            )
            db.add(customer_ledger)

        # 7. Link to Sales Return
        sales_return.journal_entry_id = journal_entry.id
        db.commit()
        
        return journal_entry

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
