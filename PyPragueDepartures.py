from datetime import datetime
from math import floor
import requests
from requests.exceptions import HTTPError
import json
import schedule # https://schedule.readthedocs.io/en/stable/
import time


def stahniOdjezdy(limit=1000):
    
    # https://golemioapi.docs.apiary.io/#reference/public-transport/departure-boards/get-departure-board?console=1
    # https://api.golemio.cz/api-keys/dashboard

    with open('APIkey.secret','r') as f:
        accessToken=f.read()

    headers = {
    'Content-Type': 'application/json; charset=utf-8',
    'x-access-token': accessToken
    }

    minutPred = 0
    minutPo = 60*24*7
    id1 = 'U861Z1P' # VosmikovychA
    id2 = 'U861Z2P' # VosmikovychB

    url1 = 'https://api.golemio.cz/v2/departureboards/'
    url1+= '?ids=' + id1 + '&limit=' + str(limit)
    url1 += '&minutesBefore='+str(minutPred)+'&minutesAfter='+str(minutPo)
    
    url2 = 'https://api.golemio.cz/v2/departureboards/'
    url2+= '?ids=' + id2 + '&limit='+str(limit)
    url2 += '&minutesBefore='+str(minutPred)+'&minutesAfter='+str(minutPo)

    
    try:
        # api gives max 100 entries, even tho stated limit is 1000
        response1 = requests.get(url1, headers=headers)
        response1.raise_for_status()
        # access JSOn content
        response2 = requests.get(url2, headers=headers)
        response2.raise_for_status()
        vystup = response2.json()+response1.json()
        return(vystup)
    except HTTPError as http_err:
        print('HTTP error occurred:',http_err)
    except Exception as err:
        print('Other error occurred:',err)


def ulozOdjezdy():
    try:
        odjezdy = stahniOdjezdy()
        zapis = json.dumps(odjezdy)
        with open("odjezdyCache.txt",'w',encoding = 'utf-8') as f:
            f.write(zapis)
    except Exception as err:    
        print('ulozOdjezd error occurred:', err)
        
    
def vypisOdjezdy():

    odjezdNejdrive = 0 # min
    pocetOdjezduMax = 20

    dolu = []
    nahoru = []
    doluUq = []
    nahoruUq = []

    try:
        vystup = stahniOdjezdy(limit=pocetOdjezduMax*2)
    except:
        print("Error: stazeni odjezdu pro vypis")
        try:
            with open("odjezdyCache.txt",'r',encoding = 'utf-8') as fCt:
                vystup = json.load(fCt)
        except:
            print("Error: nacteni odjezdu ze souboru")
        
    
    pocetOdjezdu = 0
    for polozka in vystup:
        
        # deleting ':' in timezone 
        polozkaCas = datetime.strptime(polozka['departure_timestamp']['predicted'].replace("+01:00","+0100"),"%Y-%m-%dT%H:%M:%S.%f%z")
        aktualniCas = datetime.now(polozkaCas.tzinfo)
        casDoOdjezdu = polozkaCas-aktualniCas

        linka = polozka["route"]["short_name"]
        if len(linka) < 2:
            linka=" "+linka

        if abs(casDoOdjezdu.total_seconds())<60:
            doOdjezdu = str(floor(casDoOdjezdu.total_seconds()))+"s"
            doOdjezduVal = floor(casDoOdjezdu.total_seconds())
        else:
            doOdjezdu = str(floor(casDoOdjezdu.total_seconds()/60))+"m"
            doOdjezduVal = floor(casDoOdjezdu.total_seconds()/60)
        if doOdjezduVal>0:
            doOdjezdu = " "+doOdjezdu
        if abs(doOdjezduVal)<10:
            doOdjezdu = " "+doOdjezdu
        odjezd = linka+" "+doOdjezdu+" |"

        if casDoOdjezdu.total_seconds()/60<odjezdNejdrive:
            continue
        
        if polozka['stop']['platform_code']=="A":
            dolu.append(odjezd)
            doluUq.append({linka:odjezd})
        else:
            nahoru.append(odjezd)
            nahoruUq.append({linka:odjezd})
        pocetOdjezdu=pocetOdjezdu+1
        
        
    print("nahoru:",len(nahoru))
    print("dolu:",len(dolu))
    # print("\u25BC |",*dolu)
    # print("\u25B2 |",*nahoru)
    txt = "\u25BC |"+dolu[0]+dolu[1]+dolu[2]+"\n\u25BC |"+dolu[3]+dolu[4]+dolu[5]
    txt = txt+"\n\u25B2 |"+nahoru[0]+nahoru[1]+nahoru[2]+"\n\u25B2 |"+nahoru[3]+nahoru[4]+nahoru[5]
    print(txt)
    
    
try:
    ulozOdjezdy()
    schedule.every(10).seconds.do(vypisOdjezdy)
    schedule.every(1).hours.do(ulozOdjezdy)
    
    while 1:
        schedule.run_pending()
        time.sleep(1)
finally:
    schedule.clear()
