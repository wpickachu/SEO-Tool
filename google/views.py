from django.shortcuts import render

import re
import os
import bs4
import csv
import ast
import json
import math
import time

import urllib
import requests
import xlsxwriter

import multiprocessing
from functools import partial
from itertools import repeat
from multiprocessing import Pool

from django.template.loader import render_to_string
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from django.conf import settings
from tinydb import TinyDB, Query
from openpyxl import load_workbook
from bs4 import BeautifulSoup, SoupStrainer
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseRedirect
from selenium.common.exceptions import TimeoutException

# Create your views here.

SEARCH_URL = "https://www.google.com/search?q="
DRIVER_PATH = settings.BASE_DIR  + '/static/google/chromedriver'
DB_PATH = settings.BASE_DIR + '/static/google/db.json'
FILE_PATH = settings.BASE_DIR + '/static/google/google.html'

WEIGHT = [0.5, 3, 3, 0.5, 3.5, 1.25, 0.5, 0.25, 1, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25]

USER_AGENT = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}

def fetch_results(search_term, number_results, language_code):
    assert isinstance(search_term, str), 'Search term must be a string'
    assert isinstance(number_results, int), 'Number of results must be an integer'
    escaped_search_term = search_term.replace(' ', '+')

    google_url = 'https://www.google.com/search?q={}&num={}&hl={}'.format(escaped_search_term, number_results, language_code)
    response = requests.get(google_url, headers=USER_AGENT)
    response.raise_for_status()

    return response.text

def parse_results(html): # get top 10 urls
    soup = BeautifulSoup(html, 'html.parser')

    found_results = []
    result_block = soup.find_all('div', attrs={'class': 'g'})
    for result in result_block:
        link = result.find('a', href=True)
        link = link['href']
        if link != '#' and link.startswith('http') == True:
            found_results.append (link)
    return found_results

def scrape_google(search_term, number_results, language_code):
    try:
        html = fetch_results(search_term, number_results, language_code)
        results = parse_results(html)
        return results
    except AssertionError:
        raise Exception("Incorrect arguments parsed to function")
    except requests.HTTPError:
        raise Exception("You appear to have been blocked by Google")
    except requests.RequestException:
        raise Exception("Appears to be an issue with your connection")


class Record:
    def __init__(self, index = 0, top_url = "Average",
                        word_cnt = 0, url = 0, 
                        mt_title = 0, mt_desc = 0, 
                        body = 0, h1 = 0, h2 = 0, h3 = 0,
                        h4 = 0, p = 0, bold = 0, italic = 0, a_txt = 0, a_title = 0,
                        span_id = 0, img_alt = 0, img_name = 0, totn_ol = 0, ol_li_cnt = 0,
                        totn_ul = 0, ul_li_cnt = 0, totn_img = 0, totn_vid = 0, totn_tbl = 0,
                        h_1 = 0, h_2 = 0, h_3 = 0, h_4 = 0, rows = 0):
        self.index = index
        self.top_url = top_url
        self.word_cnt = word_cnt
        self.url = url
        self.mt_title = mt_title
        self.mt_desc = mt_desc
        self.body = body
        self.h1 = h1
        self.h2 = h2
        self.h3 = h3
        self.h4 = h4
        self.p = p
        self.bold = bold
        self.italic = italic
        self.a_txt = a_txt
        self.a_title = a_title
        self.span_id = span_id
        self.img_alt = img_alt
        self.img_name = img_name
        self.totn_ol = totn_ol
        self.ol_li_cnt = ol_li_cnt
        self.totn_ul = totn_ul
        self.ul_li_cnt = ul_li_cnt
        self.totn_img = totn_img
        self.totn_vid = totn_vid
        self.totn_tbl = totn_tbl
        self.h_1 = h_1
        self.h_2 = h_2
        self.h_3 = h_3
        self.h_4 = h_4
        self.rows = rows

def Str2Dict (rec):
    nrecord = json.dumps(rec.__dict__)
    nrecord = ast.literal_eval (nrecord)
    return nrecord
# saveFile = open(FILE_PATH, 'w', encoding="utf-8", newline='')

# def make_url (keyword):
#     return SEARCH_URL + urllib.parse.quote_plus(keyword)

# def create_writer():    
#     writer = csv.writer(saveFile)
#     return writer

# def close_writer():
#     saveFile.close()

# WRITER = create_writer()

# def write (data):
#     to_text = []
#     to_text.append (data)
#     WRITER.writerow(to_text)

def remove_space (string):
    return " ".join(string.split())

def remove_special_characters (phrase):
    return re.sub(r'\W+',' ', str(phrase))

# find all overlapping keyword
def kw_olp_cnt(string, pattern, case_sensitive = False):
    if case_sensitive != True:
        string  = string.lower()
        pattern = pattern.lower()

    l = len(pattern)
    cnt = 0
    for c in range(0, len(string)):
        if string[c:c+l] == pattern:
            cnt += 1
    return cnt

def must_contain_all(strings):                                     
    def must_contain(markup):                                                   
        return markup is not None and all(s in markup for s in strings)         
    return must_contain

