import os
import io
import glob
import json
import argparse
from urllib import parse
from unicodedata import normalize
from pathlib import Path

from tqdm import tqdm
from bs4 import BeautifulSoup
from notion.client import NotionClient
from md2notion.upload import upload, uploadBlock
from notion.block import PageBlock, PDFBlock, EmbedOrUploadBlock


def get_a_href_values(md_txt):
    values = []
    soup = BeautifulSoup(md_txt, "html.parser")
    for link in soup.findAll('a'):
        value = link.get('href')
        values.append(value)
    return values


def remove_a_href(md_txt):
    soup = BeautifulSoup(md_txt, "html.parser")
    while soup.a is not None:
        soup.a.replace_with('')
    return soup.text


def run(prop, page, file_list):
    for fname in tqdm(file_list):
        with open(fname, "r", encoding="utf-8") as mdFile:

            md_txt = mdFile.read().split("\n")
            page_title = md_txt[0].replace("#", "").strip()
            md_txt = "\n".join(md_txt[1:])
            # print('md_txt:', md_txt)

            a_href_values = get_a_href_values(md_txt)
            md_txt = remove_a_href(md_txt)

            mdFile = io.StringIO(md_txt)
            mdFile.__dict__["name"] = fname #Set this so we can resolve images later
            newPage = page.children.add_new(PageBlock, title=page_title)

            dirname = os.path.join(prop['root_dir'], os.path.splitext(fname)[0])
            block_desc_list = []
            for value in a_href_values:
                block_desc = {'type': EmbedOrUploadBlock, 'source': os.path.join(dirname, value)}
                block_desc_list.append(block_desc)
                # print(block_desc)

            def convertImagePath(imagePath, mdFilePath):
                mdFilePath_dirname = os.path.dirname(mdFilePath)
                imagePath = parse.unquote(imagePath)
                abs_image_path = os.path.join(mdFilePath_dirname, imagePath)
                ret = Path(abs_image_path)
                return ret

            upload(mdFile, newPage, imagePathFunc=convertImagePath)

            for block_desc in block_desc_list:
                uploadBlock(block_desc, newPage, mdFile.name, imagePathFunc=None)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Bear to Notion Uploader')
    parser.add_argument('-j', '--json', type=str, default='property.json', help="Property json file")
    args = parser.parse_args()
    with open(args.json, 'r') as f:
        prop = json.load(f)

    client = NotionClient(token_v2=prop['token_v2'])
    page = client.get_block(prop['page_url'])
    file_list = sorted(glob.glob("{}/**/*.md".format(prop['root_dir']), recursive=True))

    nfd_file_list = file_list
    nfc_file_list = []
    for nfd_file in nfd_file_list:
        nfc_file = normalize("NFC", nfd_file)
        nfc_file_list.append(nfc_file)

    file_list = nfc_file_list

    run(prop, page, file_list)
