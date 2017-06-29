import sys
import requests
import re
import time
import random
import google

#https://developers.google.com/analytics/devguides/collection/protocol/v1/
#https://developers.google.com/analytics/devguides/collection/protocol/v1/geoid

def main():
    #test = analytics_request(document_referrer="http://hackerzzz.com", document_location="https://zonksec.com/me",tracking_id='UA-72589501-1',client_id=559,geo_id='1007949')
    #test.send()

    # search_results = google.search(query='site:zonksec.com',num=10,stop=1)
    # test =[]
    # for result in search_results:
    #     test.append(result)
    # print test

    test = session('http://zonksec.com',bounces=5)
    print test.bounce_urls
class session:
    def __init__(self, target_urls, bounce_urls = None, page_delay=3000, page_delay_jitter=10, bounces=0):
        self.target_urls = target_urls
        self.page_delay = page_delay
        self.page_delay_jitter = page_delay_jitter
        self.bounces = bounces
        self.bounce_urls = bounce_urls

        if self.bounces > 0 and self.bounce_urls is None:
            self.bounce_urls = []
            search_results = google.search(query="site:"+self.target_urls, num=self.bounces,stop=1)
            for result in search_results:
                self.bounce_urls.append(str(result))


class analytics_request:
    def __init__(self,document_referrer,document_location,tracking_id,client_id,version=1,hit_type='pageview',user_agent ='Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',geo_id ='US', anon_ip =1):
        self.version = version
        self.tracking_id = tracking_id
        self.client_id = client_id
        self.hit_type = hit_type
        self.user_agent = user_agent
        self.geo_id = geo_id
        self.document_referrer = document_referrer
        self.document_location = document_location
        self.anon_ip = anon_ip

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
        print(r)


main()