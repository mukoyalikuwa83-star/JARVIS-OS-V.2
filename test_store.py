import requests, re
url = 'https://mukoyalikuwa83-star.github.io/JARVIS-OS-V.2/'
r = requests.get(url, timeout=15)
products = re.findall(r'class="product"', r.text)
paypal = re.findall(r'cgi-bin/webscr', r.text)
print(f'Live store: HTTP {r.status_code}')
print(f'Products: {len(products)}')
print(f'PayPal buttons: {len(paypal)}')
if len(products) > 0 and len(paypal) > 0:
    print('STORE IS LIVE AND WORKING')
else:
    print('STORE ISSUES')