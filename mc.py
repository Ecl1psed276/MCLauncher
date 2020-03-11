'''
Minecraft Launcher
by Ecl1psed
idk what else to put up here lol
'''

__version = '1.0'

import getpass, json, os, platform, random, re, urllib.request, zipfile

DEFHEADER = {'Content-Type':'application/json'}

BYTES = 131072

versionJsonURL = 'https://launchermeta.mojang.com/mc/game/version_manifest.json'

class LaunchError(Exception):
    pass

def getOsName():
    plat = platform.system()
    if plat == 'Darwin':
        return 'osx'
    else:
        return plat.lower()

OS_NAME = getOsName()
OS_VER = platform.release()
OS_ARCH = 'x64' if platform.machine().endswith('64') else 'x86'

def checkRules(rules):
    userdata = jsonLoad('userdata.json')
    allow = 'disallow'
    for rule in rules:
        match = True
        if 'os' in rule:
            if 'name' in rule['os'] and OS_NAME != rule['os']['name']:
                match = False
            if 'arch' in rule['os'] and OS_ARCH != rule['os']['arch']:
                match = False
            if 'version' in rule['os']:
                p = re.compile(rule['os']['version'])
                if not re.match(p, OS_VER):
                    match = False
        if 'features' in rule:
            if 'has_custom_resolution' in rule['features']:
                match = False
            print(rule['features'].keys(), type(userdata['isDemoUser']))
            if 'is_demo_user' in rule['features'] and not userdata['isDemoUser']:
                match = False
        if match:
            allow = rule['action']
    return allow == 'allow'

def createDir(name):
    if not os.path.isdir(name):
        os.makedirs(name)

def downloadFile(url, filename, overwrite=False):
    res = not os.path.isfile(filename)
    if res or overwrite:
        a = urllib.request.urlopen(url)
        dest = open(str(filename), 'wb')
        data = True #this could be anything that is not False, 0, [], etc.
        while data:
            data = a.read(BYTES)
            dest.write(data)
        
        dest.close()
    return res

def copyFile(oldfile, filename, overwrite=False):
    res = not os.path.isfile(filename)
    if res or overwrite:
        a = open(oldfile, 'rb')
        createDir(os.path.dirname(filename))
        dest = open(str(filename), 'wb')
        data = True
        while data:
            data = a.read(BYTES)
            dest.write(data)
        
        dest.close()
    return res

def downloadResources(version):
    createDir('assets/indexes')
    createDir('assets/objects')
    jsondata = json.loads(open('versions/%s/%s.json'%(version,version)).read())
    #assetsName = jsondata.get('assets', 'legacy')
    #assetIndexFile = 'assets/indexes/%s.json' % assetsName
    #assetIndexLink = 'https://s3.amazonaws.com/Minecraft.Download/indexes/%s.json' % assetsName
    assetIndexUrl = jsondata['assetIndex']['url']
    assetIndexFile = 'assets/indexes/%s.json' % jsondata['assetIndex']['id']
    downloadFile(assetIndexUrl, assetIndexFile, overwrite=True)
    prettyJson(assetIndexFile)

    f = open(assetIndexFile)
    assetsData = json.loads(f.read())
    f.close()

    legacy = jsondata['assetIndex']['id'] == 'pre-1.6'
    if legacy:
        baseDir = 'resources'
    else:
        baseDir = 'assets'
    
    length = len(assetsData['objects'])
    current = 0
    
    skipNext = False
    for key, value in assetsData['objects'].items():
        current += 1
        hash = value['hash']
        pref = hash[:2]
        createDir(baseDir+'/objects/%s'%pref)
        if not os.path.isfile(baseDir+'/objects/%s/%s'%(pref, hash)):
            yield hash, current, length
            skipNext = True
            downloadFile('http://resources.download.minecraft.net/%s/%s'%(pref, hash), baseDir+'/objects/%s/%s'%(pref, hash))
    
    if legacy:
        print('Preparing legacy resources... (should only take a few seconds)')
        unpackLegacyResources()

