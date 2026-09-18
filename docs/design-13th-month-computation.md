# Design: 13th Month Pay Computation

This document describes how **13th month pay** (Philippines) should be computed in PH Payroll, and how **Payroll Settings** will let administrators choose which **income items** count toward that computation.

## 1. Business context

Under **Presidential Decree No. 851** (as amended), covered employers must pay rank-and-file employees a **13th month benefit** not later than 24 December each year. The statutory minimum is **one-twelfth (1/12)** of the employee’s **total basic salary earned** for the calendar year.

In practice, employers and HR teams need:

- A **clear calendar-year basis** (typically 1 January–31 December).
- A **configurable definition** of what counts as income for 13th month (basic only vs inclusion of certain pay types), aligned with internal policy and legal advice.
- **Auditability**: which vouchers and line items were summed, for which period.

This design keeps the legal minimum in mind while making **inclusion rules data-driven** via Payroll Settings.

## 2. Goals

| Goal | Description |
|------|-------------|
| Configurable base | Payroll admins define which income components are included in the 13th month base. |
| Same document as payroll | **13th month** is stored on **Payroll Voucher**, distinguished by **Run Type**, not a separate pay document type. |
| Triggered run | **Run 13th Month** (list action) creates/updates vouchers the same way **Run Payroll** does for regular cycles. |
| Reproducible runs | Explicit period (typically calendar year), stored amount in **`thirteenth_month_pay`**, auditable from voucher. |
| Frappe-native | **Payroll Settings** + server-side aggregation; **Run Type** drives which code path runs (`populate_items` vs 13th month aggregation). |

## 2.1 Payroll Voucher — Run Type and 13th month field

**Payroll Voucher** is extended so every run is classified and 13th month results have a dedicated column.

### Field: `run_type` (Select, required)

Identifies how the voucher was produced and which computation applies.

| Option | Meaning |
|--------|---------|
| **Regular** | Normal payroll period: time logs, incentives, statutory deductions, etc. (today’s default behavior). |
| **13th Month** | Voucher created by **Run 13th Month**: no daily attendance engine; amount comes from **annual aggregation** ÷ 12 (or policy), using Payroll Settings income rules. |
| **Special** | Other non-regular runs (bonuses, adjustments, one-offs) — same DocType and permissions as regular payroll, but **do not** use the regular daily `populate_items` path unless explicitly configured. |

**Default:** `Regular` on new manual vouchers. Vouchers created by **Run Payroll** set `run_type = Regular`. Vouchers created by **Run 13th Month** set `run_type = 13th Month`.

**Frappe Select options (example):** store stable values exactly as used in Python filters, e.g. `Regular`, `13th Month`, `Special` (labels can match values for clarity).

### Field: `thirteenth_month_pay` (Currency)

- Stores the **computed 13th month pay amount** for this voucher when `run_type = 13th Month`.
- For **Regular** and **Special** runs, keep **0** or leave blank (hide in form when not applicable, optional).
- **Net pay** for a 13th month voucher should be driven by policy (often **13th month amount minus tax/withholding** if applicable); document whether `net_pay` equals `thirteenth_month_pay` in phase 1 or after deductions.

**UI:** place `run_type` near **Date From / Date To** (or branch) so users see run context immediately; place `thirteenth_month_pay` in the earnings summary section with a short description: “Computed 13th month (Run Type = 13th Month).”

## 3. Current model (reference)

Today, recurring pay is captured on **Payroll Voucher** with child **Payroll Item** rows. Relevant **currency fields on Payroll Item** include:

- `basic_pay`
- `overtime_pay`
- `holiday_pay`
- `incentive`
- `cash_advance` (typically a recovery/advance, not “earned salary”—usually **excluded** from 13th month by policy)
- `net_sales` (context-dependent)

Voucher-level fields include aggregates such as `total_basic_pay`, `total_overtime_pay`, `total_holiday_pay`, `total_incentive`, and `taxable_income`.

**Design principle:** 13th month aggregation should sum **only components that Payroll Settings marks as included**, mapped to the corresponding fields on **Payroll Item** (and optionally voucher-level totals if ever needed for adjustments).

## 3.1 How Run 13th Month is triggered (mirror Run Payroll)

Today, **Run Payroll** on the **Payroll Voucher** list opens a prompt (**Date From**, **Date To**, **Branch**) and calls a whitelisted method that loops **Active** employees for that branch and **get_or_create_payroll_voucher** + **populate_items**.

**Run 13th Month** follows the **same UX and server pattern**:

1. **List view:** add menu item **Run 13th Month** on **Payroll Voucher** (alongside **Run Payroll**).
2. **Prompt fields (minimum):**
   - **Calendar year** (Int or Date interpreted as year) **or** **Date From / Date To** spanning the accrual year (e.g. 2026-01-01 → 2026-12-31).
   - **Branch** (Link: Branch), same as regular run.
   - Optional: **Payment date / voucher period** — if the voucher’s `date_from` / `date_to` should represent the **payout window** (e.g. December only) while the **accrual year** is separate, add two explicit fields: `accrual_year` (or accrual from/to) vs voucher dates; otherwise use one year for both accrual lookup and voucher period for simplicity in phase 1.
