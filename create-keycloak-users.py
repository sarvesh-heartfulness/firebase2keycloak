import dotenv, json, os, requests

# load environment variables
dotenv.load_dotenv()

# keycloak admin connection
KEYCLOAK_URL = os.getenv('KEYCLOAK_URL')
REALM_NAME = os.getenv('REALM_NAME')
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN')

# get users from admin
url = f'{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users'
headers = {
    'Authorization': f'Bearer {ADMIN_TOKEN}',
    'Content-Type': 'application/json'
}

# load hash configurations
hash_config = json.load(open('dev-password-hash-config.json'))['hash_config']

# load users from file
users_data = json.load(open('dev-users.json'))

'''
Types of users:
- email and password
- phone number
- google
- facebook
'''

# create users
# for i, fb_user in enumerate([fb_user_data]):
for i, fb_user in enumerate(users_data):
    print('|------------------------------------------------------------------------|')
    print('Processing record... - Index:', i)
    try:
        if 'displayName' in fb_user:
            display_name = fb_user['displayName'].split(' ')
        else:
            display_name = []
        first_name = display_name[0] if len(display_name) > 0 else None
        last_name = display_name[1] if len(display_name) > 1 else None
        if 'phoneNumber' in fb_user and not 'passwordHash' in fb_user:
            user_data = {
                'username': fb_user['phoneNumber'],
                'firstName': first_name,
                'lastName': last_name,
                'attributes': {
                    'phoneNumber': fb_user['phoneNumber'],
                    'phoneNumberVerified': True,
                    'userId': fb_user['localId'],
                    'photoUrl': fb_user['photoUrl'] if 'photoUrl' in fb_user else '',
                },
            }
            response = requests.post(url, headers=headers, data=json.dumps(user_data))
            if response.status_code == 201:
                print('User created successfully with phone number.')
            else:
                print('Error creating phone user.')

        elif 'email' in fb_user and 'passwordHash' in fb_user:
            continue
            user_data = {
                'username': fb_user['email'],
                'email': fb_user['email'],
                'emailVerified': fb_user['emailVerified'],
                'enabled': not fb_user['disabled'] if 'disabled' in fb_user else True,
                'firstName': first_name,
                'lastName': last_name,
                'attributes': {
                    'phoneNumber': fb_user['phoneNumber'] if 'phoneNumber' in fb_user else None,
                    'phoneNumberVerified': fb_user['phoneNumberVerified'] if 'phoneNumber' in fb_user else False,
                    'userId': fb_user['localId'],
                    'photoUrl': fb_user['photoUrl'] if 'photoUrl' in fb_user else '',
                },
            }
            response = requests.post(url, headers=headers, data=json.dumps(user_data))
            if not response.status_code == 201:
                print('Error creating email user.')
                print(fb_user)
                continue
            print('User created successfully with email.')
            print('Adding password to user...')
            print('Searching for user in Keycloak...')
            user_id = None
            url = f'{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users?username={fb_user["email"]}'
            response = requests.get(url, headers=headers)
            if not (response.status_code == 200 and len(response.json()) > 0):
                print(response.text)
                print('User not found in KeyCloak - Index:', i)
                continue
            user_id = response.json()[0]['id']
            print('User found in KeyCloak.')
            url = f'{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}/reset-password'
            response = requests.put(url,
                                    headers=headers,
                                    data=json.dumps({
                                        'type': 'password',
                                        'secretData': json.dumps({'value': fb_user['passwordHash'],
                                                                  'salt': fb_user['salt']}),
                                        'credentialData': json.dumps(hash_config),
                                        'algorithm': 'firebase-scrypt',
                                        'temporary': False})
                                    )
            if response.status_code == 204:
                print('Password added successfully. - Index:', i)
            else:
                print('Error adding password to user. - Index:', i)
                print(response.text)
        elif 'providerUserInfo' in fb_user and len(fb_user['providerUserInfo']) > 0:
            # create user and link to google or facebook
            user_data = {
                'username': fb_user['email'] if 'email' in fb_user else fb_user['localId'],
                'email': fb_user['email'] if 'email' in fb_user else None,
                'emailVerified': fb_user['emailVerified'] if 'emailVerified' in fb_user else False,
                'firstName': first_name,
                'lastName': last_name,
                'enabled': not fb_user['disabled'] if 'disabled' in fb_user else True,
                'attributes': {
                    'phoneNumber': fb_user['phoneNumber'] if 'phoneNumber' in fb_user else None,
                    'phoneNumberVerified': fb_user['phoneNumberVerified'] if 'phoneNumber' in fb_user else False,
                    'userId': fb_user['localId'],
                    'photoUrl': fb_user['photoUrl'] if 'photoUrl' in fb_user else '',
                },
            }

            response = requests.post(url, headers=headers, data=json.dumps(user_data))
            if not response.status_code == 201:
                print('Error creating user.')
                print(fb_user)
                print(response.text)
                continue

            print('User created successfully.')

            print('Searching for user in Keycloak...')
            user_id = None
            if 'email' in fb_user:
                url = f'{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users?username={fb_user["email"]}'
                response = requests.get(url, headers=headers)
                if not (response.status_code == 200 and len(response.json()) > 0):
                    print(response.text)
                    print('User not found in KeyCloak - Index:', i)
                    continue
                user_id = response.json()[0]['id']
                print('User found in KeyCloak.')
            else:
                url = f'{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users?username={fb_user["localId"]}'
                response = requests.get(url, headers=headers)
                if not(response.status_code == 200 and len(response.json()) > 0):
                    print(response.text)
                    print('User not found in KeyCloak - Index:', i)
                    continue
                user_id = response.json()[0]['id']
                print('User found in KeyCloak.')
            for provider in fb_user['providerUserInfo']: # Add a social login provider to the user
                if provider['providerId'] == 'google.com':
                    print('Adding Google provider to user.')
                    identityProvider = 'google'
                    social_data = {
                        'identityProvider': identityProvider,
                        'userId': provider['rawId'],
                        'userName': provider['email'] if 'email' in provider else provider['displayName'],
                    }
                    url = f'{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}/federated-identity/{identityProvider}'
                    response = requests.post(url, headers=headers, data=json.dumps(social_data))
                    if response.status_code == 201:
                        print(response.text)
                        print('Google provider added successfully.')
                    else:
                        print(fb_user)
                        print(response.text)
                        print('Error adding google provider.')
                elif provider['providerId'] == 'facebook.com':
                    pass
        else:
            print('Invalid user data.')
            print(fb_user)
            print(response.text)

        print('\n')

    except Exception as e:
        print('Error creating user.')
        print(e)
        continue