def unpackLegacyResources():
    assetsData = jsonLoad('assets/indexes/pre-1.6.json')
    for subPath in assetsData['objects']:
        obj = assetsData['objects'][subPath]
        path = 'resources/' + subPath
        fromPath = 'resources/objects/%s/%s' % (obj['hash'][:2], obj['hash'])
        copyFile(fromPath, path)

def unzipNatives(natives):
    for nat in natives:
        try:
            zipf = zipfile.ZipFile(nat)
            for name in zipf.namelist():
                if not (name.startswith('META-INF') or name.startswith('.') or os.path.isfile('natives/%s'%name)):
                    zipf.versionTypect(name, 'natives')
            zipf.close()
        except zipfile.BadZipfile:
            print('Could not download the file!')
            try:
                os.remove(nat)
            except:
                pass

def hasDownloadedVersion(version):
    try:
        open('versions\%s\%s.json'%(version, version))
    except:
        return False
    else:
        return True

def versionExists(version): #never called if INTERNET is false
    if INTERNET:
        a = json.loads(open('versions/versions.json').read())
        for b in a['versions']:
            if b['id'] == version:
                return True
        return False

def UUID(username):
    req = urllib.request.Request('https://api.mojang.com/profiles/minecraft', json.dumps([username]).encode('utf-8'), DEFHEADER)
    resp = json.loads(urllib.request.urlopen(req).read())
    try:
        return [resp[x]['id'] for x in range(len(resp))]
    except IndexError:
        raise LaunchError('Invalid username')

def getUserType(username):
    url = 'https://api.mojang.com/users/profiles/minecraft/%s'%username
    data = urllib.request.urlopen(url).read()
    #print(data)
    data = json.loads(data)
    if 'legacy' in data and data['legacy']:
        return 'legacy'
    return 'mojang'

def downloadVersionJson(version):
    jsondata = json.loads(open('versions/versions.json').read())
    vlist = jsondata['versions']
    versionData = next(filter(lambda x: x['id'] == version, vlist))
    downloadFile(versionData['url'], 'versions/%s/%s.json'%(version,version))
    prettyJson('versions/%s/%s.json'%(version,version))

def downloadLibraries(version):
    createDir('libraries')
    createDir('versions/%s'%version)
    print('====== Downloading Libraries ======')
    #downloadFile('http://s3.amazonaws.com/Minecraft.Download/versions/%s/%s.json'%(version,version), 'versions/%s/%s.json'%(version,version))
    downloadVersionJson(version)
    jsondata = json.loads(open('versions/%s/%s.json'%(version,version)).read()) #to find which libraries to download
    libraries = jsondata['libraries']
    classpath = []
    nativespath = []
    numlibs = len(libraries)
    currentlibnum = 0
    for lib in libraries:
        currentlibnum += 1
        '''allow = 'allow'
        if 'rules' in lib:
            allow = 'disallow'
            for rule in lib['rules']:
                if not ('os' in rule and rule['os']['name'] != 'windows'):
                    allow = rule['action']
        if allow == 'disallow':
            #print('  ! Skipped library %s of %s (%s)'%(currentlibnum, numlibs, lib['name']))
            continue'''
        if 'rules' in lib and not checkRules(lib['rules']):
            #print('  ! Skipped library %s of %s (%s)'%(currentlibnum, numlibs, lib['name']))
            continue
        
        if 'artifact' in lib['downloads']:
            url = lib['downloads']['artifact']['url']
            dest = 'libraries/'+lib['downloads']['artifact']['path']
            classpath.append(dest)
            createDir(os.path.dirname(dest))
            res = downloadFile(url, dest)
            if res:
                print('  - Downloaded library %s of %s (%s)'%(currentlibnum, numlibs, lib['name']))
            
        if 'natives' in lib and 'windows' in lib['natives']:
            n = lib['natives']['windows'] #should be natives-windows
            n = n.replace('${arch}', OS_ARCH)
            dest = 'libraries/'+lib['downloads']['classifiers'][n]['path']
            nativespath.append(dest)
            url = lib['downloads']['classifiers'][n]['url']
            createDir(os.path.dirname(dest))
            res = downloadFile(url, dest)
            if res:
                print('  - Downloaded library %s of %s (%s)'%(currentlibnum, numlibs, lib['name']))
            z = zipfile.ZipFile(dest)
            z.extractall('natives')

    #if not os.path.exists('versions/%s/%s.jar'%(version,version)):
    #    downloadFile('http://s3.amazonaws.com/Minecraft.Download/versions/%s/%s.jar'%(version,version),'versions/%s/%s.jar'%(version,version))
    res = downloadFile(jsondata['downloads']['client']['url'],'versions/%s/%s.jar'%(version,version))
    if res:
        print('  - Downloaded version jar')

    return classpath, nativespath

