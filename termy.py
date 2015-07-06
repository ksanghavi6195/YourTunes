import tornado.ioloop
import tornado.web
import tornado.autoreload
import os, uuid
import json
import unicodedata
import requests
rooms = dict()

def getAvailableSongs(roomID):
    # Determine what songs are locally available in a room of varied users
    result = []
    resultSongs = []
    # A list of users from the dictionary describing rooms
    users = rooms[roomID]['users']
    for user in users:
        for song in trimUserSongs(user):
            if song['title'] not in resultSongs:
                result.append(song)
                resultSongs.append(song['title'])
    return result

def removeDuplicates(songs):
    # Removes duplicate songs available in a room
    result = set()
    for i in xrange(len(songs)):
        result = set(songs[i]['title']).union(result)
    return list(result)

def userSongs(path):
    # This function is slightly modified from our recursion course lecture notes
    # to list the files in a given directory. 
    # This function determines what songs are available to a 
    # specific user's music path
    if not os.path.isdir(path):
        # A ditionary is used to differentiate local files and youtube links
        pathDictionary = {"title":path, "type":"local"}
        return [pathDictionary]
    else:
        files = []
        for filename in os.listdir(path):
            # Limit available files to .mp3 files
            if filename[-3:] == 'mp3':
                files += userSongs(path + "/" + filename)
        return files

def trimUserSongs(user):
    # Modifies the list of available songs to remove the path prefix
    path = "./users/" + user + "/music/"
    files = userSongs(path)
    for i in xrange(len(files)):
        files[i]["title"] = files[i]["title"][len(path)+1:]
    return files

def getAvailablePlaylists(user):
    # Determines what playlists are available to the user
    results = []
    for playlist in trimPlaylists(user):
        results.append(playlist)
    return results

def trimPlaylists(user):
    # Removes the path prefix for each playlist
    path = "./users/" + user + "/playlists/"
    playlists = userPlaylists(path)
    for i in xrange(len(playlists)):
        playlists[i] = playlists[i][len(path)+1:]
    return playlists

def userPlaylists(path):
    # Recursively determines the playlist available. This function is similar
    # to listFiles(path) from the recursion course notes
    if not os.path.isdir(path):
        return [path]
    else:
        playlists = []
        for playlistName in os.listdir(path):
            playlists += userPlaylists(path + "/" + playlistName)
    return playlists

class HomeHandler(tornado.web.RequestHandler):
    # Handles a request to visit the homepage 
    def get(self):
        self.render("homepage.html", rooms = rooms)

class CreateRoomHandler(tornado.web.RequestHandler):
    # Creates a room in the global dictionary of all rooms available
    def get(self):
        # Parameters are passed in through the request from template.html
        roomID = self.get_argument("roomID").lower().strip()
        user = self.get_argument("user").lower().strip()
        # Only create a room if a username or roomID is entered
        if roomID != '' and user != '':
            global rooms
            # Set up a new user's directory for music files and playlists
            if os.path.exists("./users/%s/" % user) == False:
                os.makedirs("./users/%s/music" % user)
                os.makedirs("./users/%s/playlists" % user)
            # Set up a new room, which has many attributes defined and passed
            # through the global rooms dictionary
            if roomID not in rooms:
                # Add roomID to list of available rooms and initialize keys
                rooms[str(roomID)] = {"songs":[], "queue":[], "currSong":'', \
                'playlists':[], 'results':[], 'users':[user], 'ytSearches':[], \
                'host':user}
            else:
                if user not in rooms[str(roomID)]['users']:
                    rooms[str(roomID)]['users'].append(user)
        # Redirect the browswer to display a room
        self.redirect("/room/%s/%s/" % (roomID, user))

class InRoomHandler(tornado.web.RequestHandler):
    def get(self, roomID, user):
        # Render a room using an html template and dictionary of data for a room
        # This is code for what's currently happening in the room
        queue = rooms[roomID]['queue']
        # Directly link the value of currSong to the first item in queue
        currSong = queue[0] if len(queue) != 0 else ''
        rooms[roomID]["currSong"] = currSong
        rooms[str(roomID)]['songs'] = getAvailableSongs(roomID)
        rooms[str(roomID)]['playlists'] = getAvailablePlaylists(user)
        # Load data to an html file to display in the browser
        self.render("template.html", room = roomID,\
            params = [rooms[roomID]], user=user)

