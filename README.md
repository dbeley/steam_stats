# steam_stats

`steam_stats` is a python command-line utility to extract data from Steam games based on their appids.

Data collected include:

- number of positive reviews
- number of negative reviews
- developers
- publishers
- platforms supported
- genres
- release date
- achievements
- etc.

The script `get_ids.py` is included to fetch appids of Steam games (several options: all steam games, owned, wishlisted).

## Requirements

- pandas
- requests
- beautifulsoup4 (for curator script)

## Configuration

All scripts need a config.ini file with a valid Steam API key and a Steam ID (see config_sample.ini for an example).

Values can also be set via environment variables:
- `STEAM_API_KEY` — Steam Web API key
- `STEAM_USER_ID` — Steam ID64
- `STEAM_CONFIG_PATH` — path to an alternative config file
- `ITAD_API_KEY` — IsThereAnyDeal API key (for `--export_extra_data`)

If you want to extract latest price information from IsThereAnyDeal, you can also set it in the config file. You will need to create an API key on their website and use `steam_stats` with the `--export_extra_data` parameter.

- Sample config.ini file :

```
[steam]
api_key=api_key_here
user_id=user_id_here
[itad]
api_key=api_key_here
```

## Installation

```bash
python setup.py install --user
```

## Usage

You can use the `get_ids.py` script to export a list of appids (see below).

`steam_stats` expects a readable csv file with a column `appid` containing Steam appids as input.

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

```bash
steam_stats -f steam_games.csv
```

### Options

```
usage: steam_stats [-h] [--debug] [-f FILE] [--export_filename EXPORT_FILENAME]
                   [--export_extra_data] [--workers WORKERS] [--deduplicate]
                   [--export_json]

Export Steam games data from a list of appids

optional arguments:
  -h, --help                    show this help message and exit
  --debug                       Display debugging information
  -f FILE, --file FILE          File containing the appids to parse
  --export_filename EXPORT_FILENAME
                                Override export filename (without extension)
  --export_extra_data           Enable extra data fetching (ITAD prices)
  --workers WORKERS             Number of concurrent workers (default: 10)
  --deduplicate                 Remove duplicate appids before processing
  --export_json                 Also export results as JSON (in addition to CSV)
```

## Helper scripts

Several scripts are included in the `scripts` folder.

### get_ids.py

Export the appids of all Steam games, owned games or wishlisted games of a Steam user.

```bash
python get_ids.py -h
```

#### Usage

```bash
python get_ids.py -t owned
python get_ids.py -t wishlist
python get_ids.py -t both
python get_ids.py -t all
python get_ids.py -t owned -u $STEAM_USER_ID
```

### get_playtime.py

Export the playtime of all games played by a Steam user.

```bash
python get_playtime.py -h
```

### get_ids_from_curator_page.py

Export the ids of a curator page (the page needs to be saved in an HTML file).

```bash
python get_ids_from_curator_page.py -h
```

### diff_two_lists.py

Compute the difference between two files (appid lists, CSV fields, or text files).

```bash
python diff_two_lists.py -f1 file1.csv -fn1 appid -f2 file2.csv -fn2 appid
```

## Environment variables reference

| Variable | Purpose |
|---|---|
| `STEAM_API_KEY` | Steam Web API key (overrides config.ini) |
| `STEAM_USER_ID` | Steam ID64 (overrides config.ini) |
| `STEAM_CONFIG_PATH` | Path to alternative config file |
| `ITAD_API_KEY` | IsThereAnyDeal API key (overrides config.ini) |
