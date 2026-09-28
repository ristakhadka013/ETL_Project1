from pathlib import Path
import pandas as pd

pd.set_option("display.max_columns", None)

# Reading multiple data at once
folder = Path('claims/')
files = folder.glob('*.csv')

# checking whether claims folder it there or not
"""print(folder.exists())
print(folder.is_dir())
print(list(folder.iterdir())) """

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
    'ClaimID': 'claim_id',
    'MemberID': 'member_id',
    'ProviderID': 'provider_id',
    'ServiceDate': 'service_date',
    'DiagnosisCode': 'diagnosis_code',
    'ProcedureCode': 'procedure_code',
    'BilledAmount': 'billed_amount',
    'PaidAmount': 'paid_amount',
    'ClaimStatus': 'claim_status',
    'source_file': 'source_file'
}

march_mapping = {
    'rendering_provider': 'provider_id',
    'diag_code': 'diagnosis_code',
    'proc_code': 'procedure_code',
    'billed_amt': 'billed_amount',
    'paid_amt': 'paid_amount',
    'status': 'claim_status'
}

date_format = {
    'claims_january_2026.csv': '%Y-%m-%d',
    'claims_february_2026.csv': '%m/%d/%Y',
    'claims_march_2026.csv': '%Y-%m-%d'
}

claims = []

# reading each csv file in data frame
for file in files:
    df = pd.read_csv(file)
    df['source_file'] = file.name
    df['load_timestamp'] = pd.Timestamp.now()

    # checking whether the column name is consistent in all files
    """print(f'\n {file.name}')
    print(df.columns.to_list())"""

    # column standardization
    if 'jan' in file.name.lower():
        pass
    elif 'feb' in file.name.lower():
        df = df.rename(columns=february_mapping)
    elif 'mar' in file.name.lower():
        df = df.rename(columns=march_mapping)

    # date standardization
    expeceted_date_format = date_format[file.name]

    df['service_date'] = pd.to_datetime(
        df['service_date'],
        format=expeceted_date_format,
        errors="coerce"
    )

    # checking which date is invalid and got NAT
    """print(
        df.loc[
            (df['service_date'].notna()) & (df['parsed_date'].isna()),
            'service_date'
        ].head()
    )"""

    # creating new column for each table, which doesnot have standard columns
    for column in standard_columns:
        if column not in df.columns:
            df[column] = pd.NA

    # append each df in empty list
    claims.append(df)

# concating all the tables from claims in one table
combined_claims = pd.concat(claims, ignore_index=True)
"""print(combined_claims.head())"""
# ======== Data Quality check ===============================================================

# null check

missing_value = combined_claims.isna().sum()
for column, count in missing_value.items():
    if count > 0:
        """ print(f'{column} : {count}')"""

# output :
# member_id : 3 missing values
# service_date : 2 missing values
# claim_type : 40 missing values
# denial_reason : 124 missing values

missing_member_id = combined_claims[combined_claims['member_id'].isna()]
combined_claims['missing_member_id'] = combined_claims['member_id'].isna()
"""print(combined_claims['missing_member_id'].value_counts())"""

missing_service_date = combined_claims[combined_claims['service_date'].isna()]
combined_claims['missing_service_date'] = combined_claims['service_date'].isna()
"""print(combined_claims['missing_service_date'].value_counts())"""

missing_claim_type = combined_claims[combined_claims['claim_type'].isna()]
combined_claims['missing_claim_type'] = combined_claims['claim_type'].isna()
"""print(combined_claims['missing_claim_type'].value_counts())"""

missing_denial_reason = combined_claims[combined_claims['denial_reason'].isna(
)]
"""print(combined_claims.loc[
    (combined_claims["claim_status"] == "Denied") &
    (combined_claims["denial_reason"].isna()),
    [
        'claim_status',
        'denial_reason'
    ]
].shape)"""
combined_claims['missing_denial_reason'] = (
    (combined_claims["claim_status"] == "Denied") &
    (combined_claims["denial_reason"].isna())
)
"""print(combined_claims['missing_denial_reason'].value_counts())"""

# ========= Duplicate check ==================================================

