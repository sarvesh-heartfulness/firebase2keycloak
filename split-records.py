import json
import os
import re
import phonenumbers

# Regular expression for validating an email
EMAIL_REGEX = r'^[^@]+@[^@]+\.[^@]+$'

# Function to validate email using regular expression
def is_valid_email(email):
    return re.match(EMAIL_REGEX, email) is not None

# Function to validate phone number using phonenumbers library
def is_valid_phone(phone):
    try:
        phone_number = phonenumbers.parse(phone)
        return phonenumbers.is_valid_number(phone_number)
    except phonenumbers.NumberParseException:
        return False

# Read the records from the JSON file
def read_records(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        users = data['users'] if isinstance(data, dict) and 'users' in data else data
        return users

# Write records to a file
def write_records(file_path, records):
    with open(file_path, 'w') as file:
        json.dump(records, file, indent=4)

# Main function to process the records
def process_records(input_file):
    records = read_records(input_file)
    valid_records = []
    invalid_records = []

    for i, record in enumerate(records):
        print(f'Validating record no. {i+1} with id {record["localId"]}')

        # Perform all checks once and store results
        has_email = 'email' in record
        has_phone = 'phoneNumber' in record
        has_password = 'passwordHash' in record
        is_email_verified = record.get('emailVerified', False)
        email_valid = is_valid_email(record.get('email', '')) if has_email else False
        phone_valid = is_valid_phone(record.get('phoneNumber', '')) if has_phone else False

        email = record.get('email', '')
        phone = record.get('phoneNumber', '')

        email_valid = is_valid_email(email) if email else False
        phone_valid = is_valid_phone(phone) if phone else False

        # Check if the record is valid
        if (has_phone and phone_valid) or (has_email and has_password) or \
            (has_email and is_email_verified):
                if phone_valid or email_valid:
                    valid_records.append(record)
                    continue
        
        # If any of the conditions are not met, capture the reasons
        reasons = {}
        if has_email and has_phone:
            if not email_valid and not phone_valid:
                reasons['invalidEmailPhone'] = "User with invalid email and phone"
            elif email_valid and not phone_valid and not has_password and not is_email_verified:
                reasons['invalidPhoneUnverifiedEmailMissingPassword'] = "User with invalid phone, unverified address and missing password"
        elif has_email and not has_phone:
            if not has_password and not is_email_verified:
                reasons['unverifiedEmailMissingPassword'] = "Email user with unverified address and missing password"
        elif not has_email and has_phone and not phone_valid:
            reasons['invalidPhone'] = "User with Invalid phone number"
        elif not has_email and not has_phone:
            reasons['anon'] = "Anonymous user"
        
        record_with_reasons = record.copy()
        record_with_reasons['reasons'] = reasons if reasons else 'N.A.'
        invalid_records.append(record_with_reasons)

    write_records('filtered_records.json', valid_records)
    write_records('skipped_records.json', invalid_records)
    print(f"Valid records written to filtered_records.json")
    print(f"Invalid records written to skipped_records.json")

if __name__ == "__main__":
    input_file = 'LOG/users.json'
    process_records(input_file)
