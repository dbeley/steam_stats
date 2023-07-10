# steam_stats

`steam_stats` is an python command-line utility to extract data from Steam games based on their appids.

Data collected include:

- number of positive reviews
- number of negative reviews
- developers
- publishers
- plaforms supported
- genres
- release date
- etc.

The script `get_ids.py` is included to fetch appids of Steam games (several options: all steam games, owned, wishlisted).

## Requirements

- pandas
- requests
- unicode

## Configuration

All the scripts need a config.ini file with a valid steam api key and a steam id (see config_sample.ini for an example).

If you want to extract latest price information from IsThereAnyDeal, you can also set it in the config file. You will need to create an API key on their website and use `steam_stats` with the `--export_extra_data` parameter.

- Sample config.ini file :

```
[steam]
api_key=api_key_here
user_id=user_id_ere
[itad]
api_key=api_key_here
```

## Installation

```
python setup.py install --user
```

## Usage

You can use the `get_ids.py` script to export a list of appids (see below).

`steam_stats` expects a readable csv file with a column `appid` containg Steam appids as input.

Given a steam_games.csv file containing :

```
name;appid
Dead Cells;152266
Wizard of Legend;445980
Hollow Knight;367520
Lethis Path of Progress;359230
Banished;242920
```

You can call steam_stats with the command :

```
steam_stats -f steam_games.csv
```

### Help

```
steam_stats -h
```

```
usage: steam_stats [-h] [--debug] [-f FILE]
                   [--export_filename EXPORT_FILENAME] [-s] [--export_extra_data]

Export Steam games data from a list of appids

options:
  -h, --help            show this help message and exit
  --debug               Display debugging information
  -f FILE, --file FILE  File containing the appids to parse
  --export_filename EXPORT_FILENAME
                        Override export filename
  -s, --separate_export
                        Export separately (one file per game + the global
                        file)
  --export_extra_data          Enable extra data fetching (ITAD)
```

## Helper scripts

Several scripts are included in the `scripts` folder.

### get_ids.py

Export the appids of all Steam games, owned games or wishlisted games of a Steam user.

```
python get_ids.py -h
```

#### Usage

```
python get_ids.py -t owned
python get_ids.py -t wishlist
python get_ids.py -t both
python get_ids.py -t all
python get_ids.py -t owned -u $STEAM_USER_ID
```

#### Help

```
usage: get_ids.py [-h] [--debug] [-t TYPE] [-u USER_ID]

export ids of a set of games

optional arguments:
  -h, --help            show this help message and exit
  --debug               Display debugging information
  -t TYPE, --type TYPE  Type of ids to export (all, owned, wishlist or both
                        (owned and wishlist))
  -u USER_ID, --user_id USER_ID
                        User id to extract the games data from (steamID64).
                        Default : user in config.ini
```


### get_playtime.py

Export the playtime of all Steam games, owned games or wishlisted games of a Steam user.

```
python get_playtime.py -h
```

### get_ids_from_curator_page.py

Export the ids of a curator page (the page needs to be saved in an HTML file).

```
python get_ids_from_curator_page.py -h
```
