import logging
import time
import argparse
import collections
import pandas as pd
from pathlib import Path

logger = logging.getLogger()
start_time = time.time()


def read_from_file(filename: str):
    if not Path(filename).is_file():
        raise FileNotFoundError("%s is not a valid file.", filename)
    with open(filename, "r") as f:
        content = f.read().splitlines()
    return content


def read_field_from_file(filename: str, fieldname: str, sheet_name: str | int):
    if not Path(filename).is_file():
        raise FileNotFoundError("%s is not a valid file.", filename)
    if Path(filename).suffix in [".csv", ".txt"]:
        df = pd.read_csv(filename, sep="\t")
    elif Path(filename).suffix in [
        ".xls",
        ".xlsx",
        ".xlsm",
        ".xlsb",
        ".odf",
        ".ods",
        ".odt",
    ]:
        df = pd.read_excel(filename, engine=None, sheet_name=sheet_name)
    else:
        raise ValueError(
            "File %s with type %s not supported.", filename, Path(filename).suffix
        )
    return df[fieldname].astype("string").tolist()


def main():
    args = parse_args()

    logger.debug("Reading files")
    if args.fieldname1 and args.fieldname2:
        print(f"Reading field {args.fieldname1} for file {args.filename1}")
        content1 = read_field_from_file(
            args.filename1, args.fieldname1, args.sheetname1
        )
        print(f"Reading field {args.fieldname2} for file {args.filename2}")
        content2 = read_field_from_file(
            args.filename2, args.fieldname2, args.sheetname2
        )
    else:
        content1 = read_from_file(args.filename1)
        content2 = read_from_file(args.filename2)

    print(f"---------- Duplicates in {args.filename1}")
    print([item for item, count in collections.Counter(content1).items() if count > 1])
    print(f"---------- Duplicates in {args.filename2}")
    print([item for item, count in collections.Counter(content2).items() if count > 1])
    print(f"---------- Complete diff between {args.filename1} and {args.filename2}")
    print("\n".join(sorted(set(content1) ^ set(content2))))
    print(f"---------- Values in {args.filename2} and not in {args.filename1}")
    print("\n".join(sorted([item for item in content2 if item not in content1])))
    print(f"---------- Values in {args.filename1} and not in {args.filename2}")
    print("\n".join(sorted([item for item in content1 if item not in content2])))

    logger.info("Runtime : %.2f seconds." % (time.time() - start_time))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compute the difference between two files"
    )
    parser.add_argument(
        "--debug",
        help="Display debugging information",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    parser.add_argument(
        "-f1",
        "--filename1",
        help="File containing data",
        type=str,
    )
    parser.add_argument(
        "-fn1",
        "--fieldname1",
        help="Field for the file 1",
        type=str,
    )
    parser.add_argument(
        "-sn1", "--sheetname1", help="Sheetname for file 1 (optional)", default=1
    )
    parser.add_argument(
        "-f2",
        "--filename2",
        help="File containing data",
        type=str,
    )
    parser.add_argument(
        "-fn2",
        "--fieldname2",
        help="Field for the file 2",
        type=str,
    )
    parser.add_argument(
        "-sn2", "--sheetname2", help="Sheetname for file 2 (optional)", default=1
    )
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)
    return args


if __name__ == "__main__":
    main()