duplicate_rows = combined_claims.duplicated().sum()
"""print(duplicate_rows)"""

"""print(combined_claims[combined_claims.duplicated(keep=False)])"""
combined_claims = combined_claims.drop_duplicates()
"""print(combined_claims.duplicated().sum())"""

# primary key check
primary_key_duplicates = combined_claims['claim_id'].duplicated().sum()
"""print(combined_claims[combined_claims['claim_id'].duplicated(keep=False)])"""

combined_claims["conflicting_claim_id_flag"] = (
    combined_claims["claim_id"].duplicated(keep=False)
)
"""print(combined_claims["conflicting_claim_id_flag"].value_counts())"""
# ========== Data type and consistent check =======================================================

"""print(combined_claims.info())"""
# procedure_code         127 non-null    int64   => must be in string

"""print(
    combined_claims['procedure_code']
    .astype(str)
    .str.len().value_counts()
) """
# all are of same format
combined_claims['procedure_code'] = combined_claims['procedure_code'].astype(
    str)
"""print(combined_claims.info())"""


# checking the diagnosis_code format also
"""print(
    combined_claims['diagnosis_code'].head(10)
)"""

diagnosis_pattern = r'^[A-Z0-9]{3}(\.[0-9]{1,3})?$'
invalid_daignosis = combined_claims[
    ~combined_claims['diagnosis_code'].str.match(diagnosis_pattern, na=False)
]

"""print(f'invalid_diagnosis : {len(invalid_daignosis)}')"""

# category column data consistency check

categories_column = [
    'claim_type',
    'claim_status'
]

for col in categories_column:
    """print(f'----{col}----')
    print(combined_claims[col].value_counts())"""

# standardization is needed for claim_status
combined_claims['claim_status'] = combined_claims['claim_status'].str.strip(
).str.title()
"""print(combined_claims['claim_status'].str.strip().str.lower().value_counts())"""

# ======== Numeric column check ============================================================================

"""print(combined_claims[
    combined_claims['paid_amount'] > combined_claims['billed_amount']
][['claim_id', 'paid_amount', 'billed_amount']])"""

combined_claims['paid_greater_than_billed'] = combined_claims['paid_amount'] > combined_claims['billed_amount']
"""print(combined_claims['paid_greater_than_billed'].value_counts())"""
combined_claims['negative_billed_amt'] = combined_claims['billed_amount'] < 0
"""print(combined_claims['negative_billed_amt'].value_counts())"""

negative_paid_amount = combined_claims[combined_claims['paid_amount'] < 0]
"""print(f'negative_paid_amount: {len(negative_paid_amount)}')"""

Denied_paid_amt = combined_claims[
    (combined_claims['claim_status'] == 'Denied')
    & (combined_claims['paid_amount'] > 0)
]
"""print(f'denied paid claim : {len(Denied_paid_amt)}')"""

# ======== Referential integrity check =========================================

provider = pd.read_csv('providers.csv')

valid_provider_ids = set(provider['provider_id'])
invalid_provider_ids = combined_claims[
    ~combined_claims['provider_id'].isin(valid_provider_ids)
]
"""print(f'invalid providers : {len(invalid_provider_ids)}')"""

excel_member = pd.ExcelFile('members.xlsx')
members = []
for sheet in excel_member.sheet_names:
    df = pd.read_excel('members.xlsx', sheet_name=sheet)
    df['member_type'] = sheet

    """print(f'-----{sheet}----')
    print(df.columns.to_list())"""
    members.append(df)

combined_members = pd.concat(members, ignore_index=True)
"""print(combined_members.head())"""
valid_member_ids = set(combined_members['member_id'])
invalid_member_ids = combined_claims[
    (~combined_claims['member_id'].isin(valid_member_ids)) &
    (combined_claims['member_id'].notna())
]
"""print(f'invalid member : {len(invalid_member_ids)}')"""

output = Path("output")
output.mkdir(exist_ok=True)
claims_file = "output/cleaned_claims.csv"
combined_claims.to_csv(claims_file, index=False)

print(f'Finally saved to : {claims_file}')
