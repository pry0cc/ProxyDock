# ProxyDock
<small> Credit for the awesome name goes to [@atoscher](https://medium.com/@adam.toscher)</small>
---

## What is it
ProxyDock is a Dockerfile and Bash script that converts your OpenVPN files (and potentially others) into local proxies, that can be easily coupled with proxychains to make for an awesome, quick, private botnet.


## Why I made it
I came up with the idea for this while attempting to make an automatic google dorker, you'll know if you make enough requests for google dorks, eventually Google return 403's with a funky captcha, not very helpful for automatic dorking at all.

I then had the bright idea of scraping public proxies, this seemed like genius, until you discover that Google has a magic method of detecting and blacklisting public proxies.

"Ahh I'll just use Tor!"

Nope. They blacklist that too.

However, they seem to have no issue with VPN's, however automatic scraping with a VPN is hard work. Everytime you switch VPN, it has to disconnect, reconnect, and re-route all your traffic. 

## Introducing ProxyDock
Take a Dockerfile, put openvpn on it, put a simple http proxy script on it, forward the proxy port locally, and then repeat for each VPN file you have. That is all this does, and it works amazing.

### Why would I use this over ProxyCannon?
Oh yeah, that AWS private botnet thing, that is very cool, however it is potentially expensive. This VPN2Proxy method is very cheap, as annual VPN subscriptions can be as cheap as 20 dollars, and for that you can get around 40 countries and 40 different IP's.

To use this is very simple, modify the Dockerfile to add your openvpn key files into the container, you can put them in the /VPN directory. Then, make sure they have auth included, aka, they don't prompt for credientials, otherwise automating this will not work.

Run the start.sh!