3. **Server method (e.g. `run_13th_month`):**
   - Resolve employee set: same filter as `run_payroll` (`Employee` Active, `reporting_branch`).
   - For each employee: **get or create Payroll Voucher** with **`run_type = 13th Month`**, branch, and chosen dates.
   - **Populate** the voucher using the **13th month pipeline** (not `populate_items`):
     - Query **Regular** (and optionally **Special**) vouchers in the accrual period per §6; sum configured income components.
     - Set **`thirteenth_month_pay`** = computed amount (and set **`net_pay`** per policy).
   - **Save** the voucher (`ignore_permissions` pattern may match existing `run_payroll`).

4. **Recompute:** extend **Recompute Payroll** on the form (draft only) so that if `run_type == 13th Month`, it calls **`recompute_13th_month_voucher`** (or branches inside one recompute method) instead of **`populate_items`**.

**Important:** the trigger **creates the same DocType** (**Payroll Voucher**); only **`run_type`** and the **13th month population logic** differ from **Run Payroll**.

## 3.2 Voucher creation, overlap, and naming (must include `run_type`)

Refactor **`get_or_create_payroll_voucher`** (or add parallel **`get_or_create_payroll_voucher_for_run`**) to accept **`run_type`** and set it on new documents. **Run Payroll** passes `Regular`; **Run 13th Month** passes `13th Month`.

Existing logic finds an **exact match** on employee, branch, `date_from`, `date_to`. For 13th month, **add `run_type` to all uniqueness and overlap filters**:

- **Exact match:** employee + branch + `date_from` + `date_to` + **`run_type`** → reuse and recompute.
- **Overlap:** two vouchers **overlap** only if they share the same **`run_type`** (and employee). A **Regular** voucher for 1–15 Dec must **not** block a **13th Month** voucher whose dates also fall in December for the same employee.

**Autoname:** current pattern `{employee} {date_to}` can **collide** when both Regular and 13th Month vouchers share the same `date_to`. Options (pick one in implementation):

- Append run type or year: e.g. `{employee}-{date_to}-{run_type}` or `{employee}-13th-{calendar_year}`.
- Or use **Naming Series** per `run_type` (separate series for 13th month).

Document the chosen rule in the DocType description field.

## 4. Payroll Settings — new / extended configuration

Introduce or extend a **Single DocType** named **Payroll Settings** (module: PH Payroll) with the following conceptual structure.

### 4.1 Section: 13th month

| Field | Type | Purpose |
|-------|------|---------|
| `enable_13th_month` | Check | Master switch for features (reports, validations, optional UI hints). |
| `thirteenth_month_calendar_year` | Check (default on) | If enabled, period is strictly calendar year; if off, allow custom `from`/`to` per run (advanced). |
| `thirteenth_month_payment_month` | Int / Select | e.g. December; used for reminders / due-date logic only. |

### 4.2 Child table: Included income items

**Table name (suggested):** `13th Month Income Items` (or `payroll_settings_13th_month_item`)

Each row identifies **one** income component that contributes to the 13th month **base** (before dividing by 12).

| Field | Type | Purpose |
|-------|------|---------|
| `income_component` | Link **or** Select | Stable code for the component (see §5). |
| `include_in_13th_month` | Check (default on) | If rows are used only for inclusion, this can be omitted; otherwise allows explicit exclude. |
| `notes` | Small Text | Optional admin note (e.g. “Approved by HR 2026”). |

**Alternative (simpler UI):** a **Multi Select** field listing all allowed components, if the list is small and fixed. The child table is preferable when you need ordering, effective dating, or per-component notes later.

### 4.3 Permissions

- **System Manager** / **HR Manager**: maintain Payroll Settings.
- Other roles: read-only or no access, depending on existing HR security model.

## 5. Income component registry

To avoid fragile string matching on labels, define a **controlled set of codes** that map to Payroll Item (and voucher) fields.

**Suggested codes** (align with `Payroll Item`):

| Code | Maps to | Typical 13th month treatment |
|------|---------|-------------------------------|
| `basic_pay` | `Payroll Item.basic_pay` | Almost always **included** (core of PD 851). |
| `overtime_pay` | `Payroll Item.overtime_pay` | Policy-dependent; often included if treated as part of regular compensation. |
| `holiday_pay` | `Payroll Item.holiday_pay` | Policy-dependent. |
| `incentive` | `Payroll Item.incentive` | Policy-dependent; may be excluded if purely discretionary. |
| `net_sales` | `Payroll Item.net_sales` | Only if policy treats it as salary-related; often excluded. |
| `cash_advance` | `Payroll Item.cash_advance` | Usually **excluded** (not earned salary). |