#----- this is for search with separated keywords
# text.parent for text in soup.find_all(text=must_contain_all("world", "puzzle"))]

#----- this is code for tracking time
# StartTime = time.time() 
# for i in range(TimesToDo):
#     Regex2.search(TestString) 
# Seconds = time.time() - StartTime 
# print "Character Class takes " + fpformat.fix(Seconds,3) + " seconds"

def wordcount(value):
    # Find all non-whitespace patterns.
    list = re.findall(r"(\S+)", value)
    # Return length of resulting list.
    return len(list)

# function for searching keyword (AND Mode) in href
def separated_keyword_search(src, sch, case_insensitive = True):
    sch = remove_space (sch)
    
    if case_insensitive is True:
        src = src.lower()
        sch = sch.lower()

    sub_split = sch.split(' ')

    cnt = 0
    ind = -1
    while ind <= len(src):
        for word in sub_split:
            ind = src.find(word, ind + 1)
            if ind == -1:
                return cnt
        cnt += 1

    return cnt
    
def exact_keyword_search(src, sch, case_insensitive = True):
    sch = remove_space (sch)
    
    if case_insensitive is True:
        src = src.lower()
        sch = sch.lower()

    return src.count (sch)

def content_search (data, keyword):
    cnt = 0
    for tag in data:
        cnt += wordcount(tag.text)
    return cnt

def h_tag_cnt (data, tag_name):
    return sum(1 for item in data if item.name == tag_name)

def keyword_cnt (data, keyword, setting = 0, _AND = True, case_insensitive = True):
    cnt = 0
    if len(data) == 0:  return cnt
    
    for tag in data:
        string = tag.text

        if setting == 1:    # image filename
            curString = []
            if tag.has_attr ('src'):
                curString.append (tag['src'])
            
            if tag.has_attr ('data-src'):
                curString.append (tag['data-src'])
                
            if tag.has_attr ('data-lazy-src'):
                curString.append (tag['data-lazy-src'])

            name = tag.parent.name
            if name == "noscript": continue

            if _AND == True:
                for string in curString:
                    string = remove_special_characters (string)
                    if string == None:  continue
                    curcnt = separated_keyword_search (string, keyword, case_insensitive)
                    if curcnt > 0:
                        cnt += curcnt
                        break
                continue
        elif setting == 2:  # image alt
            name = tag.parent.name
            if name == "noscript": continue
            string = tag.get('alt')
            if string == None:  continue
        elif setting == 3: # anchor title
            string = tag.get('title')
            if string == None:  continue
        elif setting == 4: # anchor name
            string = tag.get('name')
            if string == None:  continue
        elif setting == 5: # ID
            string = tag.get('id')
            if string == None:  continue

        if _AND == True:
            cnt += separated_keyword_search (string, keyword, case_insensitive)
        else:
            cnt += exact_keyword_search (string, keyword, case_insensitive)

    return cnt
    

