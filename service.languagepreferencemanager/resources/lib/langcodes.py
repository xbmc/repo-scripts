# -*- coding: utf-8 -*-

#    This script is based on the one of script.xbmc.subtitles
#    Thanks to their original authors amet, mr_blobby



LANGUAGES      = (

    # Full Language name[0]     podnapisi[1]  ISO 639-1[2]   ISO 639-1 Code[3]   Script Setting Language[4]   localized name id number[5]

    ("Albanian"                   , "29",       "sq",            "alb",                 "0",                     30201  ),
    ("Arabic"                     , "12",       "ar",            "ara",                 "1",                     30202  ),
    ("Belarusian"                 , "0" ,       "hy",            "arm",                 "2",                     30203  ),
    ("Bosnian"                    , "10",       "bs",            "bos",                 "3",                     30204  ),
    ("Bulgarian"                  , "33",       "bg",            "bul",                 "4",                     30205  ),
    ("Catalan"                    , "53",       "ca",            "cat",                 "5",                     30206  ),
    ("Chinese"                    , "17",       "zh",            "chi",                 "6",                     30207  ),
    ("Croatian"                   , "38",       "hr",            "hrv",                 "7",                     30208  ),
    ("Czech"                      , "7",        "cs",            "cze",                 "8",                     30209  ),
    ("Danish"                     , "24",       "da",            "dan",                 "9",                     30210  ),
    ("Dutch"                      , "23",       "nl",            "dut",                 "10",                    30211  ),
    ("English"                    , "2",        "en",            "eng",                 "11",                    30212  ),
    ("Estonian"                   , "20",       "et",            "est",                 "12",                    30213  ),
    ("Farsi"                      , "52",       "fa",            "per",                 "13",                    30214  ),
    ("Finnish"                    , "31",       "fi",            "fin",                 "14",                    30215  ),
    ("French"                     , "8",        "fr",            "fre",                 "15",                    30216  ),
    ("German"                     , "5",        "de",            "ger,deu",             "16",                    30217  ),
    ("Greek"                      , "16",       "el",            "ell,gre",             "17",                    30218  ),
    ("Hebrew"                     , "22",       "he",            "heb",                 "18",                    30219  ),
    ("Hindi"                      , "42",       "hi",            "hin",                 "19",                    30220  ),
    ("Hungarian"                  , "15",       "hu",            "hun",                 "20",                    30221  ),
    ("Icelandic"                  , "6",        "is",            "ice",                 "21",                    30222  ),
    ("Indonesian"                 , "0",        "id",            "ind",                 "22",                    30223  ),
    ("Italian"                    , "9",        "it",            "ita",                 "23",                    30224  ),
    ("Japanese"                   , "11",       "ja",            "jpn",                 "24",                    30225  ),
    ("Korean"                     , "4",        "ko",            "kor",                 "25",                    30226  ),
    ("Latvian"                    , "21",       "lv",            "lav",                 "26",                    30227  ),
    ("Lithuanian"                 , "0",        "lt",            "lit",                 "27",                    30228  ),
    ("Macedonian"                 , "35",       "mk",            "mac",                 "28",                    30229  ),
    ("Norwegian"                  , "3",        "no",            "nor",                 "29",                    30230  ),
    ("Persian"                    , "52",       "fa",            "per",                 "30",                    30231  ),
    ("Polish"                     , "26",       "pl",            "pol",                 "31",                    30232  ),
    ("Portuguese"                 , "32",       "pt",            "por",                 "32",                    30233  ),
    ("Portuguese (Brazil)"        , "48",       "pb",            "pt-br",               "33",                    30234  ),
    ("Romanian"                   , "13",       "ro",            "rum",                 "34",                    30235  ),
    ("Russian"                    , "27",       "ru",            "rus",                 "35",                    30236  ),
    ("Serbian"                    , "36",       "sr",            "srp,scc",             "36",                    30237  ),
    ("Slovak"                     , "37",       "sk",            "slo",                 "37",                    30238  ),
    ("Slovenian"                  , "1",        "sl",            "slv",                 "38",                    30239  ),
    ("Spanish"                    , "28",       "es",            "spa",                 "39",                    30240  ),
    ("Swedish"                    , "25",       "sv",            "swe",                 "40",                    30241  ),
    ("Thai"                       , "0",        "th",            "tha",                 "41",                    30242  ),
    ("Turkish"                    , "30",       "tr",            "tur",                 "42",                    30243  ),
    ("Ukrainian"                  , "46",       "uk",            "ukr",                 "43",                    30244  ),
    ("Vietnamese"                 , "51",       "vi",            "vie",                 "44",                    30245  ),
    ("None"                       , "-1",       "",              "non",                 "45",                    30200  ),
    ("Any"                        , "-2",       "",              "any",                 "46",                    30300  ) )

def languageTranslate(lang, lang_from, lang_to):
  for x in LANGUAGES:
    codes = x[lang_from].split(r',')
    for code in codes:
      if lang == code :
        return x[lang_to]
