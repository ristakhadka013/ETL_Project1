from pathlib import Path

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

claims_folder = Path("claims/")
output_folder = Path("output/")

standard_columns = [
    "claim_id",
    "member_id",
    "provider_id",
    "service_date",
    "diagnosis_code",
    "procedure_code",
    "claim_type",
    "billed_amount",
    "paid_amount",
    "claim_status",
    "denial_reason",
    "source_file",
    "load_timestamp"
]

february_mapping = {
    "ClaimID": "claim_id",
    "MemberID": "member_id",
    "ProviderID": "provider_id",
    "ServiceDate": "service_date",
    "DiagnosisCode": "diagnosis_code",
    "ProcedureCode": "procedure_code",
    "BilledAmount": "billed_amount",
    "PaidAmount": "paid_amount",
    "ClaimStatus": "claim_status"
}

march_mapping = {
    "rendering_provider": "provider_id",
    "diag_code": "diagnosis_code",
    "proc_code": "procedure_code",
    "billed_amt": "billed_amount",
    "paid_amt": "paid_amount",
    "status": "claim_status"
}

date_format = {
    "claims_january_2026.csv": "%Y-%m-%d",
    "claims_february_2026.csv": "%m/%d/%Y",
    "claims_march_2026.csv": "%Y-%m-%d"
}

diagnosis_pattern = r"^[A-Z0-9]{3}(\.[0-9]{1,3})?$"

procedure_pattern = r"^\d{5}$"


# ============================================================
# 1. EXTRACT
# ============================================================

def extract_claims(claims_folder):

    files = claims_folder.glob("*.csv")

    claims = []

    for file in files:

        df = pd.read_csv(file)

        # Data lineage
        df["source_file"] = file.name

        # Load timestamp
        df["load_timestamp"] = pd.Timestamp.now()

        claims.append(df)

    return claims

# ============================================================
# 2. DATA PROFILING
# ============================================================


def profile_dataframe(df, file_name):

    print("\n" + "=" * 90)
    print(f"DATA PROFILE: {file_name}")
    print("=" * 90)

    # Shape
    print("\nShape:")
    print(df.shape)

    # Basic information
    print("\nInformation:")
    print(df.info())

    # Missing values
    print("\nMissing Values:")
    print(df.isna().sum())

    # First few records
    print("\nHead:")
    print(df.head())

    # Duplicate rows
    print("\nDuplicate Rows:")
    print(df.duplicated().sum())

    # Numeric summary
    print("\nDescribe:")
    print(df.describe())

    # Unique values
    print("\nUnique Values:")
    print(df.nunique(dropna=False))

    # Categorical values
    print("\nCategorical Values:")

    categorical_columns = [
        "claim_status",
        "claim_type"
    ]

    for column in categorical_columns:

        if column in df.columns:

            print(f"\n{column}:")
            print(
                df[column]
                .value_counts(dropna=False)
            )


def profile_claims(claims):

    for df in claims:

        file_name = df["source_file"].iloc[0]

        profile_dataframe(
            df,
            file_name
        )

    return claims


# ============================================================
# 3. TRANSFORMATION
# ============================================================

def transform_claims(claims):

    transformed_claims = []

    for df in claims:

        file_name = df["source_file"].iloc[0]

        # ----------------------------------------------------
        # Standardize column names
        # ----------------------------------------------------

        if "february" in file_name.lower():

            df = df.rename(
                columns=february_mapping
            )

        elif "march" in file_name.lower():

            df = df.rename(
                columns=march_mapping
            )

        # ----------------------------------------------------
        # Standardize date
        # ----------------------------------------------------

        df["service_date"] = pd.to_datetime(
            df["service_date"],
            format=date_format[file_name],
            errors="coerce"
        )

        # ----------------------------------------------------
        # Align schema
        # ----------------------------------------------------

        for column in standard_columns:

            if column not in df.columns:

                df[column] = pd.NA

        # ----------------------------------------------------
        # Standardize procedure code
        # ----------------------------------------------------

        df["procedure_code"] = (
            df["procedure_code"]
            .astype("string")
        )

        # ----------------------------------------------------
        # Standardize claim status
        # ----------------------------------------------------

        df["claim_status"] = (
            df["claim_status"]
            .str.strip()
            .str.title()
        )

        # ----------------------------------------------------
        # Keep standard column order
        # ----------------------------------------------------

        df = df[standard_columns]

        transformed_claims.append(df)

    # --------------------------------------------------------
    # Combine all files
    # --------------------------------------------------------

    combined_claims = pd.concat(
        transformed_claims,
        ignore_index=True
    )

    # --------------------------------------------------------
    # Remove exact duplicate records
    # --------------------------------------------------------

    combined_claims = (
        combined_claims
        .drop_duplicates()
        .reset_index(drop=True)
    )

    return combined_claims


