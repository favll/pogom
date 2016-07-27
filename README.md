# PoGoMap
The no-bloat version of [PokemonGo-Map](https://github.com/AHAAAAAAA/PokemonGo-Map) (their rewrite is actually an early-stage fork of this project).

Heavily using [pgoapi](https://github.com/tejado/pgoapi). 

![image](https://cloud.githubusercontent.com/assets/1723176/17143769/c5db3a80-5354-11e6-85d9-ba664e293cfc.png)

##Installation and usage:

On Linux, for Debian-based distributions, you should install pycurl's dependencies before installing the project's requirements:

`sudo apt-get install libssl-dev libcurl4-openssl-dev python-dev`

Edit `pogom/__init__.py` and enter your GMaps Key.

```
pip install -r requirements.txt
python runserver.py -u USERNAME -p PASSWORD -l LOCATION -r SEARCHRADIUS -c
```
The `-c` flag switches to pycurl (python wrapper around the libcurl library) as downloader. This is so performant that the parsing and DB stuff becomes the bottleneck. 


##Features
- [x] Extremely fast (scans a 5km search radius in 1m30s with the -c flag)
- [x] Perfect coverage (using a perfect hexagonal grid of radius 100m)
- [x] No Bloat (we tried to keep this as lightweight as possible, therefore you won't see as many flags in the help file)
- [x] Hide common Pokemon
- [x] Server status in the Web-GUI
- [x] Stats about seen Pokemon
- [x] Proper handling of server downtime (using exponential backoff strategy)
- [x] Mobile friendly
- [ ] Show/Hide Pokestops
- [ ] Notifications

##TODO
 - Move processing of responses (protobuf parsing & save to DB) to seperate process
 - Use different (faster) library for protobuf parsing
 - Web-GUI for all configuration settings
 - Heatmaps!
