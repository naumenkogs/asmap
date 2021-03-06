#!/usr/bin/env python

import sys
import os
import re

PARSED_DUMPS_DIR = 'paths/'
RESULT_OUTPUT = 'prefix_asns.out'
first_octet = re.compile(r"^[^.|:]*")


# Remove duplicate asns in a row
# [1, 1, 2, 3, 3, 3] -> [1, 2, 3]
def dedup(asn_path):
    i = len(asn_path) - 2
    while i > 0:
        if asn_path[i] == asn_path[i - 1]:
            asn_path = asn_path[0:i] + asn_path[i+1:]
        i -= 1
    return asn_path

def find_common_suffixes(prefix_asn_paths, common_asn_suffix):
    for prefix, asn_lists in prefix_asn_paths.items():
        asn_lists = [dedup(asn_list.split(' ')) for asn_list in asn_lists] # preprocess
        asn_lists = [asn_list for asn_list in asn_lists if asn_list != [] and asn_list != ['']] # this very rarely happens in dumps
        if len(asn_lists) == 0:
            continue
        asn_lists.sort(key = len)
        cur_asn_suffix = asn_lists[0] # represents the common sub-path (from the end) of asns to a prefix
        for asn_list in asn_lists[1:]:
            if cur_asn_suffix == asn_list:
                continue
            if cur_asn_suffix[-1] != asn_list[-1]: # multi-homed
                break
            cur_asn_suffix_len = len(cur_asn_suffix)
            for i in range(1, cur_asn_suffix_len): # position from the end
                if cur_asn_suffix[len(cur_asn_suffix) - i - 1] != asn_list[len(asn_list) - i - 1]:
                    cur_asn_suffix = cur_asn_suffix[len(cur_asn_suffix) - i:]
                    break
        common_asn_suffix[prefix] = cur_asn_suffix

def process_files():
    res = dict()
    files = os.listdir(PARSED_DUMPS_DIR)
    step = 40
    for i in range(1, 256, step): # process ip range chunks so that memory is not filled
        print("Working on chunk: ", i, flush=True)
        announcements = dict()
        for file_name in files:
            print('Reading file: ', file_name, flush=True)
            with open(PARSED_DUMPS_DIR + file_name, "r") as file:
                for line in file:
                    announcement_data = re.sub(r'{[^>]+}', ' ', line.strip()) # removes {} sets in AS path
                    announcement_data = announcement_data.split('|')
                    prefix = announcement_data[0]
                    first_oc = re.search(first_octet, prefix).group(0)
                    if first_oc == '' or int(first_oc) > i + step: # passed current chunk
                        break
                    if int(first_oc) < i: # current chunk is ahead
                        continue
                    asns = announcement_data[1]
                    announcements.setdefault(prefix, set()).add(asns)
        find_common_suffixes(announcements, res)
    return res

def dump_result(prefix_unique_asn_suffixes):
    with open(RESULT_OUTPUT, 'w+') as file:
        for prefix, unique_asn_suffix in prefix_unique_asn_suffixes.items():
            file.write("%s AS%s\n" % (prefix, unique_asn_suffix[0]))

res = process_files()
dump_result(res)