def process_url (browser, table, keyword, param, my_url=False):
    # browser, db, keyword, param, my_url = args[0], args[1], args[2], args[3], args[4]
    # insert to db
    
    b_exists = False
    for item in table:
        if item.top_url == param:
            b_exists = True
            break

    if b_exists and my_url == False:
        return None

    print (param)
    browser.get(param)
    try:
        try:
            elem = browser.find_element_by_xpath("//*")
        except Exception as e:
            print ('exception found', format(e))

        if elem is None:
            return None

        page_source = elem.get_attribute("outerHTML")
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # case-insensitive
        try:
            meta_title = soup.find ('title')
        except Exception as e:
            print ('can not read title', format(e))

        meta_title = meta_title.text
        meta_tl_cnt = exact_keyword_search(meta_title, keyword)
        
        try:
            meta_description = soup.find ('meta', attrs={'name': 'description'})
        except Exception as e:
            print ("Can't read page")
        
        if meta_description is None:
            meta_de_cnt = 0
        else:
            meta_de_cnt = exact_keyword_search(meta_description.get('content'), keyword)

        body = soup.find('body')
        body_cnt = exact_keyword_search (body.text, keyword)

        span_tags = body.find_all('span')

        # anchor text
        a_tags = body.find_all ('a')
        anchor_cnt = keyword_cnt (a_tags, keyword, 0, False)

        a_name = []
        try:  # considering lawn-owner, lawn_owner, lawnowner by using regular expression
            a_name = soup.find_all('a', {'name' : must_contain_all( keyword.split() )})
        except:
            print ("Attribute Error: <a> tag attribute error occured")

        span_id_cnt = len(a_name)
        # count for <a name>
        span_id_cnt += keyword_cnt (a_tags, keyword, 4)
        # count for <a id>
        span_id_cnt += keyword_cnt (a_tags, keyword, 5)
        # count for <span id>
        span_id_cnt += keyword_cnt (span_tags, keyword, 5)

        # SPAN/ID = <a name> + <a id> + <span id> + <h(1-6) id> - <a href>

        tags_for_word_cnt = body.find_all (['h1', 'h2', 'h3', 'h4', 'p'])
        word_cnt = content_search (tags_for_word_cnt, keyword)

        h_1_cnt = h_tag_cnt (tags_for_word_cnt, 'h1')
        h_2_cnt = h_tag_cnt (tags_for_word_cnt, 'h2')
        h_3_cnt = h_tag_cnt (tags_for_word_cnt, 'h3')
        h_4_cnt = h_tag_cnt (tags_for_word_cnt, 'h4')

        table_rows = body.find_all ('tr')
        rows = len(table_rows)

        h1_cnt = h2_cnt = h3_cnt = h4_cnt = p_cnt = 0

        for tag in tags_for_word_cnt:
            string = tag.text
            cnt = exact_keyword_search(string, keyword)

            if tag.name == 'h1':
                h1_cnt += cnt
            elif tag.name == 'h2':
                h2_cnt += cnt
            elif tag.name == 'h3':
                h3_cnt += cnt
            elif tag.name == 'h4':
                h4_cnt += cnt
            elif tag.name == 'p':
                p_cnt += cnt

            # count for <h>
            tag_id = tag.get('id')
            if tag_id == None:  continue
            tag_id = tag_id.lower()
            span_id_cnt += separated_keyword_search (tag_id, keyword)

        # eliminate img tags in <noscript>
        img_tags = body.find_all ('img')
        img_cnt = len(img_tags)
        for img in img_tags:
            name = img.parent.name
            if name == "noscript":
                img_cnt -= 1

        img_name_cnt = keyword_cnt (img_tags, keyword, 1)
        img_alt_cnt = keyword_cnt (img_tags, keyword, 2)
        
        # bold text decorated with <strong> & <b> tags
        b_s_string = body.find_all (['strong', 'b'])
        b_s_str_cnt = keyword_cnt (b_s_string, keyword, 0, False)
        bold_txt = body.find_all ('span', class_='font-weight:bold;')
        bold_cnt = keyword_cnt (bold_txt, keyword, 0, False)
        bold_cnt = bold_cnt + b_s_str_cnt
        
        # italic text decorated with <i> & <em> & <span class="italic"> & <span class="footnote">
        em_i_tag = body.find_all (['em', 'i'])
        em_i_cnt = keyword_cnt (em_i_tag, keyword, 0)

        italic_class = []
        try:    # verify if using regular expression is ok
            italic_class = soup.find_all ('span', {'class' : lambda x : x and x in ['italic', 'footnote']})
        except Exception as e:
            print (e)
            print ("Attribute Error: something wrong with attribute class_")

        italic_cnt = keyword_cnt (italic_class, keyword, 0)
        italic_cnt += em_i_cnt

        # url
        url_cnt = separated_keyword_search (param, keyword)

        # anchor title
        a_title_cnt = keyword_cnt (a_tags, keyword, 3)

        # find all possible video tags
        video_cnt = len(body.find_all('video'))

        # consider iframe tags with link to youtube and vimeo videos
        iframe_tags = body.find_all ('iframe')
        
        for iframe_tag in iframe_tags: 
            txt = iframe_tag.get('src')
            match = txt is not None and (re.search (r'\byoutube\b', txt) or re.search (r'\bvimeo\b', txt))
            if match:
                video_cnt += 1

        # consider span tags
        for span_tag in span_tags:
            classes = span_tag.get('class')
            match1 = False
            if classes is not None:
                for mclass in classes:
                    if 'nav' in mclass or 'menu' in mclass or 'post' in mclass or 'comment' in mclass or 'icon' in mclass:
                        match1 = True
                        break

            txt = span_tag.get('id')
            match2 = txt is not None and ('nav' in txt or 'menu' in txt or 'post' in txt or 'comment' in txt)
            if match1 == False and match2 == False:
                word_cnt += wordcount(span_tag.text)

        # consider ol tags
        ol_tags = body.find_all('ol')
            
        ol_cnt = len(ol_tags)
        ol_li_cnt = 0

        for ol_tag in ol_tags:
            classes = ol_tag.get('class')
            parent_classes = ol_tag.parent.get('class')

            match1 = match2 = match3 = False
            if classes is not None:
                for mclass in classes:
                    if 'nav' in mclass or 'meta' in mclass or 'widget' in mclass  or 'side' in mclass or 'sub' in mclass or 'menu' in mclass or 'post' in mclass or 'comment' in mclass:
                        match1 = True
                        break

            if parent_classes is not None:
                for mclass in parent_classes:
                    if 'nav' in mclass or 'meta' in mclass or 'widget' in mclass  or 'side' in mclass or 'sub' in mclass or 'menu' in mclass or 'post' in mclass or 'comment' in mclass:
                        match2 = True
                        break
                
            id_attr = ol_tag.get('id')
            match3 = id_attr is not None and ('nav' in id_attr or 'widget' in id_attr or 'meta' in id_attr or 'side' in id_attr or 'sub' in id_attr or 'menu' in id_attr or 'post' in id_attr or 'comment' in id_attr)
            if match1 or match2 or match3:
                ol_cnt -= 1
            else:
                word_cnt += wordcount(ol_tag.text)
                lis = ol_tag.find_all('li')
                if lis is not None:
                    ol_li_cnt += len(lis)

        # consider ul tags
        ul_tags = body.find_all('ul')
            
        ul_cnt = len(ul_tags)
        ul_li_cnt = 0

        for ul_tag in ul_tags:
            classes = ul_tag.get('class')
            parent_classes = ul_tag.parent.get('class')

            match1 = match2 = match3 = False
            if classes is not None:
                for mclass in classes:
                    if 'nav' in mclass or 'widget' in mclass or 'meta' in mclass or 'side' in mclass or 'sub' in mclass or 'menu' in mclass or 'post' in mclass or 'comment' in mclass:
                        match1 = True
                        break
            
            if parent_classes is not None:
                for mclass in parent_classes:
                    if 'nav' in mclass or 'side' in mclass or 'meta' in mclass or 'widget' in mclass or 'sub' in mclass or 'menu' in mclass or 'post' in mclass or 'comment' in mclass:
                        match2 = True
                        break

            id_attr = ul_tag.get('id')
            match3 = id_attr is not None and ('nav' in id_attr or 'meta' in id_attr or 'widget' in id_attr  or 'side' in id_attr or 'sub' in id_attr or 'menu' in id_attr or 'post' in id_attr or 'comment' in id_attr)
            if match1 or match2 or match3:
                ul_cnt -= 1
            else:
                word_cnt += wordcount(ul_tag.text)
                lis = ul_tag.find_all('li')
                if lis is not None:
                    ul_li_cnt += len(lis)

        # consider p tags for word
        # p_tags = body.find_all('p')
        
        # for p_tag in p_tags:
        #     parent_classes = p_tag.parent.get('class')

        #     if parent_classes is not None and (lambda classe: 'comment' in classe for classe in parent_classes):
        #         word_cnt -= wordcount (p_tag.text)

        table_cnt = len(body.find_all('table'))
    
        record = Record(index, param, word_cnt, url_cnt, meta_tl_cnt, meta_de_cnt, 
                        body_cnt, h1_cnt, h2_cnt, h3_cnt, h4_cnt, p_cnt, bold_cnt, 
                        italic_cnt, anchor_cnt, a_title_cnt, span_id_cnt,
                        img_alt_cnt, img_name_cnt, ol_cnt, ol_li_cnt, ul_cnt, ul_li_cnt, 
                        img_cnt, video_cnt, table_cnt, h_1_cnt, h_2_cnt, h_3_cnt, h_4_cnt, rows)
        
    except TimeoutException:
        pass
    return record

