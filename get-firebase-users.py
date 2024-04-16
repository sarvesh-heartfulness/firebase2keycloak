import firebase_admin
from firebase_admin import credentials, auth
import json


# Initialize Firebase Admin SDK
cred = credentials.Certificate('./your-service.json') # path to your service account key
firebase_admin.initialize_app(cred)

def get_all_users():
  all_users = []
  page_token = None

  while True:
    # Retrieve a batch of users (max 1000)
    if page_token:
        users = auth.list_users(page_token)
    else:
        users = auth.list_users()

    # Add retrieved users to the list
    all_users.extend(users.users)

    # Check if there's a next page (avoid empty string check)
    if users.has_next_page:
      page_token = users.next_page_token
    else:
      break  # No more pages

  return all_users

# Get all users
users = get_all_users()

# save all users to a json file
users_json = []
count = 0
for user in users:
    count += 1
    print(f'Processing user {count}...')

    provider_data = []
    for provider in user.provider_data:
        provider_data.append({
            'provider_id': provider.provider_id,
            'uid': provider.uid,
            'email': provider.email,
            'phone_number': provider.phone_number,
            'photo_url': provider.photo_url,
            'display_name': provider.display_name
        })
    users_json.append({
        'uid': user.uid,
        'email': user.email,
        'display_name': user.display_name,
        'phone_number': user.phone_number,
        'photo_url': user.photo_url,
        'disabled': user.disabled,
        'provider_id': user.provider_id,
        'email_verified': user.email_verified,
        'custom_claims': user.custom_claims,
        'provider_data': provider_data,
        'password_hash': user.password_hash
    })

with open('users.json', 'w') as f:
    json.dump(users_json, f)