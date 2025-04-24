
# Virtual environment

## Activate

### Linux & MacOs
```
source ./.venv/bin/activate
```
### Windows
```
.\.venv\Scripts\activate
```


# Struktur

En mappe for de tre delene av prosjektet:
1. Scooter
2. Server
3. GUI



# Installation and running

## GUI
The GUI is run from a computer with python 3.9 or 3.10 with necessary libraries. Before running the GUI, it is necessary to set the IP-address of the server. If running the server locally on same computer as GUI, localhost is sufficient. Start the GUI by running:
```
python ./Attempt2.py
```

## Server
The server runs in a containerized environment. To run the server, the host needs to have a docker engine with docker compose installed and running. Start the server by navigating into the "server" directory and running:
```
docker compose build
docker compose up
```

# Scooter
The scooter runs locally on the sense-hat raspberry pi. To run the scooter-code, open a terminal on the raspberry pi (can be done via SSH), navigate to "~/TTM4115/scooter" and run:
```
python main.py
``` 