# Design: Philippine Compensation Tax Computation (User-Maintained Rates)

This document describes how **taxes on compensation** for the Philippines should be computed in PH Payroll, with **rates and brackets maintained by users** (not hard-coded in Python). It builds on existing DocTypes (**Annual Tax Table**, **SSS Table**, **Philhealth Table**, **Pagibig Table**) and **Payroll Voucher** fields already present in the app.

## 1. Business context

Philippine payroll typically involves:

| Levy | Nature | Typical handling in payroll software |
|------|--------|--------------------------------------|
| **Income tax (BIR)** | Withholding on compensation (e.g. under **RA 10963 / TRAIN** and BIR issuances) | Graduated **annual** or **monthly** tables; employee status (e.g. MWE, exemptions) may apply |
| **SSS** | Social security (employee + employer) | Bracket table by salary credit / MSC |
| **PhilHealth** | Health insurance | Rate and premium rules by period |
| **Pag-IBIG (HDMF)** | Home development mutual fund | Rate caps and brackets |

The app **already** computes **SSS, PhilHealth, and Pag-IBIG** from **active** table documents (`SSS Table`, `Philhealth Table`, `Pagibig Table`). **Income tax** is the main gap: **Payroll Voucher** exposes `taxable_income` and `tax`, but regular payroll computation does not yet derive them from a maintained table.

**Scope of this design:** define a clear, auditable pipeline for **taxable compensation** and **withholding tax**, with **all numeric rules (brackets, rates, fixed amounts) stored in DocTypes** that HR or finance can edit when laws or BIR tables change.

**Out of scope (unless later specified):** BIR **2316** export, alphalist generation, employer **remittance filing** workflows, and legal interpretation (implement formulas that match your accountant’s reading of the relevant RRs).

## 2. Goals

| Goal | Description |
|------|-------------|
| User-maintained rates | Brackets, percentages, and fixed “base tax” amounts live in **Frappe documents**, not constants in code. |
| Consistent with existing patterns | Same idea as **SSS Table**: one **active** table (or versioned table + effective date), child rows for brackets. |
| Single payroll document | Results land on **Payroll Voucher** (`taxable_income`, `tax`, `net_pay`); optional detail rows for audit. |
| Configurable tax base | **Payroll Settings** (or equivalent) defines which earnings count toward **taxable income** for withholding (policy + law). |
| Safe updates | Changing a table affects **future** runs; optionally **effective dating** so past vouchers stay reproducible. |

## 3. Current model (reference)

### 3.1 Payroll Voucher (existing fields)

Relevant fields already on **Payroll Voucher**:

- **Earnings totals:** `total_basic_pay`, `total_overtime_pay`, `total_holiday_pay`, `total_incentive`, `thirteenth_month_pay` (for 13th month runs), `less_cash_advance`, etc.
- **Tax:** `taxable_income`, `tax` (withholding).
- **Statutory contributions:** `sss`, `philhealth`, `hdmf` (aggregates), plus breakdown fields (`ss_ee`, `ph_ee`, `hd_ee`, …).

Regular **`populate_items`** today: sums items, applies **SSS / PhilHealth / Pag-IBIG** from tables, updates **`net_pay`** after those contributions, but **does not** set `taxable_income` / `tax`.

### 3.2 Annual Tax Table (existing DocType)

**Annual Tax Table** (parent) + **Annual Tax Table Item** (child) already model a **graduated bracket** structure:

| Child field | Typical meaning (BIR-style) |
|-------------|-----------------------------|
| `from` | Lower bound of taxable income band (inclusive) |
| `to` | Upper bound of taxable income band (inclusive) |
| `fixed` | Tax due at the lower bound of the band (cumulative base tax) |
| `rate` | Marginal rate (percent) on the excess over `from` |

**Recommended bracket formula** (to implement in one shared function):

\[
\text{tax} = \text{fixed} + \max(0, \text{taxable\_income} - \text{from}) \times \frac{\text{rate}}{100}
\]

when `from <= taxable_income <= to` for the matching row.

