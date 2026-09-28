from pathlib import Path
import pandas as pd

# ===== CONFIGURATION ==============================================================================

input_folder = Path('claims/')
output_folder = Path('output/')

standard_column = [
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

diagnosis_pattern = r'^[A-Z0-9]{3}(\.[0-9]{1,3})?$'

procedure_pattern = r'^\d{5}$'

# ===== EXTRACT ====================================================================================


def extract_file(input_folder):

    files = input_folder.glob('*.csv')

    claims = []

    for file in files:

        df = pd.read_csv(file)
        df['source_file'] = file.name
        df['load_timestamp'] = pd.Timestamp.now()

        claims.append(df)

    return claims

# ==== PROFILING SOURCE FILE ========================================================================


def profile_dataframe(df, file_name):

    print('=' * 80)
    print(f'File name : {file_name}')
    print('=' * 80)

    # SHAPE
    print(f'\nShape: ')
    print(df.shape)

    # BASIC INFORMATION
    print('\nBaic Info : ')
    print(f'\n{df.info()}')

    # MISSING VALUES
    print(f'\nMissing Value : {df.isna().sum()}')

    # DUPLICATES
    print(f'\nDuplicates : {df.duplicated().sum()}')

    # FIRST FEW RECORDS
    print('\nFisrt 5 records')
    print(f'\n{df.head()}')

    # NUMERIC SUMMARY
    print('\nNumeric Describe')
    print(f'\n{df.describe()}')

    # UNIQUE VALUES
    print(f'\nUnique Values:')
    print(df.nunique(dropna=False))


def profile_claims(claims):

    for df in claims:

        file_name = df['source_file'].iloc[0]

        profile_dataframe(df, file_name)


# ==== TRANSFORMATION ================================================================================

def transforms_claims(claims):

    transformed_claims = []

    for df in claims:

        file_name = df['source_file'].iloc[0]

        # COLUMN STANDARDIZATION

        if 'february' in file_name.lower():

            df = df.rename(columns=february_mapping)

        elif 'march' in file_name.lower():

            df = df.rename(columns=march_mapping)

        # DATE STANDARDLIZATION

        expect_format = date_format[file_name]

        df['service_date'] = pd.to_datetime(
            df['service_date'],
            format=expect_format,
            errors="coerce"
        )

        # PROCEDURE CODE DATATYPE

        df['procedure_code'] = df['procedure_code'].astype('string')

        # INCONSISTENT CLAIM STATUS

        df['claim_status'] = df['claim_status'].str.strip().str.title()

        # ALIGN SCHEMA

        for column in standard_column:

            if column not in df.columns:

                df[column] = pd.NA

        # KEEPING STANDARD COLUMN ORDER

        df = df[standard_column]

        transformed_claims.append(df)

    # COMBINE THE TRANSFORMED CLAIMS

    combined_claims = pd.concat(transformed_claims, ignore_index=False)

    # REMOVE DUPLICATES

    combined_claims = combined_claims.drop_duplicates().reset_index(drop=True)

    return combined_claims


# ==== LOAD REERENCIAL TABLE =========================================================================

def load_reference_data():

    # LOADING PROVIDER DATA

    providers = pd.read_csv('providers.csv')

    valid_provider_ids = set(providers['provider_id'].dropna())

    # LOADING MEMBER DATA

    excel_member = pd.ExcelFile('members.xlsx')

    members = []

    for sheet in excel_member.sheet_names:

        df = pd.read_excel('members.xlsx', sheet_name=sheet)
        df['member_type'] = sheet

        members.append(df)

    combined_members = pd.concat(members, ignore_index=True)

    valid_member_ids = set(combined_members['member_id'].dropna())

    return valid_member_ids, valid_provider_ids

# ==== VALIDATION ====================================================================================


def validate_claims(combined_claims, valid_provider_ids, valid_member_ids):

    validation_result = {}

    # MISSING CLAIM ID
    validation_result['missing_claim_id'] = combined_claims['claim_id'].isna()

    # DUPLICATES
    validation_result['duplicate_row'] = combined_claims.duplicated(keep=False)

    # DUPLICATE CLAIM ID

    validation_result['duplicate_claim_id'] = combined_claims['claim_id'].duplicated(
        keep=False)

    # CODES PATTERN CHECK

    validation_result['invalid_procedure_code'] = (
        ~combined_claims['procedure_code'].str.match(
            procedure_pattern, na=False)
    )

    validation_result['invalid_diagnosis_code'] = (
        ~combined_claims['diagnosis_code'].str.match(
            diagnosis_pattern, na=False)
    )

    # REFERENCIAL INTEGRITY CHECK

    validation_result["invalid_provider"] = (
        (~combined_claims["provider_id"].isin(valid_provider_ids))
        &
        (combined_claims["provider_id"].notna())
    )

    validation_result["invalid_member"] = (
        (~combined_claims["member_id"].isin(valid_member_ids))
        &
        (combined_claims["member_id"].notna())
    )

    # NUMERIC COLUMN VALIDATION

    validation_result['paid_greater_than_billed'] = (
        combined_claims['paid_amount'] > combined_claims['billed_amount']
    )

    validation_result['negative_paid_amount'] = (
        combined_claims['paid_amount'] < 0
    )

    validation_result['negative_billed_amount'] = (
        combined_claims['billed_amount'] < 0
    )

    # BUSINESS RULE CHECK

    validation_result['denied_paid_amount'] = (
        (combined_claims['claim_status'] == 'Denied')
        &
        (combined_claims['paid_amount'] > 0)
    )

    validation_result['missing_denied_reason'] = (
        (combined_claims['claim_status'] == 'Denied')
        &
        (combined_claims['denial_reason'].isna())
    )

    return validation_result

# ==== VALIDATION_RESULT ============================================================================


def show_validation_result(validation_result):

    print("\n" + "=" * 90)
    print("VALIDATION RESULTS")
    print("=" * 90)

    for name, result in validation_result.items():

        print(f'\n{name}')
        print(f'{result.sum()} failed')


# ==== CREATE FLAG ===================================================================================


def flag_claims(combined_claims, validation_result):

    flagged_claims = combined_claims.copy()

    flagged_claims['qa_status'] = 'pass'

    flagged_claims['qa_reason'] = ''

    for name, result in validation_result.items():

        flagged_claims.loc[
            result,
            "qa_status"
        ] = 'fail'

        old_reason = flagged_claims.loc[result, "qa_reason"]
        flagged_claims.loc[result, "qa_reason"] = old_reason + name + ';'

    return flagged_claims


# ==== LOAD ==========================================================================================

def load_claims(flagged_claims, output_folder):

    output_folder.mkdir(parents=True, exist_ok=True)

    # full processed dataset

    processed_file = output_folder/'processed_claims.csv'

    flagged_claims.to_csv(processed_file, index=False)

    # QA failed records

    qa_failed_claims = flagged_claims[flagged_claims['qa_status'] == 'fail']

    qa_file = output_folder / 'qa_failes_claims.csv'

    qa_failed_claims.to_csv(qa_file, index=False)

    print(f'\nLoad complete')
    print(f'\nProcessed claims : {processed_file}')
    print(f'Total Processed claims loaded: {len(flagged_claims)}')

    print(f"\nQA failed claims: {qa_file}")
    print(f"QA failed claims loaded: {len(qa_failed_claims)}")


# ==== MAIN ==========================================================================================


def main():

    print(f'\nStarting healthcare claims ETL...')

    # EXTRACT
    print(f'\n1. Extracting files')

    claims = extract_file(input_folder)

    print(f'\nFile extracted : {len(claims)}')

    # PROFILING
    print(f'\n2. Profiling files')

    dataframe_profile = profile_claims(claims)

    print(dataframe_profile)

    # TRANFORM

    print(f'\n3. Transform')

    combined_claims = transforms_claims(claims)

    print(f'\nRows after transformation : {len(combined_claims)}')

    # PROFILE TRANSFORMED DATA

    print(f'\n4. PROFILE TRANSFORMED DATA')

    profile_dataframe(combined_claims, "combined_claims")

    # LOADING REFERENCE DATA

    print(f'\n5. Load reference data')

    valid_member_ids, valid_provider_ids = load_reference_data()

    print(f'Valid member IDs: {len(valid_member_ids)}')

    print(f'Valid provider IDs: {len(valid_provider_ids)}')

    # VALIDATION

    print(f'\n6. Validation')

    validation_result = validate_claims(
        combined_claims, valid_provider_ids, valid_member_ids)

    show_validation_result(validation_result)

    # FLAGGED
    print(f'\n7. Flag')

    flagged_claims = flag_claims(combined_claims, validation_result)

    print('QA status distribution')

    print(
        flagged_claims["qa_status"].value_counts()
    )

    # LOADING DATA

    print(f'\n7. Load')
    load_claims(flagged_claims, output_folder)


if __name__ == "__main__":
    main()
