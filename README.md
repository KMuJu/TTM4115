# Structure

One folder for each of the devices in the deployment diagram:
1. Scooter
2. Server
3. GUI


# Installation and running
Execute each instruction in the correct folder

## GUI
The GUI is run from a computer with python 3.9 or 3.10 with necessary libraries. Before running the GUI, it is necessary to set the IP-address of the server. If running the server locally on same computer as GUI, localhost is sufficient. Start the GUI by running:
```
python ./E-Scooter-phone-app.py
```

## Server
The server runs in a containerized environment. To run the server, the host needs to have a docker engine with docker compose installed and running. Start the server by navigating into the "server" directory and running:
```
docker compose build
docker compose up
```

## Scooter
Requires: sense-hat packet
install with `sudo apt install sense-hat`

The scooter runs locally on the sense-hat raspberry pi. To run the scooter-code, open a terminal on the raspberry pi (can be done via SSH), navigate to "~/TTM4115/scooter" and run:
```
python main.py
``` 
