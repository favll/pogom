# PoGoMap
The fastest Pokémon Go map available.

Heavily using [pgoapi](https://github.com/keyphact/pgoapi). Shout-out to the Unknown6 team!

![image](https://cloud.githubusercontent.com/assets/1723176/17143769/c5db3a80-5354-11e6-85d9-ba664e293cfc.png)

##Installation:
-
**Note:** If you are upgrading from the last version, you will have to update and/or reinstall the requirements.

1. Clone the repository `git clone https://github.com/favll/pogom.git`
2. Install the dependencies `pip install -r requirements.txt`
3. Start the server by running `python runserver.py`

**Pro-Tip:** Use the `-H` and `-P` flag to specify host and port. E.g. `-H "127.0.0.1" -P 5001` will tell the webserver to listen to localhost requests on port 5001. You can then head over and take a look at the map at `http://127.0.0.1:5001/`. If you want the server to listen on all public IPs use the host `0.0.0.0`. This will allow you to access your server from other machines.

##Usage

Before you can use the map you will have to configure it. Pogom provides a configuration web interface. The first time you start the server and visit `http://<ip>:<port>/` the server will redirect you to the config page. There you can enter your Google Maps Api key, the accounts used for scanning (**Note:** never use your real account for scanning) and set a password to protect the config. The configuration is saved server-side so you do not have to worry about entering these settings every time you restart the server. You can still edit the settings if you visit `http://<ip>:<port>/config`.

After the server has been started and you completed the configuration you can go back to `http://<ip>:<port>/` again where you can start adding scan locations simply by clicking on the map. **Note:** If you can't add locations by clicking on the map try going back to `http://<ip>:<port>/` and reauthenticate by entering the configuration password.

##Features
- [x] Extremely fast (using multiple accounts)
- [x] Multiple locations
- [x] Perfect coverage (using a perfect hexagonal grid of radius 70m)
- [x] Hide common Pokemon
- [x] Server status in the Web-GUI
- [x] Stats about seen Pokemon
- [x] Mobile friendly

##TODO
- **Notifications**
- Show/Hide Pokestops
- Move processing of responses (protobuf parsing & save to DB) to seperate process
- Use different (faster) library for protobuf parsing
- Heatmaps!