def getLibraries(version):
    jsondata = json.loads(open('versions/%s/%s.json'%(version,version)).read())
    libraries = jsondata['libraries']
    classpath = []
    #nativespath = []
    for lib in libraries:
        package, name, version = lib['name'].split(':')
        package = package.split('.')
        dest = 'libraries/%s/%s/%s/%s-%s.jar'%('/'.join(package),name,version,name,version)
        if 'natives' not in lib:
            classpath.append(dest)
    return classpath

def getVersionType(version):
    allVers = jsonLoad('versions/versions.json')['versions']
    for ver in allVers:
        #print(version, ver['id'], type(version), type(ver['id']))
        if ver['id'] == version:
            #input()
            return ver['type']
    return 'null'

def launchMC(version):
    userdata = jsonLoad('userdata.json')
    classpath = getLibraries(version)
    classpath.append('versions/%s/%s.jar'%(version,version))
    classpath = ';'.join(classpath)
    
    jsondata = json.loads(open('versions/%s/%s.json'%(version,version)).read())
    mainClass = jsondata['mainClass']

    if 'minecraftArguments' in jsondata: # Before 1.13
        args = jsondata['minecraftArguments']
        args = args.replace('${auth_player_name}', userdata['username2'])
        args = args.replace('${version_name}', version)
        args = args.replace('${game_directory}', '"'+os.getcwd()+'"')
        args = args.replace('${game_assets}', 'assets') # only in older versions of MC
        args = args.replace('${assets_root}', 'assets')
        args = args.replace('${auth_uuid}', userdata['uuid'])
        args = args.replace('${auth_access_token}', userdata['accessToken'])
        args = args.replace('${auth_session}', userdata['accessToken']) #only in older versions
        args = args.replace('${assets_index_name}', jsondata['assets'])
        args = args.replace('${user_properties}', '{}')
        args = args.replace('${user_type}', userdata['userType'])
        args = args.replace('${version_type}', getVersionType(version))

        extraArgs = '-XX:HeapDumpPath=MojangTricksIntelDriversForPerformance_javaw.exe_minecraft.exe.heapdump -Xmx1G'
        cmd = 'java %s -Djava.library.path=natives -cp %s %s %s' % (extraArgs, classpath, mainClass, args)
        
            
    else: # 1.13 or later
        argsList = []
        for arg in jsondata['arguments']['jvm'] + ['${main_class}'] + jsondata['arguments']['game']:
            if type(arg) is str:
                argsList.append(arg)
            else: # type is dict
                if 'rules' not in arg or checkRules(arg['rules']):
                    if type(arg['value']) is list:
                        argsList += arg['value']
                    else: # type is str
                        argsList.append(arg['value'])
        args = ' '.join(argsList)
        args = args.replace('${auth_player_name}', userdata['username2'])
        args = args.replace('${version_name}', version)
        args = args.replace('${game_directory}', '"'+os.getcwd()+'"')
        args = args.replace('${assets_root}', 'assets')
        args = args.replace('${assets_index_name}', jsondata['assets'])
        args = args.replace('${auth_uuid}', userdata['uuid'])
        args = args.replace('${auth_access_token}', userdata['accessToken'])
        args = args.replace('${user_type}', userdata['userType'])
        args = args.replace('${version_type}', getVersionType(version))
        args = args.replace('${natives_directory}', 'natives')
        args = args.replace('${launcher_name}', 'Ecl1_Python_Launcher')
        args = args.replace('${launcher_version}', __version)
        args = args.replace('${classpath}', classpath)
        args = args.replace('${main_class}', mainClass)
        
        cmd = 'java %s' % args

    #print(cmd)
    if '${' in cmd:
        print('ERROR: There are missing arguments!!!')
        input('If you see this, tell Ecl1 which version of MC you tried to run')
    os.system(cmd)