**User maintenance:** HR creates a new **Annual Tax Table** document (e.g. code `TRAIN-2026-ANNUAL`), fills **Items** from the official BIR table, marks it **Active** (and deactivates the previous table). Code **never** embeds the numeric brackets.

**Validation (server-side):** on save of **Annual Tax Table**:

- Rows sorted by `from`; no overlapping `(from, to)` ranges; gaps defined as intentional or disallowed per policy.
- Optional: assert `to >= from`, non-negative `fixed`, `rate` in `[0, 100]` (or higher if law allows surcharges—keep configurable).

### 3.3 Other contribution tables (already user-maintained)

- **SSS Table**, **Philhealth Table**, **Pagibig Table** — continue as today; this design only **orders** operations so income tax uses a **consistent base** (see §5).

## 4. Payroll Settings extensions

Extend **Payroll Settings** (Single DocType) with a small **Income tax / withholding** section.

| Field | Type | Purpose |
|-------|------|---------|
| `default_annual_tax_table` | Link → **Annual Tax Table** | Which table to use when none specified on employee. |
| `income_tax_enabled` | Check | Master switch to compute withholding on regular runs. |
| `tax_base_components` | Child table **or** multi-select of stable codes | Same pattern as 13th month: which `Payroll Item` / voucher fields feed **gross taxable compensation** before exemptions (see §5). |
| `withholding_method` | Select | e.g. `Annual_Table_Per_Cycle`, `Monthly_Cumulative` (phase 2), `Manual_Only`. |
| `tax_table_effective_policy` | Select | e.g. `Voucher_Date_To` vs `Payroll_Period_Month` — determines which table row set applies when multiple tables have overlapping effective dates (if you add effective dating). |

**Permissions:** same as existing Payroll Settings (e.g. HR / System Manager).

## 5. Taxable income (gross for withholding)

Before applying **Annual Tax Table** brackets, define **taxable_income** for the **payroll voucher period**.

### 5.1 Component registry (recommended)

Reuse the **controlled codes** approach from the 13th month design, e.g.:

| Code | Maps to | Typical withholding treatment |
|------|---------|-------------------------------|
| `basic_pay` | Sum of `Payroll Item.basic_pay` (+ manual basic) | Usually taxable |
| `overtime_pay` | `Payroll Item.overtime_pay` | Usually taxable |
| `holiday_pay` | `Payroll Item.holiday_pay` | Usually taxable |
| `incentive` | `Payroll Item.incentive` | Often taxable; policy-dependent |

**Excluded by default** (unless policy enables): amounts already statutory or recoveries—e.g. **employer-only** items, or **non-taxable allowances** if you add explicit fields later.

### 5.2 Formula (per voucher, phase 1)

For **Regular** (and optionally **Special**) runs:

\[
\text{taxable\_income}_{\text{voucher}} = \sum_{\text{included codes}} \text{period total for that component}
\]

**13th month runs:** either use a **separate** BIR rule (bonus tax) or a dedicated table; do not blindly reuse the same annual table without payroll/accounting sign-off. The design allows **`run_type`**-specific tax rules in code while still reading **rates from DocTypes**.

### 5.3 Relationship to contributions

Two common policies (pick one and document in Settings):

1. **Taxable income before employee SSS/PhilHealth/Pag-IBIG:** gross compensation only (simpler; matches some internal “gross-up” discussions).
2. **Taxable income after mandatory employee contributions:** subtract `ss_ee + wisp_ee + ph_ee + hd_ee` (or subset) from the gross taxable base **before** bracket lookup, if that matches your BIR withholding method.

The implementation should read the choice from **Payroll Settings** so users can align with their accountant without code changes.

## 6. Withholding tax computation

### 6.1 Annual table per payroll cycle (phase 1)

For each **Payroll Voucher** (regular period):

1. Resolve **Annual Tax Table**: `Employee` override (optional future field) → else **Payroll Settings.default_annual_tax_table** → else single **Active** table (`active = 1`).
2. Compute **taxable_income** per §5.
3. Find the **Annual Tax Table Item** where `from <= taxable_income <= to`.
4. Compute **tax** with the formula in §3.2.
5. Store **`voucher.taxable_income`** and **`voucher.tax`**.
6. Reduce **`net_pay`** by **`voucher.tax`** (in addition to existing contribution deductions).

