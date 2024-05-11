# firebase2keycloak
Script to migrate Firebase users to KeyCloak

## Execution
### Get Firebase user dump
- Firebase CLI - https://firebase.google.com/docs/cli/
- Get User dump using Firebase CLI - https://firebase.google.com/docs/cli/auth#auth-export
### Clone the repository
```sh
git clone https://github.com/sarvesh-heartfulness/firebase2keycloak.git
```
### Add credentials to .env
- Change directory to cloned repository
```sh
cd firebase2keycloak
touch .env
```
- Sample .env
```txt
KEYCLOAK_URL=https://keycloak-xxx.com
REALM_NAME=realm-name
CLIENT_ID=client-name
CLIENT_SECRET=xxxxxxxxxxxxxxxxx
NUM_THREADS=5
NUM_USERS_TO_PROCESS=100
LOG_FILE_PATH=thread_
PROCESSED_IDS_FILE_PATH=processed_ids_thread_
FAILED_IDS_FILE_PATH=failed_ids_thread_
USER_DUMP_FILE=users.json
```
### Build a docker image
```sh
docker build -t fb2kk .
```
### Execute the Script
```sh
docker run -v /path/to/dump/:/app/data --env-file .env fb2kk python create-users.py
```
_Assuming absolute path of the user dump is `/path/to/dump/users.json`_