def get_average (table):
    av_record = Record()
    
    count = len(table)
    for one in table:
        av_record.word_cnt += one.word_cnt
        av_record.url += one.url
        av_record.mt_title += one.mt_title
        av_record.mt_desc += one.mt_desc
        av_record.body += one.body
        av_record.h1 += one.h1
        av_record.h2 += one.h2
        av_record.h3 += one.h3
        av_record.h4 += one.h4
        av_record.p += one.p
        av_record.bold += one.bold
        av_record.italic += one.italic
        av_record.a_txt += one.a_txt
        av_record.a_title += one.a_title
        av_record.span_id += one.span_id
        av_record.img_alt += one.img_alt
        av_record.img_name += one.img_name
        av_record.totn_ol += one.totn_ol
        av_record.ol_li_cnt += one.ol_li_cnt
        av_record.totn_ul += one.totn_ul
        av_record.ul_li_cnt += one.ul_li_cnt
        av_record.totn_img += one.totn_img
        av_record.totn_vid += one.totn_vid
        av_record.totn_tbl += one.totn_tbl
        av_record.h_1 += one.h_1
        av_record.h_2 += one.h_2
        av_record.h_3 += one.h_3
        av_record.h_4 += one.h_4
        av_record.rows += one.rows

    av_record.word_cnt = "{:10.1f}".format(av_record.word_cnt / count)
    av_record.url = "{:10.1f}".format(av_record.url / count)
    av_record.mt_title = "{:10.1f}".format(av_record.mt_title / count)
    av_record.mt_desc = "{:10.1f}".format(av_record.mt_desc / count)
    av_record.body = "{:10.1f}".format(av_record.body / count)
    av_record.h1 = "{:10.1f}".format(av_record.h1 / count)
    av_record.h2 = "{:10.1f}".format(av_record.h2 / count)
    av_record.h3 = "{:10.1f}".format(av_record.h3 / count)
    av_record.h4 = "{:10.1f}".format(av_record.h4 / count)
    av_record.p = "{:10.1f}".format(av_record.p / count)
    av_record.bold = "{:10.1f}".format(av_record.bold / count)
    av_record.italic = "{:10.1f}".format(av_record.italic / count)
    av_record.a_txt = "{:10.1f}".format(av_record.a_txt / count)
    av_record.a_title = "{:10.1f}".format(av_record.a_title / count)
    av_record.span_id = "{:10.1f}".format(av_record.span_id / count)
    av_record.img_alt = "{:10.1f}".format(av_record.img_alt / count)
    av_record.img_name = "{:10.1f}".format(av_record.img_name / count)
    av_record.totn_ol = "{:10.1f}".format(av_record.totn_ol / count)
    av_record.ol_li_cnt = "{:10.1f}".format(av_record.ol_li_cnt / count)
    av_record.totn_ul = "{:10.1f}".format(av_record.totn_ul / count)
    av_record.ul_li_cnt = "{:10.1f}".format(av_record.ul_li_cnt / count)
    av_record.totn_img = "{:10.1f}".format(av_record.totn_img / count)
    av_record.totn_vid = "{:10.1f}".format(av_record.totn_vid / count)
    av_record.totn_tbl = "{:10.1f}".format(av_record.totn_tbl / count)
    av_record.h_1 = "{:10.1f}".format(av_record.h_1 / count)
    av_record.h_2 = "{:10.1f}".format(av_record.h_2 / count)
    av_record.h_3 = "{:10.1f}".format(av_record.h_3 / count)
    av_record.h_4 = "{:10.1f}".format(av_record.h_4 / count)
    av_record.rows = "{:10.1f}".format(av_record.rows / count)

    return av_record

