import json

# Load the JSON file
with open('filtered_records.json', 'r') as file:
    data = json.load(file)
    users_data = data['users'] if isinstance(data, dict) and 'users' in data else data

# Count the number of records
record_count = len(users_data)

print(f'Total number of records: {record_count}')
