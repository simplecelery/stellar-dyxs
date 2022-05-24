import StellarPlayer
import threading
import time
import bs4
import requests
import re
import urllib.parse
import urllib.request
import math
import json
import urllib3

dyxx_urls = ['http://dyxs8.xyz', 'http://dyxs7.xyz', 'http://dyxs6.xyz', 'http://dyxs9.xyz', 'http://dyxs16.xyz', 'http://dyxs17.xyz','http://dyxs11.com','http://dyxs12.com','http://dyxs13.com','http://dyxs14.com','http://dyxs15.com','http://dianying.in', 'http://dianying.im', 'http://dianyingim.com'] 

def getPlayUrl(pageurl,xlname):
    playurl = ""
    res = requests.get(pageurl)
    if res.status_code == 200:
        bs = bs4.BeautifulSoup(res.content.decode('UTF-8','ignore'),'html.parser')
        selector = bs.select('#main > div.player-block > div > div.player-box > div > script')
        if selector:
            scriptitem = selector[1]
            jsonstr = re.findall(r"var player_aaaa=(.+)",scriptitem.string)[0]
            playerjson = json.loads(jsonstr)
            encodeurl  = playerjson['url']
            playurl = urllib.parse.unquote(encodeurl)
    if playurl != "":
        return [xlname,playurl]
    else:
        return None
    
class GetPlayUrlThread(threading.Thread):
    def __init__(self, searchurl,name):
        threading.Thread.__init__(self)
        self.searchurl = searchurl
        self.xlname = name
        
    def run(self):
        self.result = getPlayUrl(self.searchurl,self.xlname)
    def get_result(self):
        try:
            return self.result
        except Exception:
            return None
    
    
def getMovieDetail(mediainfo,weburl):
    url = mediainfo["url"]
    resinfo = {}
    resinfo["name"] = mediainfo["name"]
    resinfo["pic"] = mediainfo["pic"]
    resinfo["summary"] = mediainfo["summary"]
    resinfo["pub_date"] = mediainfo["pub_date"]
    res = requests.get(url,verify=False)
    allmovies = []
    if res.status_code != 200:
        return allmovies
    bs = bs4.BeautifulSoup(res.content.decode('UTF-8','ignore'),'html.parser')           
    xlselector = bs.find_all('div', class_='module-tab-item tab-item') 
    jjselector = bs.find_all('div', class_='module-blocklist scroll-box scroll-box-y')
    li = []
    if xlselector and jjselector:
        xlnames = []
        movieurls = []
        i = 0
        for xl in xlselector:
            xlinfo = xl.select('span')
            if xlinfo:
                playname = xlinfo[0].string
                jj = jjselector[i]
                if jj:
                    moviegroup = jj.select('div > a')
                    if moviegroup:
                        for movieinfo in moviegroup:
                            movieurl = weburl + movieinfo.get('href')
                            playname = playname + movieinfo.select('span')[0].string
                            t = GetPlayUrlThread(movieurl,playname)
                            li.append(t)
                            t.start()
            i = i + 1
    return [resinfo,li]

class GetMediaDetailThread(threading.Thread):
    def __init__(self, mediainfo,weburl):
        threading.Thread.__init__(self)
        self.mediainfo = mediainfo
        self.weburl = weburl
    
    def run(self):
        self.result = getMovieDetail(self.mediainfo,self.weburl)
    
    def get_result(self):
        try:
            return self.result
        except Exception:
            return None



def concatUrl(url1, url2):
    splits = re.split(r'/+',url1)
    url = splits[0] + '//'
    if url2.startswith('/'):
        url = url + splits[1] + url2
    else:
        url = url + '/'.join(splits[1:-1]) + '/' + url2
    return url

