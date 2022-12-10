# steam_stats

## Requirements

- pandas
- requests
- unicode

## Configuration

All the scripts need a config.ini file with a valid steam api key and a steam id (see config_sample.ini for an example).

- Sample config.ini file :

```
[steam]
api_key=api_key_here
user_id=user_id_ere
```

## get_ids.py

Export the ids of all Steam games, owned games or wishlisted games of a steam user.

```
python get_ids.py -h
```

### Usage

```
python get_ids.py -t owned
python get_ids.py -t wishlist
python get_ids.py -t both
python get_ids.py -t all
python get_ids.py -t owned -u $STEAM_USER_ID
```

### Help

```
usage: get_ids.py [-h] [--debug] [-t TYPE] [-u USER_ID]

export ids of a set of games

optional arguments:
  -h, --help            show this help message and exit
  --debug               Display debugging information
  -t TYPE, --type TYPE  Type of ids to export (all, owned, wishlist or both
                        (owned and wishlist))
  -u USER_ID, --user_id USER_ID
                        User id to extract the games info from (steamID64).
                        Default : user in config.ini
```


## get_playtime.py

Export the playtime of all Steam games, owned games or wishlisted games of a steam user.

```
python get_playtime.py -h
```

## get_ids_from_curator_page.py

Export the ids of a curator page (the page needs to be saved in an html file).

```
python get_ids_from_curator_page.py -h
```

## steam_stats

Export games info from a list of ids

## Installation in a virtualenv (recommended)

```
pipenv install '-e .'
```

## Usage

You can use the `get_ids.py` script to export a list of appids.

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

## Help

```
steam_stats -h
```

```
usage: steam_stats [-h] [--debug] [-f FILE]
                   [--export_filename EXPORT_FILENAME] [-s] [--extra_infos]

Export games info from a list of ids

optional arguments:
  -h, --help            show this help message and exit
  --debug               Display debugging information
  -f FILE, --file FILE  File containing the ids to parse
  --export_filename EXPORT_FILENAME
                        Override export filename.
  -s, --separate_export
                        Export separately (one file per game + the global
                        file)
  --extra_infos         Enable extra information fetching (ITAD, HLTB,
                        opencritic).
```
