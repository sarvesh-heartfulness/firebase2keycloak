import dotenv, json, logging, os, requests, threading, time
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
# ADMIN_TOKEN = get_admin_token()
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN')

# Lock for file writing
file_lock = threading.Lock()

# Timestamp for log folder
timestamp = str(int(time.time()))

class UserProcessor(threading.Thread):
    def __init__(self, thread_num, users_data):
        # Initialize thread attributes
        super().__init__()
        self.thread_num = thread_num
        self.users_data = users_data
        self.log_folder = os.getenv('LOG_FILE_PATH', 'Log') + f'logs_{timestamp}'
        self.logger = self.setup_logger()

    def setup_logger(self):
        '''
        This will setup logger to store log files in a sub folder along with timestamp
        '''
        os.makedirs(self.log_folder, exist_ok=True)
        log_file = os.path.join(self.log_folder, f'thread_{self.thread_num}_log.txt')
        logger = logging.getLogger(f'Thread-{self.thread_num}')
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

    def run(self):
        # Set KeyCloak users URL and authentication headers 
        url = f'{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users'
        headers = {'Authorization': f'Bearer {ADMIN_TOKEN}', 'Content-Type': 'application/json'}

        # Store execution data for overall report
        processed_ids_file = f'{self.log_folder}/processed_ids_thread_{self.thread_num}.json'
        unprocessed_ids_file = f'{self.log_folder}/unprocessed_ids_thread_{self.thread_num}.json'
        failed_ids_file = f'{self.log_folder}/failed_ids_thread_{self.thread_num}.json'
        skipped_ids_file = f'{self.log_folder}/skipped_ids_thread_{self.thread_num}.json'
        failed_records_file = f'{self.log_folder}/failed_records_thread_{self.thread_num}.json'

        processed_ids = self.load_json(processed_ids_file)
        unprocessed_ids = self.load_json(unprocessed_ids_file)
        failed_ids = self.load_json(failed_ids_file)
        skipped_ids = self.load_json(skipped_ids_file)
        failed_records = self.load_json(failed_records_file)

        # Process records for a thread
        for i, user in enumerate(self.users_data):
            print(f'Processing record... - userId: {user["localId"]} (Thread {self.thread_num}) (Index {i})')
            self.logger.info('|------------------------------------------------------------------------|')
            self.logger.info(f'Processing record... - userId: {user["localId"]} (Thread {self.thread_num}) (Index {i})')

            try:
                success = False
                # Note: Duplicate phone user is not handled unless it used as username
                if 'phoneNumber' in user and 'passwordHash' not in user:
                    # Process phone number users
                    self.logger.info('Processing phone number user...')
                    success = self.process_phone_number_user(user, url, headers, processed_ids, failed_ids, failed_records)

                elif 'email' in user and 'passwordHash' in user:
                    # Process email users (records with passwordHash)
                    self.logger.info('Processing email-password user...')
                    success = self.process_email_user(user, url, headers, processed_ids, failed_ids, failed_records)

                elif 'providerUserInfo' in user and len(user['providerUserInfo']) > 0:
                    # Process users with provider information (Social Login)
                    providerAvailable = False
                    for provider in user['providerUserInfo']:
                        # Records with 'facebookProvider' will be processed without adding facebook provider
                        if provider['providerId'] in ['google.com', 'facebook.com']:
                            providerAvailable = True
                            self.logger.info('Processing user with Google/Facebook provider...')
                            success = self.process_provider_user(user, url, headers, processed_ids, failed_ids, failed_records)
                    if not providerAvailable:
                        self.logger.error(f'Skipping the provider user without Google Login with data - {user}')
                        skipped_ids.append(user['localId'])
                elif 'email' in user and user['emailVerified']:
                    # Process email users with verified id
                    self.logger.info('Processing verified email user...')
                    success = self.process_email_user(user, url, headers, processed_ids, failed_ids, failed_records)
                else:
                    self.logger.error(f'Skipping the user with invalid user data. {user}')
                    skipped_ids.append(user['localId'])

            except Exception as e:
                self.logger.error(f'Error processing user: {e}')
                self.logger.info('|------------------------------------------------------------------------|')
                self.logger.info('\n')
                unprocessed_ids.append(user["localId"])
                continue
            self.logger.info('|------------------------------------------------------------------------|')
            self.logger.info('\n')

        # Update processed/failed/skipped IDs file
        with file_lock:
            self.write_to_file(processed_ids, processed_ids_file)
            self.write_to_file(unprocessed_ids, unprocessed_ids_file)
            self.write_to_file(failed_ids, failed_ids_file)
            self.write_to_file(failed_records, failed_records_file)
            self.write_to_file(skipped_ids, skipped_ids_file)

    def load_json(self, file_path):
        '''
        Helper function to load json file
        '''
        try:
            with open(file_path) as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except Exception as e:
            logging.error(f'Error loading IDs from file {file_path}: {e}')
            return []

    def write_to_file(self, data, file_path):
        '''
        Helper function to write to a file
        '''
        try:
            with open(file_path, 'w') as f:
                json.dump(list(data), f, indent=4)
        except Exception as e:
            logging.error(f'Error writing data to file {file_path}: {e}')

    def process_phone_number_user(self, user, url, headers, processed_ids, failed_ids, failed_records):
        '''
        Helper function to process phone user
        '''
        local_id = user['localId']
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
        self.logger.info(f'Creating user with phone number')
        response = self.create_user(url, headers, user_data)
        if response and response.status_code == 201:
            self.logger.info('User created successfully with phone number.')
            processed_ids.append(local_id)
            return True
        else:
            error_message = f'Error creating phone number user: {response.text}'
            self.logger.error(error_message)
            failed_ids.append(local_id)
            user['error'] = error_message
            failed_records.append(user)
            return False

    def process_email_user(self, user, url, headers, processed_ids, failed_ids, failed_records):
        '''
        Helper function to process email user
        '''
        local_id = user['localId']
        display_name = user.get('displayName', '').split(' ')
        first_name = display_name[0] if display_name else None
        last_name = display_name[1] if len(display_name) > 1 else None
        photo_url = user.get('photoUrl', '')

        user_data = {
            'username': user['email'],
            'email': user['email'],
            'emailVerified': user['emailVerified'],
            'enabled': True,
            'firstName': first_name,
            'lastName': last_name,
            'attributes': {
                'phoneNumber': user.get('phoneNumber'),
                'phoneNumberVerified': user.get('phoneNumberVerified', False),
                'userId': local_id,
            }
        }

        if 'passwordHash' in user:
            user_data['credentials'] = [{
                "hashedSaltedValue": user['passwordHash'],
                "salt": user['salt'],
                "hashIterations": -1,
                "algorithm": "firebase-scrypt",
                "temporary": False,
                "type": "password"
                }]
            user_data['enabled'] = not user.get('disabled', False)
        
        if photo_url:
            user_data['attributes']['photoUrl'] = photo_url

        response = self.create_user(url, headers, user_data)
        if response and response.status_code == 201:
            self.logger.info('User created successfully with email.')
            processed_ids.append(local_id)
            return True
        else:
            error_message = f'Error creating email user: {response.text}'
            self.logger.error(error_message)
            failed_ids.append(local_id)
            user['error'] = error_message
            failed_records.append(user)
            return False

    def process_provider_user(self, user, url, headers, processed_ids, failed_ids, failed_records):
        '''
        Helper function to process provicer user i.e. user with Social Login
        '''
        local_id = user['localId']
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
            # Get user id from response header `Location``
            location_header = response.headers.get('Location')
            user_id = location_header.split('/')[-1]
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
            processed_ids.append(local_id)
            return True
        else:
            error_message = f'Error creating provider user: {response.text}'
            self.logger.error(error_message)
            failed_ids.append(local_id)
            user['error'] = error_message
            failed_records.append(user)
            return False

    def create_user(self, url, headers, user_data):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(user_data))
            return response
        except Exception as e:
            self.logger.error(f'Error creating user: {e}')
            return None

def load_users(file_path, num_users_to_process):
    try:
        with open(file_path) as f:
            users_data = json.load(f)
            if num_users_to_process:
                return users_data[:num_users_to_process]
            return users_data
    except Exception as e:
        logging.error(f'Error loading users: {e}')
        return None

def main():
    # Script execution starts here
    start_time = time.time() # Record the start time
    user_dump = os.getenv('USER_DUMP_FILE')
    users_data = load_users(user_dump, NUM_USERS_TO_PROCESS)
    if users_data:
        threads = []
        chunk_size = len(users_data) // NUM_THREADS
        # Divide user data in chunks for specified number of threads
        user_chunks = [users_data[i:i + chunk_size] for i in range(0, len(users_data), chunk_size)]

        # Start threads for processing user data
        for i in range(NUM_THREADS):
            thread = UserProcessor(i + 1, user_chunks[i])
            threads.append(thread)
            thread.start()

        # This waits until all threads are completed
        for thread in threads:
            thread.join()
    else:
        logging.warning('No users data found.')

    end_time = time.time() # Record the end time
    total_time = end_time - start_time
    print(f"Total time taken: {total_time} seconds")

if __name__ == "__main__":
    main()
