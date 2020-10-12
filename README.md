# steam_stats

## Requirements

- pandas
- requests
- unicode

## get_ids.py

Export the ids of a either all games, owned games or wishlisted games of a steam user.

```
python get_ids.py -h
```

### Configuration


Needs a config.ini file with a valid steam api key and a steam id (see config_sample.ini for an example).

- Sample config.ini file :

```
[steam]
api_key=api_key_here
user_id=user_id_ere
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

# steam_stats

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
usage: steam_stats [-h] [--debug] [-f FILE] [-s]

Export games info from a list of ids

optional arguments:
  -h, --help            show this help message and exit
  --debug               Display debugging information
  -f FILE, --file FILE  File containing the ids to parse
  -s, --separate_export
                        Export separately (one file per game + the global
                        file)
```
