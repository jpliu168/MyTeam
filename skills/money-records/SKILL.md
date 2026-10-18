---
name: money-records
description: Handling {{GROUP}}'s financial records — bank/card exports, receipts, invoices, categories, monthly summaries, tax prep files. Use whenever a task touches money, books, or taxes.
---

# Money records

Goal: tidy, traceable records the {{BOSS}} (and their accountant) can trust.

Where things live:
- Raw inputs the {{BOSS}} drops in: `{{STATE}}/deliverables/books/inbox/`
  (never edit these — copy, then work on the copy).
- Monthly work: `{{STATE}}/deliverables/books/<YYYY-MM>/` — a ledger CSV
  (date, payee, amount, category, source file, note) and `summary.md`.
- Tax files: `{{STATE}}/deliverables/tax/<YYYY>/`.

Rules:
- Every number traces to a source file and row. If it doesn't, it isn't in
  the summary — it's in a "needs the {{BOSS}}" list.
- Business vs personal, unclear categories, duplicates, missing receipts:
  flag them, don't guess.
- Totals are computed with code or spreadsheet formulas, never mental math;
  show the check (e.g. ledger total = bank statement change).
- Tax rules: cite the official source (IRS or state revenue page) and the
  tax year; anything that is a judgment call is "for the CPA to confirm".
  You are not a tax advisor or accountant.
- You never move money, pay, file, or log in to bank, payment, payroll or tax
  portals. You prepare; the {{BOSS}} acts.
- Account numbers, SSNs/EINs and card numbers: last 4 digits only in notes.
