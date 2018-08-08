import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath('__file__'))))

import datetime
import os
import time
from pprint import pprint

import numpy as np
import pandas as pd
import requests
from tqdm import tqdm
import scholarly_proxy as scholarly
import json
import bs4


# Printed on completion and interruption
now = datetime.datetime.now()
last_author_name = ""
last_author_index = 0
start_time = now.strftime("%Y-%m-%d %H:%M")


def get_author_by_scholarid(id):
    try:
        result = scholarly.Author(id).fill()
        return result
    except AttributeError:
        return None


def start_crawler(input_df, save_name, start=0, load_from=None):
    global last_author_index
    global last_author_name

    # Check if we should continue from existing file
    if load_from:
        result_df = pd.read_csv(load_from, index_col=0)
    else:
        result_columns = input_df.columns.values
        result_columns = np.append(result_columns, ['google_scholar_page', 'article_title', 'year','authors',  'journal', 'abstract',  'cited_by', 'raw', 'source', 'date_collected'])
        result_df = pd.DataFrame(columns=result_columns)

    base_profile_url = "https://scholar.google.com/citations?user="

    # Names of authors that returned no search result (could be due to name formatting or no Google Scholar page)
    manual_check = []


    # For each publication, construct new row
    for index, row in input_df[start:].iterrows():
        full_name = row['NameFirst'] + " " + row['NameLast']
        id = row['ScholarID']

        seconds = 60
        while(True):
            try:
                author = get_author_by_scholarid(id)
                break
            except Exception as e: 
                # Exception usually means Forbidden 403 Error
                # Wait one minute, for IP address to refresh change, then keep trying
                tqdm.write("Encountered error: " + str(e) )
                tqdm.write("Waiting " + str(seconds) + "s before retrying...")
                time.sleep(seconds)
                seconds *= 2
            
        # If no search result add to manual review and skip
        if author is None:
            manual_check.append(full_name)
            tqdm.write("No results for " + full_name + ". Added to manual review.")
            continue

        curr_time = datetime.datetime.now().strftime("%m-%d %H:%M")

        # Progress (use tqdm.write() instead of print so it does not interfere with tqdm progress bars)
        tqdm.write(curr_time + ": Working on " + author.name + " - " + str(index) + " of " + str(input_df.shape[0]) + ' (' + str(len(author.publications)) + '): ')

        # Construct Profile URL
        scholar_page = base_profile_url + author.id

        # Construct base row that is constant between author
        base_row = row.tolist()
        base_row.append(scholar_page)

        last_author_index = index
        last_author_name = full_name

        # Progress bar properties
        tqdm_publications = tqdm(author.publications)
        tqdm_publications.ncols = 80
        tqdm_publications.leave = False

        # Create rows that extend the base row for each publication for an author
        for publication in tqdm_publications:
            new_row = base_row[:]

            # Get missing data from bib
            seconds = 60
            while(True):
                try:
                    bib = publication.fill().bib
                    break
                except Exception as e: 
                    # Exception usually means Forbidden 403 Error
                    # Wait one minute for IP address to refresh change, then keep trying
                    tqdm.write("Encountered error: " + str(e) )
                    tqdm.write("Waiting " + str(seconds) + "s before retrying...")
                    time.sleep(seconds)
                    seconds *= 2

            # Get all required data and append to row
            # Use get to avoid KeyValue Exceptions and define defaults (some publications do not have authors, for exm.)
            title = bib.get('title', '')
            author_names = bib.get('author', '')
            year = bib.get('year', np.NaN)
            journal = bib.get('journal', '')
            abstract = bib.get('abstract', '')

            if isinstance(abstract, bs4.element.Tag):
                abstract = abstract.text

            raw_dict = vars(publication)

            try:
                raw_dict['bib']['abstract'] = abstract
                raw = json.dumps(raw_dict)   
            except KeyError:
                raw = json.dumps(raw_dict)   

            date = datetime.datetime.today().strftime('%Y-%m-%d')

            if hasattr(publication, 'citedby'):
                cited_by = publication.citedby
            else:
                cited_by = 0

            new_row.append(title)
            new_row.append(year)
            new_row.append(author_names)
            new_row.append(journal)
            new_row.append(abstract)
            new_row.append(cited_by)
            new_row.append(raw)
            new_row.append("Google Scholar")
            new_row.append(date)


            # Append row to dataframe
            result_df.loc[result_df.shape[0]] = new_row
            

        # Save to dataframe each time done with author
        result_df.to_csv(save_name)
        tqdm.write("Completed")

    pprint("No results were found for: ")
    pprint(manual_check)

    return result_df, manual_check


def main():
    example_df = pd.read_excel('NESCent Google Scholar IDs.xlsx')

    # # test = pd.read_csv('example2.csv', index_col=0)
    # # test = test.drop(test.index[:-60])
    # # test.to_csv("example2.csv")
    #
    # os.system('export http_proxy="http://localhost:8123"')
    # os.system('export https_proxy="http://localhost:8123"')
    #
    # if not check_tor_proxy():
    #     raise Exception('Tor proxy is not configured properly')


    try:
        scholarly.supress_warnings()
        start_crawler(example_df, 'NESCent_ID.csv', 440, 'NESCent_ID.csv')
        pprint("Completed")
        end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        pprint("Start: " + start_time + "   End:   " + end_time)
    except KeyboardInterrupt:
        pprint("Interrupted")
        end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        pprint("Start: " + start_time + "   End:   " + end_time)
        pprint("Last Worked on: " + last_author_name + " (index " + str(last_author_index) + ")")


    # 179
if __name__ == "__main__":
    main()