def make_recommendation (nrecord, av_record):
    recom = Record()
    recom.top_url = "Recommendation"

    diff = nrecord.word_cnt - math.ceil(float(av_record.word_cnt))
    calc = "(Optional) Remove " if diff > 0 else "Add "
    recom.word_cnt = calc + (str)(abs(diff))
    recom.word_cnt = "No Change" if diff == 0 else recom.word_cnt

    diff = nrecord.body - math.ceil(float(av_record.body))
    calc = "Remove " if diff > 0 else "Add "
    recom.body = calc + (str)(abs(diff))
    recom.body = "No Change" if diff == 0 else recom.body

    # url
    diff = nrecord.url - 1
    calc = "Remove " if diff > 0 else "Add "
    recom.url = calc + (str)(abs(diff))
    recom.url = "No Change" if diff == 0 else recom.url

    # meta title
    diff = nrecord.mt_title - 1
    calc = "Remove " if diff > 0 else "Add "
    recom.mt_title = calc + (str)(abs(diff))
    recom.mt_title = "No Change" if diff == 0 else recom.mt_title

    # meta description
    diff = nrecord.mt_desc - 1
    calc = "Remove " if diff > 0 else "Add "
    recom.mt_desc = calc + (str)(abs(diff))
    recom.mt_desc = "No Change" if diff == 0 else recom.mt_desc

    # h1 tag
    diff = nrecord.h1 - 1
    calc = "Remove " if diff > 0 else "Add "
    recom.h1 = calc + (str)(abs(diff))
    recom.h1 = "No Change" if diff == 0 else recom.h1

    # h2 tag
    diff = nrecord.h2 - math.ceil(float(av_record.h2))
    if nrecord.h2 == 0 and diff > 0:   diff = 1
    calc = "Remove " if diff > 0 else "Add "
    recom.h2 = calc + (str)(abs(diff))
    recom.h2 = "No Change" if (diff == 0 and nrecord.h2 > 0) or (diff == 1 and nrecord.h2 == 1) else recom.url

    # h3 tag
    diff = nrecord.h3 - math.ceil(float(av_record.h3))
    if math.ceil(float(av_record.h3)) < 1 and nrecord.h3 > 1: diff -= 1
    if nrecord.h3 == 0 and diff > 0: diff = 1
    calc = "Remove " if diff > 0 else "Add "
    recom.h3 = calc + (str)(abs(diff))
    recom.h3 = "No Change" if diff == 0 or (float(av_record.h3) == 0 and (nrecord.h3 == 0 or nrecord.h3 == 1)) else recom.h3
 
    # h4 tag
    diff = nrecord.h4 - math.ceil(float(av_record.h4))
    if math.ceil(float(av_record.h4)) < 1 and nrecord.h4 > 1: diff -= 1
    if nrecord.h4 == 0 and diff > 0: diff = 1
    calc = "Remove " if diff > 0 else "Add "
    recom.h4 = calc + (str)(abs(diff))
    recom.h4 = "No Change" if diff == 0 or (float(av_record.h4) == 0 and (nrecord.h4 == 0 or nrecord.h4 == 1)) else recom.h4

    # p tag
    diff = nrecord.p - math.ceil(float(av_record.p) + 2.0)
    calc = "Remove " if diff > 0 else "Add "
    recom.p = calc + (str)(abs(diff))
    recom.p = "No Change" if diff == 0 else recom.p

    # bold
    diff = nrecord.bold - math.ceil(float(av_record.bold))
    if math.ceil(float(av_record.bold)) < 1 and nrecord.bold > 1: diff -= 1
    if nrecord.bold == 0 and diff > 0: diff = 1
    calc = "Remove " if diff > 0 else "Add "
    recom.bold = calc + (str)(abs(diff))
    recom.bold = "No Change" if diff == 0 or (float(av_record.bold) == 0 and (nrecord.bold == 0 or nrecord.bold == 1)) else recom.bold

    # anchor text
    diff = nrecord.a_txt - math.ceil(float(av_record.a_txt))
    if math.ceil(float(av_record.a_txt)) < 1 and nrecord.a_txt > 1: diff -= 1
    if nrecord.a_txt == 0 and diff > 0: diff = 1
    calc = "Remove " if diff > 0 else "Add "
    recom.a_txt = calc + (str)(abs(diff))
    recom.a_txt = "No Change" if diff == 0 or (float(av_record.a_txt) == 0 and (nrecord.a_txt == 0 or nrecord.a_txt == 1)) else recom.a_txt

    # anchor title
    diff = nrecord.a_title - math.ceil(float(av_record.a_title))
    if math.ceil(float(av_record.a_title)) < 1 and nrecord.a_title > 1: diff -= 1
    if nrecord.a_title == 0 and diff > 0: diff = 1
    calc = "Remove " if diff > 0 else "Add "
    recom.a_title = calc + (str)(abs(diff))
    recom.a_title = "No Change" if diff == 0 or (float(av_record.a_title) == 0 and (nrecord.a_title == 0 or nrecord.a_title == 1)) else recom.a_title

    # span id
    diff = nrecord.span_id - math.ceil(float(av_record.span_id))
    if math.ceil(float(av_record.span_id)) < 1 and nrecord.span_id > 1: diff -= 1
    if nrecord.span_id == 0 and diff > 0: diff = 1
    calc = "Remove " if diff > 0 else "Add "
    recom.span_id = calc + (str)(abs(diff))
    recom.span_id = "No Change" if diff == 0 or (float(av_record.span_id) == 0 and (nrecord.span_id == 0 or nrecord.span_id == 1)) else recom.span_id

    # image alt
    diff = nrecord.img_alt - math.ceil(float(av_record.img_alt))
    if math.ceil(float(av_record.img_alt)) < 1 and nrecord.img_alt > 1: diff -= 1
    if nrecord.img_alt == 0 and diff > 0: diff = 1
    calc = "Remove " if diff > 0 else "Add "
    recom.img_alt = calc + (str)(abs(diff))
    recom.img_alt = "No Change" if diff == 0 or (float(av_record.img_alt) == 0 and (nrecord.img_alt == 0 or nrecord.img_alt == 1)) else recom.img_alt

    # image name
    diff = nrecord.img_name - math.ceil(float(av_record.img_name))
    if math.ceil(float(av_record.img_name)) < 1 and nrecord.img_name > 1: diff -= 1
    if nrecord.img_name == 0 and diff > 0: diff = 1
    calc = "Remove " if diff > 0 else "Add "
    recom.img_name = calc + (str)(abs(diff))
    recom.img_name = "No Change" if diff == 0 or (float(av_record.img_name) == 0 and (nrecord.img_name == 0 or nrecord.img_name == 1)) else recom.img_name

    diff = nrecord.totn_ol - math.ceil(float(av_record.totn_ol))
    calc = "Remove " if diff > 0 else "Add "
    recom.totn_ol = calc + (str)(abs(diff))
    recom.totn_ol = "No Change" if diff == 0 else recom.totn_ol

    diff = nrecord.ol_li_cnt - math.ceil(float(av_record.ol_li_cnt))
    calc = "Remove " if diff > 0 else "Add "
    recom.ol_li_cnt = calc + (str)(abs(diff))
    recom.ol_li_cnt = "No Change" if diff == 0 else recom.ol_li_cnt

    diff = nrecord.totn_ul - math.ceil(float(av_record.totn_ul))
    calc = "Remove " if diff > 0 else "Add "
    recom.totn_ul = calc + (str)(abs(diff))
    recom.totn_ul = "No Change" if diff == 0 else recom.totn_ul

    diff = nrecord.ul_li_cnt - math.ceil(float(av_record.ul_li_cnt))
    calc = "Remove " if diff > 0 else "Add "
    recom.ul_li_cnt = calc + (str)(abs(diff))
    recom.ul_li_cnt = "No Change" if diff == 0 else recom.ul_li_cnt

    diff = nrecord.totn_img - math.ceil(float(av_record.totn_img))
    calc = "Remove " if diff > 0 else "Add "
    recom.totn_img = calc + (str)(abs(diff))
    recom.totn_img = "No Change" if diff == 0 else recom.totn_img

    diff = nrecord.totn_vid - math.ceil(float(av_record.totn_vid))
    calc = "Remove " if diff > 0 else "Add "
    recom.totn_vid = calc + (str)(abs(diff))
    recom.totn_vid = "No Change" if diff == 0 else recom.totn_vid

    diff = nrecord.totn_tbl - math.ceil(float(av_record.totn_tbl))
    calc = "Remove " if diff > 0 else "Add "
    recom.totn_tbl = calc + (str)(abs(diff))
    recom.totn_tbl = "No Change" if diff == 0 else recom.totn_tbl

    diff = nrecord.h_1 - math.ceil(float(av_record.h_1))
    calc = "Remove " if diff > 0 else "Add "
    recom.h_1 = calc + (str)(abs(diff))
    recom.h_1 = "No Change" if diff == 0 else recom.h_1

    diff = nrecord.h_2 - math.ceil(float(av_record.h_2))
    calc = "Remove " if diff > 0 else "Add "
    recom.h_2 = calc + (str)(abs(diff))
    recom.h_2 = "No Change" if diff == 0 else recom.h_2

    diff = nrecord.h_3 - math.ceil(float(av_record.h_3))
    calc = "Remove " if diff > 0 else "Add "
    recom.h_3 = calc + (str)(abs(diff))
    recom.h_3 = "No Change" if diff == 0 else recom.h_3

    diff = nrecord.h_4 - math.ceil(float(av_record.h_4))
    calc = "Remove " if diff > 0 else "Add "
    recom.h_4 = calc + (str)(abs(diff))
    recom.h_4 = "No Change" if diff == 0 else recom.h_4

    diff = nrecord.rows - math.ceil(float(av_record.rows))
    calc = "Remove " if diff > 0 else "Add "
    recom.rows = calc + (str)(abs(diff))
    recom.rows = "No Change" if diff == 0 else recom.rows
    return recom
    