class dyxsplugin(StellarPlayer.IStellarPlayerPlugin):
    def __init__(self,player:StellarPlayer.IStellarPlayer):
        super().__init__(player)
        self.mainmenu = [
            {'title':'正在热播','url':'/'},
            {'title':'电影','url':'/v/dianying/'},
            {'title':'电视剧','url':'/v/dianshiju/'},
            {'title':'动漫','url':'/v/dongman/'},
            {'title':'综艺','url':'/v/zongyi/'}
        ]
        self.secmenu = []
        self.medias = []
        self.cur_page = ''
        self.firstpage = ''
        self.previouspage = ''
        self.nextpage = ''
        self.lastpage = ''
        self.xls = []
        self.addarr = []
        self.allmovidesdata = {}
        urllib3.disable_warnings()
    
    def start(self):
        super().start()
        self.dyxsurl = self.getDyxsUrl()
        print('--------------------------')
        print(self.dyxsurl)
        if self.dyxsurl == '':
            self.player.showText('无法打开电影先生网站')
        else:
            self.onMainMenuReload(self.dyxsurl)
    
    def checkDyxsUrl(self,url):
        urlCanOpen = True
        try:
            res = requests.get(url,timeout=5,verify=False)
        except :
            urlCanOpen = False
        if urlCanOpen:
            if res.status_code == 200:
                bs = bs4.BeautifulSoup(res.content.decode('UTF-8','ignore'),'html.parser')
                picselector = bs.select('#header > div.header-content > div.dianying-im')
                if picselector:
                    self.addarr.append(url)
    
    
    def getDyxsUrl(self):
        li = []
        self.addarr = []
        for url in dyxx_urls:
            t = threading.Thread(target=self.checkDyxsUrl,args=(url,))
            li.append(t)
            t.start()
        for t in li:
            t.join()
        if len(self.addarr) > 0:
            return self.addarr[0]
        return ''
    
    def show(self):
        controls = self.makeLayout()
        self.doModal('main',800,600,'',controls)
    
    def makeLayout(self):
        mainmenulist = []
        for cat in self.mainmenu:
            mainmenulist.append({'type':'link','name':cat['title'],'@click':'onMainMenuClick','width':60})
        secmenu_layout = [
            {'type':'link','name':'title','@click':'onSecMenuClick'}
        ]

        mediagrid_layout = [
            [
                {
                    'group': [
                        {'type':'image','name':'picture', '@click':'on_grid_click'},
                        {'type':'link','name':'title','textColor':'#ff7f00','fontSize':15,'height':0.2, '@click':'on_grid_click'}
                    ],
                    'dir':'vertical'
                }
            ]
        ]
        controls = [
            {'type':'space','height':5},
            {
                'group':[
                    {'type':'edit','name':'search_edit','label':'搜索','width':0.4},
                    {'type':'button','name':'搜索','@click':'onSearch','width':80}
                ],
                'width':1.0,
                'height':30
            },
            {'type':'space','height':10},
            {'group':mainmenulist,'height':30},
            {'group':[],'height':30,'name':'secmenugroup'},
            {'type':'space','height':5},
            {'type':'grid','name':'mediagrid','itemlayout':mediagrid_layout,'value':self.medias,'separator':True,'itemheight':220,'itemwidth':120},
            {'group':
                [
                    {'type':'space'},
                    {'group':
                        [
                            {'type':'label','name':'cur_page',':value':'cur_page'},
                            {'type':'link','name':'首页','@click':'onClickFirstPage'},
                            {'type':'link','name':'上一页','@click':'onClickFormerPage'},
                            {'type':'link','name':'下一页','@click':'onClickNextPage'},
                            {'type':'link','name':'末页','@click':'onClickLastPage'},
                        ]
                        ,'width':0.45
                    },
                    {'type':'space'}
                ]
                ,'height':30
            },
            {'type':'space','height':5}
        ]
        return controls
    
    def onSearch(self, *args):
        self.loading()
        search_word = self.player.getControlValue('main','search_edit')
        if len(search_word) > 0:
            searchurl = self.dyxsurl +'/search-' + urllib.parse.quote(search_word,encoding='utf-8') + '-------------/'
            self.onProcessDetalPage(searchurl)
        self.loading(True)
    
    def onMainMenuClick(self,pageId,control,*args):
        self.loading()
        self.firstpage = ''
        self.previouspage = ''
        self.nextpage = ''
        self.lastpage = ''
        self.cur_page = ''
        self.secmenu = []
        pageurl = ''
        for cat in self.mainmenu:
            if cat['title'] == control:
                pageurl = self.dyxsurl + cat['url']
                break
        if pageurl != '':
            self.onMainMenuReload(pageurl)
        self.loading(True)
    
    def onMainMenuReload(self,pageurl):
        controls = []
        self.player.removeControl('main','canremovemenugroup')
        print(pageurl)
        res = requests.get(pageurl,verify=False)
        if res.status_code == 200:         
            bs = bs4.BeautifulSoup(res.content.decode('UTF-8','ignore'),'html.parser')
            selector = bs.find_all('div', class_='module-items')
            if selector:
                self.reloadMedias(selector)
                
            selector = bs.find_all('div', class_='block-box-items scroll-content swiper-wrapper')
            if (selector):
                items = selector[0].select('div')
                for item in items:
                    iteminfo = item.select('a')
                    if iteminfo:
                        secmeninfo = iteminfo[0]
                        menuname = secmeninfo.get('title')
                        menuurl = self.dyxsurl + secmeninfo.get('href')
                        self.secmenu.append({'title':menuname,'url':menuurl})

        for cat in self.secmenu:
            controls.append({'type':'link','name':cat['title'],'width':60,'@click':'onSecondMenuClick'})  
        row = {'group':controls,'name':'canremovemenugroup'}
        self.player.addControl('main','secmenugroup',row)
        
    def reloadMedias(self,moduleitems):
        self.medias = []
        self.player.updateControlValue('main','mediagrid',self.medias)
        for moduleitem in moduleitems:
            for item in moduleitem:
                try:
                    imageinfo = item.select('div.module-item-cover > a > img')[0]
                except:
                    imageinfo = item.select('div.module-item-cover > div > img')[0]
                imgurl = imageinfo.get('data-src')
                if imgurl.find('http') < 0:
                    imgurl = self.dyxsurl + imgurl
                try:
                    nameinfo = item.select('div.module-item-titlebox > a')[0]
                    name = nameinfo.string
                except:
                    nameinfo = item.select('div.video-info > div.video-info-header > h3 > a')[0]
                    name = nameinfo.string
                url = self.dyxsurl + nameinfo.get('href')
                self.medias.append({'picture':imgurl,'title':name,'url':url})
        self.player.updateControlValue('main','mediagrid',self.medias)
    
    def onSecondMenuClick(self,pageId,control,*args):
        self.loading()
        pageurl = ''
        for cat in self.secmenu:
            if cat['title'] == control:
                pageurl = cat['url']
                break
        if pageurl != '':
            self.onProcessDetalPage(pageurl)
        self.loading(True)
     
    def onProcessDetalPage(self,pageurl):
        self.firstpage = ''
        self.previouspage = ''
        self.nextpage = ''
        self.lastpage = ''
        self.cur_page = ''
        res = requests.get(pageurl,verify=False)
        if res.status_code == 200:
            bs = bs4.BeautifulSoup(res.content.decode('UTF-8','ignore'),'html.parser')
            selector = bs.find_all('div', class_='module-items')
            if selector:
                self.reloadMedias(selector)
            pageselector = bs.select('#page')
            if pageselector:
                pages = pageselector[0].select('a')
                pagenumber = pageselector[0].select('span')
                if pagenumber:
                    self.cur_page = '第' + pagenumber[0].string + '页'
                if pages:
                    n = len(pages)
                    if pages[0]:
                        self.firstpage = self.dyxsurl + pages[0].get('href')
                    if pages[1]:
                        self.previouspage = self.dyxsurl + pages[1].get('href')
                    if pages[n - 2]:
                        self.nextpage = self.dyxsurl + pages[n - 2].get('href')
                    if pages[n - 1]:
                        self.lastpage = self.dyxsurl + pages[n - 1].get('href')
        #print("self.firstpage:" + self.firstpage)
        #print("self.previouspage:" + self.previouspage)
        #print("self.nextpage:" + self.nextpage)
        #print("self.lastpage:" + self.lastpage)
                
        
    def on_grid_click(self, page, listControl, item, itemControl):
        self.loading()
        mediapageurl = self.medias[item]['url']
        medianame = self.medias[item]['title']
        res = requests.get(mediapageurl,verify=False)
        picurl = ''
        infostr = ''
        allmovies = []
        self.xls = []
        if res.status_code == 200:
            bs = bs4.BeautifulSoup(res.content.decode('UTF-8','ignore'),'html.parser')
            
            picselector = bs.select('#main > div > div.box.view-heading > div.video-cover > div > div > img')
            headerselector = bs.find_all('div', class_= 'video-info-title')
            infoselector = bs.find_all('div', class_= 'video-info-items')
            if picselector:
                picurl = picselector[0].get('data-src')
                if picurl.find('http') < 0:
                    picurl = self.dyxsurl + picurl
            if headerselector:
                headinfo = headerselector[0].getText()
            if infoselector:
                for info in infoselector:
                    infostr = infostr + info.getText() + '\n'
            
            xlselector = bs.find_all('div', class_='module-tab-item tab-item') 
            jjselector = bs.find_all('div', class_='module-blocklist scroll-box scroll-box-y')
            if xlselector and jjselector:
                for xl in xlselector:
                    xlinfo = xl.select('span')
                    if xlinfo:
                        xlname = xlinfo[0].string
                        self.xls.append({'title':xlname})
                for jj in jjselector:
                    movies = []
                    moviegroup = jj.select('div > a')
                    if moviegroup:
                        for movieinfo in moviegroup:
                            movieurl = self.dyxsurl + movieinfo.get('href')
                            moviename = movieinfo.select('span')[0].string
                            movies.append({'playname':moviename,'url':movieurl})
                    allmovies.append(movies)
        
        actmovies = []
        if len(allmovies) > 0:
            actmovies = allmovies[0]
        self.allmovidesdata[medianame] = {'allmovies':allmovies,'actmovies':actmovies}
                  
        xl_list_layout = {'type':'link','name':'title','textColor':'#ff0000','width':0.6,'@click':'on_xl_click'}
        movie_list_layout = {'type':'link','name':'playname','@click':'on_movieurl_click'}
        controls = [
            {'type':'space','height':5},
            {'group':[
                    {'type':'image','name':'mediapicture', 'value':picurl,'width':0.2},
                    {'type':'label','name':'info','value':infostr,'width':0.8}
                ],
                'width':1.0,
                'height':250
            },
            {'group':
                {'type':'grid','name':'xllist','itemlayout':xl_list_layout,'value':self.xls,'separator':True,'itemheight':28,'itemwidth':80},
                'height':60
            },
            {'type':'space','height':5},
            {'group':
                {'type':'grid','name':'movielist','itemlayout':movie_list_layout,'value':actmovies,'separator':True,'itemheight':30,'itemwidth':60},
                'height':270
            }
        ]
        self.loading(True)
        result,control = self.player.doModal(medianame,800,600,medianame,controls)  
        if result == False:
            del self.allmovidesdata[medianame]
        
    def onClickFirstPage(self, *args):
        if self.firstpage == '':
            return 
        self.loading()
        self.onProcessDetalPage(self.firstpage)
        self.loading(True)
        
    def onClickFormerPage(self, *args):
        if self.previouspage == '':
            return 
        self.loading()
        self.onProcessDetalPage(self.previouspage)
        self.loading(True)
    
    def onClickNextPage(self, *args):
        if self.nextpage == '':
            return 
        self.loading()
        self.onProcessDetalPage(self.nextpage)
        self.loading(True)
        
    def onClickLastPage(self, *args):
        if self.lastpage == '':
            return 
        self.onProcessDetalPage(self.lastpage)
        
    def on_xl_click(self, page, listControl, item, itemControl):
        self.player.updateControlValue(page,'movielist',[])
        if len(self.allmovidesdata[page]['allmovies']) > item:
            self.allmovidesdata[page]['actmovies'] = self.allmovidesdata[page]['allmovies'][item]
        self.player.updateControlValue(page,'movielist',self.allmovidesdata[page]['actmovies'])
        
    def on_movieurl_click(self, page, listControl, item, itemControl):
        if len(self.allmovidesdata[page]['actmovies']) > item:
            playurl = self.allmovidesdata[page]['actmovies'][item]['url']
            self.playMovieUrl(playurl,page)
            
    def playMovieUrl(self,playpageurl,page):
        playurl = self.getPlayUrl(playpageurl)
        if playurl != "":
            try:
                self.player.play(playurl, caption=page)
            except:
                self.player.play(playurl)  
            
    def loading(self, stopLoading = False):
        if hasattr(self.player,'loadingAnimation'):
            self.player.loadingAnimation('main', stop=stopLoading)
            
    def getPlayUrl(self,pageurl):
        playurl = ""
        res = requests.get(pageurl)
        if res.status_code == 200:
            bs = bs4.BeautifulSoup(res.content.decode('UTF-8','ignore'),'html.parser')
            selector = bs.select('#main > div.player-block > div > div.player-box > div > script')
            if selector:
                scriptitem = selector[1]
                jsonstr = re.findall(r"var player_aaaa=(.+)",scriptitem.string)[0]
                playerjson = json.loads(jsonstr)
                encodeurl  = playerjson['url']
                playurl = urllib.parse.unquote(encodeurl)
        return playurl
            
    def searchMoive(self,wd):
        print("search:" + wd)
        medias = []
        li = []
        if len(wd) > 0:
            searchurl = self.dyxsurl +'/search-' + urllib.parse.quote(wd,encoding='utf-8') + '-------------/'
            res = requests.get(searchurl,verify=False)
            if res.status_code == 200:
                bs = bs4.BeautifulSoup(res.content.decode('UTF-8','ignore'),'html.parser')
                selector = bs.find_all('div', class_='module-items')
                for moduleitem in selector:
                    for item in moduleitem:
                        novideo = item.select('div.video-info > div.video-info-footer > div > i')
                        if len(novideo) > 0:
                            continue
                        try:
                            imageinfo = item.select('div.module-item-cover > a > img')[0]
                        except:
                            imageinfo = item.select('div.module-item-cover > div > img')[0]
                        imgurl = self.dyxsurl + imageinfo.get('data-src')
                        try:
                            nameinfo = item.select('div.module-item-titlebox > a')[0]
                            name = nameinfo.string
                        except:
                            nameinfo = item.select('div.video-info > div.video-info-header > h3 > a')[0]
                            name = nameinfo.string
                        detal = item.select('div.video-info > div.video-info-main > div:nth-child(3) > div')[0]
                        try:
                            dateinfo = item.select('div.video-info > div.video-info-header > div > a')[1]
                            date = dateinfo.string
                        except:
                            date = ""
                        url = self.dyxsurl + nameinfo.get('href')
                        mediainfo = {}
                        if name.find(wd) >= 0:
                            mediainfo["name"] = name
                            mediainfo["pic"] = imgurl
                            mediainfo["summary"] = detal.string
                            mediainfo["pub_date"] = date
                            mediainfo["url"] = url
                            t = GetMediaDetailThread(mediainfo,self.dyxsurl)
                            li.append(t)
                            t.start()
            for i in li:
                i.join()  
            allres = []
            for i in li:
                allres.append(i.get_result())
            for res in allres:
                if res:
                    for t in res[1]:
                        t.join()
            
            for res in allres:
                if res:
                    allmovies = []
                    resinfo = res[0]
                    for t in res[1]:
                        t.join()
                        playurl = t.get_result()
                        if playurl != None:
                           allmovies.append(playurl) 
                    if len(allmovies) > 0:
                        resinfo["urls"] = allmovies
                        medias.append(resinfo)
            return medias
           
    def onPlayerSearch(self, dispatchId, searchId, wd, limit):
        try:
            if self.dyxsurl == "":
                result = []
            else:
                result = self.searchMoive(wd)
            print(result)
            self.player.dispatchResult(dispatchId, searchId=searchId, wd=wd, result=result)
        except:
            self.player.dispatchResult(dispatchId, searchId=searchId, wd=wd, result=[])

def newPlugin(player:StellarPlayer.IStellarPlayer,*arg):
    plugin = dyxsplugin(player)
    return plugin

def destroyPlugin(plugin:StellarPlayer.IStellarPlayerPlugin):
    plugin.stop()