# ============================================================
# 4. REFERENCE DATA
# ============================================================

def load_reference_data():

    # --------------------------------------------------------
    # Provider master
    # --------------------------------------------------------

    providers = pd.read_csv(
        "providers.csv"
    )

    valid_provider_ids = set(
        providers["provider_id"]
        .dropna()
    )

    # --------------------------------------------------------
    # Member master
    # --------------------------------------------------------

    excel_member = pd.ExcelFile(
        "members.xlsx"
    )

    members = []

    for sheet in excel_member.sheet_names:

        df = pd.read_excel(
            "members.xlsx",
            sheet_name=sheet
        )

        df["member_type"] = sheet

        members.append(df)

    combined_members = pd.concat(
        members,
        ignore_index=True
    )

    valid_member_ids = set(
        combined_members["member_id"]
        .dropna()
    )

    return valid_member_ids, valid_provider_ids


# ============================================================
# 5. VALIDATION
# ============================================================

def validate_claims(
    claims,
    valid_member_ids,
    valid_provider_ids
):

    validation_results = {}

    # --------------------------------------------------------
    # Missing required fields
    # --------------------------------------------------------

    validation_results["missing_member_id"] = (
        claims["member_id"].isna()
    )

    validation_results["missing_service_date"] = (
        claims["service_date"].isna()
    )

    validation_results["missing_claim_type"] = (
        claims["claim_type"].isna()
    )

    validation_results["missing_denial_reason"] = (
        claims["denial_reason"].isna()
    )

    # --------------------------------------------------------
    # Duplicate claim ID
    # --------------------------------------------------------

    validation_results["duplicate_claim_id"] = (
        claims["claim_id"]
        .duplicated(keep=False)
    )

    # --------------------------------------------------------
    # Diagnosis and procedure code
    # --------------------------------------------------------

    validation_results["invalid_diagnosis"] = (
        ~claims["diagnosis_code"].str.match(
            diagnosis_pattern, na=False
        )
    )

    validation_results['invalid_procedure'] = (
        ~claims['procedure_code'].str.match(
            procedure_pattern, na=False
        )
    )

    # --------------------------------------------------------
    # numeric checks
    # --------------------------------------------------------

    validation_results["paid_greater_than_billed"] = (
        claims["paid_amount"]
        > claims["billed_amount"]
    )

    validation_results["negative_billed_amount"] = (
        claims["billed_amount"] < 0
    )

    validation_results["negative_paid_amount"] = (
        claims["paid_amount"] < 0
    )

    # --------------------------------------------------------
    # Denial business rule
    # --------------------------------------------------------

    validation_results["denied_missing_reason"] = (
        (claims["claim_status"] == "Denied")
        & (claims["denial_reason"].isna())
    )

    validation_results["denied_paid_amount"] = (
        (claims['claim_status'] == "Denied")
        & (claims['paid_amount'] > 0)
    )

    # --------------------------------------------------------
    # Referential integrity
    # --------------------------------------------------------

    validation_results["invalid_provider"] = (
        ~claims["provider_id"].isin(
            valid_provider_ids
        )
        & claims["provider_id"].notna()
    )

    validation_results["invalid_member"] = (
        ~claims["member_id"].isin(
            valid_member_ids
        )
        & claims["member_id"].notna()
    )

    return validation_results


# ============================================================
# 6. SHOW VALIDATION RESULTS
# ============================================================

def show_validation_results(validation_results):

    print("\n" + "=" * 90)
    print("VALIDATION RESULTS")
    print("=" * 90)

    for name, result in validation_results.items():

        print(
            f"{name}: "
            f"{result.sum()} failed"
        )


