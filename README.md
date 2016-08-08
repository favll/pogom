# PoGoMap
The fastest Pokémon Go map available.

Heavily using [pgoapi](https://github.com/keyphact/pgoapi). Shout-out to the Unknown6 team!

![image](https://cloud.githubusercontent.com/assets/1723176/17482369/bf3df2b2-5d81-11e6-904e-edfd496702dc.png)

##Installation:

**Note:** If you are upgrading from the last version, you will have to update and/or reinstall the requirements.

1. Clone the repository `git clone https://github.com/favll/pogom.git`
2. Install the dependencies `pip install -r requirements.txt`
3. Start the server by running `python runserver.py`

**Pro-Tip:** Use the `-H` and `-P` flag to specify host and port. E.g. `-H "127.0.0.1" -P 5001` will tell the webserver to listen to localhost requests on port 5001. You can then head over and take a look at the map at `http://127.0.0.1:5001/`. If you want the server to listen on all public IPs use the host `0.0.0.0`. This will allow you to access your server from other machines.

There's no other flags besides  `-H` and `-P`, everything else is configured through the Web UI.

##Usage

 - Visit `http://<ip>:<port>/` (by default: `http://127.0.0.1:5000/`)
 - On the first run you will be redirected to a configuration page
   - Enter your Google Maps Api Key
   - Enter all accounts and passwords to be used for scanning
   - Optionally protect the configuration with a password (only authenticated users can access the config and change scan locations)
 - Go back to `http://<ip>:<port>/` to view the map
 - Add scan locations simply by clicking on the map

##Features
- [x] Extremely fast (using multiple accounts)
- [x] Multiple locations
- [x] Perfect coverage (using a perfect hexagonal grid of radius 70m)
- [x] Everything configurable from the browser (bye bye command-line flags)
- [x] Hide common Pokemon
- [x] Server status in the Web-GUI
- [x] Stats about seen Pokemon
- [x] Mobile friendly

##TODO
- **Notifications**
- Show/Hide Pokestops
- Heatmaps!
