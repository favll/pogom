# PoGoMap
The no-bloat version of [PokemonGo-Map](https://github.com/AHAAAAAAA/PokemonGo-Map) (their rewrite is actually an early-stage fork of this project).

Heavily using [pgoapi](https://github.com/tejado/pgoapi). 

![image](https://cloud.githubusercontent.com/assets/1723176/17143565/f6838c9c-5353-11e6-8e4e-fa0383697f38.png)

##Usage (the usual):

```
pip install -r requirements.txt
python runserver.py -u USERNAME -p PASSWORD -l LOCATION -r SEARCHRADIUS
```
The `-c` switches to pycurl (python wrapper around the libcurl library) as downloader. This is so performant that the parsing and DB stuff becomes the bottleneck. 

##Features
- [x] Extremely fast (scans a 5km search radius in 1m30s with the -c flag)
- [x] Perfect coverage (using a perfect hexagonal grid of radius 100m)
- [x] No Bloat (we tried to keep this as lightweight as possible, therefore you won't see as many flags in the help file)
- [x] Hide common Pokemon
- [x] Server status in the Web-GUI
- [x] Stats about seen Pokemon
- [ ] Show/Hide Pokestops
- [ ] Notifications

##TODO
 - Move processing of responses (protobuf parsing & save to DB) to seperate process
 - Web-GUI for all configuration settings
