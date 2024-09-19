from utils.searxng_utils import Search
import argparse

parser = argparse.ArgumentParser()
# 必填参数
parser.add_argument('-q', '--question', dest='question', type=str, required=True)

args = parser.parse_args()
search = Search(result_num=15)
search.auto_writer(args.question)