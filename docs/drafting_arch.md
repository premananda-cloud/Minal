project root = rt
I am thinking rt/app/{asset/, schemas/, models/, main.py , db/, skill/}
asset: where data is stored in json instruction faculty notice current date and data course
skill : python scripts to perfrom data collection refresh necessary, like getting date time etc, its reun by main every prompy from user and embed i\
necessary data into model call to Ollma server
db : i put it so we can route data and handling logic logs, so main -> skill -[data]> db -> asset.
