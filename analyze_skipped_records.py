import json
from collections import Counter

def read_json_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def analyze_skipped_records(file_path):
    skipped_records = read_json_file(file_path)
    
    total_records = len(skipped_records)
    reason_counter = Counter()
    
    for record in skipped_records:
        reasons = record.get('reasons', {})
        if reasons == 'N.A.':
            reason_counter['Unknown'] += 1
        else:
            reason_counter.update(reasons.keys())
    
    print(f"Total skipped records: {total_records}")
    print("\nReasons for skipping:")
    for reason, count in reason_counter.most_common():
        percentage = (count / total_records) * 100
        print(f"- {reason}: {count} ({percentage:.2f}%)")
    
    print("\nSample records for each reason:")
    for reason in reason_counter.keys():
        if reason == 'Unknown':
            sample = next((r for r in skipped_records if r.get('reasons') == 'N.A.'), None)
        else:
            sample = next((r for r in skipped_records if reason in r.get('reasons', {})), None)
        
        if sample:
            print(f"\n{reason}:")
            print(json.dumps(sample, indent=2))

if __name__ == "__main__":
    skipped_records_file = 'skipped_records.json'
    analyze_skipped_records(skipped_records_file)