# ============================================================
# 7. FLAG
# ============================================================

def flag_claims(
    claims,
    validation_results
):

    flagged_claims = claims.copy()

    # --------------------------------------------------------
    # Create overall QA status
    # --------------------------------------------------------

    flagged_claims["qa_status"] = "PASS"

    # --------------------------------------------------------
    # Create QA reason
    # --------------------------------------------------------

    flagged_claims["qa_reason"] = ""

    for name, result in validation_results.items():

        flagged_claims.loc[
            result,
            "qa_status"
        ] = "FAIL"

        flagged_claims.loc[
            result,
            "qa_reason"
        ] = (
            flagged_claims.loc[
                result,
                "qa_reason"
            ]
            + name
            + "; "
        )

    return flagged_claims


# ============================================================
# 8. LOAD
# ============================================================

def load_claims(flagged_claims, output_folder):

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Full processed dataset
    # --------------------------------------------------------

    processed_file = (
        output_folder
        / "processed_claims.csv"
    )

    flagged_claims.to_csv(
        processed_file,
        index=False
    )

    # --------------------------------------------------------
    # QA failed records
    # --------------------------------------------------------

    qa_failed_claims = flagged_claims[
        flagged_claims["qa_status"] == "FAIL"
    ]

    qa_file = (
        output_folder
        / "qa_failed_claims.csv"
    )

    qa_failed_claims.to_csv(
        qa_file,
        index=False
    )

    print("\n" + "=" * 60)
    print("LOAD COMPLETE")
    print("=" * 60)

    print(
        f"Processed claims: "
        f"{processed_file}"
    )

    print(
        f"QA failed claims: "
        f"{qa_file}"
    )

    print(
        f"Total records loaded: "
        f"{len(flagged_claims)}"
    )

    print(
        f"QA failed records: "
        f"{len(qa_failed_claims)}"
    )


# ====MAIN PIPELINE========================================================


def main():

    print("\nStarting Healthcare Claims ETL")

    # ========================================================
    # 1. EXTRACT
    # ========================================================

    print("\n[1] EXTRACT")

    claims = extract_claims(
        claims_folder
    )

    print(
        f"Files extracted: {len(claims)}"
    )

    # ========================================================
    # 2. PROFILE SOURCE DATA
    # ========================================================

    print("\n[2] PROFILE SOURCE DATA")

    profile_claims(claims)

    # ========================================================
    # 3. TRANSFORM
    # ========================================================

    print("\n[3] TRANSFORM")

    combined_claims = transform_claims(
        claims
    )

    print(
        f"Rows after transformation: "
        f"{len(combined_claims)}"
    )

    # ========================================================
    # 4. PROFILE TRANSFORMED DATA
    # ========================================================

    print("\n[4] PROFILE TRANSFORMED DATA")

    profile_dataframe(
        combined_claims,
        "combined_claims"
    )

    # ========================================================
    # 5. LOAD REFERENCE DATA
    # ========================================================

    print("\n[5] LOAD REFERENCE DATA")

    valid_member_ids, valid_provider_ids = (
        load_reference_data()
    )

    print(
        f"Valid member IDs: "
        f"{len(valid_member_ids)}"
    )

    print(
        f"Valid provider IDs: "
        f"{len(valid_provider_ids)}"
    )

    # ========================================================
    # 6. VALIDATE
    # ========================================================

    print("\n[6] VALIDATE")

    validation_results = validate_claims(
        combined_claims,
        valid_member_ids,
        valid_provider_ids
    )

    # ========================================================
    # REVIEW VALIDATION RESULTS
    # ========================================================

    show_validation_results(
        validation_results
    )

    # ========================================================
    # 7. FLAG
    # ========================================================

    print("\n[7] FLAG")

    flagged_claims = flag_claims(
        combined_claims,
        validation_results
    )

    print(
        "QA status distribution:"
    )

    print(
        flagged_claims["qa_status"]
        .value_counts()
    )

    # ========================================================
    # 8. LOAD
    # ========================================================

    print("\n[8] LOAD")

    load_claims(
        flagged_claims,
        output_folder
    )


# ====RUN========================================================

if __name__ == "__main__":
    main()