Optional extension: add codes for **voucher-level adjustments** (e.g. manual corrections) if those fields exist or are added later—only if business requires including posted adjustments in the annual base.

**Implementation note:** a small Python dict or module constant `THIRTEENTH_MONTH_FIELD_MAP` should map `income_component` → `(parent_doctype, fieldname)` for use in aggregation queries.

## 6. Computation specification

### 6.1 Period

- **Default:** calendar year **Y**: `date_from >= Y-01-01` and `date_to <= Y-12-31` on **Payroll Voucher**, or overlap rules as defined (see §6.3).
- Vouchers whose period falls **partially** inside the year should either be **prorated by days** or **included in full** if the entire voucher lies inside the year—this must be an explicit **setting** (recommended: include voucher if `date_from` and `date_to` are both within the calendar year, or prorate by intersection days for stricter accuracy).

### 6.2 Formula (statutory-style)

For each employee and calendar year:

\[
\text{13th month (minimum statutory style)} = \frac{1}{12} \times \sum (\text{included income amounts for year})
\]

Where the sum is over all **Payroll Item** rows belonging to payroll vouchers in scope with **`run_type = Regular`** (and optionally **`Special`** if policy says those earnings count), **excluding** vouchers with **`run_type = 13th Month`** to avoid circular references. Sum only fields whose code appears in Payroll Settings → included income items. **Submitted-only** restriction applies if the site uses submission for payroll vouchers.

### 6.3 Voucher inclusion rules

Precisely define one of:

1. **Voucher end date in year:** include voucher if `date_to` falls in calendar year Y.  
2. **Overlap:** include if `[date_from, date_to]` intersects Y.  
3. **Accrual by item date:** sum `Payroll Item.date` within Y (most accurate for daily rows).

**Recommendation:** use **Payroll Item.date** within the calendar year when populated; otherwise fall back to voucher `date_from`/`date_to` intersection with Y. Document the chosen rule in the same Settings screen (short help text).

### 6.4 Caps and floors

- Statutory rules may interact with **minimum wage** and **total benefit** caps in specific cases; any cap should be a **separate setting** or documented as out of scope until legal requirements are encoded.

### 6.5 Pro-rated employment

Employees who **started mid-year** or **left mid-year** typically receive a **pro-rated** 13th month based on **months or days** in service within the year. Support as a **second phase**:

- Parameter: `pro_rate_by` = `None` | `months` | `days`.
- Use Employee `date_of_joining` and (if applicable) relieving date.

Phase 1 can compute **full sum of included pay** for the year; HR applies proration manually, or Phase 2 automates it.

## 7. Outputs (implementation phases)

| Phase | Deliverable |
|-------|-------------|
| 1 | **Payroll Voucher** fields: `run_type`, `thirteenth_month_pay`; **get_or_create** / overlap updated to include `run_type`; **autoname** safe across run types. |
| 2 | **Payroll Settings** + **`run_13th_month`** + list action **Run 13th Month**; 13th month populate + **Recompute** branch for `run_type = 13th Month`. |
| 3 | Optional report: breakdown of annual base by component; pro-ration; export / statutory minimum checks. |

**Note:** A separate **13th Month Pay** DocType is **not required** if **Payroll Voucher** with **`run_type = 13th Month`** and **`thirteenth_month_pay`** is the payment record; use workflow/submit on the same voucher as regular payroll.

## 8. Edge cases checklist

- **Multiple vouchers** in the same period for the same employee: prevent double count; **overlap rules must be scoped by `run_type`** so Regular and 13th Month can coexist for related dates.
- **Second 13th month run** for the same year: exact match on employee + branch + dates + **`run_type = 13th Month`** updates the same voucher; overlapping 13th month vouchers for the same year should be rejected or use distinct date ranges per policy.
- **Amended vouchers:** recompute or freeze annual figures when amendment occurs (depends on submit/cancel workflow).
- **Negative or adjustment lines:** define whether negative `basic_pay` (if allowed) reduces the base.
- **Inter-branch transfers:** employee key is `Employee`; branch on voucher should not split statutory entitlement without explicit policy.

## 9. Summary

- **`run_type`** on **Payroll Voucher** (**Regular** | **13th Month** | **Special**) identifies the run; **Run Payroll** sets Regular; **Run 13th Month** creates/updates vouchers with **13th Month**.
- **`thirteenth_month_pay`** stores the computed 13th month amount on those vouchers; Regular/Special typically leave it unused.
- **Run 13th Month** (list menu) triggers the same **create/update voucher per employee** pattern as **Run Payroll**, but runs the **annual aggregation** pipeline and must **not** use the daily **`populate_items`** path.
- **Payroll Settings** holds **`enable_13th_month`** and configurable **included income components**; source data for aggregation comes from **Regular** (and optionally **Special**) vouchers only.
- **Uniqueness and overlap** always include **`run_type`**; **autoname** must avoid collisions between Regular and 13th month vouchers.

This document is the functional blueprint for implementation in the PH Payroll Frappe app.
