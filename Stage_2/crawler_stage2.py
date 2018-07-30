import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import scholarly_proxy as scholarly
import numpy as np
import requests
import datetime
import time
import json

# NOTE: scholarly also includes built in 5s wait time between queries

# Result:
# participant_name (given)
# article_title
# authors
# year
# journal
# article_reference
# citations
# date_collected

# Printed on completion and interruption
now = datetime.datetime.now()
last_author_name = ""
last_author_index = 0
start_time = now.strftime("%Y-%m-%d %H:%M")

last_refresh = time.time()


def check_tor_proxy():
    return 'Congratulations' in requests.get('http://check.torproject.org/').text


def make_APA_citation(bib):
    # Turns David B. Cheng into Cheng, D. B.
    author_names = bib.get('author', '').split(' and ')
    author_names_split = [list(reversed(name.split())) for name in author_names]
    for author in author_names_split:
        if len(author) == 0:
            continue

        author[0] = author[0] + ','
        author[-1] = author[-1][0] + '.'

        if len(author) == 3:
            author[1] = author[1] + '.'
            # Switch front and middle inital
            author[1], author[2] = author[2], author[1]

    author_names_initial = [' '.join(name) for name in author_names_split]
    if len(author_names_initial) > 1:
        authors = ', '.join(author_names_initial[0:-2]) + ' & ' + author_names_initial[-1]
    else:
        authors = author_names_initial[0]

    year = " (" + str(bib.get('year', 'n.d')) + "). "

    title = bib.get('title', '') + '. '

    journal = bib.get('journal', '') + ', ' + bib.get('volume', '(n.v.)') + "(" + bib.get('number', 'n.i.') + "), "
    pages = bib.get('pages', '') + '. '
    url = bib.get('url', '')

    citation = authors + year + title + journal + pages

    if url is not '':
        citation += "Retrieved from " + url + '. '

    return citation


def start_crawler(input_df_name, save_name, start=0, load_from=False):
    global last_refresh

    input_df = pd.read_csv(input_df_name)

    if load_from:
        result_df = pd.read_csv(save_name, index_col=0)
    else:
        result_df = pd.DataFrame(columns=["name", "initials", "institution", "department", "discipline", "publication", "author", "year", "journal", "raw", "date_collected", "cited_by"])
    
    for index, row in input_df[start:].iterrows():
        print("Working on author index: " + str(index))

        initials = row["Google Scholar Middle Initial"]

        name = row["Input.name"]
        name = name.replace('-', ' ')
        name_split = name.split()

        if len(name_split) > 2:
            query = initials
        else:
            query = " ".join([name_split[0], initials[1], name_split[1]])

        search_query = scholarly.search_pubs_query(query)

        print(query)

        no_result_count = 0
        result_number = 0

        base_row = [name, initials, row["Input.university"], row["Input.department"], row["Input.discipline"]]

        while no_result_count < 10:
            while True:
                try:
                    publication = next(search_query)
                    break
                except StopIteration:
                    # Query error, query again
                    print("Encountered StopIteration")
                    search_query = scholarly.search_pubs_query(initials)
                except AttributeError:
                    # Not a publication, skip
                    pass

            result_number += 1

            if initials not in publication.bib['author']:
                no_result_count += 1
            else:
                print("Found article for: " + initials + " (" + str(result_number) + ")" )


                seconds = 60
                while True:
                    try:
                        bib = publication.fill().bib
                        break
                    except Exception as e:
                        print(e)
                        # Exception usually means Forbidden 403 Error
                        # Wait one minute for IP address to refresh change, then keep trying

                        print("Encountered error: " + str(e))
                        print("Waiting " + str(seconds) + "s before retrying...")
                        time.sleep(seconds)
                        seconds *= 2


                # Get all required data and append to row
                # Use get to avoid KeyValue Exceptions and define defaults (some publications do not have authors, for exm.)
                title = bib.get('title', '')
                author_names = bib.get('author', '')
                year = bib.get('year', np.NaN)
                journal = bib.get('journal', '')

                # Create APA Citation from data given
                raw = json.dumps(vars(publication))

                date = datetime.datetime.today().strftime('%Y-%m-%d')

                if hasattr(publication, 'citedby'):
                    cited_by = publication.citedby
                else:
                    cited_by = 0

                new_row = base_row[:]
                new_row.append(title)
                new_row.append(author_names)
                new_row.append(year)
                new_row.append(journal)
                new_row.append(raw)
                new_row.append(date)
                new_row.append(cited_by)

                # Append row to dataframe
                result_df.loc[result_df.shape[0]] = new_row

        # Save to dataframe each time done with author
        result_df.to_csv(save_name)
        print("Completed")

    print("Finished all")


def main():
    # try:
    scholarly.supress_warnings()
    start_crawler('turk_grouped_with_middle_initial_only.csv', 'NESCent_No_ID.csv', load_from=True, start=54)
    print("Completed")
    end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print("Start: " + start_time + "   End:   " + end_time)
    # except Exception as e:
    #     print(e)
    #     print(traceback.format_exc())
    #     print("Interrupted")
    #     end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    #     print("Start: " + start_time + "   End:   " + end_time)
    #     print("Last Worked on: " + last_author_name + " (index " + str(last_author_index) + ")")


if __name__ == "__main__":
    main()