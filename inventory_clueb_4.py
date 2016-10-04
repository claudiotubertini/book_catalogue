from woocommerce import API
import json, os, sys, requests
import numpy as np


# https://clueb.it/wc-api/v1/customers?fields=email,first_name,last_name&consumer_key=ck_d175af265f3ea1375260564ba12054ad5b0fd33e&consumer_secret=cs_83da7a63ee1127fcf0115da54bd116e4a11f8ea7
# https://clueb.it/wp-json/wc/v1/products?filter[post_status]=any&fields=id,sku,in_stock,status,stock_quantity,managing_stock&page=1&consumer_key=ck_5d6fe327d4442904c362694868fda696eb4f5ff2&consumer_secret=cs_c7552174517786cdd6f8c4e5e953e5c0853b13b6
# 
# ALLA FINE DI AGOSTO RICORDARSI DI CARICARE ANCHE LE GIACENZE = 0 
#funzioni ausiliarie

def ISBNgenerator(mystr):
    """ return a 13 digit isbn code without dash (-)"""
    mylist = []
    mysum = 0
    if mystr and (mystr.find('-') != -1):
        if len(mystr) == 13:
            mystr = '978' + ''.join(mystr.split('-'))
            mystr = mystr[:-1]
            for i in range(len(mystr)):
                if (i+1) % 2 == 0:
                    mysum = mysum + int(mystr[i])*3
                else:
                    mysum = mysum + int(mystr[i])
            ckd = (10 - mysum % 10) % 10
            return mystr + str(ckd)
        elif len(mystr) == 17:
            return ''.join(mystr.split('-'))
        else:
            return mystr
    else:
        return mystr
        # raise SystemExit
def ISBNcomparing(mystr):
    """ returns only the significant part of the ISBN"""
    mylist = []
    mysum = 0
    if mystr.find('-') != -1:
        if len(mystr) == 13:
            return mystr[3:-2]
        elif len(mystr) == 17:
            return mystr[7:-2]
        else:
            print("Something went wrong with " + mystr)
    else:
        if len(mystr) == 13:
            return mystr[5:-2]
        elif len(mystr) == 10:
            return mystr[2:-2]
        else:
            print("Something went wrong with " + mystr)


def EAN10to13(mystr):
    """ returns 13 digits ISBN"""
    if mystr and mystr.find('-') != -1:
        if len(mystr) == 13:
            newstr = ISBNgenerator(mystr)
            mystr = '978-' + mystr[:-1]
            return mystr + newstr[-1]
        elif len(mystr) == 17:
            return mystr
        else:
            return mystr
    else:
        return mystr


wcapi = API(
    url="https://clueb.it",
    consumer_key="ck_5d6fe327d4442904c362694868fda696eb4f5ff2",
    consumer_secret="cs_c7552174517786cdd6f8c4e5e953e5c0853b13b6",
    wp_api=True,
    timeout=500,
    version="wc/v1"
 )

cat = [] #categories
for i in range(1,30):
    myResponse = requests.get("https://clueb.it/wp-json/wc/v1/products/categories?page=%s&consumer_key=ck_5d6fe327d4442904c362694868fda696eb4f5ff2&consumer_secret=cs_c7552174517786cdd6f8c4e5e953e5c0853b13b6" %i)
    jData = json.loads(myResponse.content.decode('utf8'))
    cat.append(jData)
categories = [{'name':cat[x][y]['name'], 'description':cat[x][y]['description']} for x in range(28) for y in range(10)]
categories2 = [{'name':cat[28][y]['name'], 'description':cat[28][y]['description']} for y in range(6)]
categories.extend(categories2)
with open("categories.json", 'w') as f:
    json.dump(categories, f, indent=4)
series = []
with open("categories.json", 'r') as fl:
    series = json.load(fl)
series = 

vol = []


res = []
for i in range(1,294):
    myResponse = requests.get("https://clueb.it/wc-api/v1/products?filter[post_status]=any&page=%s&consumer_key=ck_5d6fe327d4442904c362694868fda696eb4f5ff2&consumer_secret=cs_c7552174517786cdd6f8c4e5e953e5c0853b13b6" %i)
    jData = json.loads(myResponse.content.decode('utf8'))
    res.append(jData)  # each record is a python dict
with open("volumes_oldformat.json", 'w') as fd:
    json.dump(res, fd, indent=4)
volumes = [{'title':res[x][y]['title'],
            'description':res[x][y]['description'],
            'short_desc': res[x][y]['short_description'],
            'price': res[x][y]['price'],
            'author': res[x][y]['author'],
            'topic': res[x][y]['tags'],
            'cover': res[x][y]['images']['src'],
            } for x in range(28) for y in range(10)]
# for i in range(1,3):
#     jData = wcapi.get("products?filter[post_status]=any&fields=id,sku,in_stock,status,stock_quantity,managing_stock&page=" + str(i)).json()
#     res2.append(jData)

d = np.genfromtxt("/home/mips/GiacenzeCLUEB.csv", delimiter=';', skip_header=7)
d1 = {x[1]: x[2] for x in d if not np.isnan(x[1]) if x[2] > 3}
#d1 = {x[1]: x[2] for x in d}

# for x in range(len(res)):
#     res[x]['update'] = res[x]['products']
#     del res[x]['products']

for x in range(len(res)):
    for y in range(len(res[x]['products'])):
        try:
            if int(ISBNgenerator(res[x]['products'][y]['sku'])) not in d1.keys():
                res[x]['products'][y]['in_stock'] = False
                ean = EAN10to13(res[x]['products'][y]['sku'])
                res[x]['products'][y]['sku'] = ean
                res[x]['products'][y]['stock_quantity'] = 0
            else:
                ean = EAN10to13(res[x]['products'][y]['sku'])
                res[x]['products'][y]['sku'] = ean
                res[x]['products'][y]['in_stock'] = True
                res[x]['products'][y]['status'] = "publish"
                res[x]['products'][y]['stock_quantity'] = int(d1[int(ISBNgenerator(res[x]['products'][y]['sku']))])
                res[x]['products'][y]['managing_stock'] = True
        except ValueError:
            res[x]['products'][y]['in_stock'] = False
            res[x]['products'][y]['status'] = "draft"
            res[x]['products'][y]['stock_quantity'] = 0

ans = 'Ok'
try:
    for i in range(len(res)):
        for y in range(len(res[i]['products'])):
            art_id = res[i]['products'][y]['id']
            wcapi.post("products/" + str(art_id), res[i]['products'][y])
except Exception as inst:
    ans = inst

# for i in range(len(res)):
#     for y in range(len(res[i]['products'])):
#         art_id = res[i]['products'][y]['id']
#         res[]
#         wcapi.put("products/" + str(art_id), json.dumps(res[i]['products'][y])).json()

# a = {u'status': u'publish', u'sku': u'978-88-491-3909-9', u'in_stock': True, u'stock_quantity': '37', u'managing_stock': True}

# wcapi.post("products/200000005427", a)
import smtplib
msg = """\
From: server cluebmips
To: me
Subject: Giacenze clueb.it

Risultato: %s
""" % ans
s = smtplib.SMTP('localhost')
s.sendmail("claudio@cluebmips", "claudio.tubertini@gmail.com", msg)
s.quit()
