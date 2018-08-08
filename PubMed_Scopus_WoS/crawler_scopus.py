import scopus
from scopus import AuthorSearch
import pandas as pd
import numpy as np
import datetime
import time
import json
import scopus_api_keys
import requests



def get_api_keys():
    keys = scopus_api_keys.keys
    for key in keys:
        yield key

key_generator = get_api_keys()

def get_author_name(x):
    name = ""
    if x.given_name is not None:
        name += x.given_name

    if x.surname is not None:
        name += " " + x.surname

    return name


def search_author_pubs(first, last, affil):
    global key_generator

    try:
        if affil is np.NaN:
            print("No affil..")
            s = AuthorSearch('AUTHLASTNAME(' + last + ') and AUTHFIRST(' + first + ')', refresh=True)
        else:
            s = AuthorSearch('AUTHLASTNAME(' + last + ') and AUTHFIRST(' + first + ') and AFFIL(' + affil + ')', refresh=True)

        if len(s.authors) == 0:
            print("Narrowing search to name only")
            s = AuthorSearch('AUTHLASTNAME(' + first + ') and AUTHFIRST(' + last + ')', refresh=True)

            if s._json == []:
                return None

        if len(s.authors)==1:
            return scopus.ScopusAuthor(s.authors[0].eid).get_abstracts()
    except requests.exceptions.HTTPError:
        print("Switching API Keys..")
        scopus.MY_API_KEY = next(key_generator)
        return search_author_pubs(first, last, affil)

    return -1


def new_entry_to_file(name, entry):
   hs = open(name,"a")
   hs.write(entry + '\n')
   hs.close()


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



    # For each publication, construct new row
    # NOTE: takes about 6s for each publication (query delay)
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
                pubs = search_author_pubs(row['NameFirst'], row['NameLast'], institution)
                break
            except Exception as e:
                if retry_count > 3:
                    break
                
                print("Encountered error: " + str(e))
                time.sleep(60)
                retry_count += 1


        # If no search result add to manual review and skip
        if pubs == -1:
            print("Multiple results for " + full_name + ". Added to multiple results review.")
            new_entry_to_file('scopus_multiple_results.txt', full_name)
            continue
        if pubs == None:
            print("No results for " + full_name + ". Added to no results review.")
            new_entry_to_file('scopus_no_results.txt', full_name)

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

            # Get all required data and append to row
            # Use get to avoid KeyValue Exceptions and define defaults (some p" and ".join([x.given_name + " " + x.surname for x in test.authors])ublications do not have authors, for exm.)
            title = pub.title
            author_names = " and ".join([get_author_name(x) for x in pub.authors])
            year = int(pub.coverDate[0:4])
            journal = pub.publicationName
            abstract = pub.abstract

            # Create APA Citation from data given
            pre_raw = vars(pub)
            pre_raw['xml'] = None
            pre_raw['_authors'] = [get_author_name(x) for x in pub.authors]
            pre_raw['_affiliations'] = [x.affilname for x in pub.affiliations]
            raw = json.dumps(pre_raw)

            date = datetime.datetime.today().strftime('%Y-%m-%d')

            cited_by = pub.citedby_count

            new_row.append(title)
            new_row.append(year)
            new_row.append(author_names)
            new_row.append(journal)
            new_row.append(abstract)
            new_row.append(cited_by)
            new_row.append(raw)
            new_row.append("Scopus")
            new_row.append(date)
            

            # Append row to dataframe
            result_df.loc[result_df.shape[0]] = new_row

        # Save to dataframe each time done with author
        result_df.to_csv(save_name)
        print("Completed")

        

        


    return result_df


def main():
    scopus.MY_API_KEY = next(key_generator)
    example_df = pd.read_csv('all_researchers.csv', index_col=0)
    start_crawler(example_df, 'NESCent_Scopus.csv', 15, 'NESCent_Scopus.csv')
    print("Completed")


if __name__ == "__main__":
    main()