import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-t', action='store_true')
args = parser.parse_args()
print(args)
