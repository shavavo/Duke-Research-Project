from bs4 import BeautifulSoup

import requests
import mimetypes

import io
from io import StringIO

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage

import textract


def get_text_from_url(url, verify=True):
    try:
        response = requests.get(url, verify=verify)
    except requests.exceptions.RequestException as e:
        print("ERROR with " + url)
        print(e)
        return ""

    content_type = response.headers['content-type']
    extension = mimetypes.guess_extension(content_type)

    # HTML
    if extension is None or extension == '.htm':
        soup = BeautifulSoup(response.content, 'lxml')

        for script in soup(["script", "style"]):
            script.extract()  # rip it out

        text = soup.get_text()

        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return text

    # PDFs
    elif extension == '.pdf':
        open('./temp/temp.pdf', 'wb').write(response.content)
        return textract.process('./temp/temp.pdf').decode('utf-8')
    elif extension == '.rtf':
        open('./temp/temp.rtf', 'wb').write(response.content)
        return textract.process('./temp/temp.rtf').decode('utf-8')
    elif extension == '.docx':
        open('./temp/temp.docx', 'wb').write(response.content)
        return textract.process('./temp/temp.docx').decode('utf-8')
    elif extension == '.doc':
        open('./temp/temp.doc', 'wb').write(response.content)
        return textract.process('./temp/temp.doc').decode('utf-8')
    else:
        return ""