class AddHandler(tornado.web.RequestHandler):
    #  Handles a request to add a song to the queue from available local songs
    def get(self, roomID, user):
        # self.get_argument extracts variable values from the request made in 
        # template.html
        addedSongType = self.get_argument('type')
        addedSongTitle = self.get_argument('file')
        availableSongNames=[song['title'] for song in getAvailableSongs(roomID)]
        if addedSongTitle in availableSongNames:
            songData = {'title':addedSongTitle, 'type':addedSongType}
            rooms[roomID]["queue"].append(songData)
        rooms[roomID]['results'] = []
        # Redirect the browswer to display a room
        self.redirect("/room/%s/%s/" % (roomID, user))

class SearchFilesHandler(tornado.web.RequestHandler):
    # Handles a request to search for the files available to the current user
    def post(self, roomID, user):
        searchFor = self.get_argument('searchFor').lower()
        # use s.lower() to remove case-sensitivity in searching
        if searchFor.strip() != '':
            searchResults = []
            # For each song in the songs available in the current room ...
            for song in rooms[roomID]['songs']:
                songTitle = song['title'].lower().strip()
                # If our search matches an available song ...
                if searchFor in song['title'].lower().strip():
                    searchResults.append(song)
            rooms[roomID]['results'] = searchResults
        # Redirect the browswer to display a room
        self.redirect("/room/%s/%s/" % (roomID, user))

class SavePlaylistHandler(tornado.web.RequestHandler):
    # Handles a request to save the current queue as a playlist
    def get(self, roomID, user):
        playlistName = self.get_argument('savePlaylist')
        if playlistName.strip() != '':
            playlistName = playlistName.strip()
            playlistName += ".txt"
            playlistQueue = rooms[roomID]['queue']
            self.writePlaylist(playlistName, playlistQueue, user)
            rooms[roomID]['playlists'] += playlistName
        # Redirect the browswer to display a room
        self.redirect("/room/%s/%s/" % (roomID, user))

    def writePlaylist(self, filename, contents, user, mode='wt'):
        # This function is adapted from the File I/O lecture notes
        # json is used to dump data since a dictionary is written to the .txt
        # file, which needs to be later extracted. 
        filename = "./users/%s/playlists/" % (user) + filename
        with open(filename, mode) as outfile:
            json.dump(contents, outfile)

class LoadPlaylistHandler(tornado.web.RequestHandler):
    # Loads a saved playlist from the current user's directory
    def get(self, roomID, user):
        # These parameters are passed in from the browser's request to load
        playlistName = self.get_argument('playlistName')
        playlistData = self.readPlaylist(playlistName, user)
        playlistData = self.decodeData(playlistData)
        rooms[roomID]['queue'] = playlistData
        # Redirect the browswer to display a room
        self.redirect("/room/%s/%s/" % (roomID, user))

    def readPlaylist(self, filename, user, mode='rt'):
        # Reads the data saved in the text file. Data must be decoded from 
        # a string to a dictionary, so json is used.
        filename = "./users/%s/playlists/" % (user) + filename
        with open(filename, mode) as fin:
            return fin.read()

    def decodeData(self, data):
        # Decode using json
        return json.loads(data)

class UploadHandler(tornado.web.RequestHandler,):
    # Handles a request to upload a file to a user's directory
    def post(self, roomID, user):
        __UPLOADS__ = "users/music/"
        saveForUser = 'users/%s/music/' % user
        fileinfo = self.request.files['filearg'][0]
        fname = fileinfo['filename']
        fileinfo['filename'] = fileinfo['filename'].encode("UTF-8")
        extn = os.path.splitext(fname)[1]
        extn = os.path.splitext(fname)[1]
        # cname = str(uuid.uuid4()) + extn
        cname = str(fileinfo['filename'])
        fh = open(__UPLOADS__ + cname, 'wb')
        fh.write(fileinfo['body'])
        fh = open(saveForUser + cname, 'wb')
        fh.write(fileinfo['body'])
        ## Add some var to indiciate in html to display "Uploaded"
        # self.finish(cname + " is uploaded!! Check %s folder" %__UPLOADS__)
        print fileinfo, 'uploaded'
        # Redirect the browswer to display a room
        self.redirect("/room/%s/%s/" % (roomID, user))

class SkipHandler(tornado.web.RequestHandler):
    # Allows the room host to skip the song which is currently playing
    def get(self, roomID, user):
        queue = rooms[roomID]["queue"] 
        if len(queue) > 0:
            queue.pop(0)
        # Redirect the browswer to display a room
        self.redirect("/room/%s/%s/" % (roomID, user))

