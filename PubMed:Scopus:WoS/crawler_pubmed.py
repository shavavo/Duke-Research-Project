import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import requests
import json
import numpy as np
import time
import urllib3
import datetime
import crawlera_proxies
import re

_SESSION = requests.session()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

proxies = crawlera_proxies.proxies


def get_page_content(url, retry=0):
    global _SESSION

    if retry == 5:
        return None

    response = _SESSION.get(url, proxies=proxies, verify=False)

    if response.status_code == 200:
        return response.content
    else:
        print(str(response.status_code) + " Code, waiting 10s before retrying")
        time.sleep(10)
        _SESSION = requests.Session()
        return get_page_content(url, retry+1)


def search_pubmed(query):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=1000&term="
    end_url = "&field=title"

    full_url = base_url + query.replace(" ", "%20") + end_url

    content = get_page_content(full_url)

    if content is None:
        return []

    x = json.loads(content)

    try:
        return x['esearchresult']['idlist']
    except KeyError:
        return []


def get_pubmed_pub(pubid):
    full_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?retmode=json&db=pubmed&id=" + pubid

    content = get_page_content(full_url)

    if content is None:
        return []

    x = json.loads(content)

    return x


def get_author_pubs(name, affiliation):
    if affiliation is np.NaN:
        pub_ids = search_pubmed("(" + name + "[Author])")
    else:
        pub_ids = search_pubmed("(" + name + "[Author]) AND " + affiliation + "[Affiliation]")

    pubs = []
    for pub_id in pub_ids:
        pubs.append(get_pubmed_pub(pub_id))

    return pubs


def start_crawler(input_df, save_name, start=0, load_from=None):
    # Check if we should continue from existing file
    if load_from:
        result_df = pd.read_csv(load_from, index_col=0)
    else:
        result_columns = list(input_df.columns.values)
        result_columns = np.append(result_columns,
                                   ['article_title', 'authors', 'year', 'journal', 'raw',
                                    'cited_by', 'date_collected'])
        result_df = pd.DataFrame(columns=result_columns)

    # Names of authors that returned no search result
    manual_check = []

    # For each publication, construct new row
    for index, row in input_df[start:].iterrows():
        full_name = row['NameFirst'] + " " + row['NameLast']
        institution = row['institution_name']
        curr_time = datetime.datetime.now().strftime("%m-%d %H:%M")

        print(curr_time + ": Working on " + full_name + " - " + str(index) + " of " + str(
            input_df.shape[0]))

        pubs = None
        retry_count = 0
        while True:
            try:
                pubs = get_author_pubs(full_name, institution)
                break
            except Exception as e:
                if retry_count > 3:
                    break

                print("Encountered error: " + str(e))
                print("Sleeping 60s..")
                time.sleep(60)
                retry_count += 1

        # If no search result add to manual review and skip
        if pubs is None:
            manual_check.append(full_name)
            print("No results for " + full_name + ". Added to manual review.")
            continue

        print("Found " + str(len(pubs)) + " publications")

        # Construct base row that is constant between author
        base_row = []
        base_row.append(row['NameLast'])
        base_row.append(row['NameFirst'])
        base_row.append(row['institution_name'])
        base_row.append(row['profession_role'])
        base_row.append(row['dept_current'])

        # Create rows that extend the base row for each publication for an author
        for pub in pubs:
            new_row = base_row[:]

            stripped_pub = list(pub['result'].values())[1]
            title = stripped_pub['title']
            author_names = " and ".join([y['name'] for y in stripped_pub['authors']])
            try:
                year = int(stripped_pub['pubdate'][0:4])
            except ValueError:
                year = re.search(r"(\d{4})", stripped_pub['pubdate']).group(1)
            journal = stripped_pub['fulljournalname']
            raw = json.dumps(pub)
            cited_by = stripped_pub['pmcrefcount']
            date = datetime.datetime.today().strftime('%Y-%m-%d')

            new_row.append(title)
            new_row.append(author_names)
            new_row.append(year)
            new_row.append(journal)
            new_row.append(raw)
            new_row.append(cited_by)
            new_row.append(date)

            # Append row to dataframe
            result_df.loc[result_df.shape[0]] = new_row

        # Save to dataframe each time done with author
        result_df.to_csv(save_name)
        print("Completed")

        f = open('manualreview_pubmed.txt', 'w')
        f.write('\n'.join([x for x in manual_check]))
        f.close()

    print("No results were found for: ")
    print(" ".join(manual_check))

    return result_df, manual_check


def main():
    example_df = pd.read_csv('all_researchers.csv', index_col=0)
    start_crawler(example_df, 'NESCent_PubMed.csv')
    print("Completed")


if __name__ == "__main__":
    main()