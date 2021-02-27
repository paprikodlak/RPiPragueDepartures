from datetime import datetime
from math import floor
import requests
from requests.exceptions import HTTPError
import json
import schedule # https://schedule.readthedocs.io/en/stable/
import time

import sys
import os
os.chdir('/home/pi/odjezdy/')

picdir = os.path.realpath("pic")
libdir = os.path.realpath("lib")
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging
from waveshare_epd import epd2in13
from PIL import Image,ImageDraw,ImageFont
import traceback


def stahniOdjezdy():
    
    # https://golemioapi.docs.apiary.io/#reference/public-transport/departure-boards/get-departure-board?console=1
    # https://api.golemio.cz/api-keys/dashboard

    with open('APIkey.secret','r') as f:
    accessToken = f.read()
    
    headers = {
    'Content-Type': 'application/json; charset=utf-8',
    'x-access-token': accessToken
    }

    minutPred = 0
    minutPo = 600
    url = 'https://api.golemio.cz/v2/departureboards/?minutesBefore='+str(minutPred)+'&minutesAfter='+str(minutPo)+'&names=Vosm%C3%ADkov%C3%BDch&preferredTimezone=Europe%2FPrague'

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        # access JSOn content
        vystup = response.json()
        # print(vystup)
        
        zapis = json.dumps(vystup)
        with open("odjezdyCache.txt",'w',encoding = 'utf-8') as f:
            f.write(zapis)
        

    except HTTPError as http_err:
        print('HTTP error occurred: {http_err}')
    except Exception as err:
        print('Other error occurred: {err}')


def vypisOdjezdy():

    odjezdNejpozdeji = 120 # min
    odjezdNejdrive = 0 # min
    pocetOdjezduMax = 20 

    dolu = []
    nahoru = []
    doluUq = []
    nahoruUq = []

    with open("odjezdyCache.txt",'r',encoding = 'utf-8') as fCt:
        vystup = json.load(fCt)
        
    
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
        
        if casDoOdjezdu.total_seconds()/60>odjezdNejpozdeji or pocetOdjezdu>pocetOdjezduMax:
            break
        
    txt = "\u25BC |"+dolu[0]+dolu[1]+"\n"
    txt = txt+"\u25BC |"+dolu[2]+dolu[3]+"\n"
    txt = txt+"\u25BC |"+dolu[4]+dolu[5]+"\n"
    txt = txt+"\u25B2 |"+nahoru[0]+nahoru[1]+"\n"
    txt = txt + "\u25B2 |"+nahoru[2]+nahoru[3]
    return txt

    


def vycistiDisplay():
    global epd
    logging.info("vycisteni")
    epd.init(epd.lut_full_update)
    epd.Clear(0xFF)
    vykresli()    


def vykresli():
    global epd
    global fontik
    logging.info(" vypsani ")
    epd.init(epd.lut_partial_update)

    txt = vypisOdjezdy()

    image = Image.new('1', (epd.height, epd.width), 255)  # 255: clear the frame    
    draw = ImageDraw.Draw(image)
    
    draw.text((0, 0), txt, font = fontik, fill = 0)
           
    draw.text((170, 100), time.strftime('%H:%M:%S'), font = fontik, fill = 0)
    epd.display(epd.getbuffer(image.rotate(180)))
    epd.sleep()




logging.basicConfig(level=logging.DEBUG,
    filename='odjezdovaniListener.log',
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',)

try:
    logging.info("odjezdy")

    logging.info("inicializace")
    epd = epd2in13.EPD()

    logging.info("fonty")
    # fontik = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 16)
    fontik = ImageFont.truetype(os.path.join(picdir, 'JetBrainsMono-Bold.ttf'), 16) 
    fontisk = ImageFont.truetype(os.path.join(picdir, 'JetBrainsMono-Bold.ttf'), 100) 
    
    
    finalniText = ":*"
    finalniObraz =  Image.new('1', (epd.height, epd.width), 255)
    finalniDraw = ImageDraw.Draw(finalniObraz)
    finalniDraw.text((0,0),finalniText,font = fontisk, fill = 0)
    
        
    logging.info("prvni stahnuti a vycisteni")
    stahniOdjezdy()
    vycistiDisplay()
    
    logging.info("vytvoreni schedule")
    schedule.every(60).seconds.do(vykresli)
    
    schedule.every(10).minutes.do(vycistiDisplay)
    schedule.every(10).minutes.do(stahniOdjezdy)
    
    logging.info("beh v cyklu")
    while 1:
        schedule.run_pending()
        time.sleep(1)

        
except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    
    
finally:
    logging.info("provadeni finally")
    epd.init(epd.lut_full_update)
    logging.info("finally: init")
    epd.display(epd.getbuffer(finalniObraz.rotate(180)))
    logging.info("finally: display")
    schedule.clear()
    logging.info("finally: schledule clear")
    epd2in13.epdconfig.module_exit()
    logging.info("ukonceni")
    exit()
