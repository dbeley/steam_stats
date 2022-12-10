import logging
import time
import argparse
import collections
from pathlib import Path

logger = logging.getLogger()
start_time = time.time()


def read_from_file(filename: str):
    if not Path(filename).is_file():
        raise FileNotFoundError("%s is not a valid file.", filename)
    with open(filename, "r") as f:
        content = f.read().splitlines()
    return content


def main():
    args = parse_args()

    logger.debug("Reading files")
    file1 = read_from_file(args.filename1)
    file2 = read_from_file(args.filename2)

    print(f"---------- Duplicates in {args.filename1}")
    print([item for item, count in collections.Counter(file1).items() if count > 1])
    print(f"---------- Duplicates in {args.filename2}")
    print([item for item, count in collections.Counter(file2).items() if count > 1])
    print(f"---------- Complete diff between {args.filename1} and {args.filename2}")
    print("\n".join(sorted(set(file1) ^ set(file2))))
    print(f"---------- Files in {args.filename2} and not in {args.filename1}")
    print("\n".join(sorted([item for item in file2 if item not in file1])))
    print(f"---------- Files in {args.filename1} and not in {args.filename2}")
    print("\n".join(sorted([item for item in file1 if item not in file2])))

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
        "-f2",
        "--filename2",
        help="File containing data",
        type=str,
    )
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)
    return args


if __name__ == "__main__":
    main()
