from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models import GRN, Supplier
from app.services.accounting_service import AccountingService
from decimal import Decimal
from datetime import datetime, date

def fix_historical_grns():
    db = SessionLocal()
    try:
        # Get all schemas
        result = db.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%'"))
        schemas = [row[0] for row in result]
        
        for schema in schemas:
            print(f"\n--- Processing Schema: {schema} ---")
            db.execute(text(f"SET search_path TO {schema}, public"))
            
            # Find "Cash" GRNs
            cash_grns = db.query(GRN).filter(GRN.payment_mode.ilike('%cash%')).all()
            
            for grn_ref in cash_grns:
                # Re-fetch or use ID to avoid detachment issues
                grn_id = grn_ref.id
                grn = db.query(GRN).get(grn_id)
                
                # Count ledger entries for this GRN
                ledger_count = db.execute(text("""
                    SELECT count(*) FROM supplier_ledger 
                    WHERE reference_number = :ref
                """), {"ref": grn.custom_grn_no}).scalar()
                
                if ledger_count == 0:
                    print(f"  [FIXING-ALL] GRN {grn.custom_grn_no} has 0 ledger entries. Recording full transaction...")
                    try:
                        # Ensure fields for accounting service
                        grn.grn_number = grn.custom_grn_no
                        grn.received_date = grn.invoice_date.date() if isinstance(grn.invoice_date, datetime) else grn.invoice_date
                        grn.total_amount = grn.net_total
                        
                        AccountingService.record_purchase_transaction(db, grn, None)
                        print(f"    ✓ Recorded Purchase & Payment for {grn.custom_grn_no}")
                    except Exception as e:
                        print(f"    [ERR] Failed to record GRN {grn.custom_grn_no}: {e}")
                        db.rollback()

                elif ledger_count == 1:
                    print(f"  [FIXING-PAYMENT] GRN {grn.custom_grn_no} has only 1 entry. Adding Payment...")
                    try:
                        from app.models.accounting_models import TransactionType, ReferenceType, JournalEntryLine, JournalEntry, PaymentVoucher, PaymentMethod, PayeeType, SupplierLedger
                        from app.schemas.accounting_schemas import JournalEntryCreate, JournalEntryLineCreate
                        
                        ap_account = AccountingService.get_account_by_code(db, "2000")
                        cash_account = AccountingService.get_account_by_code(db, "1000")
                        
                        if not all([ap_account, cash_account]):
                             print(f"    [SKIP] Missing accounts (AP/Cash) for {schema}")
                             continue

                        total_amount = Decimal(str(grn.net_total))
                        entry_date = grn.invoice_date.date() if isinstance(grn.invoice_date, datetime) else (grn.invoice_date or date.today())
                        
                        payment_lines = [
                            JournalEntryLineCreate(
                                account_id=ap_account.id,
                                debit_amount=total_amount,
                                credit_amount=Decimal('0.00'),
                                description=f"Cash Payment for GRN #{grn.custom_grn_no} (REPAIR)",
                                line_number=1
                            ),
                            JournalEntryLineCreate(
                                account_id=cash_account.id,
                                debit_amount=Decimal('0.00'),
                                credit_amount=total_amount,
                                description=f"Cash Payment for GRN #{grn.custom_grn_no} (REPAIR)",
                                line_number=2
                            )
                        ]
                        
                        payment_entry_data = JournalEntryCreate(
                            entry_date=entry_date,
                            transaction_type=TransactionType.PAYMENT,
                            reference_type=ReferenceType.GRN,
                            reference_id=grn.id,
                            description=f"Immediate Cash Payment - GRN #{grn.custom_grn_no} (REPAIR)",
                            lines=payment_lines
                        )
                        
                        payment_entry = AccountingService.create_journal_entry(db, payment_entry_data, None)
                        
                        # Update supplier balance
                        if grn.supplier_id:
                            supplier = db.query(Supplier).get(grn.supplier_id)
                            if supplier:
                                current_bal = Decimal(str(supplier.ledger_balance or 0.0))
                                supplier.ledger_balance = float(current_bal - total_amount)

                            supplier_ledger_payment = SupplierLedger(
                                supplier_id=grn.supplier_id,
                                journal_entry_id=payment_entry.id,
                                transaction_date=payment_entry.entry_date,
                                transaction_type=TransactionType.PAYMENT,
                                reference_number=grn.custom_grn_no,
                                debit_amount=total_amount,
                                credit_amount=Decimal('0.00'),
                                balance=Decimal(str(supplier.ledger_balance)),
                                description=f"Cash Payment - GRN #{grn.custom_grn_no} (REPAIR)"
                            )
                            db.add(supplier_ledger_payment)
                        
                        # Create PaymentVoucher
                        payment_voucher = PaymentVoucher(
                            voucher_number=f"PV-GRN-{grn.custom_grn_no}-R",
                            payment_date=payment_entry.entry_date,
                            payment_method=PaymentMethod.CASH,
                            payee_type=PayeeType.SUPPLIER,
                            payee_id=grn.supplier_id,
                            amount=total_amount,
                            account_id=cash_account.id,
                            journal_entry_id=payment_entry.id,
                            description=f"Auto-generated repair for Cash GRN #{grn.custom_grn_no}",
                            created_by=None
                        )
                        db.add(payment_voucher)
                        db.commit()
                        print(f"    ✓ Added Payment entry for {grn.custom_grn_no}")
                    except Exception as e:
                        print(f"    [ERR] Failed to fix payment for GRN {grn.custom_grn_no}: {e}")
                        db.rollback()
                else:
                    # 2 entries = OK
                    pass

    except Exception as e:
        print(f"Global error repairing GRNs: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_historical_grns()
