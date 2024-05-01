import dotenv
import json
import os
import requests
import logging
from datetime import datetime

# Load environment variables
dotenv.load_dotenv()

# Global variables
KEYCLOAK_URL = os.getenv('KEYCLOAK_URL')
REALM_NAME = os.getenv('REALM_NAME')
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN')

# Configure logging
log_file = 'user_creation.log'
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Function to load users from a file
def load_users(file_path):
    try:
        with open(file_path) as f:
            return json.load(f)
    except Exception as e:
        logging.error(f'Error loading users: {e}')
        return None

# Function to create a user
def create_user(url, headers, user_data):
    try:
        response = requests.post(url, headers=headers, data=json.dumps(user_data))
        return response
    except Exception as e:
        logging.error(f'Error creating user: {e}')
        return None

# Function to find a user by username
def find_user(url, headers, username):
    try:
        response = requests.get(url, headers=headers, params={'username': username})
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]['id']
        else:
            return None
    except Exception as e:
        logging.error(f'Error finding user: {e}')
        return None

# Function to process phone number users
def process_phone_number_user(user, url, headers):
    try:
        display_name = user.get('displayName', '').split(' ')
        first_name = display_name[0] if display_name else None
        last_name = display_name[1] if len(display_name) > 1 else None

        user_data = {
            'username': user['phoneNumber'],
            'firstName': first_name,
            'lastName': last_name,
            'attributes': {
                'phoneNumber': user['phoneNumber'],
                'phoneNumberVerified': True,
                'userId': user['localId'],
                'photoUrl': user.get('photoUrl', ''),
            },
        }

        response = create_user(url, headers, user_data)
        if response and response.status_code == 201:
            logging.info('User created successfully with phone number.')
        else:
            logging.error(f'Error creating phone number user: {response.text}')
    except Exception as e:
        logging.error(f'Error processing phone number user: {e}')

# Function to process email users
def process_email_user(user, url, headers):
    try:
        display_name = user.get('displayName', '').split(' ')
        first_name = display_name[0] if display_name else None
        last_name = display_name[1] if len(display_name) > 1 else None

        user_data = {
            'username': user['email'],
            'email': user['email'],
            'emailVerified': user['emailVerified'],
            'enabled': not user.get('disabled', True),
            'firstName': first_name,
            'lastName': last_name,
            'attributes': {
                'phoneNumber': user.get('phoneNumber'),
                'phoneNumberVerified': user.get('phoneNumberVerified', False),
                'userId': user['localId'],
                'photoUrl': user.get('photoUrl', ''),
            },
            "credentials" : [{
                "hashedSaltedValue": user['passwordHash'],
                "salt": user['salt'],
                "hashIterations" : -1,
                "algorithm": "firebase-scrypt",
                "temporary": False,
                "type":"password"
            }]
        }

        response = create_user(url, headers, user_data)
        if response and response.status_code == 201:
            logging.info('User created successfully with email.')
            logging.info('Adding password to user...')
            user_id = find_user(url, headers, user['email'])
            if user_id:
                logging.info(f'User found in Keycloak. - ID: {user_id}')
                # Do something with user_id
            else:
                logging.warning('User not found in Keycloak.')
        else:
            logging.error(f'Error creating email user: {response.text}')
    except Exception as e:
        logging.error(f'Error processing email user: {e}')

# Function to process provider users
def process_provider_user(user, url, headers):
    try:
        display_name = user.get('displayName', '').split(' ')
        first_name = display_name[0] if display_name else None
        last_name = display_name[1] if len(display_name) > 1 else None

        user_data = {
            'username': user.get('email', user['localId']),
            'email': user.get('email'),
            'emailVerified': user.get('emailVerified', False),
            'firstName': first_name,
            'lastName': last_name,
            'enabled': not user.get('disabled', True),
            'attributes': {
                'phoneNumber': user.get('phoneNumber'),
                'phoneNumberVerified': user.get('phoneNumberVerified', False),
                'userId': user['localId'],
                'photoUrl': user.get('photoUrl', ''),
            },
        }

        response = create_user(url, headers, user_data)
        if response and response.status_code == 201:
            logging.info('User created successfully.')
            user_id = find_user(url, headers, user.get('email', user['localId']))
            if user_id:
                logging.info('Searching for user in Keycloak...')
                for provider in user['providerUserInfo']:
                    if provider['providerId'] == 'google.com':
                        logging.info('Adding Google provider to user.')
                        # Add Google provider to user
                    elif provider['providerId'] == 'facebook.com':
                        logging.info('Adding Facebook provider to user.')
                        # Add Facebook provider to user
            else:
                logging.warning('User not found in Keycloak.')
        else:
            logging.error(f'Error creating provider user: {response.text}')
    except Exception as e:
        logging.error(f'Error processing provider user: {e}')

# Function to process users
def process_users(users_data):
    url = f'{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users'
    headers = {'Authorization': f'Bearer {ADMIN_TOKEN}', 'Content-Type': 'application/json'}

    for i, user in enumerate(users_data):
        logging.info('|------------------------------------------------------------------------|')
        logging.info(f'Processing record... - Index: {i}')

        try:
            # Process different types of users
            if 'phoneNumber' in user and 'passwordHash' not in user:
                # Process phone number users
                logging.info('Processing phone number user...')
                process_phone_number_user(user, url, headers)

            elif 'email' in user and 'passwordHash' in user:
                # Process email users
                logging.info('Processing email user...')
                process_email_user(user, url, headers)

            elif 'providerUserInfo' in user and len(user['providerUserInfo']) > 0:
                # Process users with provider information
                logging.info('Processing provider user...')
                process_provider_user(user, url, headers)

            else:
                logging.error('Invalid user data.')
                logging.error(user)

            logging.info('\n')

        except Exception as e:
            logging.error(f'Error processing user: {e}')
            continue

# Main function
def main():
    logging.info('Script execution started.')
    users_data = load_users('dev-users.json')
    if users_data:
        process_users(users_data)
    else:
        logging.warning('No users data found.')
    logging.info('Script execution completed.')

if __name__ == "__main__":
    main()
