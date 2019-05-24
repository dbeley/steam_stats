# steam_stats

Export games info from a list of ids

## Requirements

- pandas
- requests
- unicode

## Installation in a virtualenv (recommended)

```
pipenv install '-e .'
```

## Usage

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
