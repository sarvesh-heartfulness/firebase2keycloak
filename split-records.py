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
        return json.load(file)

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
        email = record.get('email', '')
        phone = record.get('phoneNumber', '')

        email_valid = is_valid_email(email) if email else False
        phone_valid = is_valid_phone(phone) if phone else True  # Validate phone only if present

        if ('phoneNumber' in record and 'passwordHash' not in record) or \
           ('email' in record and 'passwordHash' in record) or \
           ('providerUserInfo' in record and len(record['providerUserInfo']) > 0):
               if email_valid or 'email' not in record:  # If email is present, it should be valid
                   if phone_valid or 'phoneNumber' not in record:  # If phoneNumber is present, it should be valid
                       valid_records.append(record)
                       continue
        
        # If any of the conditions are not met
        reasons = {}
        if 'email' in record and not email_valid:
            reasons['invalidEmail'] = "User with invalid email"
        if 'email' in record and 'passwordHash' not in record and 'phoneNumber' not in record:
            reasons['missingEmailPassword'] = "Email user without password"
        if 'phoneNumber' in record and not phone_valid:
            reasons['invalidPhoneNumber'] = "User with Invalid phone number"
        if 'email' not in record and 'phoneNumber' not in record:
            reasons['anon'] = "Anonymous user"
        
        # Add 'reasons' key to record level
        record_with_reasons = record.copy()
        record_with_reasons['reasons'] = reasons if reasons else 'N.A.'
        invalid_records.append(record_with_reasons)

    write_records('filtered_records.json', valid_records)
    write_records('skipped_records.json', invalid_records)
    print(f"Valid records written to filtered_records.json")
    print(f"Invalid records written to skipped_records.json")

if __name__ == "__main__":
    input_file = 'Exec/users.json'
    process_records(input_file)
