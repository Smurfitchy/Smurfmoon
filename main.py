import config
import time
import numpy as np
import ccxt
import requests
if config.RUN_EMULATOR:
    import cv2
else:
    import sys
    sys.path.append('./drivers')
    import SPI
    import SSD1305

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageChops

def clamp(n, smallest, largest): return max(smallest, min(n, largest))

def inverse_lerp(a, b, value):
    if a != b:
        return clamp((value - a) / (b - a), 0, 1)
    return 0

def lerp(a, b, t):
    return a + (b-a) * clamp(t, 0, 1)

def get_bscscan_balance():
    url = "https://api.bscscan.com/api?module=account&action=tokenbalance&contractaddress={0}&address={1}&tag=latest&apikey={2}".format(config.SAFEMOON_CONTRACT_ADDRESS, config.WALLET_ADDRESS, config.BSCSCAN_API_KEY)
    return (float)(requests.get(url).json()["result"]) * 0.000000001

def get_exchange_rate():
    url = "https://free.currconv.com/api/v7/convert?q=USD_{0}&compact=ultra&apiKey=324712ba3ce941d0593c".format(config.LOCAL_CURRENCY_SYMBOL)
    return (float)(requests.get(url).json()["USD_{0}".format(config.LOCAL_CURRENCY_SYMBOL)])

if config.RUN_EMULATOR:
    imageEncoding = 'RGB'
else:
    imageEncoding = '1'
    # Raspberry Pi pin configuration:
    RST = None     # on the PiOLED this pin isnt used
    # Note the following are only used with SPI:
    DC = 24
    SPI_PORT = 0
    SPI_DEVICE = 0

    # 128x32 display with hardware SPI:
    disp = SSD1305.SSD1305_128_32(rst=RST, dc=DC, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=8000000))
    # Initialize library.
    disp.begin()
    # Clear display.
    disp.clear()
    disp.display()    
#480x320 for the pi display 
frameSize = (254, 200)

titleFont = ImageFont.truetype("fonts/04B_03__.TTF", 16)
splashFont = ImageFont.truetype("fonts/aAtmospheric.ttf", 24)
balanceFont = ImageFont.truetype("fonts/Nunito-ExtraLight.ttf", 28)
safemoonFont_large = ImageFont.truetype("fonts/aAtmospheric.ttf", 28)
currencyFont = ImageFont.truetype("fonts/lilliput steps.ttf", 16)

arrow = Image.open('images/arrow.bmp').convert(imageEncoding)
arrow = arrow.resize((16, 16), Image.ANTIALIAS)

previousBalance = 0
currentBalance = 0

previousRate = 0
currentRate = 0

previousPerc = 0
currentPerc = 0

startTime = time.time()
timeDelta = 0

displayTime = 30   #time between pauses
screenToShow = 0

exchange = ccxt.gateio()

def update_data():
    global previousBalance
    global currentBalance
    global previousRate
    global currentRate
    global previousPerc
    global currentPerc

    previousBalance = currentBalance
    try:
        currentBalance = get_bscscan_balance()
    except:
        currentBalance = previousBalance
        pass

    try:
        ticker = exchange.fetch_ticker("SAFEMOON/USDT")
    except:
        pass

    previousRate = currentRate        
    currentRate = (float)(ticker['info']['last'])
    
    previousPerc = currentPerc
    currentPerc = (float)(ticker['info']['percentChange'])

update_data()

localExchange = get_exchange_rate()

while True:
    canvas = Image.new(imageEncoding, (frameSize))
    if (time.time() - startTime) > displayTime:
        startTime = time.time()
        update_data()

    
    flip = False
    time2 = np.arange(0, 1, 0.1)
    screen_x_offset = np.sin((time.time() * 3.5))

    if screen_x_offset < 0:
        flip = True
    else:
        flip = False

    pix = (int)(lerp(10, 58, abs(screen_x_offset)))
    
    image = Image.open('images/safe_logo.bmp').convert(imageEncoding)
    if flip:
        image = ImageOps.mirror(image)
    image = image.resize((pix, 56), Image.ANTIALIAS)
    canvas.paste(image, (56 - (int)(pix * 0.5) - 24, 4))

    draw = ImageDraw.Draw(canvas)
#Safemoon
    draw.text((64, 28), "SAFEMOON", fill='white', font=splashFont)
#Tracker
    draw.text((190, 52), "Tracker", fill='white', font=titleFont)
#Safemoon S
    draw.text((2, 72), "S", fill='white', font=safemoonFont_large)
#Number of coins
    draw.text((30, 68), "{:,.2f}".format(lerp(previousBalance, currentBalance, timeDelta)), fill="white", font=balanceFont)
#$
    draw.text((0, 100), "=" + config.LOCAL_CURRENCY_CHAR, fill='white', font=balanceFont)
#How much money I got
    draw.text((36, 100), "{:,.2f}".format((lerp(previousBalance, currentBalance, timeDelta) * lerp(previousRate, currentRate, timeDelta)) * localExchange, lerp(previousRate, currentRate, timeDelta) * localExchange), fill='white', font=balanceFont)   
#cost per coin
    draw.text((2, 140), "$", fill='white', font=safemoonFont_large)
    draw.text((34, 136), "{:,.9f}".format(lerp(previousRate, currentRate, timeDelta)), fill="white", font=balanceFont)
    
    sign = currentRate - previousRate

    if sign > 0: #Going up
        arrow2 = ImageOps.flip(arrow)
        canvas.paste(arrow2, (210, 146))
        draw.rectangle((100, 174, 250, 196), fill=(49, 192, 0), outline=(32, 125, 0))

    if sign < 0: #Going down
        canvas.paste(arrow, (210, 146))
        draw.rectangle((100, 174, 250, 196), fill=(192, 0, 0), outline=(125, 0, 0))
        

    perc24 = lerp(previousPerc, currentPerc, timeDelta)
    includeSign = ""
    if perc24 > 0:
        includeSign = "+"
#24 % change
    draw.text((4, 174), "24h {}{:,.2f}%".format(includeSign, perc24), fill='white', font=titleFont)    
    

    timeDelta = inverse_lerp(0, displayTime, time.time() - startTime)

    if config.RUN_EMULATOR:
        # Virtual display
        npImage = np.asarray(canvas)
        frameBGR = cv2.cvtColor(npImage, cv2.COLOR_RGB2BGR)
        
        #This is where I flipped it 
        #frameBGR=cv2.flip(frameBGR,-1)


        cv2.imshow('HashAPI', frameBGR)
        k = cv2.waitKey(16) & 0xFF
        if k == 27:
            break
    else:
        # Hardware display
        disp.image(canvas)
        disp.display()
        time.sleep(1./60)

if config.RUN_EMULATOR:
    # Virtual display
    cv2.destroyAllWindows()
else:
    # Hardware display
    pass
