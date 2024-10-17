# Prerequisites

- A server with Docker and Git installed.
- Firebase user dump and admin credentials of a Keycloak instance.

## 1. Setup Environment

Clone the repository:
```sh
git clone git@github.com:HeartfulnessInstitute/firebase2keycloak.git
```

## 2. Environment Preparation

### Create .env file

In the project directory (firebase2keycloak), create a file named `.env` to store environment variables used by the script.

Example `.env`:
```
KEYCLOAK_URL=https://auth.keycloakhost.com
REALM_NAME=rxxxx
NUM_THREADS=20
NUM_USERS_TO_PROCESS=20000
LOG_FILE_PATH=/app/data/
USER_DUMP_FILE=/app/data/users.json
ADMIN_TOKEN=eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJrM05JU3ZKVWdsUy05THNtVDh3WDhpTzlBXzJlQ3hkcmF1TmdMWFB5a05vIn0.eyJleHAiOjE3MTc0ODY5ODIsImlhdCIxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```


### Put User Dump in Proper Location

1. Place your Firebase user data in a JSON file named `users.json`.
2. Move this file to the `LOG` directory within the project directory (create the `LOG` directory if it doesn't exist).

## 3. Build and Run the Script

### Build Docker Image

Navigate to the project directory (firebase2keycloak) and run the following command to build the Docker image:

```sh
sudo docker build -t fb2kk .
```

### Run the Script

Run the script to migrate users:

```sh
sudo docker run -v /home/ec2-user/firebase2keycloak/LOG/:/app/data --env-file .env fb2kk python create-users.py
```
> 
This command mounts the `LOG` directory on the host machine to the `/app/data` directory within the container. It also uses the `.env` file for environment variables.