def get_optimized_value (nrecord, av_record):
    optimized = 0.0

    diff = nrecord.word_cnt - math.ceil(float(av_record.word_cnt))
    calc = 2 if diff > 0 else 0
    calc = 1 if diff == 0 else calc
    optimized += calc * WEIGHT[0]

    # url
    diff = nrecord.url - 1
    calc = 2 if diff > 0 else 0
    calc = 1 if diff == 0 else calc
    optimized += calc * WEIGHT[1]

    # meta title
    diff = nrecord.mt_title - 1
    calc = 2 if diff > 0 else 0
    calc = 1 if diff == 0 else calc
    optimized += calc * WEIGHT[2]

    # meta description
    diff = nrecord.mt_desc - 1
    calc = 2 if diff > 0 else 0
    calc = 1 if diff == 0 else calc
    optimized += calc * WEIGHT[3]

    # h1 tag
    diff = nrecord.h1 - 1
    calc = 2 if diff > 0 else 0
    calc = 1 if diff == 0 else calc
    optimized += calc * WEIGHT[4]

    # h2 tag
    diff = nrecord.h2 - math.ceil(float(av_record.h2))
    if nrecord.h2 == 0 and diff > 0:   diff = 1
    calc = 2 if diff > 0 else 0
    calc = 1 if (diff == 0 and nrecord.h2 > 0) or (diff == 1 and nrecord.h2 == 1) else calc
    optimized += calc * WEIGHT[5]

    # h3 tag
    diff = nrecord.h3 - math.ceil(float(av_record.h3))
    if math.ceil(float(av_record.h3)) < 1 and nrecord.h3 > 1: diff -= 1
    if nrecord.h3 == 0 and diff > 0: diff = 1
    calc = 2 if diff > 0 else 0
    calc = 1 if diff == 0 or (float(av_record.h3) == 0 and (nrecord.h3 == 0 or nrecord.h3 == 1)) else calc
    optimized += calc * WEIGHT[6]
 
    # h4 tag
    diff = nrecord.h4 - math.ceil(float(av_record.h4))
    if math.ceil(float(av_record.h4)) < 1 and nrecord.h4 > 1: diff -= 1
    if nrecord.h4 == 0 and diff > 0: diff = 1
    calc = 2 if diff > 0 else 0
    calc = 1 if diff == 0 or (float(av_record.h4) == 0 and (nrecord.h4 == 0 or nrecord.h4 == 1)) else calc
    optimized += calc * WEIGHT[7]

    # p tag
    diff = nrecord.p - math.ceil(float(av_record.p) + 2.0)
    calc = 2 if diff > 0 else 0
    calc = 1 if diff == 0 else calc
    optimized += calc * WEIGHT[8]

    # bold
    diff = nrecord.bold - math.ceil(float(av_record.bold))
    if math.ceil(float(av_record.bold)) < 1 and nrecord.bold > 1: diff -= 1
    if nrecord.bold == 0 and diff > 0: diff = 1
    calc = 2 if diff > 0 else 0
    calc = 1 if diff == 0 or (float(av_record.bold) == 0 and (nrecord.bold == 0 or nrecord.bold == 1)) else calc
    optimized += calc * WEIGHT[9]

    # anchor text
    diff = nrecord.a_txt - math.ceil(float(av_record.a_txt))
    if math.ceil(float(av_record.a_txt)) < 1 and nrecord.a_txt > 1: diff -= 1
    if nrecord.a_txt == 0 and diff > 0: diff = 1
    calc = 2 if diff > 0 else 0
    calc = 1 if diff == 0 or (float(av_record.a_txt) == 0 and (nrecord.a_txt == 0 or nrecord.a_txt == 1)) else calc
    optimized += calc * WEIGHT[10]

    # anchor title
    diff = nrecord.a_title - math.ceil(float(av_record.a_title))
    if math.ceil(float(av_record.a_title)) < 1 and nrecord.a_title > 1: diff -= 1
    if nrecord.a_title == 0 and diff > 0: diff = 1
    calc = 2 if diff > 0 else 0
    calc = 1 if diff == 0 or (float(av_record.a_title) == 0 and (nrecord.a_title == 0 or nrecord.a_title == 1)) else calc
    optimized += calc * WEIGHT[11]

    # span id
    diff = nrecord.span_id - math.ceil(float(av_record.span_id))
    if math.ceil(float(av_record.span_id)) < 1 and nrecord.span_id > 1: diff -= 1
    if nrecord.span_id == 0 and diff > 0: diff = 1
    calc = 2 if diff > 0 else 0
    calc = 1 if diff == 0 or (float(av_record.span_id) == 0 and (nrecord.span_id == 0 or nrecord.span_id == 1)) else calc
    optimized += calc * WEIGHT[12]

    # image alt
    diff = nrecord.img_alt - math.ceil(float(av_record.img_alt))
    if math.ceil(float(av_record.img_alt)) < 1 and nrecord.img_alt > 1: diff -= 1
    if nrecord.img_alt == 0 and diff > 0: diff = 1
    calc = 2 if diff > 0 else 0
    calc = 1 if diff == 0 or (float(av_record.img_alt) == 0 and (nrecord.img_alt == 0 or nrecord.img_alt == 1)) else calc
    optimized += calc * WEIGHT[13]

    # image name
    diff = nrecord.img_name - math.ceil(float(av_record.img_name))
    if math.ceil(float(av_record.img_name)) < 1 and nrecord.img_name > 1: diff -= 1
    if nrecord.img_name == 0 and diff > 0: diff = 1
    calc = 2 if diff > 0 else 0
    calc = 1 if diff == 0 or (float(av_record.img_name) == 0 and (nrecord.img_name == 0 or nrecord.img_name == 1)) else calc
    optimized += calc * WEIGHT[14]

    optimized = optimized / 15 * 100
    return optimized

