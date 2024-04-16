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

response = requests.get(url, headers=headers)
if response.status_code == 200:
    print('Users retrieved successfully.')
else:
    print(response.status_code)
    print(response.text)
    exit()
users = response.json()

with open('keycloak-users.json', 'w') as f:
    json.dump(users, f)