def testVersion(version):
    a = json.loads(open('versions/versions.json').read())
    for b in a['versions']:
        if b['id'] == version:
            return True, b['type']
    return False, None

def getRandomToken():
    return str(hex(random.getrandbits(128)))[2:]

def authenticate(username, password):
    clientToken = getRandomToken()
    data = {
        "agent": {
            "name": "Minecraft",
            "version": 2
        },
        "username": username,
        "password": password,
        "clientToken": clientToken,
        "requestUser": True
    }
    r = urllib.request.Request('https://authserver.mojang.com/authenticate', json.dumps(data).encode('utf-8'), DEFHEADER)
    try:
        resp = json.loads(urllib.request.urlopen(r).read())
    except urllib.error.HTTPError:
        return None, None, None, None, None, None
    '''if 'error' in resp and resp['error'] == 'ForbiddenOperationException':
        print('------------------------------------')
        print('ERROR: Invalid username or password!')
        print('------------------------------------')
        print(resp)
        print('------------------------------------')
        raise LaunchError'''
    accessToken = resp['accessToken']
    userType = getUserType(resp['selectedProfile']['name'])
    #print(json.dumps(resp, sort_keys=True, indent=4))
    if 'paid' in resp['selectedProfile']:
        demo = not resp['selectedProfile']
    else:
        demo = False
    return resp['selectedProfile']['id'], clientToken, accessToken, \
            resp['selectedProfile']['name'], userType, False

def refreshToken(clientToken, oldToken):
    data = {
        "accessToken": oldToken,
        "clientToken": clientToken,
    }
    r = urllib.request.Request('https://authserver.mojang.com/refresh', json.dumps(data).encode('utf-8'), DEFHEADER)
    resp = json.loads(urllib.request.urlopen(r).read())
    try:
        newToken = resp['accessToken']
        return clientToken, newToken
    except:
        return None, None

def testToken(clientToken, accessToken):
    data = {'clientToken':clientToken, 'accessToken':accessToken}
    r = urllib.request.Request('https://authserver.mojang.com/validate', json.dumps(data).encode('utf-8'), DEFHEADER)
    try:
        resp = urllib.request.urlopen(r).read()
    except urllib.error.HTTPError:
        return False
    if len(resp):
        raise Exception
    return True

def signOut(clientToken, accessToken):
    data = {'clientToken':clientToken, 'accessToken':accessToken}
    r = urllib.request.Request('https://authserver.mojang.com/invalidate', json.dumps(data).encode('utf-8'), DEFHEADER)
    try:
        resp = urllib.request.urlopen(r).read()
    except urllib.error.HTTPError:
        return False
    if len(resp):
        raise Exception
    return True

'''
TODO:

- Catch more types of errors when logging in
- Check for demo user
- Make options! Installation directory, console output?
- Before downloading, ask user for install dir
'''
def updateUserData(chngDic):
    if os.path.exists('userdata.json'):
        dic = jsonLoad('userdata.json')
    else:
        dic = {}
    for thing in chngDic:
        dic[thing] = chngDic[thing]
    with open('userdata.json','w') as f:
        json.dump(dic, f)

def jsonLoad(filename):
    with open(filename) as f:
        return json.load(f)

def prettyJson(filename):
    d = jsonLoad(filename)
    t = json.dumps(d, sort_keys=True, indent=4)
    with open(filename,'w') as f:
        f.write(t)