**Edge cases:**

- **No matching bracket:** do not silently zero tax; **warn** or **throw** with a clear message so users extend the table.
- **Negative or zero taxable income:** tax = 0 (unless future rules add refundable credits—out of scope).

### 6.2 Monthly cumulative withholding (phase 2, optional)

Many PH employers use **cumulative** monthly withholding (tax due YTD minus tax withheld YTD). That requires:

- Storing **per-month** or **per-run** withheld amounts on submitted vouchers.
- Querying **YTD** totals per employee and tax year.
- A **monthly** BIR table DocType (or the same child structure with a `period_type` field).

Keep **phase 1** as **per-voucher** annual-table proration or **full period taxable** as defined in Settings (e.g. “treat voucher taxable income as annualized: `taxable * (12 / n_months)`” is **policy-heavy**—only add if required).

### 6.3 Minimum wage earners (MWE) and exemptions

If **Employee** (or custom fields) marks **MWE** or **no withholding**:

- **Settings** or **Employee** flag skips bracket lookup; set `tax = 0` and optionally still set `taxable_income` for reporting.

This keeps special cases **data-driven** where possible.

## 7. Integration points in code

| Location | Change (conceptual) |
|----------|---------------------|
| `populate_items` (after earnings totals, after contributions) | Call `compute_withholding_tax(voucher)` that sets `taxable_income`, `tax`, and adjusts `net_pay`. |
| `populate_13th_month_voucher` | Either call a **13th-month-specific** tax helper or leave tax manual until rules are defined. |
| New module e.g. `phpayroll.ph_payroll.tax.withholding` | Pure functions: `get_active_tax_table(doc)`, `lookup_bracket(table, taxable)`, `compute_tax_from_bracket(row, taxable)`. |
| **Payroll Settings** | Fields in §4. |
| **Employee** (optional) | Link or select: preferred **Annual Tax Table**, withholding exempt, civil status code for future multi-table support. |

**Tests:** unit tests for bracket math (boundary values: exactly `from`, exactly `to`, between brackets) and for “active table” resolution.

## 8. Auditability and versioning

| Mechanism | Purpose |
|-----------|---------|
| **Annual Tax Table** `code` + `description` | Human-readable label (“BIR RR 8-2018 Annual”). |
| **track_changes** (already on parent) | Know who changed brackets. |
| Optional **`effective_from` / `effective_to`** on **Annual Tax Table** | Support overlapping versions; voucher stores **which table** was used (optional snapshot field `tax_table` on **Payroll Voucher** for reproducibility). |
| Optional child **Payroll Voucher Tax Detail** | Line items: gross base, adjustments, exempt amounts, final taxable, bracket used—only if reports need more than two numbers. |

## 9. Implementation phases

| Phase | Deliverable |
|-------|-------------|
| 1 | **Payroll Settings**: default tax table, tax base component list, contribution adjustment flag; **`compute_withholding_tax`** using **Annual Tax Table**; wire into **`populate_items`**; **`net_pay`** includes tax. |
| 2 | Employee overrides (exempt, table override); validation on **Annual Tax Table** rows; reports for taxable vs tax. |
| 3 | Monthly cumulative withholding; effective dating; 13th month / bonus tax table as separate maintained DocType if needed. |

## 10. Summary

- **User-maintained tax rates** = **Annual Tax Table** (+ future monthly table) child rows: **`from`, `to`, `fixed`, `rate`**, edited by admins when BIR updates guidance.
- **Taxable income** should be **configurable** via **Payroll Settings** using the same **component code** pattern as 13th month, mapped to **Payroll Item** aggregates.
- **Withholding** runs in **`populate_items`** after earnings (and after deciding whether contributions reduce the base), updates **`taxable_income`**, **`tax`**, and **`net_pay`**.
- **SSS, PhilHealth, Pag-IBIG** remain on their existing tables; this design **aligns** income tax with that pattern and keeps legal nuance (MWE, 13th month, cumulative) as **phased**, data-driven extensions.

This document is the functional blueprint for implementing Philippine **compensation withholding tax** in the PH Payroll Frappe app.
