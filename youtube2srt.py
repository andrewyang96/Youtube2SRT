import urllib, urllib2
from urllib2 import HTTPError
import xml.etree.ElementTree as ET
import pysrt
import HTMLParser

"""
Youtube2SRT is a module for fetching Youtube subtitles and converting them to SRT (SubRip) format files.
"""

h = HTMLParser.HTMLParser()

class SubLangData():
    """
    Class for keeping track of a Youtube video's available subtitle languages.
    """
    def __init__(self, d, default_lang=None):
        """
        d - A dict with key-value pair of lang_code: subtitle_stream_name (could be None).
        default_lang - a string representing the default language code. Defaults to None.
        """
        self.dict = d
        self.default_lang = default_lang
    def is_empty(self):
        """
        SubLangData instance is empty if self.dict is empty and self.default_lang is None.
        """
        return self.dict == {} and self.default_lang == None


def get_subtitle_data(videoID):
    """
    videoID - a string of alphanumeric characters in the Youtube URL after watch?v=
    Returns an ET, or None if 404 error occurs.
    """
    try:
        response = urllib2.urlopen("https://www.youtube.com/api/timedtext?caps=asr&hl=en-US&tlangs=1&type=list&v={}&vssids=1".format(videoID))
    except HTTPError:
        return None
    xml = response.read()
    response.close()
    return ET.fromstring(xml)


def get_subtitle_languages(videoID):
    """
    videoID - a string of alphanumeric characters in the Youtube URL after watch?v=
    Returns a SubLangData instance.
    """
    root = get_subtitle_data(videoID)
    result = {}
    default_lang = None
    for child in root:
        if "name" in child.attrib:
            if "lang_default" in child.attrib:
                default_lang = child.attrib["lang_code"]
            result[child.attrib["lang_code"]] = child.attrib["name"]
        else: # translated languages don't have "name" key
            if child.attrib["lang_code"] not in result: # could exist duplicates
                result[child.attrib["lang_code"]] = None
    return SubLangData(result, default_lang)



def get_youtube_subtitle(videoID, lang_code="en", allow_translate=False):
    """
    videoID - a string of alphanumeric characters in the Youtube URL after watch?v=
    lang_code - a string representing the language code of the desired subtitle
    allow_translate - a boolean specifying whether using Google Translate is OK
    Returns an ET, or None if 404 error occurs or if no subtitles are available.
    """
    sub_langs = get_subtitle_languages(videoID)
    
    if sub_langs.is_empty():
        return None
    
    is_translated = sub_langs.dict[lang_code] is None # if name is none, then it's translated

    if is_translated and not allow_translate:
        return None
    
    try:
        if is_translated:
            url = u"https://www.youtube.com/api/timedtext?lang={}&name={}&tlang={}&v={}".format(sub_langs.default_lang, urllib.quote(sub_langs.dict[sub_langs.default_lang].encode("utf8")), lang_code, videoID).encode('ascii', 'xmlcharrefreplace')
            response = urllib2.urlopen(url)
        else:
            url = u"https://www.youtube.com/api/timedtext?lang={}&name={}&v={}".format(lang_code, urllib.quote(sub_langs.dict[lang_code].encode("utf8")), videoID).encode('ascii', 'xmlcharrefreplace')
            response = urllib2.urlopen(url)
    except HTTPError:
        return None
    xml = response.read()
    response.close()
    return ET.fromstring(xml)


def xml_to_srt(xml_data):
    """
    xml_data - ET
    Converts XML data received from Google's servers and returns a SubRipFile instance.
    """
    f = pysrt.SubRipFile()
    for child in xml_data:
        sub = pysrt.SubRipItem()
        sub.text = h.unescape(child.text)
        sub.start.seconds = float(child.attrib["start"])
        sub.end.seconds = float(child.attrib["start"]) + float(child.attrib["dur"])
        f.append(sub)
    return f


def combine_srt(srt_list):
    """
    srt_list - a list of SubRipFiles
    Combines the text of all SubRipFiles in srt_list and returns a SubRipFile instance.
    """
    if srt_list is None or len(srt_list) == 0:
        return None
    f = pysrt.SubRipFile()
    for index in xrange(len(srt_list[0])):
        sub = pysrt.SubRipItem()
        for srt in srt_list:
            sub.text += (srt[index].text + "\n")
        sub.text = sub.text.rstrip()
        sub.start = srt_list[0][index].start
        sub.end = srt_list[0][index].end
        f.append(sub)
    return f


def youtube_to_srt(videoID, lang_codes=["en"], allow_translate=False):
    """
    videoID - a string of alphanumeric characters in the Youtube URL after watch?v=
    lang_codes - a list of language codes to be fetched. Defaults of [\"en\"]
    allow_translate - a boolean specifying whether using Google Translate is OK
    Returns a SubRipFile instance. If multiple languages were specified in lang_codes, then the returned SubRipFile's text will include as many available languages as possible.
    """
    subs = []
    for lang_code in lang_codes:
        sub = get_youtube_subtitle(videoID, lang_code, allow_translate)
        if sub is not None: # eliminate unavailable subtitles
            subs.append(xml_to_srt(sub))
    return None if subs == [] else combine_srt(subs)


def save_youtube_srt(path, videoID, lang_codes=["en"], allow_translate=False):
    """
    path - a string representing the desired filepath
    videoID - a string of alphanumeric characters in the Youtube URL after watch?v=
    lang_codes - a list of language codes to be fetched. Defaults of [\"en\"]
    allow_translate - a boolean specifying whether using Google Translate is OK
    Saves Youtube subtitles to computer.
    """
    srt = youtube_to_srt(videoID, lang_codes, allow_translate)
    if srt is not None:
        srt.save(path, encoding="utf-8")
