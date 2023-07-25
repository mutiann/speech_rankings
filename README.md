# Speech Rankings
The [rankings](https://mutiann.github.io/speech_rankings) mimics [CSRankings](http://csrankings.org/) to generate an ordered list
of researchers in speech/spoken language processing along with their possible research topics, based on 
recent (2016-) publications on important venues of the field, so as to help students seeking for PhD studies to 
find desirable advisors.

## How to use
The pre-generated report is available at [here](https://mutiann.github.io/speech_rankings). To build it by
yourself, 
1. Run `prepare_data.py` to build `publications.json` and `authors.json`, or simply use the data provided in this repository, covering 
   publications from 2011 to 2022.
2. Run `export.py` to generate the report.

## How does it work
We scrape author metadata and publication data of the following three types of venues from DBLP, including:
* Speech venues: Interspeech, Speech Communications; SLT, SSW, ASRU, IWSLT (these four are are supported but not included in the pregenerated report)
* Mixed venues: ICASSP, TASLP
* General venues: NeurIPS, ICML, ICLR, ACL, EMNLP, NAACL, KDD, AAAI, IJCAI

All publications in Speech venues are included. Paricularly for Interspeech, section/field of each paper are collected
from ISCA Archive to show possible research topics of each researcher. So are the keywords from IEEE Xplore 
for papers published on IEEE-held venues. Keywords (as well as titles) are also used to filter out non-speech papers in
Mixed venues by a set of rules. Titles are used to identify speech papers in General venues. Researchers are sorted by
the total number of publications.

The collected data contain errors. The project is by no means an appropriate measure to rank or compare the researchers,
and the collected publication data are incomplete as well. Hence the generated index is for reference only and should not be
taken seriously.
