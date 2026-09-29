# Healthcare Claims ETL & Data Quality Pipeline

A Python-based ETL and data-quality project built around a practice **US healthcare claims dataset**.

The project demonstrates how to build a reusable pipeline that extracts claims data from multiple source files, standardizes inconsistent schemas and formats, validates data quality using business rules, and produces QA-ready outputs.

---

## 📌 Project Overview

Healthcare claims data often comes from multiple sources with differences in:

- Column names
- Data types
- Date formats
- Status formatting
- Missing fields
- Duplicate records
- Identifier consistency

This project simulates that environment using three monthly claims files and separate member/provider reference data.

The pipeline transforms these different source files into a standardized claims dataset and applies row-level data-quality validation.

### Pipeline

```text
Source Files
     ↓
Extraction
     ↓
Data Profiling
     ↓
Transformation / Cleaning
     ↓
Validation
     ↓
QA Flagging
     ↓
Processed + QA Outputs
```

---

## 📂 Dataset

### Monthly Claims

| Source        |    Rows |
| ------------- | ------: |
| January 2026  |      46 |
| February 2026 |      40 |
| March 2026    |      43 |
| **Total**     | **129** |

After removing 2 exact duplicate rows:

**127 transformed claim records**

### Reference Data

| File            |                    Records |
| --------------- | -------------------------: |
| `providers.csv` |               12 providers |
| `members.xlsx`  | 30 members across 2 sheets |

---

## 🔄 What the Pipeline Does

### 1. Extract

The pipeline:

- Reads all monthly CSV claim files
- Loads provider reference data
- Loads both member Excel sheets
- Preserves the original source filename
- Adds a pipeline `load_timestamp`

The `source_file` column provides basic source-level data lineage.

---

### 2. Profile

Each source file is profiled before transformation.

The profiling process checks:

- Dataset shape
- Column names
- Data types
- Missing values
- Duplicate records
- Sample records
- Unique values
- Numeric distributions

This step helps identify source-specific problems before transformation begins.

---

### 3. Transform

The source files contain different schemas.

For example:

```text
February:
ClaimID
MemberID
ProviderID
ServiceDate
DiagnosisCode
ProcedureCode
BilledAmount
PaidAmount
ClaimStatus
```

while March contains fields such as:

```text
rendering_provider
diag_code
proc_code
billed_amt
paid_amt
status
```

These fields are mapped into a common target schema:

```text
claim_id
member_id
provider_id
service_date
diagnosis_code
procedure_code
claim_type
billed_amount
paid_amount
claim_status
denial_reason
source_file
load_timestamp
```

---

## 🧹 Data Standardization

### Date Standardization

The source files use different date formats:

```text
January → YYYY-MM-DD
February → MM/DD/YYYY
March → YYYY-MM-DD
```

Each source is parsed using its appropriate format and converted to pandas datetime.

Invalid values are converted to `NaT` so they can be identified during QA.

### Procedure Code

`procedure_code` is converted from integer representation to string because it is an identifier rather than a numeric measure.

### Claim Status

Claim statuses are standardized by:

- Removing leading/trailing whitespace
- Applying consistent title case

Example:

```text
denied
DENIED
 Denied
```

becomes:

```text
Denied
```

---

# 🔍 Data Quality Checks

The pipeline performs row-level validation using Boolean validation rules.

### Validation Rules

| Validation                           | Result |
| ------------------------------------ | -----: |
| Missing `claim_id`                   |      0 |
| Duplicate `claim_id`                 |      2 |
| Invalid procedure code               |      0 |
| Invalid diagnosis code               |      0 |
| Invalid provider ID                  |      0 |
| Invalid member ID                    |      0 |
| `paid_amount > billed_amount`        |      3 |
| Negative `paid_amount`               |      0 |
| Negative `billed_amount`             |      3 |
| Denied claim with paid amount > 0    |      0 |
| Denied claim missing `denial_reason` |     37 |

---

## ⚠️ Important Data Quality Findings

### Exact duplicates

Two exact duplicate rows were identified and removed during transformation.

```text
129 source rows
      ↓
2 exact duplicates removed
      ↓
127 transformed rows
```

### Conflicting duplicate claim ID

A `claim_id` appeared in two records with different claim-level information, including:

- Member
- Provider
- Service date
- Diagnosis code
- Procedure code

These records were **not automatically deleted**.

Instead, both records were retained and flagged for review.

### Negative billed amounts

3 claims contained negative `billed_amount` values.

These records were retained but flagged as QA failures.

### Paid amount greater than billed amount

3 claims had:

```text
paid_amount > billed_amount
```

These records were also retained and flagged for review.

### Missing denial reason

`denial_reason` is only expected when a claim is denied.

Therefore, the pipeline does not treat every missing `denial_reason` as an error.

The validation specifically checks:

```text
claim_status = Denied
AND
denial_reason is missing
```

This resulted in **37 QA failures**.

---

# 📊 QA Results

After applying all validation rules:

| QA Status | Records |
| --------- | ------: |
| Pass      |      88 |
| Fail      |      39 |
| **Total** | **127** |

The validation-rule counts should not be added together because one claim can fail multiple rules.

For example, a single claim may have both a negative billed amount and a duplicate claim ID.

---

# 📤 Outputs

The pipeline produces two primary outputs.

### `processed_claims.csv`

Contains the standardized claims dataset together with QA status and QA reason information.

### `qa_failed_claims.csv`

Contains claims that failed at least one validation rule.

Each failed record includes the reason(s) for the QA failure.

Example:

```text
qa_status = fail
qa_reason = duplicate_claim_id;negative_billed_amount;
```

---

# 🧠 Key Data Engineering Concepts Demonstrated

This project focuses on practical concepts used in ETL and data-quality workflows:

- Multi-source data extraction
- Schema standardization
- Source-specific transformations
- Data profiling
- Data type standardization
- Date parsing
- Duplicate handling
- Data validation
- Business-rule validation
- Referential integrity
- Conditional validation
- Row-level QA flagging
- Source lineage
- QA reporting
- Clean output generation

---

# 🎯 Project Objective

The goal of this project is not simply to clean a dataset.

It demonstrates the ability to build a pipeline that can answer:

> **What data came in, what was different about the sources, what did we change, what quality problems did we find, how did we handle them, and what records still require review?**

This approach is designed to reflect a practical healthcare data analytics / ETL workflow rather than a simple pandas data-cleaning exercise.

---

# 📚 Documentation

For a detailed explanation of the transformations, validation rules, data-quality findings, and QA decisions, see:

**`Healthcare_documentation.pdf`**