def main():
    global INTERNET
    createDir('versions')
    try:
        downloadFile('https://launchermeta.mojang.com/mc/game/version_manifest.json', 'versions/versions.json')
        INTERNET = True
        print('Found internet')
    except:
        INTERNET = False
        print('NO INTERNET!')
    print()
    
    print('======== Minecraft Launcher - by Ecl1psed ========\n')
    skipLogin = False
    if os.path.isfile('userdata.json'):
        print('Refreshing...')
        userData = jsonLoad('userdata.json')
        result = testToken(userData['clientToken'], userData['accessToken'])
        if result:
            clientToken, accessToken = refreshToken(userData['clientToken'], userData['accessToken'])
            if accessToken is not None:
                skipLogin = True
                username2 = userData['username2']
                updateUserData({'accessToken':accessToken})
            else:
                print('Could not refresh access token!')
        else:
            print('Saved access token is no longer valid!')
    
    if not skipLogin:
        while True:
            username = input('Username: ')
            password = getpass.getpass('Password: ')
            print('\nLogging in...')
            uuid, clientToken, accessToken, username2, userType, isDemo = \
                  authenticate(username, password)
            del password
            if accessToken:
                break
            print('Oops, could not log in! Incorrect username/pasword?\n')
        updateUserData({'username':username, 'username2':username2,
                        'clientToken':clientToken, 'accessToken':accessToken,
                        'uuid':uuid, 'userType':userType,
                        'installDir':os.getcwd(), 'isDemoUser':isDemo})
    print('Welcome, %s!\n' % username2)

    while True:
        print('1 - Play Minecraft')
        print('2 - List Releases')
        print('3 - List Releases and Snapshots')
        print('4 - Settings')
        print('5 - Log Out')
        print('6 - Quit')
        task = input()
        print()
        if task == '1':
            userData = jsonLoad('userdata.json')
            versionInput = True
            if 'version' in userData:
                print('Would you like to play Minecraft %s? (y/n)'%(userData['version']))
                result = input()
                if result.lower() == 'y':
                    version = userData['version']
                    versionInput = False
            
            if versionInput:
                version = input('Select version to play: ')
                result, versionType = testVersion(version)
                if not result:
                    print('ERROR: The specified version does not exist!\n')
                    continue
                if versionType != 'release':
                    print('WARNING: The selected version is of type "%s"!'%versionType)
                    print('Are you sure you want to continue? (y/n)')
                    if input().lower() != 'y':
                        print()
                        continue
                updateUserData({'version': version})
                
            createDir('assets')
            createDir('libraries')
            createDir('natives')
            createDir('versions')
            createDir('versions/'+version)

            classpath, nativespath = downloadLibraries(version)
            #print('CLASSPATH: ',classpath)
            #print('NATIVESPATH: ',nativespath)
            unzipNatives(nativespath)

            print('====== Downloading Resources ======')
            for h, num, length in downloadResources(version):
                print('  - Downloading object %s of %s'%(num, length))

            print('======= Launching Minecraft =======')
            classpath = getLibraries(version)
            launchMC(version)
            
        elif task in ('2','3'):
            versionInfo = json.loads(open('versions/versions.json').read())
            latest = versionInfo['latest']
            print('Latest:')
            print('Release: %s'%latest['release'])
            if task == 3:
                print('Snapshot: %s'%latest['snapshot'])
            print('')
            for v in versionInfo['versions']:
                if task == '3' or (task == '2' and v['type'] == 'release'):
                    print(v['id'])
            print()

        elif task == '4':
            print('No settings just yet... ')
        
        elif task in ('5','6'):
            if task == '4':
                signOut(clientToken, accessToken)
                os.remove('userdata.json')
                print('Successfully logged out.\n')
                input('Press enter to close the launcher...')
            break
        
        else:
            print('Type a number from 1 to 5\n')
        

#l = 'versions/1.15.2/1.15.2.json'
#d = json.load(open(l))
#print(json.dumps(d, sort_keys=True, indent=4))

if __name__ == '__main__':
    main()