class YouTubeSearchHandler(tornado.web.RequestHandler):
    # Handles a request to search for a youtube video using Youtube's API
    # By parsing through the json data on YouTube, search results are displayed
    def get(self, roomID, user):
        search = self.get_argument('video')
        # Search parameter is passed through the browser's request
        if search.strip() != "":
            search = search.strip()
            ytQuery = {"v":2, "alt":"json", "prettyprint":"true", "q":search}
            # Youtubes API, which returns json data with search results
            r = requests.get("https://gdata.youtube.com/feeds/api/videos", \
                params = ytQuery, stream=True)
            asciiText =\
                unicodedata.normalize("NFKD", r.text).encode("ascii", "ignore")
            # Store the search results in the data of the current room
            ytSearches = rooms[roomID]['ytSearches']
            # Show the top six results
            for i in xrange(6):
                # Extracting the link, title, and thumbnail from the json data
                link = json.loads(asciiText)["feed"]["entry"][i]["content"]["src"]
                title = json.loads(asciiText)["feed"]["entry"][i]["title"]["$t"]
                thumbnail = json.loads(asciiText)['feed']['entry'][i]['media$group']['media$thumbnail'][1]['url']
                ytSearches.append({'link':link, 'title':title, 'thumbnail':thumbnail})
        # Redirect the browswer to display a room
        self.redirect("/room/%s/%s/" % (roomID, user))

class YouTubeAddHandler(tornado.web.RequestHandler):
    # Handles a request to add a YouTube file to a room's queue
    def get(self, roomID, user):
        # Variables are passed through the browser's request
        link = self.get_argument('link')
        title = self.get_argument('title')
        stringLink = unicodedata.normalize("NFKD", link).encode("ascii", "ignore")
        # A dictionary is used so that there can be a distinction between 
        # youtube links and local files
        song = {"link": stringLink, "title":title, "type":"youtube"}
        rooms[roomID]["queue"].append(song)
        rooms[roomID]['ytSearches'] = []
        # Redirect the browswer to display a room
        self.redirect("/room/%s/%s/" % (roomID, user))

class HelpScreenHandler(tornado.web.RequestHandler):
    # Handle a request to view the help screen from a room
    def get(self, roomID, user):
        self.render("help.html", roomID=roomID, user=user, inRoom=True)

class HelpOUTHandler(tornado.web.RequestHandler):
    # Handle a request to view the help screen from the home screen
    def get(self):
        self.render('help.html', roomID=None, user=None, inRoom=False)

def run():
    # The following handlers indicate which functions from above 
    # should be called for certain requests from the browser
    handlers = [
      (r'/', HomeHandler),
      (r'/room/([a-z]+)/([a-z]+)/add', AddHandler),
      (r'/room/([a-z]+)/([a-z]+)/skip', SkipHandler),
      (r'/room/([a-z]+)/([a-z]+)/ytSearch', YouTubeSearchHandler),
      (r'/room/([a-z]+)/([a-z]+)/ytAdd', YouTubeAddHandler),
      (r'/room/([a-z]+)/([a-z]+)/upload', UploadHandler),
      (r'/room/([a-z]+)/([a-z]+)/saveplaylist', SavePlaylistHandler),
      (r'/room/([a-z]+)/([a-z]+)/loadplaylist', LoadPlaylistHandler),
      (r'/room/([a-z]+)/([a-z]+)/searchLocal', SearchFilesHandler),
      (r'/room/([a-z]+)/([a-z]+)/', InRoomHandler),
      (r'/room/([a-z]+)/([a-z]+)/help', HelpScreenHandler),
      (r'/help', HelpOUTHandler),
      (r'/create', CreateRoomHandler),
      (r'/assets/(.*)', tornado.web.StaticFileHandler, {'path': ".\\assets"}),
      (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': '.\users\music'})
      # (r'/(.*)', tornado.web.StaticFileHandler, {'path': './music'})
    ]
    # Tornado is a module which sets up a server using python
    # The lines below set up the server on port 9000. Any unused port can be
    # used for this application.
    application = tornado.web.Application(handlers)
    application.listen(9000)
    tornado.autoreload.start()
    tornado.ioloop.IOLoop.instance().start()

run()

## Features to Add ##
# Twilio - Text in song Request
# allow users to vote on songs
# support option to stream music (soundcloud)
# chatroom
# Search currently contains; needs to be prefix search
 
