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
import xml.dom.minidom
from tqdm import tqdm
import re
from multiprocessing import Pool


_SESSION = requests.session()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

proxies = crawlera_proxies.proxies

def parse_authors(authors):
    authors = [x for x in authors if len(x.getElementsByTagName("LastName"))==1 and len(x.getElementsByTagName("ForeName"))==1]
    author_names = [x.getElementsByTagName("ForeName")[0].firstChild.data + " " + x.getElementsByTagName("LastName")[0].firstChild.data for x in authors]
    return author_names

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
    full_url1 = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=" + pubid + "&retmode=xml"
    full_url2 = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=' + pubid + '&retmode=json'

    with Pool(2) as p:
        contents = p.map(get_page_content, [full_url1, full_url2])

    content1 = contents[0]
    content2 = contents[1]
    
    if content1 is None:
        return []
    
    e = xml.dom.minidom.parseString(content1)

    x = json.loads(content2)
    stripped_pub = list(x['result'].values())[1]
    
    return e, stripped_pub['pmcrefcount']


def get_author_pubs(name, affiliation):
    pub_ids = search_pubmed("(" + name + "[Author])")

    pubs = []
    refs = []

    print("Found " + str(len(pub_ids)) + " publications")

    # Progress bar properties
    tqdm_pub_ids = tqdm(pub_ids)
    tqdm_pub_ids.ncols = 80
    tqdm_pub_ids.leave = False

    for pub_id in tqdm_pub_ids:
        x, y = get_pubmed_pub(pub_id)
        pubs.append(x)
        refs.append(y)

    return pubs, refs


def start_crawler(input_df, save_name, start=0, load_from=None):
    # Check if we should continue from existing file
    if load_from:
        result_df = pd.read_csv(load_from, index_col=0)
    else:
        result_columns = list(input_df.columns.values)
        result_columns = np.append(result_columns,
                                   ['article_title', 'year', 'authors', 'journal', 'abstract', 
                                    'cited_by', 'raw', 'source', 'date_collected'])
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
        refs = None
        retry_count = 0
        while True:
            try:
                pubs, refs = get_author_pubs(full_name, institution)
                break
            except Exception as e:
                if retry_count > 3:
                    break

                print("Encountered error: " + str(e))
                print("Sleeping 60s..")
                time.sleep(60)
                retry_count += 1

        

        # Construct base row that is constant between author
        base_row = []
        base_row.append(row['NameLast'])
        base_row.append(row['NameFirst'])
        base_row.append(row['institution_name'])
        base_row.append(row['profession_role'])
        base_row.append(row['dept_current'])

        # Create rows that extend the base row for each publication for an author
        for pub, ref in zip(pubs, refs):
            new_row = base_row[:]

            try:
                title = pub.getElementsByTagName("ArticleTitle")[0].firstChild.data
            except AttributeError:
                title = re.sub('<[^<]+?>', '', pub.getElementsByTagName("ArticleTitle")[0].toxml())
            except IndexError:
                title = pub.getElementsByTagName("BookTitle")[0].firstChild.data

            author_names = " and ".join(parse_authors(pub.getElementsByTagName("Author")))
            try:
                year = int(pub.getElementsByTagName("PubDate")[0].getElementsByTagName("Year")[0].firstChild.data)
            except IndexError:
                year = int(re.search('\d{4}', pub.getElementsByTagName("MedlineDate")[0].toxml()).group(0))

            try:
                abstract = pub.getElementsByTagName("AbstractText")[0].toxml()
                abstract = re.sub('<[^<]+?>', '', abstract)
            except IndexError:
                abstract = ""

            try:
                journal = pub.getElementsByTagName("Journal")[0].getElementsByTagName("Title")[0].firstChild.data
            except IndexError:
                journal = ""

            raw = re.sub('\n\s*', '', pub.toxml())
            cited_by = ref
            date = datetime.datetime.today().strftime('%Y-%m-%d')

            new_row.append(title)
            new_row.append(year)
            new_row.append(author_names)
            new_row.append(journal)
            new_row.append(abstract)
            new_row.append(cited_by)
            new_row.append(raw)
            new_row.append("PubMed")
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
    print("\n".join(manual_check))

    return result_df, manual_check


def main():
    example_df = pd.read_csv('all_researchers.csv', index_col=0 )
    start_crawler(example_df, 'NESCent_PubMed.csv', 146,'NESCent_PubMed.csv')
    print("Completed")


if __name__ == "__main__":
    main()