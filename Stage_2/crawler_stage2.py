import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import scholarly_proxy as scholarly
import numpy as np
import requests
import datetime
import time
import json
import bs4

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




def start_crawler(input_df_name, save_name, start=0, load_from=False):
    input_df = pd.read_csv(input_df_name)

    if load_from:
        result_df = pd.read_csv(save_name, index_col=0)
    else:
        result_df = pd.DataFrame(columns=["NameFirst", "NameLast", "institution", "profession", "dept_current", "article_title", "year", "authors", "journal", "abstract", "cited_by", "raw", "source", "date_collected"])
    
    for index, row in input_df[start:].iterrows():
        print("Working on author index: " + str(index))

        initials = row["Google Scholar Middle Initial"]

        name = row["Input.name"]
        name_split = name.replace('-', ' ').split()

        if len(name_split) > 2:
            query = initials
        else:
            query = " ".join([name_split[0], initials[1], name_split[1]])

        search_query = scholarly.search_pubs_query(query)

        print(query)

        no_result_count = 0
        result_number = 0

        firstName = " ".join(name.split()[0:-1])
        lastName = name.split()[-1]

        base_row = [firstName, lastName, row["Input.university"], row["Input.discipline"], row["Input.department"] ]

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

                new_row = base_row[:]
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
        print("Completed")

    print("Finished all")


def main():
    scholarly.supress_warnings()
    start_crawler('turk_grouped_with_middle_initial_only.csv', 'NESCent_No_ID.csv', 2, True)
    print("Completed")
    end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print("Start: " + start_time + "   End:   " + end_time)
  


if __name__ == "__main__":
    main()