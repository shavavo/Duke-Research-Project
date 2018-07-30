import pandas as pd
from tqdm import tqdm
import peewee
from peewee import *
import sqlCredentials

db = MySQLDatabase(sqlCredentials.name, user=sqlCredentials.user, passwd=sqlCredentials.password, port=sqlCredentials.port)


class BaseModel(Model):
    class Meta:
        database = db


class Publications(BaseModel):
    authid = IntegerField(db_column='authid', null=False)
    authname = TextField(db_column='authname', null=False)
    title = TextField(db_column='title', null=False, primary_key=True)
    authors = TextField(db_column='authors', null=False)
    year = IntegerField(db_column='year', null=False)
    journal = TextField(db_column='journal', null=False)
    source = TextField(db_column='source', null=False)
    raw = TextField(db_column='raw', null=False)


class Citations(BaseModel):
    title = TextField(db_column='title', null=False)
    year = IntegerField(db_column='year', null=False)
    journal = TextField(db_column='journal', null=False)
    citation_count = IntegerField(db_column='citation_count', null=False)


class CVPersonalWebsites(BaseModel):
    class Meta:
        db_table = 'CV_personal_websites'

    authname = TextField(db_column='authname', null=False)
    website1_url = TextField(db_column='website1_url', null=False)
    website2_url = TextField(db_column='website2_url', null=False)
    website3_url = TextField(db_column='website3_url', null=False)
    website4_url = TextField(db_column='website4_url', null=False)
    website5_url = TextField(db_column='website5_url', null=False)
    website1_raw = TextField(db_column='website1_raw', null=False)
    website2_raw = TextField(db_column='website2_raw', null=False)
    website3_raw = TextField(db_column='website3_raw', null=False)
    website4_raw = TextField(db_column='website4_raw', null=False)
    website5_raw = TextField(db_column='website5_raw', null=False)
    full_name = TextField(db_column="full_name", null=False)
    publication = TextField(db_column="publication", null=False)


def populate_publications(file_name):
    data = pd.read_csv(file_name)
    data = data.fillna(-1)

    for index, row in tqdm(data.iterrows()):
        authid = row['UID']
        authname = row["NameFirst"] + " " + row["NameLast"]
        title = row["article_title"]
        authors = row["authors"]
        year = row["year"]
        journal = row["journal"]
        source = "Google Scholar"
        raw = row["reference"]

        try:
            Publications.create(authid=authid, authname=authname, title=title, authors=authors, year=year, journal=journal, source=source, raw=raw)
        except Exception as e:
            print(e)
            print("Interrupted at index: " + str(index))


def populate_citations(file_name):
    data = pd.read_csv(file_name)
    data = data.fillna(-1)

    for index, row in tqdm(data.iterrows()):
        title = row['article_title']
        year = row['year']
        journal = row['journal']
        citation_count = row['citations']

        try:
            Citations.create(title=title, year=year, journal=journal, citation_count=citation_count)
        except Exception as e:
            print(e)
            print("Interrupted at index: " + str(index))


def populate_CVs(file_name):
    data = pd.read_csv(file_name)
    data = data.fillna(-1)

    for index, row in tqdm(data.iterrows()):

        authname = row['Input.name']
        website1_url = row['top_1_url']
        website2_url = row['top_2_url']
        website3_url = row['top_3_url']
        website4_url = row['top_4_url']
        website5_url = row['top_5_url']
        website1_raw = row['top_1_raw']
        website2_raw = row['top_2_raw']
        website3_raw = row['top_3_raw']
        website4_raw = row['top_4_raw']
        website5_raw = row['top_5_raw']
        publication = row['unconfirmed_publications']

        name = row["Input.name"]
        name_split = name.split('-')

        # Handle cases like "Donald-Mac Lump"
        if len(name_split) == 2:
            full_name = " ".join(name_split)
        else:
            initials = row["Google Scholar Middle Initial"]

            if isinstance(initials, int):
                full_name = name
            else:
                middle = initials[1]
                first = name_split[0].split()[0]
                last = name_split[0].split()[1]
                full_name = first + " " + middle + " " + last

        try:
            CVPersonalWebsites.create(authname=authname,
                                      website1_url=website1_url,
                                      website2_url=website2_url,
                                      website3_url=website3_url,
                                      website4_url=website4_url,
                                      website5_url=website5_url,
                                      website1_raw=website1_raw,
                                      website2_raw=website2_raw,
                                      website3_raw=website3_raw,
                                      website4_raw=website4_raw,
                                      website5_raw=website5_raw,
                                      publication=publication,
                                      full_name=full_name)
        except Exception as e:
            print(e)
            print("Interrupted at index: " + str(index))


def main():
    db.connect()

    # populate_publications('NESCent_publications/nescent_ID.csv')
    # populate_citations('Stage_1/NESCent_ID_citations.csv')
    # populate_CVs("Stage_2/turk_grouped.csv")

    db.close()




if __name__ == "__main__":
    main()

