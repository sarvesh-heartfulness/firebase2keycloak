import os
import json
from collections import Counter

def analyze_failed_records(folder_path):
    failed_records = []
    error_counts = Counter()

    # Iterate through files in the folder
    for filename in os.listdir(folder_path):
        if filename.startswith("failed_records_thread_") and filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r') as file:
                records = json.load(file)
                failed_records.extend(records)
                for record in records:
                    if 'error' in record:
                        error_counts[record['error']] += 1

    # Generate summary
    total_failed = len(failed_records)
    print(f"Total failed records: {total_failed}")
    print("\nError types and counts:")
    for error, count in error_counts.most_common():
        print(f"- {error}: {count}")

    # Calculate percentages
    print("\nError percentages:")
    for error, count in error_counts.most_common():
        percentage = (count / total_failed) * 100
        print(f"- {error}: {percentage:.2f}%")

    # Sample of failed records
    print("\nSample of failed records (up to 5):")
    for record in failed_records[:5]:
        print(f"- User ID: {record.get('localId', 'N/A')}")
        print(f"  Error: {record.get('error', 'N/A')}")
        print(f"  Email: {record.get('email', 'N/A')}")
        print()

if __name__ == "__main__":
    folder_path = input("Enter the folder path containing the failed records files: ")
    analyze_failed_records(folder_path)
