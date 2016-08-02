# PoGoMap
The fastest Pokémon Go map available.

Heavily using [pgoapi](https://github.com/tejado/pgoapi). 

![image](https://cloud.githubusercontent.com/assets/1723176/17143769/c5db3a80-5354-11e6-85d9-ba664e293cfc.png)

##Installation and usage:

**Note:** If you are upgrading from the last version, you will have to update and/or reinstall the requirements.

1. Clone the repository `git clone https://github.com/favll/pogom.git`
2. Install our dependencies `pip install -r requirements.txt`
3. Copy `config.sample.json` to `config.json`, remove the comment and fill in your data. You can enter anything from *one* up to as many accounts as you want.
4. Start the server by running `python runserver.py -l "<LOCATION>" -r <SEARCHRADIUS_IN_METERS>`

- Use the `-H` and `-P` flag to specify host and port. E.g. `-H "127.0.0.1" -P 80` will tell the webserver to listen to localhost requests on port 80. You can then head over and take a look at the map at `http://127.0.0.1:5000/`. If you want the server to listen on all public IPs use the host `0.0.0.0`. This will allow you to access your server from other machines.  
- You can quickly configure the map by using the sidebar. For more advanced configuration settings (e.g. accounts, Google Maps key) you can open the open the config page `/config`.

##Features
- [x] Extremely fast (using multiple accounts)
- [x] Perfect coverage (using a perfect hexagonal grid of radius 70m)
- [x] No Bloat (we tried to keep this as lightweight as possible, therefore you won't see as many flags in the help file)
- [x] Hide common Pokemon
- [x] Server status in the Web-GUI
- [x] Stats about seen Pokemon
- [x] Proper handling of server downtime (using exponential backoff strategy)
- [x] Mobile friendly
- [x] Web-GUI
- [ ] Show/Hide Pokestops
- [ ] Notifications

##TODO
 - Move processing of responses (protobuf parsing & save to DB) to seperate process
 - Use different (faster) library for protobuf parsing
 - Heatmaps!
