import os
import json

def load_ids(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from file {file_path}")
        return []
    except Exception as e:
        print(f"Error loading IDs from file {file_path}: {e}")
        return []

def count_user_statuses(folder_path):
    processed_count = 0
    failed_count = 0
    skipped_count = 0

    for file_name in os.listdir(folder_path):
        if file_name.startswith('processed_ids'):
            processed_count += len(load_ids(os.path.join(folder_path, file_name)))
        elif file_name.startswith('failed_ids'):
            failed_count += len(load_ids(os.path.join(folder_path, file_name)))
        elif file_name.startswith('skipped_ids'):
            skipped_count += len(load_ids(os.path.join(folder_path, file_name)))

    return processed_count, failed_count, skipped_count

def main():
    folder_path = input("Enter the path to the logs folder: ")
    if not os.path.isdir(folder_path):
        print("Invalid folder path. Please provide a valid absolute path to the logs folder.")
        return

    processed_count, failed_count, skipped_count = count_user_statuses(folder_path)

    print(f"Processed users count: {processed_count}")
    print(f"Failed users count: {failed_count}")
    print(f"Skipped users count: {skipped_count}")

if __name__ == "__main__":
    main()
