import dotenv
import json
import os
import requests
import logging
import threading
from datetime import datetime

# Load environment variables
dotenv.load_dotenv()

# Global variables
KEYCLOAK_URL = os.getenv('KEYCLOAK_URL')
REALM_NAME = os.getenv('REALM_NAME')
NUM_THREADS = int(os.getenv('NUM_THREADS', '1'))  # Default to 1 thread if not provided
NUM_USERS_TO_PROCESS = int(os.getenv('NUM_USERS_TO_PROCESS', '100'))  # Default to process 100 users if not provided

def get_admin_token():
    '''
    Get KeyCloak Admin Token
    '''
    keycloak_url = os.getenv('KEYCLOAK_URL')
    realm_name = os.getenv('REALM_NAME')
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')

    token_url = f'{keycloak_url}/realms/{realm_name}/protocol/openid-connect/token'
    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    try:
        response = requests.post(token_url, data=payload)
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get('access_token')
        else:
            print(f"Failed to obtain admin token: {response.text}")
            return None
    except Exception as e:
        print(f"Error obtaining admin token: {e}")
        return None

# Obtain the admin token
ADMIN_TOKEN = get_admin_token()

# Lock for file writing
file_lock = threading.Lock()

class UserProcessor(threading.Thread):
    def __init__(self, thread_num, users_data):
        super().__init__()
        self.thread_num = thread_num
        self.users_data = users_data
        self.logger = self.setup_logger()

    def setup_logger(self):
        log_file = os.getenv('LOG_FILE_PATH', f'thread_') + f'{self.thread_num}_log.txt'
        logger = logging.getLogger(f'Thread-{self.thread_num}')
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

    def run(self):
        url = f'{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users'
        headers = {'Authorization': f'Bearer {ADMIN_TOKEN}', 'Content-Type': 'application/json'}

        processed_ids_file = os.getenv('PROCESSED_IDS_FILE_PATH', f'processed_ids_thread_') + f'{self.thread_num}.json'
        failed_ids_file = os.getenv('FAILED_IDS_FILE_PATH', f'failed_ids_thread_') + f'{self.thread_num}.json'

        processed_ids = self.load_ids(processed_ids_file)
        failed_ids = self.load_ids(failed_ids_file)

        for i, user in enumerate(self.users_data):
            print(f'Processing record... - userId: {user["localId"]}')
            self.logger.info('|------------------------------------------------------------------------|')
            self.logger.info(f'Processing record... - userId: {user["localId"]} (Thread {self.thread_num})')

            try:
                success = False
                if 'phoneNumber' in user and 'passwordHash' not in user:
                    # Process phone number users
                    self.logger.info('Processing phone number user...')
                    success = self.process_phone_number_user(user, url, headers, processed_ids, failed_ids)

                elif 'email' in user and 'passwordHash' in user:
                    # Process email users
                    self.logger.info('Processing email user...')
                    success = self.process_email_user(user, url, headers, processed_ids, failed_ids)

                elif 'providerUserInfo' in user and len(user['providerUserInfo']) > 0:
                    # Process users with provider information
                    self.logger.info('Processing provider user...')
                    success = self.process_provider_user(user, url, headers, processed_ids, failed_ids)

                else:
                    if user['localId'] in failed_ids:
                        self.logger.warning(f'Skipping failed user with localId: {user["localId"]}')
                    else:
                        self.logger.error('Invalid user data.')
                        self.logger.error(user)
                        failed_ids.append(user['localId'])

                # Update processed/failed IDs file after each record
                if success:
                    with file_lock:
                        self.write_ids_to_file(processed_ids, processed_ids_file)
                else:
                    with file_lock:
                        self.write_ids_to_file(failed_ids, failed_ids_file)

            except Exception as e:
                self.logger.error(f'Error processing user: {e}')
                self.logger.info('|------------------------------------------------------------------------|')
                self.logger.info('\n')
                continue
            self.logger.info('|------------------------------------------------------------------------|')
            self.logger.info('\n')

    def load_ids(self, file_path):
        try:
            with open(file_path) as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except Exception as e:
            logging.error(f'Error loading IDs from file {file_path}: {e}')
            return []

    def write_ids_to_file(self, ids, file_path):
        try:
            with open(file_path, 'w') as f:
                json.dump(list(ids), f, indent=4)
        except Exception as e:
            logging.error(f'Error writing IDs to file {file_path}: {e}')

    def process_phone_number_user(self, user, url, headers, processed_ids, failed_ids):
        local_id = user['localId']
        if local_id in processed_ids:
            self.logger.info(f'Skipping already processed user with localId: {local_id}')
            return True

        if local_id in failed_ids:
            self.logger.warning(f'Skipping failed user with localId: {local_id}')
            return False

        display_name = user.get('displayName', '').split(' ')
        first_name = display_name[0] if display_name else None
        last_name = display_name[1] if len(display_name) > 1 else None
        photo_url = user.get('photoUrl', '')
        user_data = {
            'username': user['phoneNumber'],
            'firstName': first_name,
            'lastName': last_name,
            'email': user.get('email', ''),
            'emailVerified': user.get('emailVerified', False),
            'enabled': not user.get('disabled', False),
            'attributes': {
                'phoneNumber': user['phoneNumber'],
                'phoneNumberVerified': True,
                'userId': local_id,
            },
        }
        if photo_url:
            user_data['attributes']['photoUrl'] = photo_url
        self.logger.info(f'Creating user with phone number: {user_data}')
        response = self.create_user(url, headers, user_data)
        if response and response.status_code == 201:
            self.logger.info('User created successfully with phone number.')
            processed_ids.append(local_id)
            return True
        else:
            error_message = f'Error creating phone number user: {response.text}'
            self.logger.error(error_message)
            failed_ids.append(local_id)
            return False

    def process_email_user(self, user, url, headers, processed_ids, failed_ids):
        local_id = user['localId']
        if local_id in processed_ids:
            self.logger.info(f'Skipping already processed user with localId: {local_id}')
            return True

        if local_id in failed_ids:
            self.logger.warning(f'Skipping failed user with localId: {local_id}')
            return False

        display_name = user.get('displayName', '').split(' ')
        first_name = display_name[0] if display_name else None
        last_name = display_name[1] if len(display_name) > 1 else None
        photo_url = user.get('photoUrl', '')

        user_data = {
            'username': user['email'],
            'email': user['email'],
            'emailVerified': user['emailVerified'],
            'enabled': not user.get('disabled', False),
            'firstName': first_name,
            'lastName': last_name,
            'attributes': {
                'phoneNumber': user.get('phoneNumber'),
                'phoneNumberVerified': user.get('phoneNumberVerified', False),
                'userId': local_id,
            },
            "credentials": [{
                "hashedSaltedValue": user['passwordHash'],
                "salt": user['salt'],
                "hashIterations": -1,
                "algorithm": "firebase-scrypt",
                "temporary": False,
                "type": "password"
            }]
        }
        if photo_url:
            user_data['attributes']['photoUrl'] = photo_url

        response = self.create_user(url, headers, user_data)
        if response and response.status_code == 201:
            self.logger.info('User created successfully with email.')
            self.logger.info('Adding password to user...')
            user_id = self.find_user(url, headers, user['email'])
            if user_id:
                self.logger.info(f'User found in Keycloak. - ID: {user_id}')
                processed_ids.append(local_id)
                return True
            else:
                self.logger.warning('User not found in Keycloak.')
                failed_ids.append(local_id)
                return False
        else:
            error_message = f'Error creating email user: {response.text}'
            self.logger.error(error_message)
            failed_ids.append(local_id)
            return False

    def process_provider_user(self, user, url, headers, processed_ids, failed_ids):
        local_id = user['localId']
        if local_id in processed_ids:
            self.logger.info(f'Skipping already processed user with localId: {local_id}')
            return True

        if local_id in failed_ids:
            self.logger.warning(f'Skipping failed user with localId: {local_id}')
            return False

        display_name = user.get('displayName', '').split(' ')
        first_name = display_name[0] if display_name else None
        last_name = display_name[1] if len(display_name) > 1 else None

        user_data = {
            'username': user.get('email', user['localId']),
            'email': user.get('email'),
            'emailVerified': user.get('emailVerified', False),
            'firstName': first_name,
            'lastName': last_name,
            'enabled': not user.get('disabled', False),
            'attributes': {
                'phoneNumber': user.get('phoneNumber'),
                'phoneNumberVerified': user.get('phoneNumberVerified', False),
                'userId': local_id,
                'photoUrl': user.get('photoUrl', '')
            },
        }

        response = self.create_user(url, headers, user_data)
        if response and response.status_code == 201:
            self.logger.info('User created successfully.')
            user_id = self.find_user(url, headers, user.get('email', user['localId']))
            if user_id:
                self.logger.info('Searching for user in Keycloak...')
                for provider in user['providerUserInfo']:
                    if provider['providerId'] == 'google.com':
                        self.logger.info('Adding Google provider to user.')
                        # Add Google provider to user
                        identityProvider = 'google'
                        social_data = {
                            'identityProvider': identityProvider,
                            'userId': provider['rawId'],
                            'userName': provider['email'] if 'email' in provider else provider['displayName'],
                        }
                        url = f'{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}/federated-identity/{identityProvider}'
                        response = requests.post(url, headers=headers, data=json.dumps(social_data))
                        if response.status_code == 204:
                            self.logger.info(f'Added Google provider to user - ID: {user_id} and Provider ID: {provider["rawId"]}')
                        else:
                            self.logger.error(f'Error adding Google provider to user: {response.text}')
                    elif provider['providerId'] == 'facebook.com':
                        self.logger.info('Skip adding Facebook provider to user.')
                        # Add Facebook provider to user
                processed_ids.append(local_id)
                return True
            else:
                self.logger.warning('User not found in Keycloak.')
                failed_ids.append(local_id)
                return False
        else:
            error_message = f'Error creating provider user: {response.text}'
            self.logger.error(error_message)
            failed_ids.append(local_id)
            return False

    def create_user(self, url, headers, user_data):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(user_data))
            return response
        except Exception as e:
            self.logger.error(f'Error creating user: {e}')
            return None

    def find_user(self, url, headers, username):
        try:
            response = requests.get(url, headers=headers, params={'username': username})
            if response.status_code == 200 and len(response.json()) > 0:
                return response.json()[0]['id']
            else:
                return None
        except Exception as e:
            self.logger.error(f'Error finding user: {e}')
            return None

def load_users(file_path, num_users_to_process):
    try:
        with open(file_path) as f:
            users_data = json.load(f)
            return users_data[:num_users_to_process]
    except Exception as e:
        logging.error(f'Error loading users: {e}')
        return None

def main():
    user_dump = os.getenv('USER_DUMP_FILE')
    users_data = load_users(user_dump, NUM_USERS_TO_PROCESS)
    if users_data:
        threads = []
        chunk_size = len(users_data) // NUM_THREADS
        user_chunks = [users_data[i:i + chunk_size] for i in range(0, len(users_data), chunk_size)]

        for i in range(NUM_THREADS):
            thread = UserProcessor(i + 1, user_chunks[i])
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()
    else:
        logging.warning('No users data found.')

if __name__ == "__main__":
    main()