def get_keyword_difficulty(table, avg):
    percentage = 0.0
    for i in range(len(table)):
        percentage += get_optimized_value (table[i], avg)
    percentage /= 10
    return math.ceil(percentage)

# View Functions
def index (request):
    total_added = 0

    if request.method == 'POST':
        keyword = request.POST.get('keyword')
        my_url = request.POST.get('myurl')

        StartTime = time.time()

        # db = TinyDB(DB_PATH)
        # print (keyword in db.tables())

        # if keyword in db.tables():
        #     print ("table already exists")
        #     table = db.table(keyword)
        # else:
        #     print ("create new table")
        #     table = db.table (keyword)
        table = []

        options = Options()
        options.headless = True
        
        try:
            browser = webdriver.Chrome(DRIVER_PATH, options=options)
        except Exception as e:
            print (e)

        try:
            # get top 10 urls
            top_urls = scrape_google(keyword, 10, "en")

            for top_url in top_urls:
                
                record = process_url (browser, table, keyword, top_url)
                if record is None:
                    continue

                total_added += 1
                record.index = total_added
                table.append (record)
                print ("Adding ...", total_added)

                if total_added == 10:
                    break
        
            av_record = get_average (table)

            keyword_difficulty = get_keyword_difficulty (table, av_record)
            print ("Calculating Keyword difficulty...")

            total_added += 1
            av_record.index = total_added
            table.append (av_record)
            print ("Adding average...", total_added)

            nrecord = process_url (browser, table, keyword, my_url, True)
            if nrecord is not None:
                total_added += 1
                nrecord.index = total_added
                table.append (nrecord)
                print ("Adding my url...", total_added)

        finally:
            print ("browser closed")
            browser.close()

        recom = make_recommendation (nrecord, av_record)        
        total_added += 1            
        recom.index = total_added
        print ("Adding recommendation...", total_added)

        optimization = get_optimized_value (nrecord, av_record)
        print ("Calculating Keyword difficulty...")

        Seconds = time.time() - StartTime
        time_text = "{:10.1f}".format(Seconds) + " seconds"

        response_data = {
            'keyword' : keyword,
            'myurl'   : my_url,
            'time'    : time_text,
            'data'    : table,
            'd_avg'   : av_record,
            'd_myurl' : nrecord,
            'recom'   : recom,
            'optimization' : math.ceil(optimization),
            'keyword_difficulty' : keyword_difficulty,
        }

        return render(request, 'index.html', response_data)
    else:
        return render(request, 'index.html')

# @csrf_exempt
# def search (request):
#     if request.method == 'POST':
#         json_str = request.body.decode(encoding='UTF-8')
#         json_obj = json.loads(json_str)
#         response_data = {
#             'keyword': json_obj.keyword,
#             'myurl': json_obj.myurl,
#             'time': json_obj.time,
#             'data': json_obj.data
#         }
#         html = render_to_string('search.html', response_data)
#         return HttpResponse(html)
