import json

# Load the JSON file
with open('filtered_records.json', 'r') as file:
    data = json.load(file)

# Count the number of records
record_count = len(data)

print(f'Total number of records: {record_count}')
